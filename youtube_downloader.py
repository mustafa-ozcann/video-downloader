#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import subprocess
import json
import os
import re
import sys
from pathlib import Path

# (etiket, yt-dlp format seçici, ses_sadece)
# bestvideo+bestaudio her zaman en iyi video+ses akışını birleştirip mp4 olarak kaydeder.
PRESETS = [
    ("En İyi",
     "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
     False),
    ("4K",
     "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=2160]+bestaudio/best[height<=2160]",
     False),
    ("1080p",
     "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
     False),
    ("720p",
     "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]",
     False),
    ("480p",
     "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]",
     False),
    ("360p",
     "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]",
     False),
    ("Ses (MP3)", "bestaudio/best", True),
]

BG      = "#f5f5f5"
SURFACE = "#ffffff"
PRIMARY = "#1a73e8"
P_DARK  = "#1557b0"
TEXT    = "#212121"
MUTED   = "#6c757d"
BORDER  = "#dee2e6"
SUCCESS = "#34a853"
CANCEL  = "#ea4335"
CANCEL_D = "#c5221f"


class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video İndiricisi")
        self.root.geometry("800x700")
        self.root.minsize(680, 560)
        self.root.configure(bg=BG)

        self.download_path = str(Path.home() / "Downloads")
        self.selected_idx = 0          # seçili preset indeksi
        self.video_info = None
        self.download_process = None

        self._apply_styles()
        self._build_ui()
        self._check_dependencies()

    # ── Stiller ────────────────────────────────────────────────────────────

    def _apply_styles(self):
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass

        s.configure(".",          background=BG,      foreground=TEXT, font=("Helvetica", 11))
        s.configure("TFrame",     background=BG)
        s.configure("TLabel",     background=BG,      foreground=TEXT)
        s.configure("Muted.TLabel", background=BG,    foreground=MUTED,   font=("Helvetica", 10))
        s.configure("Title.TLabel", background=BG,    foreground=TEXT,    font=("Helvetica", 18, "bold"))

        # Kart içi label'lar
        s.configure("C.TLabel",      background=SURFACE, foreground=TEXT)
        s.configure("CMuted.TLabel", background=SURFACE, foreground=MUTED, font=("Helvetica", 10))
        s.configure("CBold.TLabel",  background=SURFACE, foreground=TEXT,  font=("Helvetica", 12, "bold"))

        s.configure("TEntry",
                    fieldbackground=SURFACE, foreground=TEXT,
                    bordercolor=BORDER, insertcolor=TEXT, padding=8)

        s.configure("Primary.TButton",
                    background=PRIMARY, foreground="white",
                    borderwidth=0, padding=(20, 12), font=("Helvetica", 13, "bold"))
        s.map("Primary.TButton",
              background=[("active", P_DARK), ("disabled", BORDER)],
              foreground=[("disabled", MUTED)])

        s.configure("Ghost.TButton",
                    background=SURFACE, foreground=PRIMARY,
                    borderwidth=1, padding=(12, 8), font=("Helvetica", 11))
        s.map("Ghost.TButton", background=[("active", "#e8f0fe")])

        s.configure("Cancel.TButton",
                    background=CANCEL, foreground="white",
                    borderwidth=0, padding=(14, 10), font=("Helvetica", 11))
        s.map("Cancel.TButton", background=[("active", CANCEL_D)])

        s.configure("Preset.TButton",
                    background=SURFACE, foreground=MUTED,
                    borderwidth=1, padding=(10, 7), font=("Helvetica", 11))
        s.map("Preset.TButton",
              background=[("active", "#e8f0fe")],
              foreground=[("active", PRIMARY)])

        s.configure("PresetSel.TButton",
                    background=PRIMARY, foreground="white",
                    borderwidth=0, padding=(10, 7), font=("Helvetica", 11, "bold"))
        s.map("PresetSel.TButton", background=[("active", P_DARK)])

        s.configure("TProgressbar",
                    troughcolor=BORDER, background=PRIMARY,
                    thickness=12, borderwidth=0)

    # ── Arayüz ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        # Durum logu son satır olarak genişlesin
        self.root.rowconfigure(6, weight=1)

        # Başlık
        ttk.Label(self.root, text="YouTube Video İndiricisi", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", padx=24, pady=(20, 10))

        # ── URL Kartı ─────────────────────────────────────────────────
        url_card = self._card(row=1)
        url_card.columnconfigure(1, weight=1)
        ttk.Label(url_card, text="YouTube URL", style="CMuted.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))

        self.url_entry = ttk.Entry(url_card, font=("Helvetica", 12))
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 10))
        self.url_entry.bind("<Return>", lambda _: self.fetch_info())

        self.fetch_btn = ttk.Button(url_card, text="Bilgi Al",
                                    style="Ghost.TButton", command=self.fetch_info)
        self.fetch_btn.grid(row=1, column=2)

        # ── Video Bilgi Kartı (başlangıçta gizli) ────────────────────
        self.info_card = self._card(row=2, show=False)
        self.info_title_lbl = ttk.Label(self.info_card, text="", style="CBold.TLabel", wraplength=720)
        self.info_title_lbl.grid(row=0, column=0, sticky="w")
        self.info_meta_lbl = ttk.Label(self.info_card, text="", style="CMuted.TLabel")
        self.info_meta_lbl.grid(row=1, column=0, sticky="w", pady=(4, 0))

        # ── Kalite Seçimi ─────────────────────────────────────────────
        q_card = self._card(row=3)
        ttk.Label(q_card, text="Kalite", style="CMuted.TLabel").grid(
            row=0, column=0, columnspan=len(PRESETS), sticky="w", pady=(0, 8))
        self.preset_btns = []
        for i, (label, _, _) in enumerate(PRESETS):
            btn = ttk.Button(
                q_card, text=label,
                style="PresetSel.TButton" if i == 0 else "Preset.TButton",
                command=lambda idx=i: self._select_preset(idx))
            btn.grid(row=1, column=i, padx=(0, 6), sticky="ew")
            q_card.columnconfigure(i, weight=1)
            self.preset_btns.append(btn)

        # ── Kayıt Klasörü ─────────────────────────────────────────────
        p_card = self._card(row=4)
        p_card.columnconfigure(1, weight=1)
        ttk.Label(p_card, text="Kayıt Klasörü", style="CMuted.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        self.path_lbl = ttk.Label(p_card, text=self.download_path,
                                   style="C.TLabel", font=("Helvetica", 11))
        self.path_lbl.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 10))
        ttk.Button(p_card, text="Değiştir", style="Ghost.TButton",
                   command=self.change_path).grid(row=1, column=2)

        # ── İndir Butonu + İlerleme ───────────────────────────────────
        act = ttk.Frame(self.root, padding=(24, 8))
        act.grid(row=5, column=0, sticky="ew")
        act.columnconfigure(0, weight=1)

        self.download_btn = ttk.Button(act, text="İndir",
                                       style="Primary.TButton",
                                       command=self.start_download,
                                       state="disabled")
        self.download_btn.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.cancel_btn = ttk.Button(act, text="İptal",
                                     style="Cancel.TButton",
                                     command=self.cancel_download)
        self.cancel_btn.grid(row=0, column=1, padx=(8, 0), pady=(0, 8))
        self.cancel_btn.grid_remove()

        self.progress_bar = ttk.Progressbar(act, mode="determinate", maximum=100)
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        self.progress_bar.grid_remove()

        self.progress_lbl = ttk.Label(act, text="", style="Muted.TLabel")
        self.progress_lbl.grid(row=2, column=0, columnspan=2, sticky="w")
        self.progress_lbl.grid_remove()

        # ── Durum Logu ────────────────────────────────────────────────
        log_card = self._card(row=6, pady_bottom=20)
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

        ttk.Label(log_card, text="Durum", style="CMuted.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        self.status_text = scrolledtext.ScrolledText(
            log_card, height=9, state="disabled",
            font=("Courier", 10), bg="#f8f9fa", fg=TEXT,
            relief="flat", borderwidth=0, wrap="word")
        self.status_text.grid(row=1, column=0, sticky="nsew")

    def _card(self, row, show=True, pady_bottom=4):
        """Beyaz arka planlı dolgu çerçevesi oluşturur."""
        outer = tk.Frame(self.root, bg=SURFACE, highlightbackground=BORDER,
                         highlightthickness=1)
        outer.grid(row=row, column=0, sticky="nsew" if row == 6 else "ew",
                   padx=24, pady=(0, pady_bottom))
        inner = tk.Frame(outer, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=16, pady=14)
        if not show:
            outer.grid_remove()
            self._card_outer = outer   # geçici referans (bilgi kartı için)
        return inner

    # ── Bağımlılık Kontrolü ────────────────────────────────────────────────

    def _check_dependencies(self):
        missing = []
        for tool in ("yt-dlp", "ffmpeg"):
            try:
                subprocess.run([tool, "--version"], capture_output=True, timeout=5)
            except FileNotFoundError:
                missing.append(tool)
        if "yt-dlp" in missing:
            self.log("⚠ yt-dlp bulunamadı → pip install yt-dlp")
        if "ffmpeg" in missing:
            self.log("⚠ ffmpeg bulunamadı — video+ses birleştirme için gerekli.")
            self.log("  macOS: brew install ffmpeg   |   https://ffmpeg.org")

    # ── Preset Seçimi ──────────────────────────────────────────────────────

    def _select_preset(self, idx):
        self.selected_idx = idx
        for i, btn in enumerate(self.preset_btns):
            btn.configure(style="PresetSel.TButton" if i == idx else "Preset.TButton")

    # ── Video Bilgisi ──────────────────────────────────────────────────────

    def fetch_info(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Hata", "Lütfen bir YouTube URL girin")
            return
        self.fetch_btn.configure(state="disabled", text="Yükleniyor…")
        self.download_btn.configure(state="disabled")
        # Bilgi kartını gizle
        self._info_outer().grid_remove()
        self.log("Video bilgisi alınıyor…")
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        try:
            r = subprocess.run(
                ["yt-dlp", "--no-check-certificate", "-j", "--no-playlist", url],
                capture_output=True, text=True, timeout=45)
            if r.returncode != 0:
                self.root.after(0, self.log, f"Hata: {r.stderr.strip()[:300]}")
                return
            info = json.loads(r.stdout)
            self.video_info = info
            self.root.after(0, self._show_info, info)
        except subprocess.TimeoutExpired:
            self.root.after(0, self.log, "Hata: Bağlantı zaman aşımına uğradı")
        except json.JSONDecodeError:
            self.root.after(0, self.log, "Hata: Yanıt işlenemedi")
        except FileNotFoundError:
            self.root.after(0, self.log, "Hata: yt-dlp bulunamadı — pip install yt-dlp")
        except Exception as e:
            self.root.after(0, self.log, f"Hata: {e}")
        finally:
            self.root.after(0, lambda: self.fetch_btn.configure(state="normal", text="Bilgi Al"))

    def _show_info(self, info):
        title    = info.get("title", "")
        uploader = info.get("uploader") or info.get("channel", "")
        duration = info.get("duration")
        views    = info.get("view_count")

        meta = []
        if uploader:
            meta.append(uploader)
        if duration:
            meta.append(f"Süre: {self._fmt_dur(duration)}")
        if views:
            meta.append(f"{views:,} görüntüleme")

        self.info_title_lbl.configure(text=title)
        self.info_meta_lbl.configure(text="  ·  ".join(meta))
        self._info_outer().grid()
        self.download_btn.configure(state="normal")
        self.log(f"✓ {title[:80]}")

    def _info_outer(self):
        """Bilgi kartının dış çerçevesini döndürür."""
        # info_card'ın parent'ı inner frame, onun parent'ı outer frame
        return self.info_title_lbl.master.master

    @staticmethod
    def _fmt_dur(secs):
        secs = int(secs)
        h, m, s = secs // 3600, (secs % 3600) // 60, secs % 60
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    # ── İndirme ────────────────────────────────────────────────────────────

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Hata", "URL girilmedi")
            return

        label, fmt, audio_only = PRESETS[self.selected_idx]
        self.download_btn.grid_remove()
        self.cancel_btn.grid()
        self.progress_bar["value"] = 0
        self.progress_bar.grid()
        self.progress_lbl.configure(text="")
        self.progress_lbl.grid()
        self.log(f"İndiriliyor — {label}…")

        threading.Thread(
            target=self._download_thread,
            args=(url, fmt, audio_only),
            daemon=True).start()

    def _download_thread(self, url, fmt, audio_only):
        try:
            out_tpl = os.path.join(self.download_path, "%(title)s.%(ext)s")
            cmd = ["yt-dlp", "--no-check-certificate", "--newline",
                   "-f", fmt, "-o", out_tpl]

            if audio_only:
                cmd += ["--extract-audio", "--audio-format", "mp3", "--audio-quality", "0"]
            else:
                cmd += ["--merge-output-format", "mp4"]

            cmd.append(url)

            self.download_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in self.download_process.stdout:
                line = line.rstrip()
                if line:
                    self.root.after(0, self._handle_line, line)

            self.download_process.wait()
            rc = self.download_process.returncode

            if rc == 0:
                self.root.after(0, self._on_success)
            elif rc not in (-15, 1):   # -15 = iptal, 1 = zaten işlendi
                self.root.after(0, self.log, f"✗ İndirme başarısız (kod {rc})")

        except Exception as e:
            self.root.after(0, self.log, f"✗ Hata: {e}")
        finally:
            self.download_process = None
            self.root.after(0, self._reset_ui)

    def _handle_line(self, line):
        # İlerleme satırı: [download]  45.3% of ~234.56MiB at 5.23MiB/s ETA 00:32
        m = re.search(
            r'\[download\]\s+([\d.]+)%(?:\s+of\s+~?([\S]+))?(?:\s+at\s+([\S]+))?(?:\s+ETA\s+([\S]+))?',
            line)
        if m:
            pct   = float(m.group(1))
            total = m.group(2) or ""
            speed = m.group(3) or ""
            eta   = m.group(4) or ""
            self.progress_bar["value"] = pct
            parts = [f"%{pct:.1f}"]
            if total: parts.append(total)
            if speed: parts.append(speed)
            if eta and eta != "Unknown": parts.append(f"ETA {eta}")
            self.progress_lbl.configure(text="   ·   ".join(parts))
            return   # ilerleme satırını log'a yazmıyoruz

        # [Merger], [ffmpeg] gibi arka plan satırlarını filtrele
        if re.match(r'\[(Merger|ffmpeg|ExtractAudio)\]', line):
            self.log(f"⚙ {line}")
            return

        self.log(line)

    def _on_success(self):
        self.progress_bar["value"] = 100
        self.progress_lbl.configure(text="İndirme tamamlandı!")
        self.log(f"✓ Dosya kaydedildi: {self.download_path}")
        if messagebox.askyesno("Tamamlandı", "İndirme tamamlandı!\n\nKlasörü açmak ister misiniz?"):
            self._open_folder()

    def cancel_download(self):
        if self.download_process:
            self.download_process.terminate()
            self.log("İndirme iptal edildi")

    def _reset_ui(self):
        self.download_btn.grid()
        self.cancel_btn.grid_remove()
        self.progress_bar.grid_remove()
        self.progress_lbl.grid_remove()

    # ── Yardımcı ───────────────────────────────────────────────────────────

    def change_path(self):
        path = filedialog.askdirectory(initialdir=self.download_path)
        if path:
            self.download_path = path
            self.path_lbl.configure(text=path)

    def _open_folder(self):
        if sys.platform == "darwin":
            subprocess.run(["open", self.download_path])
        elif sys.platform == "win32":
            os.startfile(self.download_path)
        else:
            subprocess.run(["xdg-open", self.download_path])

    def log(self, message):
        self.status_text.configure(state="normal")
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.status_text.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
