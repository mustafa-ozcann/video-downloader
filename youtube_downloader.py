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

PRESETS = [
    ("🏆 En İyi Kalite",   "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best", False, "En yüksek çözünürlük"),
    ("4K Ultra HD",        "bestvideo[height<=2160][ext=mp4]+bestaudio[ext=m4a]/best[height<=2160]", False, "3840×2160"),
    ("Full HD 1080p",      "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]", False, "1920×1080"),
    ("HD 720p",            "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]",  False, "1280×720"),
    ("Orta 480p",          "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480]",  False, "Küçük dosya"),
    ("Düşük 360p",         "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360]",  False, "En küçük"),
    ("🎵 Sadece Müzik",   "bestaudio/best", True, "MP3 ses dosyası"),
]

# ── Renk Paleti (Koyu Tema) ──────────────────────────────────────────────────
BG        = "#0f0f13"
SURFACE   = "#1a1a24"
SURFACE2  = "#24243a"
ACCENT    = "#7c3aed"
ACCENT2   = "#a855f7"
ACCENT_L  = "#c4b5fd"
SUCCESS   = "#10b981"
DANGER    = "#ef4444"
WARN      = "#f59e0b"
TEXT      = "#f1f5f9"
TEXT2     = "#94a3b8"
TEXT3     = "#64748b"
BORDER    = "#2d2d45"


class ModernDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Video İndirici 🎬")
        self.root.geometry("860x780")
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
        self.download_proc  = None
        self._info_frame    = None
        self.active_presets = []   # video'ya göre filtrelenmiş preset listesi
        self.qual_body      = None # kalite butonlarının container frame'i

        self._styles()
        self._build()
        self._check_deps()

    # ── Stiller ────────────────────────────────────────────────────────────
    def _styles(self):
        s = ttk.Style()
        try: s.theme_use("clam")
        except: pass

        s.configure(".",             background=BG,      foreground=TEXT,  font=("Helvetica", 11))
        s.configure("TFrame",        background=BG)
        s.configure("TLabel",        background=BG,      foreground=TEXT)
        s.configure("Sub.TLabel",    background=BG,      foreground=TEXT2, font=("Helvetica", 10))
        s.configure("Hint.TLabel",   background=SURFACE, foreground=TEXT2, font=("Helvetica", 9))

        s.configure("TEntry",
            fieldbackground=SURFACE2, foreground=TEXT,
            bordercolor=BORDER, insertcolor=TEXT, padding=10,
            font=("Helvetica", 12))
        s.map("TEntry", bordercolor=[("focus", ACCENT2)])

        s.configure("Primary.TButton",
            background=ACCENT, foreground=TEXT,
            borderwidth=0, padding=(24, 14),
            font=("Helvetica", 13, "bold"))
        s.map("Primary.TButton",
            background=[("active", ACCENT2), ("disabled", SURFACE2)],
            foreground=[("disabled", TEXT3)])

        s.configure("Ghost.TButton",
            background=SURFACE2, foreground=ACCENT_L,
            borderwidth=1, padding=(12, 10),
            font=("Helvetica", 11))
        s.map("Ghost.TButton", background=[("active", SURFACE)])

        s.configure("Cancel.TButton",
            background=DANGER, foreground=TEXT,
            borderwidth=0, padding=(16, 12),
            font=("Helvetica", 11, "bold"))
        s.map("Cancel.TButton", background=[("active", "#b91c1c")])

        s.configure("Qual.TButton",
            background=SURFACE2, foreground=TEXT2,
            borderwidth=1, padding=(8, 8),
            font=("Helvetica", 10))
        s.map("Qual.TButton",
            background=[("active", SURFACE)],
            foreground=[("active", ACCENT_L)])

        s.configure("QualSel.TButton",
            background=ACCENT, foreground=TEXT,
            borderwidth=0, padding=(8, 8),
            font=("Helvetica", 10, "bold"))
        s.map("QualSel.TButton", background=[("active", ACCENT2)])

        s.configure("TProgressbar",
            troughcolor=SURFACE2, background=ACCENT2,
            thickness=14, borderwidth=0)

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
        self._build_quality_section()
        self._build_folder_section()
        self._build_action_section()
        self._build_log_section()

    def _build_header(self):
        hdr = tk.Frame(self.main, bg=BG)
        hdr.grid(row=0, column=0, sticky="ew", padx=28, pady=(28, 8))

        tk.Label(hdr, text="🎬 Video İndirici",
                 bg=BG, fg=TEXT,
                 font=("Helvetica", 26, "bold")).pack(side="left")

        # ── Hover badge ────────────────────────────────────────────────────
        self._site_popup = None
        self._popup_inside = False

        badge_outer = tk.Frame(hdr, bg=ACCENT, cursor="hand2")
        badge_outer.pack(side="right", padx=(0, 4))
        badge_lbl = tk.Label(badge_outer, text="🌐  1000+ site desteklenir  ▾",
                             bg=ACCENT, fg=TEXT,
                             font=("Helvetica", 10, "bold"),
                             padx=12, pady=6, cursor="hand2")
        badge_lbl.pack()

        for w in (badge_outer, badge_lbl):
            w.bind("<Enter>",  lambda e: self._show_site_popup(badge_outer))
            w.bind("<Leave>",  lambda e: self._schedule_popup_hide())

        tk.Label(self.main,
                 text="Herhangi bir video linkini yapıştırın ve indirin — ücretsiz, hızlı, kolay.",
                 bg=BG, fg=TEXT2,
                 font=("Helvetica", 12)).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 20))

    # ── Site Popup ─────────────────────────────────────────────────────────
    POPULAR_SITES = [
        ("📺 Video",    ["YouTube", "Vimeo", "Dailymotion", "Twitch", "TED"]),
        ("📸 Sosyal",   ["Instagram", "TikTok", "Twitter / X", "Facebook", "Reddit"]),
        ("🎵 Müzik",   ["SoundCloud", "Bandcamp", "Mixcloud", "Audiomack"]),
        ("📰 Haber",   ["BBC", "CNN", "Bloomberg", "Reuters"]),
        ("🎓 Eğitim",  ["Udemy", "Coursera", "LinkedIn Learning", "Khan Academy"]),
    ]

    def _show_site_popup(self, anchor_widget):
        """Anchor widget'ın altında site listesi popup'ı açar."""
        if self._site_popup and tk.Toplevel.winfo_exists(self._site_popup):
            return   # zaten açık

        popup = tk.Toplevel(self.root)
        popup.overrideredirect(True)   # başlık çubuğu yok
        popup.configure(bg=BORDER)
        self._site_popup = popup

        # İçerik
        inner = tk.Frame(popup, bg=SURFACE2, padx=16, pady=12)
        inner.pack(padx=1, pady=1, fill="both", expand=True)

        tk.Label(inner, text="Desteklenen Popüler Siteler",
                 bg=SURFACE2, fg=ACCENT_L,
                 font=("Helvetica", 11, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        for r, (category, sites) in enumerate(self.POPULAR_SITES, start=1):
            tk.Label(inner, text=category,
                     bg=SURFACE2, fg=TEXT2,
                     font=("Helvetica", 9, "bold")).grid(
                row=r, column=0, sticky="nw", padx=(0, 16), pady=(2, 0))

            site_text = "\n".join(sites)
            tk.Label(inner, text=site_text,
                     bg=SURFACE2, fg=TEXT,
                     font=("Helvetica", 10),
                     justify="left").grid(
                row=r, column=1, sticky="w", pady=(2, 0))

        tk.Label(inner,
                 text="✦  ve 1000'den fazla site daha…",
                 bg=SURFACE2, fg=TEXT3,
                 font=("Helvetica", 9, "italic")).grid(
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
        card = self._card(row=2, title="1️⃣  Video Linkini Yapıştırın",
                          hint="YouTube, Instagram, Twitter ve 1000+ site desteklenir")
        card.columnconfigure(0, weight=1)

        self.url_var = tk.StringVar()
        entry = ttk.Entry(card, textvariable=self.url_var, font=("Helvetica", 12))
        entry.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        entry.bind("<Return>", lambda _: self.fetch_info())

        tk.Label(card,
                 text="Örnek: https://www.youtube.com/watch?v=...",
                 bg=SURFACE, fg=TEXT3,
                 font=("Helvetica", 9)).grid(row=1, column=0, sticky="w")

        self.fetch_btn = ttk.Button(card, text="🔍  Video Bilgisini Getir",
                                    style="Ghost.TButton",
                                    command=self.fetch_info)
        self.fetch_btn.grid(row=0, column=1, padx=(12, 0))

    def _build_info_section(self):
        outer = tk.Frame(self.main, bg=BG)
        outer.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 4))
        outer.columnconfigure(0, weight=1)
        outer.grid_remove()
        self._info_frame = outer

        inner = tk.Frame(outer, bg="#16213e", highlightbackground="#2d3a6d",
                         highlightthickness=1)
        inner.pack(fill="x", padx=0)
        inner.columnconfigure(1, weight=1)

        # Sol yeşil çubuk
        tk.Frame(inner, bg=SUCCESS, width=4).pack(side="left", fill="y")

        content = tk.Frame(inner, bg="#16213e")
        content.pack(side="left", fill="both", expand=True, padx=16, pady=14)

        tk.Label(content, text="✅ Video bulundu!",
                 bg="#16213e", fg=SUCCESS,
                 font=("Helvetica", 10, "bold")).pack(anchor="w")

        self.info_title = tk.Label(content, text="",
                                   bg="#16213e", fg=TEXT,
                                   font=("Helvetica", 13, "bold"),
                                   wraplength=640, justify="left")
        self.info_title.pack(anchor="w", pady=(4, 0))

        self.info_meta = tk.Label(content, text="",
                                  bg="#16213e", fg=TEXT2,
                                  font=("Helvetica", 10))
        self.info_meta.pack(anchor="w", pady=(4, 0))

    def _build_quality_section(self):
        card = self._card(row=4, title="2️⃣  Kalite Seçin",
                          hint="Video yüklendikten sonra desteklenen kaliteler görünür")
        self.qual_body = card
        self.qual_btns = []
        # Başlangıçta bekleme mesajı
        self._qual_placeholder = tk.Label(
            card, text="⏳  Önce video linkini getirin — desteklenen kaliteler burada listelenecek",
            bg=SURFACE, fg=TEXT3, font=("Helvetica", 10), anchor="w")
        self._qual_placeholder.grid(row=0, column=0, sticky="w", pady=8)

    def _build_folder_section(self):
        card = self._card(row=5, title="3️⃣  Kayıt Klasörü",
                          hint="İndirilen dosyalar buraya kaydedilir")
        card.columnconfigure(0, weight=1)

        self.folder_lbl = tk.Label(card,
                                   text="📂  " + self.download_path,
                                   bg=SURFACE2,
                                   fg=TEXT, font=("Helvetica", 11),
                                   anchor="w", padx=12, pady=10)
        self.folder_lbl.grid(row=0, column=0, sticky="ew", pady=(0, 0))

        ttk.Button(card, text="📁  Klasör Seç",
                   style="Ghost.TButton",
                   command=self.change_path).grid(row=0, column=1, padx=(12, 0))

    def _build_action_section(self):
        act = tk.Frame(self.main, bg=BG)
        act.grid(row=6, column=0, sticky="ew", padx=24, pady=(8, 4))
        act.columnconfigure(0, weight=1)

        self.dl_btn = ttk.Button(act,
                                 text="⬇️  İNDİRMEYE BAŞLA",
                                 style="Primary.TButton",
                                 command=self.start_download,
                                 state="disabled")
        self.dl_btn.grid(row=0, column=0, sticky="ew")

        self.cancel_btn = ttk.Button(act, text="⛔  İptal Et",
                                     style="Cancel.TButton",
                                     command=self.cancel_download)
        self.cancel_btn.grid(row=0, column=1, padx=(12, 0))
        self.cancel_btn.grid_remove()

        # İlerleme
        self.prog_bar = ttk.Progressbar(act, mode="determinate", maximum=100)
        self.prog_bar.grid(row=1, column=0, columnspan=2, sticky="ew",
                           pady=(12, 4))
        self.prog_bar.grid_remove()

        self.prog_lbl = tk.Label(act, text="", bg=BG, fg=TEXT2,
                                 font=("Helvetica", 10))
        self.prog_lbl.grid(row=2, column=0, columnspan=2, sticky="w")
        self.prog_lbl.grid_remove()

    def _build_log_section(self):
        card = self._card(row=7, title="📋  Durum Günlüğü",
                          hint="Neler olduğunu buradan takip edebilirsiniz",
                          pady_bottom=24)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        self.log_box = scrolledtext.ScrolledText(
            card, height=10, state="disabled",
            font=("Courier", 10), bg="#0a0a12", fg="#c4b5fd",
            relief="flat", borderwidth=0, wrap="word",
            insertbackground=TEXT, selectbackground=ACCENT)
        self.log_box.grid(row=0, column=0, sticky="nsew")

        self.main.rowconfigure(7, weight=1)

    # ── Kart Yardımcısı ────────────────────────────────────────────────────
    def _card(self, row, title="", hint="", pady_bottom=4):
        outer = tk.Frame(self.main, bg=SURFACE,
                         highlightbackground=BORDER, highlightthickness=1)
        outer.grid(row=row, column=0, sticky="ew" if row != 7 else "nsew",
                   padx=24, pady=(0, pady_bottom))
        self.main.columnconfigure(0, weight=1)

        inner = tk.Frame(outer, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        inner.columnconfigure(0, weight=1)

        if title:
            hrow = tk.Frame(inner, bg=SURFACE)
            hrow.grid(row=0, column=0, columnspan=10, sticky="ew", pady=(0, 12))
            tk.Label(hrow, text=title, bg=SURFACE, fg=TEXT,
                     font=("Helvetica", 13, "bold")).pack(side="left")
            if hint:
                tk.Label(hrow, text=hint, bg=SURFACE, fg=TEXT3,
                         font=("Helvetica", 9)).pack(side="left", padx=(12, 0),
                                                      pady=(3, 0))

        body = tk.Frame(inner, bg=SURFACE)
        body.grid(row=1, column=0, columnspan=10, sticky="ew")
        body.columnconfigure(0, weight=1)
        return body

    # ── Bağımlılık Kontrolü ────────────────────────────────────────────────
    def _check_deps(self):
        for tool, install in [("yt-dlp", "pip install yt-dlp"),
                               ("ffmpeg", "brew install ffmpeg")]:
            try:
                subprocess.run([tool, "--version"], capture_output=True, timeout=5)
            except FileNotFoundError:
                self.log(f"⚠️  '{tool}' bulunamadı → {install}", warn=True)

        self.log("👋 Hoşgeldiniz! Bir video linki yapıştırıp 'Video Bilgisini Getir'e tıklayın.")

    # ── Kalite Seçimi ──────────────────────────────────────────────────────
    def _select_qual(self, idx):
        """idx: active_presets içindeki sıra"""
        self.selected_idx = idx
        for i, btn in enumerate(self.qual_btns):
            btn.configure(style="QualSel.TButton" if i == idx else "Qual.TButton")

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
            "Full HD 1080p": 1080,
            "HD 720p": 720,
            "Orta 480p": 480,
            "Düşük 360p": 360,
        }

        filtered = []
        for label, fmt, audio_only, desc in PRESETS:
            if audio_only:
                if has_audio:
                    filtered.append((label, fmt, audio_only, desc))
            elif label == "🏆 En İyi Kalite":
                if available_heights:          # video varsa her zaman ekle
                    filtered.append((label, fmt, audio_only, desc))
            else:
                needed = height_map.get(label, 0)
                if needed and max_h >= needed:
                    filtered.append((label, fmt, audio_only, desc))

        self.active_presets = filtered

        if not filtered:
            tk.Label(self.qual_body,
                     text="⚠️ Bu video için indirilebilir format bulunamadı.",
                     bg=SURFACE, fg=WARN, font=("Helvetica", 10)).grid(
                row=0, column=0, sticky="w", pady=8)
            return

        max_col = 4
        for i, (label, _, _, desc) in enumerate(filtered):
            col = i % max_col
            row = i // max_col
            f = tk.Frame(self.qual_body, bg=SURFACE)
            f.grid(row=row, column=col, padx=(0, 8), pady=(0, 8), sticky="nsew")
            self.qual_body.columnconfigure(col, weight=1)

            style = "QualSel.TButton" if i == 0 else "Qual.TButton"
            btn = ttk.Button(f, text=label, style=style,
                             command=lambda idx=i: self._select_qual(idx))
            btn.pack(fill="x")
            tk.Label(f, text=desc, bg=SURFACE, fg=TEXT3,
                     font=("Helvetica", 8)).pack(pady=(2, 0))
            self.qual_btns.append(btn)

        self.log(f"📊 {len(filtered)} kalite seçeneği bulundu (max {max_h}p)")

    # ── Video Bilgisi ──────────────────────────────────────────────────────
    def fetch_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Uyarı", "Lütfen bir video linki yapıştırın! 🔗")
            return
        self.fetch_btn.configure(state="disabled", text="⏳  Yükleniyor…")
        self.dl_btn.configure(state="disabled")
        if self._info_frame:
            self._info_frame.grid_remove()
        self.log("🔍 Video bilgisi alınıyor, lütfen bekleyin…")
        threading.Thread(target=self._fetch_thread, args=(url,), daemon=True).start()

    def _fetch_thread(self, url):
        try:
            r = subprocess.run(
                ["yt-dlp", "--no-check-certificate", "-j", "--no-playlist", url],
                capture_output=True, text=True, timeout=45)
            if r.returncode != 0:
                self.root.after(0, self.log,
                                f"❌ Hata: {r.stderr.strip()[:200]}", True)
                return
            info = json.loads(r.stdout)
            self.video_info = info
            self.root.after(0, self._show_info, info)
        except subprocess.TimeoutExpired:
            self.root.after(0, self.log,
                            "⏱️ Bağlantı zaman aşımına uğradı. İnternet bağlantınızı kontrol edin.", True)
        except json.JSONDecodeError:
            self.root.after(0, self.log, "❌ Video bilgisi okunamadı.", True)
        except FileNotFoundError:
            self.root.after(0, self.log,
                            "❌ yt-dlp bulunamadı. Terminal'de: pip install yt-dlp", True)
        except Exception as e:
            self.root.after(0, self.log, f"❌ Hata: {e}", True)
        finally:
            self.root.after(0, lambda: self.fetch_btn.configure(
                state="normal", text="🔍  Video Bilgisini Getir"))

    def _show_info(self, info):
        title    = info.get("title", "")
        uploader = info.get("uploader") or info.get("channel", "")
        duration = info.get("duration")
        views    = info.get("view_count")

        meta = []
        if uploader: meta.append(f"📺 {uploader}")
        if duration:  meta.append(f"⏱️ {self._fmt_dur(duration)}")
        if views:     meta.append(f"👁️ {views:,} görüntüleme")

        self.info_title.configure(text=title)
        self.info_meta.configure(text="   ·   ".join(meta))
        self._info_frame.grid()
        self._update_quality_buttons(info)   # ← kalite butonlarını güncelle
        self.dl_btn.configure(state="normal")
        self.log(f"✅ Video bulundu: {title[:80]}")

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

        label, fmt, audio_only, _ = self.active_presets[self.selected_idx]
        self.dl_btn.grid_remove()
        self.cancel_btn.grid()
        self.prog_bar["value"] = 0
        self.prog_bar.grid()
        self.prog_lbl.grid()
        self.prog_lbl.configure(text="⏳ Hazırlanıyor…")
        self.log(f"⬇️ İndiriliyor — {label}…")

        threading.Thread(
            target=self._dl_thread,
            args=(url, fmt, audio_only),
            daemon=True).start()

    def _dl_thread(self, url, fmt, audio_only):
        try:
            out = os.path.join(self.download_path, "%(title)s.%(ext)s")
            cmd = ["yt-dlp", "--no-check-certificate", "--newline",
                   "-f", fmt, "-o", out]
            if audio_only:
                cmd += ["--extract-audio", "--audio-format", "mp3",
                        "--audio-quality", "0"]
            else:
                cmd += ["--merge-output-format", "mp4"]
            cmd.append(url)

            self.download_proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True)

            for line in self.download_proc.stdout:
                line = line.rstrip()
                if line:
                    self.root.after(0, self._handle_line, line)

            self.download_proc.wait()
            rc = self.download_proc.returncode
            if rc == 0:
                self.root.after(0, self._on_success)
            elif rc not in (-15, 1):
                self.root.after(0, self.log,
                                f"❌ İndirme başarısız (kod {rc})", True)
        except Exception as e:
            self.root.after(0, self.log, f"❌ Hata: {e}", True)
        finally:
            self.download_proc = None
            self.root.after(0, self._reset_ui)

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
            parts = [f"📥 %{pct:.1f}"]
            if total: parts.append(f"📦 {total}")
            if speed: parts.append(f"🚀 {speed}")
            if eta and eta != "Unknown": parts.append(f"⏳ {eta} kaldı")
            self.prog_lbl.configure(text="   ·   ".join(parts))
            return

        if re.match(r'\[(Merger|ffmpeg|ExtractAudio)\]', line):
            self.log(f"⚙️ {line}")
            return

        if line.strip():
            self.log(line)

    def _on_success(self):
        self.prog_bar["value"] = 100
        self.prog_lbl.configure(text="✅ İndirme tamamlandı!")
        self.log(f"🎉 Dosya kaydedildi: {self.download_path}")
        if messagebox.askyesno("🎉 Tamamlandı!",
                               "Video başarıyla indirildi!\n\nKlasörü açmak ister misiniz?"):
            self._open_folder()

    def cancel_download(self):
        if self.download_proc:
            self.download_proc.terminate()
            self.log("⛔ İndirme iptal edildi.")

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
            self.log_box.tag_configure("warn", foreground="#f59e0b")
        else:
            self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernDownloader(root)
    root.mainloop()
