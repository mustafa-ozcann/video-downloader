#!/bin/bash

# Projenin bulunduğu dizin (bu dosyanın konumu)
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

APP_NAME="Video Downloader"
APP_PATH="/Applications/${APP_NAME}.app"

echo "================================"
echo "  Video Downloader"
echo "  Kurulum & Uygulama Oluşturucu"
echo "================================"
echo ""

# ── 1. Python kontrolü ───────────────────────────────────────────
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 bulunamadı!"
    echo "   https://www.python.org/downloads/ adresinden yükleyin."
    read -p "Çıkmak için Enter'a basın..."
    exit 1
fi
echo "✅ Python3 bulundu: $(python3 --version)"
echo ""

# ── 2. Sanal ortam oluştur ───────────────────────────────────────
if [ ! -d "$PROJECT_DIR/venv" ]; then
    echo "🔧 Sanal ortam oluşturuluyor..."
    python3 -m venv "$PROJECT_DIR/venv"
fi

source "$PROJECT_DIR/venv/bin/activate"

# ── 3. Python paketleri (Pillow dahil): pip bunlari PyPI'dan otomatik indirir ───
echo "📦 Bağımlılıklar indirilip kuruluyor…"
python3 -m pip install --upgrade pip -q
python3 -m pip install -q -U -r "$PROJECT_DIR/requirements.txt"
echo "✅ Bağımlılıklar yüklendi/güncellendi (yt-dlp: $(python3 -m yt_dlp --version))."
echo ""

# ── 3b. ffmpeg (birleştirme) ve deno (YouTube JS doğrulaması) ────
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
for tool in ffmpeg deno; do
    if command -v "$tool" &> /dev/null; then
        echo "✅ $tool bulundu."
    elif command -v brew &> /dev/null; then
        echo "🔧 $tool kuruluyor (brew)…"
        brew install "$tool" || echo "⚠️  $tool kurulamadı — elle kurun: brew install $tool"
    else
        echo "⚠️  $tool bulunamadı. Homebrew kurup şu komutu çalıştırın: brew install $tool"
        echo "    (Homebrew: https://brew.sh)"
    fi
done
echo ""

# ── 4. .app paketi oluştur ───────────────────────────────────────
echo "🛠  Uygulama paketi oluşturuluyor: ${APP_PATH}"

# Varsa eski .app'i sil
if [ -d "$APP_PATH" ]; then
    rm -rf "$APP_PATH"
fi

# Klasör yapısını oluştur
mkdir -p "${APP_PATH}/Contents/MacOS"
mkdir -p "${APP_PATH}/Contents/Resources"

# İkon dosyasını kopyala
if [ -f "$PROJECT_DIR/app_icon.icns" ]; then
    cp "$PROJECT_DIR/app_icon.icns" "${APP_PATH}/Contents/Resources/appIcon.icns"
fi

# ── Info.plist ────────────────────────────────────────────────────
cat > "${APP_PATH}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.user.videodownloader</string>
    <key>CFBundleName</key>
    <string>Video Downloader</string>
    <key>CFBundleDisplayName</key>
    <string>Video Downloader</string>
    <key>CFBundleIconFile</key>
    <string>appIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
EOF

# ── Launcher script ───────────────────────────────────────────────
cat > "${APP_PATH}/Contents/MacOS/launcher" << EOF
#!/bin/bash
exec > "/tmp/video_downloader_app.log" 2>&1
export PATH="${PROJECT_DIR}/venv/bin:/opt/homebrew/bin:/usr/local/bin:\$HOME/.deno/bin:\$PATH"
if [ ! -x "${PROJECT_DIR}/venv/bin/python3" ] || [ ! -f "${PROJECT_DIR}/youtube_downloader.py" ]; then
    /usr/bin/osascript -e 'display alert "Video Downloader" message "Proje klasörü bulunamadı veya taşındı:\n${PROJECT_DIR}\n\nKlasördeki start_mac.command dosyasını tekrar çalıştırın."'
    exit 1
fi
"${PROJECT_DIR}/venv/bin/python3" "${PROJECT_DIR}/youtube_downloader.py" || \
    /usr/bin/osascript -e 'display alert "Video Downloader açılamadı" message "Ayrıntılar: /tmp/video_downloader_app.log"'

EOF

chmod +x "${APP_PATH}/Contents/MacOS/launcher"

echo "✅ Uygulama oluşturuldu: ${APP_PATH}"
echo ""

# ── 5. Gatekeeper'ı atlamak için imza ────────────────────────────
xattr -rd com.apple.quarantine "$APP_PATH" 2>/dev/null || true

echo "🎉 Kurulum tamamlandı!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Artık Uygulamalar klasöründen"
echo "  \"${APP_NAME}\" uygulamasını açabilirsin."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# İstersen şimdi aç
read -p "Uygulamayı şimdi açmak ister misin? (e/h): " answer
if [[ "$answer" == "e" || "$answer" == "E" ]]; then
    open "$APP_PATH"
fi
