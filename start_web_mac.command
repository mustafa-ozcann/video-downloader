#!/bin/bash
# Video İndirici — web sürümü (çift tıkla başlat)
# Telefondan da kullanmak için:  ./start_web_mac.command --lan
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.deno/bin:$PATH"

if [ ! -x "$PROJECT_DIR/venv/bin/python3" ]; then
    echo "🔧 Sanal ortam oluşturuluyor…"
    python3 -m venv "$PROJECT_DIR/venv" || { echo "❌ Python3 bulunamadı."; read -p "Enter…"; exit 1; }
fi
if ! "$PROJECT_DIR/venv/bin/python3" -c "import flask, yt_dlp" 2>/dev/null; then
    echo "📦 Bağımlılıklar kuruluyor…"
    "$PROJECT_DIR/venv/bin/python3" -m pip install -q -U -r "$PROJECT_DIR/requirements.txt"
fi
for tool in ffmpeg deno; do
    command -v "$tool" &>/dev/null || echo "⚠️  $tool bulunamadı → brew install $tool"
done

exec "$PROJECT_DIR/venv/bin/python3" "$PROJECT_DIR/web_app.py" "$@"
