# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
# Quickstart (installs deps if missing, then launches)
./run.sh

# Direct launch (assumes yt-dlp is already installed)
python3 youtube_downloader.py

# Install dependency
pip install -r requirements.txt   # yt-dlp>=2024.1.0
```

There are no tests and no linter configuration.

## Dependencies

- `yt-dlp` — video indirme motoru (`pip install yt-dlp`)
- `ffmpeg` — video+ses akışlarını birleştirmek için zorunlu (`brew install ffmpeg`)
- `tkinter` — Python ile birlikte gelir

## Architecture

Single-file tkinter GUI app (`youtube_downloader.py`), single class `YouTubeDownloader`.

**State:**
- `self.selected_idx` — `PRESETS` listesindeki seçili kalite indeksi
- `self.video_info` — `yt-dlp -j` çıktısından parse edilen video metadata dict'i
- `self.download_process` — aktif `subprocess.Popen` nesnesi; `cancel_download()` bunu `.terminate()` ile sonlandırır

**Quality presets (`PRESETS` sabiti):** Her preset bir `(etiket, yt-dlp format seçici, ses_sadece)` tuple'ıdır. Format seçici daima `bestvideo+bestaudio` kalıbını kullanır — bu sayede yt-dlp en iyi video ve ses akışlarını ayrı ayrı indirip ffmpeg ile birleştirir. Ses modunda `--extract-audio --audio-format mp3` kullanılır.

**Threading model:** Tüm `yt-dlp` çağrıları daemon thread'lerde çalışır. Thread'lerden GUI güncellemeleri daima `self.root.after(0, fn)` ile yapılır.

**İndirme akışı:**
1. `fetch_info()` → `_fetch_thread` → `yt-dlp -j` → `_show_info()` (bilgi kartını gösterir)
2. `start_download()` → `_download_thread` → `yt-dlp --newline -f <fmt> --merge-output-format mp4`
3. `_handle_line()` her çıktı satırını parse eder: `[download] X%` satırları ilerleme çubuğunu günceller, diğerleri log'a yazılır
4. `_on_success()` → klasör açma diyalogu
