# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# macOS: venv + deps + ffmpeg/deno kurar, /Applications/Video Downloader.app oluşturur
./start_mac.command

# Direct launch (masaüstü / tkinter)
venv/bin/python3 youtube_downloader.py

# Web sürümü (yerel Flask sunucusu, http://127.0.0.1:8765; --lan ile aynı ağdaki telefonlar da erişir)
./start_web_mac.command            # veya: venv/bin/python3 web_app.py [--lan]

# Install/upgrade deps
venv/bin/python3 -m pip install -U -r requirements.txt
```

There are no tests and no linter configuration.

## Dependencies

- `yt-dlp` — video indirme motoru (`pip install yt-dlp`)
- `ffmpeg` — video+ses akışlarını birleştirmek için zorunlu (`brew install ffmpeg`)
- `deno` — yt-dlp'nin YouTube JS doğrulamalarını çözmesi için gerekli (`brew install deno`)
- `tkinter` — Python ile birlikte gelir

yt-dlp eskiyince YouTube `HTTP Error 403` döner; uygulama bu yüzden açılışta günde bir kez `pip install -U yt-dlp[default]` çalıştırır (`~/.video_downloader_last_update`). yt-dlp daima `sys.executable -m yt_dlp` ile çağrılır.

## Architecture

Single-file tkinter GUI app (`youtube_downloader.py`), single class `YouTubeDownloader`.

**State:**
- `self.selected_idx` — `PRESETS` listesindeki seçili kalite indeksi
- `self.video_info` — `yt-dlp -j` çıktısından parse edilen video metadata dict'i
- `self.download_process` — aktif `subprocess.Popen` nesnesi; `cancel_download()` bunu `.terminate()` ile sonlandırır

**Quality presets (`PRESETS` sabiti):** Her preset bir `(etiket, yt-dlp format seçici, ses_sadece)` tuple'ıdır. Format seçici daima `bestvideo+bestaudio` kalıbını kullanır — bu sayede yt-dlp en iyi video ve ses akışlarını ayrı ayrı indirip ffmpeg ile birleştirir. Ses modunda `--extract-audio --audio-format mp3` kullanılır.

**H.264 (Premiere uyumu):** Komut `build_download_cmd()` ile kurulur (masaüstü + web ortak). Arayüzdeki "H.264 · Premiere uyumlu" anahtarı açıkken (varsayılan) `-S res,fps,vcodec:h264,acodec:aac` ile aynı çözünürlükte H.264/AAC tercih edilir (YouTube'da ≤1080p genelde doğrudan H.264). İnen dosya yine VP9/AV1/Opus ise (örn. 4K) `ensure_h264()` ffprobe ile kontrol edip ffmpeg ile dönüştürür (macOS'ta önce `h264_videotoolbox`, olmazsa `libx264 -crf 18`). Son dosya yolu `--print-to-file after_move:filepath` ile alınır. Sadece ses (MP3) indirmeleri bu anahtardan etkilenmez.

**Threading model:** Tüm `yt-dlp` çağrıları daemon thread'lerde çalışır. Thread'lerden GUI güncellemeleri daima `self.root.after(0, fn)` ile yapılır.

**İndirme akışı:**
1. `fetch_info()` → `_fetch_thread` → `yt-dlp -j` → `_show_info()` (bilgi kartını gösterir)
2. `start_download()` → `_download_thread` → `yt-dlp --newline -f <fmt> --merge-output-format mp4`
3. `_handle_line()` her çıktı satırını parse eder: `[download] X%` satırları ilerleme çubuğunu günceller, diğerleri log'a yazılır
4. `_on_success()` → klasör açma diyalogu

## Web sürümü (`web_app.py` + `web/index.html`)

Yerel çalışan Flask sunucusu; `PRESETS`, `_ytdlp_cmd`, `UPDATE_STAMP` gibi ortak parçaları `youtube_downloader.py`'den import eder. Her indirme bir "job" olur: yt-dlp temp klasöre (`$TMPDIR/video_downloader_web/`) indirir, tarayıcı `/api/jobs/<id>` ile ilerlemeyi yoklar, bitince `/api/jobs/<id>/file` ile dosyayı alır; işler 2 saat sonra silinir. URL'ler `^https?://` ile doğrulanır ve yt-dlp'ye `--` sonrasında verilir (seçenek enjeksiyonunu önlemek için).

Vercel/serverless'a deploy edilemez: YouTube veri merkezi IP'lerini engelliyor, indirme linkleri IP'ye kilitli, fonksiyon yanıtı 4.5 MB ile sınırlı ve ffmpeg yok.
