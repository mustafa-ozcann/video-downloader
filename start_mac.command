#!/bin/bash

# Çalıştırılan dosyanın dizinine git (çift tıklama için gerekli)
cd "$(dirname "$0")"

echo "================================"
echo "YouTube Video İndiricisi"
echo "================================"
echo ""

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 bulunamadı."
    echo "Lütfen 'brew install python' çalıştırın veya https://www.python.org/downloads/ üzerinden Python3 yükleyin."
    echo ""
    read -p "Çıkmak için Enter'a basın..."
    exit 1
fi

echo "✓ Python3 bulundu."

# Sanal ortam kontrolü
if [ ! -d "venv" ]; then
    echo "Sanal ortam (venv) oluşturuluyor, lütfen bekleyin..."
    python3 -m venv venv
fi

# Sanal ortamı aktif et
source venv/bin/activate

# Bağımlılıkları yükle
echo "Bağımlılıklar kontrol ediliyor..."
python3 -m pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "Uygulama başlatılıyor..."

# Uygulamayı başlat
python3 youtube_downloader.py
