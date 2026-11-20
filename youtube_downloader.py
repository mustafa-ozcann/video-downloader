#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
import json
import os
import re
import sys
import io
import shutil
import ssl
import tempfile
import time
import urllib.request
from pathlib import Path

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

def _video_fmt(max_h=None):
    """mp4/m4a tercih eder; yoksa herhangi bir video+ses çiftine, en son tek dosyaya düşer.
    (Eski seçiciler yalnızca mp4'e bakıyordu; YouTube'da birleşik 'best' akışı olmadığı için
    bazı videolarda 'Requested format is not available' hatası veriyordu.)"""
    h = f"[height<={max_h}]" if max_h else ""
    return f"bv*{h}[ext=mp4]+ba[ext=m4a]/bv*{h}+ba/b{h}"


PRESETS = [
    ("En iyi kalite",   _video_fmt(),     False, "En yüksek çözünürlük"),
    ("4K Ultra HD",     _video_fmt(2160), False, "3840×2160"),
    ("1080p",           _video_fmt(1080), False, "1920×1080"),
    ("720p",            _video_fmt(720),  False, "1280×720"),
    ("480p",            _video_fmt(480),  False, "Daha küçük dosya"),
    ("360p",            _video_fmt(360),  False, "En düşük"),
    ("Sadece ses",       "bestaudio/best", True, "MP3"),
]

UPDATE_STAMP = Path.home() / ".video_downloader_last_update"
UPDATE_INTERVAL_SEC = 24 * 3600


def _ytdlp_cmd():
    """yt-dlp'yi uygulamayı çalıştıran Python ile çağır (PATH'teki eski/başka bir kopya yerine).
    Böylece otomatik güncelleme ile çalıştırılan sürüm daima aynıdır."""
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        return ["yt-dlp"]


# ── H.264 (Premiere Pro uyumu) ───────────────────────────────────────────────
# YouTube en yüksek kaliteyi VP9/AV1 olarak verir; Premiere bunları açamaz.
# 1) yt-dlp'ye aynı çözünürlük/fps'de H.264 (avc1) + AAC akışlarını tercih ettiriyoruz
#    (YouTube'da 1080p'ye kadar genelde H.264 var → yeniden kodlama gerekmez).
# 2) İnen dosya yine de H.264/AAC değilse (örn. 4K, sadece VP9/AV1 var) ffmpeg ile dönüştürüyoruz.
# Sadece ses (MP3) indirmeleri bu işlemden hiç etkilenmez.
H264_SORT = "res,fps,vcodec:h264,acodec:aac"


def build_download_cmd(url, fmt, audio_only, out_tmpl, h264=True, path_file=None):
    """yt-dlp indirme komutunu oluşturur (masaüstü ve web sürümü ortak)."""
    cmd = _ytdlp_cmd() + ["--no-check-certificate", "--no-update", "--newline", "--no-playlist",
                          "-f", fmt, "-o", out_tmpl]
    if audio_only:
        cmd += ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]
    else:
        if h264:
            cmd += ["-S", H264_SORT]
        cmd += ["--merge-output-format", "mp4"]
        if path_file:
            # Son dosya yolunu (birleştirme sonrası) bir dosyaya yazdır → dönüştürme adımı için
            cmd += ["--print-to-file", "after_move:filepath", path_file]
    return cmd + ["--", url]


def _probe_media(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,height,r_frame_rate:format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=60)
    data = json.loads(r.stdout or "{}")
    streams = data.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"
              and s.get("codec_name") not in ("mjpeg", "png")), None)
    a = next((s for s in streams if s.get("codec_type") == "audio"), None)
    try:
        dur = float((data.get("format") or {}).get("duration") or 0)
    except ValueError:
        dur = 0.0
    return v, a, dur


def _h264_encoders(height, fps):
    """Denenecek H.264 kodlayıcıları (önce donanım hızlandırmalı, sonra libx264)."""
    if sys.platform == "darwin":
        mbps = 45 if height > 1440 else 24 if height > 1080 else 14 if height > 720 else 8 if height > 480 else 4
        if fps > 40:
            mbps = int(mbps * 1.5)
        yield ["-c:v", "h264_videotoolbox", "-b:v", f"{mbps}M", "-profile:v", "high", "-allow_sw", "1"]
    yield ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high"]


def ensure_h264(path, on_progress=None, on_proc=None, is_cancelled=None):
    """Dosya H.264 + AAC değilse dönüştürür. Son dosya yolunu döndürür (iptalde None).
    on_progress(yüzde), on_proc(Popen) — iptal için sürecin dışarıya verilmesi."""
    path = Path(path)
    v, a, dur = _probe_media(path)
    if not v:
        return path
    v_ok = v.get("codec_name") == "h264"
    a_ok = a is None or a.get("codec_name") == "aac"
    if v_ok and a_ok and path.suffix.lower() == ".mp4":
        return path

    height = int(v.get("height") or 1080)
    try:
        num, den = (v.get("r_frame_rate") or "30/1").split("/")
        fps = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        fps = 30.0
    final = path.with_suffix(".mp4")
    tmp = path.with_name(path.stem + ".h264-tmp.mp4")
    a_args = ["-c:a", "copy"] if a_ok else ["-c:a", "aac", "-b:a", "320k"]
    v_choices = [["-c:v", "copy"]] if v_ok else list(_h264_encoders(height, fps))

    last_err = ""
    for v_args in v_choices:
        cmd = (["ffmpeg", "-y", "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(path),
                "-map", "0:v:0", "-map", "0:a:0?"] + v_args
               + ([] if v_ok else ["-pix_fmt", "yuv420p", "-tag:v", "avc1"])
               + a_args + ["-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(tmp)])
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace")
        if on_proc:
            on_proc(proc)
        err_buf = []
        t = threading.Thread(target=lambda: err_buf.extend(proc.stderr), daemon=True)
        t.start()
        for line in proc.stdout:
            if line.startswith("out_time_us=") and dur > 0 and on_progress:
                try:
                    on_progress(min(99.9, int(line.split("=", 1)[1]) / 1e6 / dur * 100))
                except ValueError:
                    pass
        proc.wait()
        t.join(timeout=5)
        if is_cancelled and is_cancelled():
            tmp.unlink(missing_ok=True)
            return None
        if proc.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
            os.replace(tmp, final)
            if final != path:
                path.unlink(missing_ok=True)
            if on_progress:
                on_progress(100.0)
            return final
        last_err = "".join(err_buf).strip().splitlines()[-1:] or [f"ffmpeg kod {proc.returncode}"]
        last_err = last_err[0]
        tmp.unlink(missing_ok=True)
    raise RuntimeError(f"H.264 dönüştürme başarısız: {last_err[:300]}")

# ── Minimal koyu palet (neutral zinc) ───────────────────────────────────────
BG         = "#09090b"
SURFACE    = "#121214"
SURFACE2   = "#18181b"
ELEVATED   = "#1c1c1f"
BORDER     = "#27272a"
BORDER_L   = "#3f3f46"
PRIMARY_FG = "#09090b"
TEXT       = "#fafafa"
TEXT2      = "#a1a1aa"
TEXT3      = "#71717a"
ACCENT_BTN = "#f4f4f5"
MUTED_BTN  = "#27272a"
SUCCESS    = "#22c55e"
DANGER     = "#ef4444"
WARN       = "#eab308"

THUMB_PLACEHOLDER = "#141416"
THUMB_BORDER      = BORDER
PREVIEW_MAX_W    = 360
PREVIEW_MAX_H    = 202


def _augment_path_for_common_tools():
    """macOS .app / Finder ortamında /opt/homebrew/bin genelde PATH'te olmaz; ffmpeg bulunur."""
    if sys.platform != "darwin":
        return
    extra = []
    # ffmpeg (birleştirme) ve deno (YouTube JS doğrulaması) genelde buralarda olur
    for d in ("/opt/homebrew/bin", "/usr/local/bin", str(Path.home() / ".deno" / "bin")):
        if Path(d).is_dir():
            extra.append(d)
    if not extra:
        return
    path = os.environ.get("PATH", "")
    seen = {p for p in path.split(os.pathsep) if p}
    prepend = [d for d in extra if d not in seen]
    if not prepend:
        return
    os.environ["PATH"] = os.pathsep.join(prepend) + os.pathsep + path


class ModernDownloader:
    def __init__(self, root):
        self.root = root
        _augment_path_for_common_tools()
        self.root.title("Video İndirici")
        self.root.geometry("880x760")
        self.root.minsize(700, 600)
        self.root.configure(bg=BG)
        
        # Pencereyi en öne getir (macOS'ta app içinden açılınca arkada kalmaması için)
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after(500, lambda: self.root.attributes('-topmost', False))
        
        # MacOS dock ikonu vs için focus al
        if sys.platform == 'darwin':
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')

        self.download_path  = str(Path.home() / "Downloads")
        self.selected_idx   = 0
        self.video_info     = None
        self.download_proc   = None
        self._info_frame     = None
        self._preview_photo  = None  # Tk görsel GC önlemi
        self.active_presets = []     # video'ya göre filtrelenmiş preset listesi
        self.qual_body       = None  # kalite butonlarının container frame'i
        self._cancelled      = False
        self._error_lines    = []
        self._updating       = False
        self.h264_on         = True   # videolar Premiere uyumlu H.264 olarak kaydedilsin

        self._styles()
        self._build()
        self._check_deps()
        self._auto_update_ytdlp()

    # ── Stiller ────────────────────────────────────────────────────────────
    def _styles(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except tk.TclError:
            pass

        s.configure(".", background=BG, foreground=TEXT, font=("Helvetica Neue", 11))
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("Sub.TLabel", background=BG, foreground=TEXT2, font=("Helvetica Neue", 10))
        s.configure("Hint.TLabel", background=SURFACE, foreground=TEXT3, font=("Helvetica Neue", 9))

        s.configure(
            "TEntry",
            fieldbackground=ELEVATED,
            foreground=TEXT,
            bordercolor=BORDER,
            insertcolor=TEXT,
            padding=(14, 12),
            font=("Helvetica Neue", 12),
        )
        s.map("TEntry", bordercolor=[("focus", BORDER_L)])

        s.configure(
            "Primary.TButton",
            background=ACCENT_BTN,
            foreground=PRIMARY_FG,
            borderwidth=0,
            padding=(22, 12),
            font=("Helvetica Neue", 12, "bold"),
        )
        s.map(
            "Primary.TButton",
            background=[("active", "#e4e4e7"), ("disabled", MUTED_BTN)],
            foreground=[("disabled", TEXT3)],
        )

        s.configure(
            "Ghost.TButton",
            background=SURFACE2,
            foreground=TEXT2,
            borderwidth=1,
            padding=(14, 10),
            font=("Helvetica Neue", 11),
        )
        s.map("Ghost.TButton", background=[("active", ELEVATED)], foreground=[("active", TEXT)])

        s.configure(
            "Cancel.TButton",
            background=DANGER,
            foreground="#fafafa",
            borderwidth=0,
            padding=(16, 10),
            font=("Helvetica Neue", 11, "bold"),
        )
        s.map("Cancel.TButton", background=[("active", "#dc2626")])

        s.configure(
            "Qual.TButton",
            background=ELEVATED,
            foreground=TEXT2,
            borderwidth=0,
            padding=(12, 10),
            font=("Helvetica Neue", 10),
        )
        s.map("Qual.TButton", background=[("active", SURFACE2)], foreground=[("active", TEXT)])

        s.configure(
            "QualSel.TButton",
            background=TEXT,
            foreground=PRIMARY_FG,
            borderwidth=0,
            padding=(12, 10),
            font=("Helvetica Neue", 10, "bold"),
        )
        s.map("QualSel.TButton", background=[("active", "#e4e4e7")])

        s.configure("TProgressbar", troughcolor=ELEVATED, background=TEXT, thickness=10, borderwidth=0)

    # ── Ana Arayüz ─────────────────────────────────────────────────────────
    def _build(self):
        # Kaydırılabilir alan
        canvas = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.main = tk.Frame(canvas, bg=BG)
        self.win_id = canvas.create_window((0, 0), window=self.main, anchor="nw")

        def _resize(e):
            canvas.itemconfig(self.win_id, width=e.width)
        canvas.bind("<Configure>", _resize)
        self.main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        def _scroll(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _scroll)

        self.main.columnconfigure(0, weight=1)
        self._build_header()
        self._build_url_section()
        self._build_info_section()
        self._build_quality_and_folder_row()
        self._build_action_section()
        self._build_log_section()

    def _build_header(self):
        hdr = tk.Frame(self.main, bg=BG)
        hdr.grid(row=0, column=0, sticky="ew", padx=28, pady=(20, 2))

        left = tk.Frame(hdr, bg=BG)
        left.pack(side="left")

        tk.Label(
            left,
            text="Video İndirici",
            bg=BG,
            fg=TEXT,
            font=("Helvetica Neue", 22, "normal"),
        ).pack(anchor="w")

        tk.Label(
            left,
            text="Linki yapıştırın — önizleme ve kalite tek ekranda.",
            bg=BG,
            fg=TEXT3,
            font=("Helvetica Neue", 11),
        ).pack(anchor="w", pady=(4, 0))

        self._site_popup = None
        badge_outer = tk.Frame(hdr, bg=ELEVATED, highlightbackground=BORDER, highlightthickness=1)
        badge_outer.pack(side="right", padx=(16, 0))
        badge_lbl = tk.Label(
            badge_outer,
            text="1000+ site  ▸",
            bg=ELEVATED,
            fg=TEXT2,
            font=("Helvetica Neue", 10),
            padx=12,
            pady=7,
            cursor="hand2",
        )
        badge_lbl.pack()

        for w in (badge_outer, badge_lbl):
            w.bind("<Enter>", lambda e: self._show_site_popup(badge_outer))
            w.bind("<Leave>", lambda e: self._schedule_popup_hide())

        tk.Frame(self.main, bg=BORDER, height=1).grid(row=1, column=0, sticky="ew", padx=28, pady=(16, 0))

    # ── Site Popup ─────────────────────────────────────────────────────────
    POPULAR_SITES = [
        ("Video", ["YouTube", "Vimeo", "Dailymotion", "Twitch", "TED"]),
        ("Sosyal", ["Instagram", "TikTok", "Twitter / X", "Facebook", "Reddit"]),
        ("Müzik", ["SoundCloud", "Bandcamp", "Mixcloud", "Audiomack"]),
        ("Haber", ["BBC", "CNN", "Bloomberg", "Reuters"]),
        ("Eğitim", ["Udemy", "Coursera", "LinkedIn Learning", "Khan Academy"]),
    ]

    def _show_site_popup(self, anchor_widget):
        """Anchor widget'ın altında site listesi popup'ı açar."""
        if self._site_popup and tk.Toplevel.winfo_exists(self._site_popup):
            return   # zaten açık

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)   # başlık çubuğu yok
        popup.configure(bg=BORDER)
        self._site_popup = popup

        inner = tk.Frame(popup, bg=SURFACE, padx=16, pady=12)
        inner.pack(padx=1, pady=1, fill="both", expand=True)

        tk.Label(inner, text="Desteklenen siteler",
                 bg=SURFACE, fg=TEXT2,
                 font=("Helvetica Neue", 10)).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        for r, (category, sites) in enumerate(self.POPULAR_SITES, start=1):
            tk.Label(inner, text=category,
                     bg=SURFACE, fg=TEXT3,
                     font=("Helvetica Neue", 9)).grid(
                row=r, column=0, sticky="nw", padx=(0, 16), pady=(2, 0))

            site_text = "\n".join(sites)
            tk.Label(inner, text=site_text,
                     bg=SURFACE, fg=TEXT,
                     font=("Helvetica Neue", 10),
                     justify="left").grid(
                row=r, column=1, sticky="w", pady=(2, 0))

        tk.Label(inner,
                 text="ve bunun dışında yüzlerce kaynak daha",
                 bg=SURFACE, fg=TEXT3,
                 font=("Helvetica Neue", 9)).grid(
            row=len(self.POPULAR_SITES) + 1, column=0, columnspan=2,
            sticky="w", pady=(10, 0))

        # Konumlandır: badge'in hemen altı
        popup.update_idletasks()
        bx = anchor_widget.winfo_rootx()
        by = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 4
        pw = popup.winfo_reqwidth()
        # Ekrandan taşmasın
        sw = self.root.winfo_screenwidth()
        if bx + pw > sw:
            bx = sw - pw - 8
        popup.geometry(f"+{bx}+{by}")

        # Mouse popup üzerinde iken kapanmasın
        popup.bind("<Enter>",  lambda e: self._cancel_popup_hide())
        popup.bind("<Leave>",  lambda e: self._schedule_popup_hide())
        for child in inner.winfo_children():
            child.bind("<Enter>",  lambda e: self._cancel_popup_hide())
            child.bind("<Leave>",  lambda e: self._schedule_popup_hide())

    def _schedule_popup_hide(self):
        """300 ms sonra popup'ı kapat (mouse geri dönerse iptal edilir)."""
        self._hide_job = self.root.after(300, self._hide_site_popup)

    def _cancel_popup_hide(self):
        if hasattr(self, "_hide_job"):
            self.root.after_cancel(self._hide_job)

    def _hide_site_popup(self):
        if self._site_popup:
            try:
                self._site_popup.destroy()
            except Exception:
                pass
            self._site_popup = None

    def _build_url_section(self):
        outer = tk.Frame(self.main, bg=BG)
        outer.grid(row=2, column=0, sticky="ew", padx=28, pady=(12, 0))
        shell = tk.Frame(outer, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        shell.pack(fill="x")
        card = tk.Frame(shell, bg=SURFACE, padx=14, pady=10)
        card.pack(fill="x")
        card.columnconfigure(0, weight=1)

        top = tk.Frame(card, bg=SURFACE)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        tk.Label(
            top,
            text="Video adresi",
            bg=SURFACE,
            fg=TEXT2,
            font=("Helvetica Neue", 12),
        ).pack(side="left")
        tk.Label(
            top,
            text="YouTube ve benzeri",
            bg=SURFACE,
            fg=TEXT3,
            font=("Helvetica Neue", 10),
        ).pack(side="left", padx=(10, 0))

        self.url_var = tk.StringVar()
        entry = ttk.Entry(card, textvariable=self.url_var, font=("Helvetica Neue", 12))
        entry.grid(row=1, column=0, sticky="ew", pady=(0, 2))
        entry.bind("<Return>", lambda _: self.fetch_info())

        tk.Label(
            card,
            text="örn. youtube.com/watch…",
            bg=SURFACE,
            fg=TEXT3,
            font=("Helvetica Neue", 9),
        ).grid(row=2, column=0, sticky="w")

        self.fetch_btn = ttk.Button(
            card,
            text="Bilgi getir",
            style="Ghost.TButton",
            command=self.fetch_info,
        )
        self.fetch_btn.grid(row=1, column=1, rowspan=2, padx=(12, 0), sticky="ne")

    def _build_info_section(self):
        outer = tk.Frame(self.main, bg=BG)
        outer.grid(row=3, column=0, sticky="ew", padx=28, pady=(10, 0))
        outer.columnconfigure(0, weight=1)
        outer.grid_remove()
        self._info_frame = outer

        shell = tk.Frame(outer, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        shell.pack(fill="x")
        inner = tk.Frame(shell, bg=SURFACE)
        inner.pack(fill="x", padx=16, pady=12)
        inner.columnconfigure(1, weight=1)

        thumb_col = tk.Frame(inner, bg=SURFACE)
        thumb_col.grid(row=0, column=0, sticky="nw", padx=(0, 18))

        self.preview_shell = tk.Frame(
            thumb_col,
            bg=BORDER,
            highlightthickness=0,
            width=PREVIEW_MAX_W + 2,
            height=PREVIEW_MAX_H + 2,
        )
        self.preview_shell.pack()
        self.preview_shell.pack_propagate(False)

        self.preview_thumb = tk.Label(
            self.preview_shell,
            text="Kapak görseli\nyükleniyor…",
            fg=TEXT3,
            bg=THUMB_PLACEHOLDER,
            font=("Helvetica Neue", 10),
            justify="center",
        )
        self.preview_thumb.pack(expand=True, fill="both", padx=1, pady=1)

        text_col = tk.Frame(inner, bg=SURFACE)
        text_col.grid(row=0, column=1, sticky="nwe")
        text_col.columnconfigure(0, weight=1)

        badge = tk.Label(
            text_col,
            text="ÖNİZLEME",
            bg=ELEVATED,
            fg=TEXT3,
            font=("Helvetica Neue", 9),
            padx=8,
            pady=3,
        )
        badge.grid(row=0, column=0, sticky="w")

        tk.Frame(text_col, bg=SUCCESS, height=2).grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.info_title = tk.Label(
            text_col,
            text="",
            bg=SURFACE,
            fg=TEXT,
            font=("Helvetica Neue", 15, "normal"),
            wraplength=460,
            justify="left",
            anchor="nw",
        )
        self.info_title.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.info_meta = tk.Label(
            text_col,
            text="",
            bg=SURFACE,
            fg=TEXT2,
            font=("Helvetica Neue", 11),
            wraplength=460,
            justify="left",
            anchor="nw",
        )
        self.info_meta.grid(row=3, column=0, sticky="ew", pady=(6, 0))

    def _build_quality_and_folder_row(self):
        """Kalite düğümleri ile kayıt klasörünü tek kartta yan yana."""
        outer = tk.Frame(self.main, bg=BG)
        outer.grid(row=4, column=0, sticky="ew", padx=28, pady=(8, 0))

        shell = tk.Frame(outer, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        shell.pack(fill="x")
        inner = tk.Frame(shell, bg=SURFACE, padx=14, pady=12)
        inner.pack(fill="x")
        inner.columnconfigure(0, weight=1)

        lanes = tk.Frame(inner, bg=SURFACE)
        lanes.pack(fill="x")
        lanes.columnconfigure(0, weight=1)

        qual_col = tk.Frame(lanes, bg=SURFACE)
        qual_col.grid(row=0, column=0, sticky="nsew")
        qual_col.columnconfigure(0, weight=1)

        tk.Label(
            qual_col,
            text="Kalite",
            bg=SURFACE,
            fg=TEXT3,
            font=("Helvetica Neue", 9),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.qual_body = tk.Frame(qual_col, bg=SURFACE)
        self.qual_body.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.qual_btns = []
        self._qual_placeholder = tk.Label(
            self.qual_body,
            text="Önce bağlantıyı analiz edin.",
            bg=SURFACE,
            fg=TEXT3,
            font=("Helvetica Neue", 10),
            anchor="w",
        )
        self._qual_placeholder.grid(row=0, column=0, sticky="w")

        # H.264 anahtarı — yalnızca video indirmelerini etkiler, sadece ses (MP3) etkilenmez
        codec_row = tk.Frame(qual_col, bg=SURFACE)
        codec_row.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.h264_btn = ttk.Button(codec_row, style="QualSel.TButton", command=self._toggle_h264)
        self.h264_btn.pack(side="left")
        self.h264_hint = tk.Label(codec_row, text="", bg=SURFACE, fg=TEXT3,
                                  font=("Helvetica Neue", 9), justify="left", wraplength=300)
        self.h264_hint.pack(side="left", padx=(10, 0))
        self._refresh_h264_ui()

        folder_col = tk.Frame(lanes, bg=SURFACE)
        folder_col.grid(row=0, column=1, sticky="ne", padx=(24, 0))

        tk.Label(
            folder_col,
            text="Kayıt",
            bg=SURFACE,
            fg=TEXT3,
            font=("Helvetica Neue", 9),
            anchor="w",
        ).pack(anchor="w")

        self.folder_lbl = tk.Label(
            folder_col,
            text=self.download_path,
            bg=ELEVATED,
            fg=TEXT,
            font=("Helvetica Neue", 10),
            anchor="nw",
            justify="left",
            padx=10,
            pady=8,
            wraplength=220,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.folder_lbl.pack(fill="x", pady=(6, 6))

        ttk.Button(folder_col, text="Klasör…", style="Ghost.TButton", command=self.change_path).pack(
            anchor="w"
        )

    def _build_action_section(self):
        act = tk.Frame(self.main, bg=BG)
        act.grid(row=5, column=0, sticky="ew", padx=28, pady=(8, 2))
        act.columnconfigure(0, weight=1)

        self.dl_btn = ttk.Button(
            act,
            text="İndirmeyi başlat",
            style="Primary.TButton",
            command=self.start_download,
            state="disabled",
        )
        self.dl_btn.grid(row=0, column=0, sticky="ew")

        self.cancel_btn = ttk.Button(act, text="İptal",
                                     style="Cancel.TButton",
                                     command=self.cancel_download)
        self.cancel_btn.grid(row=0, column=1, padx=(12, 0))
        self.cancel_btn.grid_remove()

        # İlerleme
        self.prog_bar = ttk.Progressbar(act, mode="determinate", maximum=100)
        self.prog_bar.grid(row=1, column=0, columnspan=2, sticky="ew",
                           pady=(8, 2))
        self.prog_bar.grid_remove()

        self.prog_lbl = tk.Label(act, text="", bg=BG, fg=TEXT2, font=("Helvetica Neue", 10))
        self.prog_lbl.grid(row=2, column=0, columnspan=2, sticky="w")
        self.prog_lbl.grid_remove()

    def _build_log_section(self):
        card = self._card(
            row=6,
            eyebrow="Günlük",
            title="Durum",
            subtitle="İndirme ve hata çıktıları.",
            pady_bottom=20,
            expand_vertical=True,
        )
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.log_box = scrolledtext.ScrolledText(
            card,
            height=7,
            state="disabled",
            font=("Menlo", 10),
            bg=BG,
            fg=TEXT2,
            relief="flat",
            borderwidth=0,
            wrap="word",
            insertbackground=TEXT,
            selectbackground=BORDER_L,
            highlightthickness=0,
        )
        self.log_box.grid(row=0, column=0, sticky="nsew")

        self.main.rowconfigure(6, weight=1)

    # ── Kart Yardımcısı ────────────────────────────────────────────────────
    def _card(self, row, title="", eyebrow="", subtitle="", pady_bottom=8, expand_vertical=False):
        outer = tk.Frame(self.main, bg=BG)
        outer.grid(row=row, column=0, sticky="nsew" if expand_vertical else "ew",
                   padx=28, pady=(10, pady_bottom))
        self.main.columnconfigure(0, weight=1)

        surface = tk.Frame(outer, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        surface.pack(fill="both", expand=expand_vertical)

        inner = tk.Frame(surface, bg=SURFACE)
        inner.pack(fill="both", expand=expand_vertical, padx=16, pady=(14, 14))
        inner.columnconfigure(0, weight=1)

        head = tk.Frame(inner, bg=SURFACE)
        head.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        if eyebrow:
            tk.Label(
                head,
                text=eyebrow.upper(),
                bg=SURFACE,
                fg=TEXT3,
                font=("Helvetica Neue", 9),
                anchor="w",
            ).pack(anchor="w")
        row_title = title or ""
        if row_title:
            tk.Label(
                head,
                text=row_title,
                bg=SURFACE,
                fg=TEXT,
                font=("Helvetica Neue", 14, "normal"),
                anchor="w",
            ).pack(anchor="w", pady=(2, 0))
        if subtitle:
            tk.Label(
                head,
                text=subtitle,
                bg=SURFACE,
                fg=TEXT3,
                font=("Helvetica Neue", 10),
                anchor="w",
                wraplength=720,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(inner, bg=SURFACE)
        bsticky = "nsew" if expand_vertical else "ew"
        body.grid(row=1, column=0, sticky=bsticky)
        body.columnconfigure(0, weight=1)
        if expand_vertical:
            inner.rowconfigure(1, weight=1)
        return body

    @staticmethod
    def _best_thumbnail_url(info):
        thumbs = info.get("thumbnails") or []
        if thumbs:
            def score(t):
                return (t.get("width") or 0) * (t.get("height") or 0)
            picked = max(thumbs, key=score)
            u = picked.get("url")
            if u:
                return u
        for key in ("thumbnail", "thumbnail_url"):
            u = info.get(key)
            if u:
                return u
        return None

    def _reset_preview_placeholder(self):
        self._preview_photo = None
        self.preview_thumb.configure(
            image="",
            text="Kapak görseli\nyükleniyor…",
            fg=TEXT3,
            bg=THUMB_PLACEHOLDER,
            font=("Helvetica Neue", 10),
            justify="center",
        )

    def _preview_fallback(self, message):
        self._preview_photo = None
        self.preview_thumb.configure(
            image="",
            text=message,
            fg=TEXT3,
            bg=THUMB_PLACEHOLDER,
            font=("Helvetica Neue", 9),
            justify="center",
        )

    def _apply_preview(self, photo):
        self._preview_photo = photo
        self.preview_thumb.configure(image=photo, text="", compound="center")

    def _load_thumbnail_async(self, url):
        """Ağ çağrısı için arka plan iş parçacığı."""
        threading.Thread(target=self._fetch_thumbnail_worker, args=(url,), daemon=True).start()

    def _fetch_thumbnail_worker(self, url):
        if not url:
            self.root.after(0, lambda: self._preview_fallback("Kapak yok"))
            return
        if Image is None or ImageTk is None:
            self.root.after(0, lambda: self._preview_fallback("Kapak önizlemesi\nPillow yüklü değil"))
            return
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/605.1.15 VideoDownloader"},
            )
            # python.org Python'unda sistem sertifikaları bulunmayabilir → certifi kullan
            try:
                import certifi
                ctx = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = None
            with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            w, h = img.size
            scale = min(PREVIEW_MAX_W / w, PREVIEW_MAX_H / h, 1.0)
            nw = max(1, int(w * scale))
            nh = max(1, int(h * scale))
            img = img.resize((nw, nh), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.root.after(0, lambda p=photo: self._apply_preview(p))
        except Exception:
            self.root.after(0, lambda: self._preview_fallback("Kapak görseli\nyüklenemedi"))

    # ── Bağımlılık Kontrolü ────────────────────────────────────────────────
    @staticmethod
    def _ffmpeg_hint():
        pl = sys.platform
        if pl == "darwin":
            return "brew install ffmpeg"
        if pl == "win32":
            return "ffmpeg.org adresinden kurun PATH'e ekleyin veya: winget install ffmpeg"
        return "ffmpeg sistem paketleriyle kurun (örn. apt install ffmpeg)"

    def _check_deps(self):
        missing = []

        if _ytdlp_cmd() == ["yt-dlp"] and not shutil.which("yt-dlp"):
            missing.append("yt-dlp — pip ile: pip install yt-dlp · veya start_mac.command / start_windows.bat")

        if not (shutil.which("deno") or shutil.which("node") or shutil.which("bun")):
            missing.append(
                "deno — YouTube indirmeleri için gerekli (brew install deno · Windows: winget install DenoLand.Deno)"
            )

        if not shutil.which("ffmpeg"):
            missing.append(
                f"ffmpeg — birleştirme için ({self._ffmpeg_hint()})"
            )

        if Image is None or ImageTk is None:
            missing.append(
                "Pillow — kapak önizlemesi için: proje klasöründeki venv içinde pip install -r requirements.txt"
            )

        if missing:
            self.log(
                "Bazı araçlar yok veya PATH’te görünmüyor. Aşağıdakileri kurup uygulamayı yeniden açın:",
                warn=True,
            )
            for line in missing:
                self.log(f" • {line}", warn=True)
        else:
            self.log("Bağımlılıklar tamam (yt-dlp, ffmpeg, Pillow).")

        self.log("Adresi yapıştırın, «Bilgi getir» ile devam edin.")

    # ── yt-dlp Otomatik Güncelleme ─────────────────────────────────────────
    # YouTube sık sık değişir; eski yt-dlp sürümleri "HTTP Error 403: Forbidden" alır.
    # Bu yüzden günde bir kez arka planda güncelliyoruz.
    def _auto_update_ytdlp(self, force=False):
        if self._updating or _ytdlp_cmd() == ["yt-dlp"]:
            return
        if not force:
            try:
                age = time.time() - UPDATE_STAMP.stat().st_mtime
                if age < UPDATE_INTERVAL_SEC:
                    return
            except OSError:
                pass
        self._updating = True
        self.log("yt-dlp güncelleniyor (arka planda)…")
        threading.Thread(target=self._update_worker, daemon=True).start()

    def _update_worker(self):
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", "-U",
                 "--disable-pip-version-check", "yt-dlp[default]"],
                capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                UPDATE_STAMP.touch()
                v = subprocess.run(_ytdlp_cmd() + ["--version"],
                                   capture_output=True, text=True, timeout=30).stdout.strip()
                self.root.after(0, self.log, f"yt-dlp güncel: {v}")
            else:
                err = (r.stderr or r.stdout).strip().splitlines()[-1:] or [""]
                self.root.after(0, self.log, f"yt-dlp güncellenemedi: {err[0][:200]}", True)
        except Exception as e:
            self.root.after(0, self.log, f"yt-dlp güncellenemedi: {e}", True)
        finally:
            self._updating = False

    # ── Kalite Seçimi ──────────────────────────────────────────────────────
    def _select_qual(self, idx):
        """idx: active_presets içindeki sıra"""
        self.selected_idx = idx
        for i, btn in enumerate(self.qual_btns):
            btn.configure(style="QualSel.TButton" if i == idx else "Qual.TButton")
        self._refresh_h264_ui()

    def _toggle_h264(self):
        self.h264_on = not self.h264_on
        self._refresh_h264_ui()

    def _selected_is_audio(self):
        try:
            return bool(self.active_presets[self.selected_idx][2])
        except (IndexError, TypeError):
            return False

    def _refresh_h264_ui(self):
        if self.h264_on:
            self.h264_btn.configure(text="✓  H.264 · Premiere uyumlu", style="QualSel.TButton")
            hint = "Videolar H.264 + AAC (.mp4) olarak kaydedilir."
        else:
            self.h264_btn.configure(text="H.264 kapalı · orijinal codec", style="Qual.TButton")
            hint = "Video sitenin verdiği codec ile (VP9/AV1 olabilir) kaydedilir."
        if self._selected_is_audio():
            hint = "Sadece ses seçili — bu ayar ses (MP3) indirmelerini etkilemez."
        self.h264_hint.configure(text=hint)

    def _update_quality_buttons(self, info):
        """Video'nun gerçek formatlarına bakarak kalite butonlarını yeniden oluşturur."""
        # Mevcut widget'ları temizle
        for w in self.qual_body.winfo_children():
            w.destroy()
        self.qual_btns = []
        self.selected_idx = 0

        # Desteklenen yükseklikleri bul (yalnızca video içeren akışlar)
        formats = info.get("formats", [])
        available_heights = set()
        has_audio = False
        for f in formats:
            h = f.get("height")
            if h and f.get("vcodec", "none") != "none":
                available_heights.add(int(h))
            if f.get("acodec", "none") != "none":
                has_audio = True

        max_h = max(available_heights) if available_heights else 0

        # Her preset için uygunluk kontrolü
        #   preset height limiti: label içinden çıkarmak yerine PRESETS'e göre tanımladığımız eşleme
        height_map = {
            "4K Ultra HD": 2160,
            "1080p": 1080,
            "720p": 720,
            "480p": 480,
            "360p": 360,
        }

        filtered = []
        for label, fmt, audio_only, desc in PRESETS:
            if audio_only:
                if has_audio:
                    filtered.append((label, fmt, audio_only, desc))
            elif label == "En iyi kalite":
                if available_heights:
                    filtered.append((label, fmt, audio_only, desc))
            else:
                needed = height_map.get(label, 0)
                if needed and max_h >= needed:
                    filtered.append((label, fmt, audio_only, desc))

        self.active_presets = filtered

        if not filtered:
            tk.Label(self.qual_body,
                     text="Bu video için indirilebilir format bulunamadı.",
                     bg=SURFACE, fg=WARN, font=("Helvetica Neue", 10)).grid(
                row=0, column=0, sticky="w", pady=8)
            return

        n = len(filtered)
        max_col = min(6, n) if n else 1
        for i, (label, _, _, desc) in enumerate(filtered):
            col = i % max_col
            row = i // max_col
            f = tk.Frame(self.qual_body, bg=SURFACE)
            f.grid(row=row, column=col, padx=(0, 6), pady=(0, 6), sticky="nsew")
            self.qual_body.columnconfigure(col, weight=1)

            style = "QualSel.TButton" if i == 0 else "Qual.TButton"
            btn = ttk.Button(f, text=label, style=style,
                             command=lambda idx=i: self._select_qual(idx))
            btn.pack(fill="x")
            tk.Label(f, text=desc, bg=SURFACE, fg=TEXT3, font=("Helvetica Neue", 9)).pack(pady=(4, 0))
            self.qual_btns.append(btn)

        self.log(f"{len(filtered)} kalite seçeneği · en fazla {max_h}p")
        self._refresh_h264_ui()

    # ── Video Bilgisi ──────────────────────────────────────────────────────
    def fetch_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen bir video adresi girin.")
            return
        self.fetch_btn.configure(state="disabled", text="Yükleniyor…")
        self.dl_btn.configure(state="disabled")
        if self._info_frame:
            self._info_frame.grid_remove()
        self.log("Video bilgisi alınıyor…")
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        try:
            r = subprocess.run(
                _ytdlp_cmd() + ["--no-check-certificate", "--no-update", "-j", "--no-playlist", url],
                capture_output=True, text=True, timeout=90)
            if r.returncode != 0:
                self.root.after(0, self._report_error, r.stderr)
                return
            info = json.loads(r.stdout)
            self.video_info = info
            self.root.after(0, self._show_info, info)
        except subprocess.TimeoutExpired:
            self.root.after(0, self.log,
                            "Bağlantı zaman aşımı — ağı kontrol edin.", True)
        except json.JSONDecodeError:
            self.root.after(0, self.log, "Video bilgisi okunamadı.", True)
        except FileNotFoundError:
            self.root.after(0, self.log,
                            "yt-dlp bulunamadı · pip install yt-dlp", True)
        except Exception as e:
            self.root.after(0, self.log, f"Hata: {e}", True)
        finally:
            self.root.after(0, lambda: self.fetch_btn.configure(
                state="normal", text="Bilgi getir"))

    def _show_info(self, info):
        title    = info.get("title", "")
        uploader = info.get("uploader") or info.get("channel", "")
        duration = info.get("duration")
        views    = info.get("view_count")

        meta = []
        if uploader:
            meta.append(uploader)
        if duration:
            meta.append(self._fmt_dur(duration))
        if views:
            meta.append(f"{views:,} görüntüleme")

        self._reset_preview_placeholder()
        self.info_title.configure(text=title)
        self.info_meta.configure(text="   ·   ".join(meta))
        self._info_frame.grid()
        self._update_quality_buttons(info)
        self.dl_btn.configure(state="normal")
        self.log(f"Hazır: {title[:80]}")
        self._load_thumbnail_async(self._best_thumbnail_url(info))

    @staticmethod
    def _fmt_dur(secs):
        secs = int(secs)
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    # ── İndirme ────────────────────────────────────────────────────────────
    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Video linki bulunamadı!")
            return

        if not self.active_presets:
            messagebox.showwarning("Uyarı", "Önce «Bilgi getir» ile videoyu analiz edin.")
            return
        if self._updating:
            messagebox.showinfo("Bekleyin", "yt-dlp şu an güncelleniyor, birkaç saniye sonra tekrar deneyin.")
            return

        label, fmt, audio_only, _ = self.active_presets[self.selected_idx]
        h264 = self.h264_on and not audio_only
        self._cancelled = False
        self._error_lines = []
        self.dl_btn.grid_remove()
        self.cancel_btn.grid()
        self.prog_bar["value"] = 0
        self.prog_bar.grid()
        self.prog_lbl.grid()
        self.prog_lbl.configure(text="Hazırlanıyor…")
        self.log(f"İndiriliyor ({label}{' · H.264' if h264 else ''})…")

        threading.Thread(
            target=self._dl_thread,
            args=(url, fmt, audio_only, h264),
            daemon=True).start()

    def _dl_thread(self, url, fmt, audio_only, h264=False):
        path_file = None
        try:
            out = os.path.join(self.download_path, "%(title)s.%(ext)s")
            if h264:
                fd, path_file = tempfile.mkstemp(prefix="vd_path_", suffix=".txt")
                os.close(fd)
            cmd = build_download_cmd(url, fmt, audio_only, out, h264=h264, path_file=path_file)

            self.download_proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True)

            for line in self.download_proc.stdout:
                line = line.rstrip()
                if line:
                    self.root.after(0, self._handle_line, line)

            self.download_proc.wait()
            rc = self.download_proc.returncode
            if rc == 0 and h264 and not self._cancelled:
                if not self._convert_h264(path_file):
                    return
            if rc == 0 and not self._cancelled:
                self.root.after(0, self._on_success)
            elif not self._cancelled:
                # Önceden kod 1 (yt-dlp'nin genel hata kodu) sessizce yutuluyordu
                self.root.after(0, self._report_error, "\n".join(self._error_lines), rc)
        except Exception as e:
            self.root.after(0, self.log, f"Hata: {e}", True)
        finally:
            self.download_proc = None
            if path_file:
                Path(path_file).unlink(missing_ok=True)
            self.root.after(0, self._reset_ui)

    def _convert_h264(self, path_file):
        """İndirilen video H.264 değilse dönüştürür. Başarılıysa True."""
        try:
            lines = [l.strip() for l in Path(path_file).read_text(encoding="utf-8").splitlines() if l.strip()]
        except OSError:
            lines = []
        if not lines or not Path(lines[-1]).exists():
            self.root.after(0, self.log, "Uyarı: indirilen dosya bulunamadı, H.264 kontrolü atlandı.", True)
            return True
        src = Path(lines[-1])

        def prog(pct):
            def ui():
                self.prog_bar["value"] = pct
                self.prog_lbl.configure(text=f"H.264'e dönüştürülüyor…   ·   %{pct:.1f}")
            self.root.after(0, ui)

        def set_proc(p):
            self.download_proc = p

        try:
            v, a, _ = _probe_media(src)
            if v and v.get("codec_name") != "h264":
                self.root.after(0, self.log,
                                f"Video {v.get('codec_name', '?').upper()} geldi → H.264'e dönüştürülüyor "
                                "(uzun sürebilir)…")
                self.root.after(0, prog, 0.0)
            result = ensure_h264(src, on_progress=prog, on_proc=set_proc,
                                 is_cancelled=lambda: self._cancelled)
        except Exception as e:
            self.root.after(0, self.log, f"Hata: {e}", True)
            return False
        if result is None:
            return False
        self.root.after(0, self.log, f"H.264 hazır: {result.name}")
        return True

    def _handle_line(self, line):
        m = re.search(
            r'\[download\]\s+([\d.]+)%(?:\s+of\s+~?([\S]+))?(?:\s+at\s+([\S]+))?(?:\s+ETA\s+([\S]+))?',
            line)
        if m:
            pct   = float(m.group(1))
            total = m.group(2) or ""
            speed = m.group(3) or ""
            eta   = m.group(4) or ""
            self.prog_bar["value"] = pct
            parts = [f"%{pct:.1f}"]
            if total:
                parts.append(total)
            if speed:
                parts.append(speed)
            if eta and eta != "Unknown":
                parts.append(f"kalan ~{eta}")
            self.prog_lbl.configure(text="   ·   ".join(parts))
            return

        if line.startswith("ERROR"):
            self._error_lines.append(line)
            return

        if line.strip():
            self.log(line)

    def _report_error(self, stderr, rc=None):
        """yt-dlp hata çıktısını kullanıcıya anlaşılır bir mesajla gösterir."""
        lines = [l for l in (stderr or "").strip().splitlines()
                 if l.strip() and "older than 90 days" not in l]
        err_lines = [l for l in lines if l.startswith("ERROR")] or lines[-1:]
        msg = err_lines[-1] if err_lines else f"İndirme başarısız (kod {rc})"
        self.log(f"Hata: {msg[:300]}", True)

        low = msg.lower()
        if "403" in low or "forbidden" in low or "sign in to confirm" in low or "nsig" in low:
            self.log("İpucu: Bu genelde yt-dlp'nin eski olmasından kaynaklanır. "
                     "Şimdi güncelleniyor — bitince tekrar deneyin.", True)
            self._auto_update_ytdlp(force=True)
        elif "ffmpeg" in low:
            self.log(f"İpucu: ffmpeg gerekli → {self._ffmpeg_hint()}", True)
        elif "unsupported url" in low:
            self.log("İpucu: Bu site/link desteklenmiyor olabilir.", True)
        elif "private" in low or "unavailable" in low:
            self.log("İpucu: Video gizli, silinmiş veya bölgenizde kapalı olabilir.", True)

    def _on_success(self):
        self.prog_bar["value"] = 100
        self.prog_lbl.configure(text="İndirme tamamlandı.")
        self.log(f"Kaydedildi: {self.download_path}")
        if messagebox.askyesno("Tamamlandı", "Dosya kaydedildi.\n\nKlasörü açmak ister misiniz?"):
            self._open_folder()

    def cancel_download(self):
        if self.download_proc:
            self._cancelled = True
            self.download_proc.terminate()
            self.log("İndirme iptal edildi.")

    def _reset_ui(self):
        self.dl_btn.grid()
        self.cancel_btn.grid_remove()
        self.prog_bar.grid_remove()
        self.prog_lbl.grid_remove()

    # ── Yardımcı ───────────────────────────────────────────────────────────
    def change_path(self):
        path = filedialog.askdirectory(initialdir=self.download_path)
        if path:
            self.download_path = path
            self.folder_lbl.configure(text="📂  " + path)

    def _open_folder(self):
        if sys.platform == "darwin":
            subprocess.run(["open", self.download_path])
        elif sys.platform == "win32":
            os.startfile(self.download_path)
        else:
            subprocess.run(["xdg-open", self.download_path])

    def log(self, message, warn=False):
        self.log_box.configure(state="normal")
        if warn:
            self.log_box.insert(tk.END, message + "\n", "warn")
            self.log_box.tag_configure("warn", foreground=WARN)
        else:
            self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernDownloader(root)
    root.mainloop()
