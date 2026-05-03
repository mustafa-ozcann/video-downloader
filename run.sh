#!/bin/bash

# YouTube Video İndiricisi - Kurulum ve Başlatma Scripti

echo "================================"
echo "YouTube Video İndiricisi"
echo "================================"
echo ""

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 bulunamadı. Lütfen Python3'ü yükleyin."
    exit 1
fi

echo "✓ Python3 bulundu: $(python3 --version)"
echo ""

# yt-dlp kontrolü ve kurulumu
echo "Bağımlılıklar kontrol ediliyor..."
if ! python3 -c "import yt_dlp" 2>/dev/null; then
    echo "⚙️  yt-dlp yükleniyor..."
    python3 -m pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo "✓ yt-dlp başarıyla yüklendi"
    else
        echo "❌ yt-dlp yüklenirken hata oluştu"
        exit 1
    fi
else
    echo "✓ yt-dlp zaten yüklü"
fi

echo ""
echo "Uygulama başlatılıyor..."
echo ""

python3 youtube_downloader.py
