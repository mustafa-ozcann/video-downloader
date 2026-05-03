# YouTube Video İndiricisi

yt-dlp kullanarak YouTube videolarını farklı formatlarda ve kalitelerde indiren GUI uygulaması.

## Gereksinimler

- Python 3.7+
- yt-dlp
- tkinter (Python ile birlikte geliyor)

## Kurulum

### 1. yt-dlp'i yükleyin

```bash
pip install -r requirements.txt
```

Veya doğrudan:

```bash
pip install yt-dlp
```

### 2. Programı çalıştırın

```bash
python youtube_downloader.py
```

## Kullanım

1. **YouTube URL Girin**: Belirtilen alana YouTube video linkini yapıştırın
2. **Formatları Yükle**: "Formatları Yükle" butonuna tıklayarak video formatlarını getirin
3. **Kalite Seçin**: Açılan listeden istediğiniz format/kaliteyi seçin
   - **Best**: En iyi kalite
   - **720p, 480p, 360p**: Video kaliteleri
   - **Audio Only**: Sadece ses
4. **İndirme Klasörünü Seçin** (İsteğe bağlı): "Değiştir" butonuyla indirme klasörünü seçin
5. **İndir**: "İndir" butonuna tıklayarak videoyu indirin

## Özellikler

- 📺 Farklı video kaliteleri (720p, 480p, 360p vb.)
- 🔊 Sadece ses indirme seçeneği
- 🎬 Video formatı seçimi
- 📁 Özel indirme klasörü seçimi
- 📊 Durumu gerçek zamanlı gösterme
- 🔍 Kalite filtreleme

## Sorun Giderme

**Hata: "yt-dlp yüklü değil"**
```bash
pip install yt-dlp --upgrade
```

**Video açılamıyor**
- YouTube'un güvenlik güncellemeleri nedeniyle yt-dlp'i güncellemeyi deneyin:
```bash
pip install --upgrade yt-dlp
```

**Yavaş indirme**
- İnternet hızınızı kontrol edin
- Daha düşük bir kalite seçmeyi deneyin

## İpuçları

- Çoğu video birden fazla format/kalite seçeneğine sahiptir
- Format ID'si ve codec bilgileri listede gösterilmektedir
- Durum penceresinde indirme ilerlemesini takip edebilirsiniz
