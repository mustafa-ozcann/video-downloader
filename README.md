# 🎬 Video İndirici

**YouTube, Instagram, TikTok, Twitter/X, Facebook ve 1000'den fazla platformu** destekleyen masaüstü video indirme uygulaması. `yt-dlp` motorunu kullanan, modern koyu temalı GUI ile çalışır — terminal komutlarına gerek yok.

![Python](https://img.shields.io/badge/Python-3.7%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)
![Sites](https://img.shields.io/badge/Desteklenen%20Site-1000%2B-purple)

---

## 🌐 Desteklenen Platformlar

Uygulama, `yt-dlp` sayesinde 1000'den fazla siteyi destekler. Öne çıkan platformlar:

| Kategori | Platformlar |
|---|---|
| 📺 Video | YouTube, Vimeo, Dailymotion, Twitch, TED |
| 📸 Sosyal Medya | Instagram, TikTok, Twitter / X, Facebook, Reddit |
| 🎵 Müzik | SoundCloud, Bandcamp, Mixcloud, Audiomack |
| 📰 Haber | BBC, CNN, Bloomberg, Reuters |
| 🎓 Eğitim | Udemy, Coursera, LinkedIn Learning, Khan Academy |

Desteklenen tüm siteler için: [yt-dlp desteklenen siteler listesi](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## ✨ Özellikler

| Özellik | Detay |
|---|---|
| 🌐 1000+ site desteği | YouTube'dan Instagram'a, TikTok'tan BBC'ye tek araç |
| 🎬 Çoklu video kalitesi | En İyi, 4K, 1080p, 720p, 480p, 360p |
| 🎵 Ses indirme | MP3 formatında yüksek kalite (320kbps) |
| 📊 Gerçek zamanlı ilerleme | Yüzde, hız, kalan süre ve dosya boyutu göstergesi |
| 🔍 Video önizleme | İndirmeden önce başlık, kanal ve süreyi görün |
| 📁 Klasör seçimi | İndirme konumunu özelleştirin |
| ⛔ İptal desteği | İndirme sırasında tek tıkla iptal |
| 🎨 Modern koyu tema | Göz yormayan karanlık arayüz |
| 🖥️ Çapraz platform | macOS, Windows ve Linux desteği |

---

## 📋 Gereksinimler

- **Python** 3.7 veya üzeri
- **yt-dlp** — video indirme motoru (`pip install yt-dlp`)
- **ffmpeg** — video ve ses akışlarını birleştirmek için zorunlu
- **tkinter** — Python ile birlikte gelir (genellikle ayrıca kurulum gerekmez)

---

## 🚀 Kurulum ve Çalıştırma

Terminal komutlarıyla uğraşmanıza gerek yok. Hazırlanan başlatıcı dosyalar gerekli bağımlılıkları otomatik kurar.

### 📥 Projeyi İndirin

1. Bu sayfanın sağ üst köşesindeki yeşil **Code** butonuna tıklayın.
2. **Download ZIP** ile projeyi indirin ve bir klasöre çıkartın.

### 🍎 macOS İçin

Klasör içindeki **`start_mac.command`** dosyasına **çift tıklayın**.

- Otomatik olarak sanal ortam oluşturur, bağımlılıkları kurar ve `/Applications/Video Downloader.app` paketini oluşturur.
- İlk çalıştırmada macOS güvenlik uyarısı verirse dosyaya **sağ tıklayıp** "Aç" (Open) seçeneğini kullanın.
- Kurulum sonrası Uygulamalar klasöründeki **Video Downloader** ikonuna çift tıklayarak açabilirsiniz.

### 🪟 Windows İçin

Klasör içindeki **`start_windows.bat`** dosyasına **çift tıklayın**.

- Python kurulumunda "Add Python to PATH" seçeneğinin işaretli olması gerekir.

---

### 🔧 Manuel Kurulum

#### 1. ffmpeg Kurulumu

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Windows:**  
[ffmpeg.org/download.html](https://ffmpeg.org/download.html) adresinden indirip `PATH`'e ekleyin.

**Linux (Ubuntu/Debian):**
```bash
sudo apt install ffmpeg
```

#### 2. Python Bağımlılıklarını Kurun

```bash
pip install -r requirements.txt
```

#### 3. Uygulamayı Çalıştırın

```bash
python3 youtube_downloader.py
```

---

## 🖥️ Kullanım

1. **URL Girin** → Herhangi bir desteklenen platform linkini yapıştırın
2. **Bilgi Al** → Butona tıklayarak video başlığını, kanalı ve süreyi görün
3. **Kalite Seçin** → Videoya göre otomatik filtrelenen kalite seçeneklerinden birini seçin
4. **Klasör Seçin** *(isteğe bağlı)* → Özel kayıt konumu belirleyin
5. **İndir** → İndirme başlar; ilerleme çubuğu ve durum günlüğü anlık güncellenir
6. **Tamamlandı!** → Klasörü doğrudan uygulamadan açabilirsiniz

---

## 🔧 Sorun Giderme

**`yt-dlp` veya `ffmpeg` bulunamadı hatası**
```bash
pip install --upgrade yt-dlp
brew install ffmpeg   # macOS
```

**Video indirilemiyor / format hatası**  
Platformlar zaman zaman değişiklik yapar; yt-dlp'yi güncel tutun:
```bash
pip install --upgrade yt-dlp
```

**tkinter bulunamadı (Linux)**
```bash
sudo apt install python3-tk
```

**Yavaş indirme**  
İnternet hızınızı kontrol edin veya daha düşük bir kalite seçin.

---

## 📂 Proje Yapısı

```
.
├── youtube_downloader.py   # Ana uygulama (tek dosya)
├── start_mac.command       # macOS için tek tıkla kurulum + .app oluşturucu
├── start_windows.bat       # Windows için tek tıkla başlatıcı
├── requirements.txt        # Python bağımlılıkları
├── app_icon.icns           # macOS uygulama ikonu
├── app_icon.png            # Uygulama ikonu (PNG)
└── README.md
```

---

## ⚠️ Yasal Uyarı

Bu araç yalnızca **telif hakkı bulunmayan veya kendi içeriğiniz olan** videoları indirmek için kullanılmalıdır. İçerik paylaşım platformlarının kullanım şartlarına uymak kullanıcının sorumluluğundadır. İndirilen içeriklerin yasal sorumluluğu kullanıcıya aittir.

---

## 📄 Lisans

MIT License — dilediğiniz gibi kullanabilir, değiştirebilir ve dağıtabilirsiniz.
