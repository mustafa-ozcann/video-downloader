#!/usr/bin/env python3
"""Video İndirici — yerel web sürümü.

Mac'te (veya Windows'ta) küçük bir web sunucusu çalıştırır; tarayıcıdan kullanılır.
Video sunucuda yt-dlp + ffmpeg ile indirilir/birleştirilir, sonra tarayıcıya dosya olarak verilir.

    venv/bin/python3 web_app.py          # sadece bu bilgisayar: http://127.0.0.1:8765
    venv/bin/python3 web_app.py --lan    # aynı Wi-Fi'deki telefon/tablet de erişebilir
"""
import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
import json
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory, abort

# Kalite presetleri, yt-dlp çağrısı ve PATH düzeltmesi masaüstü sürümüyle ortak
from youtube_downloader import (
    PRESETS, UPDATE_STAMP, UPDATE_INTERVAL_SEC, _ytdlp_cmd, _augment_path_for_common_tools,
    build_download_cmd, ensure_h264,
)

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
JOBS_ROOT = Path(tempfile.gettempdir()) / "video_downloader_web"
JOB_TTL_SEC = 2 * 3600

HEIGHT_MAP = {"4K Ultra HD": 2160, "1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
PROGRESS_RE = re.compile(
    r'\[download\]\s+([\d.]+)%(?:\s+of\s+~?\s*(\S+))?(?:\s+at\s+(\S+))?(?:\s+ETA\s+(\S+))?')

app = Flask(__name__, static_folder=None)
jobs = {}
jobs_lock = threading.Lock()
update_state = {"running": False, "version": None, "error": None}


# ── Yardımcılar ──────────────────────────────────────────────────────────────
def valid_url(url):
    # "-" ile başlayan bir değer yt-dlp'ye seçenek olarak geçebilir (örn. --exec) → sadece http(s)
    return bool(re.match(r"^https?://\S+$", url or "")) and len(url) < 2048


def error_hint(msg):
    low = msg.lower()
    if "403" in low or "forbidden" in low or "sign in to confirm" in low or "nsig" in low:
        start_update(force=True)
        return "yt-dlp eski olabilir — şu an güncelleniyor, bir dakika sonra tekrar deneyin."
    if "ffmpeg" in low:
        return "ffmpeg gerekli: brew install ffmpeg"
    if "unsupported url" in low:
        return "Bu site veya link desteklenmiyor olabilir."
    if "private" in low or "unavailable" in low:
        return "Video gizli, silinmiş veya bölgenizde kapalı olabilir."
    return None


def clean_error(text):
    lines = [l for l in (text or "").strip().splitlines()
             if l.strip() and "older than 90 days" not in l]
    errs = [l for l in lines if l.startswith("ERROR")] or lines[-1:]
    return (errs[-1] if errs else "Bilinmeyen hata").removeprefix("ERROR: ")[:400]


def available_presets(info):
    heights, has_audio = set(), False
    for f in info.get("formats") or []:
        if f.get("height") and f.get("vcodec", "none") != "none":
            heights.add(int(f["height"]))
        if f.get("acodec", "none") != "none":
            has_audio = True
    max_h = max(heights) if heights else 0
    out = []
    for i, (label, _fmt, audio_only, desc) in enumerate(PRESETS):
        if audio_only:
            ok = has_audio or not info.get("formats")
        elif label == "En iyi kalite":
            ok = bool(heights) or not info.get("formats")
        else:
            ok = max_h >= HEIGHT_MAP.get(label, 10**9)
        if ok:
            out.append({"id": i, "label": label, "desc": desc, "audio": audio_only})
    return out, max_h


def best_thumbnail(info):
    thumbs = [t for t in info.get("thumbnails") or [] if t.get("url")]
    if thumbs:
        return max(thumbs, key=lambda t: (t.get("width") or 0) * (t.get("height") or 0))["url"]
    return info.get("thumbnail")


# ── yt-dlp otomatik güncelleme (masaüstü sürümüyle aynı damga dosyası) ───────
def start_update(force=False):
    if update_state["running"] or _ytdlp_cmd() == ["yt-dlp"]:
        return
    if not force:
        try:
            if time.time() - UPDATE_STAMP.stat().st_mtime < UPDATE_INTERVAL_SEC:
                return
        except OSError:
            pass
    update_state["running"] = True
    threading.Thread(target=_update_worker, daemon=True).start()


def _update_worker():
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-U",
             "--disable-pip-version-check", "yt-dlp[default]"],
            capture_output=True, text=True, timeout=300)
        if r.returncode == 0:
            UPDATE_STAMP.touch()
            update_state["error"] = None
        else:
            update_state["error"] = clean_error(r.stderr or r.stdout)
        update_state["version"] = subprocess.run(
            _ytdlp_cmd() + ["--version"], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception as e:
        update_state["error"] = str(e)
    finally:
        update_state["running"] = False


# ── İndirme işleri ───────────────────────────────────────────────────────────
def cleanup_old_jobs():
    now = time.time()
    with jobs_lock:
        for jid in [j for j, v in jobs.items()
                    if v["status"] != "running" and now - v["created"] > JOB_TTL_SEC]:
            shutil.rmtree(jobs[jid]["dir"], ignore_errors=True)
            del jobs[jid]


def run_job(job):
    _label, fmt, audio_only, _desc = PRESETS[job["preset"]]
    h264 = job.get("h264") and not audio_only
    path_file = job["dir"] + ".path" if h264 else None
    cmd = build_download_cmd(job["url"], fmt, audio_only,
                             os.path.join(job["dir"], "%(title).150B.%(ext)s"),
                             h264=h264, path_file=path_file)

    errors = []
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        job["proc"] = proc
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            m = PROGRESS_RE.search(line)
            if m:
                job["percent"] = float(m.group(1))
                job["total"] = m.group(2) or job["total"]
                job["speed"] = m.group(3) or ""
                job["eta"] = "" if m.group(4) in (None, "Unknown") else m.group(4)
                continue
            if line.startswith("ERROR"):
                errors.append(line)
            elif line.startswith("[Merger]") or line.startswith("[ExtractAudio]"):
                job["stage"] = "Birleştiriliyor…" if "Merger" in line else "MP3'e dönüştürülüyor…"
            elif line.startswith("[download] Destination"):
                job["stage"] = "İndiriliyor…"
        proc.wait()

        if not job["cancelled"] and proc.returncode == 0 and h264:
            files = [p for p in Path(job["dir"]).iterdir()
                     if p.is_file() and not p.name.endswith((".part", ".ytdl"))]
            try:
                lines = [l.strip() for l in Path(path_file).read_text(encoding="utf-8").splitlines() if l.strip()]
            except OSError:
                lines = []
            src = Path(lines[-1]) if lines and Path(lines[-1]).exists() else (
                max(files, key=lambda p: p.stat().st_size) if files else None)
            if src:
                def prog(pct):
                    job.update(percent=pct, converting=True, stage="H.264'e dönüştürülüyor…",
                               total="", speed="", eta="")
                ensure_h264(src, on_progress=prog, on_proc=lambda p: job.__setitem__("proc", p),
                            is_cancelled=lambda: job["cancelled"])
                job["converting"] = False

        if job["cancelled"]:
            job["status"] = "cancelled"
        elif proc.returncode == 0:
            files = [p for p in Path(job["dir"]).iterdir()
                     if p.is_file() and not p.name.endswith((".part", ".ytdl"))]
            if not files:
                raise RuntimeError("İndirilen dosya bulunamadı.")
            job["file"] = str(max(files, key=lambda p: p.stat().st_size))
            job["percent"] = 100.0
            job["status"] = "done"
        else:
            msg = clean_error("\n".join(errors))
            job.update(status="error", error=msg, hint=error_hint(msg))
    except Exception as e:
        job.update(status="error", error=str(e), hint=None)
    finally:
        job["proc"] = None
        if path_file:
            Path(path_file).unlink(missing_ok=True)


def public_job(job):
    keys = ("status", "percent", "total", "speed", "eta", "stage", "error", "hint", "title", "converting")
    d = {k: job.get(k) for k in keys}
    d["filename"] = Path(job["file"]).name if job.get("file") else None
    return d


# ── HTTP uç noktaları ────────────────────────────────────────────────────────
@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/api/status")
def status():
    tools = {t: bool(shutil.which(t)) for t in ("ffmpeg", "deno")}
    if not tools["deno"]:
        tools["deno"] = bool(shutil.which("node") or shutil.which("bun"))
    return jsonify(tools=tools, updating=update_state["running"],
                   version=update_state["version"], update_error=update_state["error"])


@app.post("/api/info")
def info():
    url = (request.get_json(silent=True) or {}).get("url", "").strip()
    if not valid_url(url):
        return jsonify(error="Geçerli bir video adresi girin (http:// veya https:// ile başlamalı)."), 400
    try:
        r = subprocess.run(
            _ytdlp_cmd() + ["--no-check-certificate", "--no-update", "-j", "--no-playlist", "--", url],
            capture_output=True, text=True, timeout=90, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return jsonify(error="Bağlantı zaman aşımına uğradı — ağı kontrol edin."), 504
    if r.returncode != 0:
        msg = clean_error(r.stderr)
        return jsonify(error=msg, hint=error_hint(msg)), 422
    try:
        data = json.loads(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        return jsonify(error="Video bilgisi okunamadı."), 422
    presets, max_h = available_presets(data)
    return jsonify(
        title=data.get("title") or "",
        uploader=data.get("uploader") or data.get("channel") or "",
        duration=data.get("duration"),
        views=data.get("view_count"),
        thumbnail=best_thumbnail(data),
        site=data.get("extractor_key") or "",
        max_height=max_h,
        presets=presets,
    )


@app.post("/api/download")
def download():
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    preset = body.get("preset")
    if not valid_url(url):
        return jsonify(error="Geçersiz adres."), 400
    if not isinstance(preset, int) or not 0 <= preset < len(PRESETS):
        return jsonify(error="Geçersiz kalite seçimi."), 400
    if update_state["running"]:
        return jsonify(error="yt-dlp güncelleniyor, birkaç saniye sonra tekrar deneyin."), 409

    cleanup_old_jobs()
    jid = uuid.uuid4().hex
    JOBS_ROOT.mkdir(parents=True, exist_ok=True)
    job = dict(id=jid, url=url, preset=preset, title=body.get("title") or "",
               h264=body.get("h264", True) is not False,
               dir=tempfile.mkdtemp(prefix=jid[:8] + "_", dir=JOBS_ROOT),
               created=time.time(), status="running", percent=0.0, total="", speed="",
               eta="", stage="Hazırlanıyor…", error=None, hint=None, file=None,
               proc=None, cancelled=False, converting=False)
    with jobs_lock:
        jobs[jid] = job
    threading.Thread(target=run_job, args=(job,), daemon=True).start()
    return jsonify(job_id=jid)


def get_job(jid):
    job = jobs.get(jid)
    if not job:
        abort(404)
    return job


@app.get("/api/jobs/<jid>")
def job_status(jid):
    return jsonify(public_job(get_job(jid)))


@app.post("/api/jobs/<jid>/cancel")
def job_cancel(jid):
    job = get_job(jid)
    if job.get("proc"):
        job["cancelled"] = True
        job["proc"].terminate()
    return jsonify(ok=True)


@app.get("/api/jobs/<jid>/file")
def job_file(jid):
    job = get_job(jid)
    if job["status"] != "done" or not job.get("file"):
        abort(404)
    p = Path(job["file"])
    return send_file(p, as_attachment=True, download_name=p.name)


# ── Başlatma ─────────────────────────────────────────────────────────────────
def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def main():
    ap = argparse.ArgumentParser(description="Video İndirici — yerel web sürümü")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--lan", action="store_true",
                    help="Aynı ağdaki diğer cihazlardan (telefon vb.) erişime izin ver")
    ap.add_argument("--no-browser", action="store_true", help="Tarayıcıyı otomatik açma")
    args = ap.parse_args()

    _augment_path_for_common_tools()
    start_update()
    host = "0.0.0.0" if args.lan else "127.0.0.1"
    local = f"http://127.0.0.1:{args.port}"

    print("=" * 46)
    print("  Video İndirici — web sürümü çalışıyor")
    print(f"  Bu bilgisayarda:  {local}")
    if args.lan and (ip := lan_ip()):
        print(f"  Telefondan:       http://{ip}:{args.port}  (aynı Wi-Fi)")
    print("  Kapatmak için bu pencerede Ctrl+C")
    print("=" * 46, flush=True)

    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(local)).start()
    app.run(host=host, port=args.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
