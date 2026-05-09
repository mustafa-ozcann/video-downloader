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
python3 -m pip install -q -r "$PROJECT_DIR/requirements.txt"
echo "✅ Bağımlılıklar yüklendi (Pillow + yt-dlp Pip üzerinden alındı)."
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
export PATH="${PROJECT_DIR}/venv/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH"
"${PROJECT_DIR}/venv/bin/python3" "${PROJECT_DIR}/youtube_downloader.py"
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
