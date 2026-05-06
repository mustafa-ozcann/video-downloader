# 📥 YouTube Video İndiricisi

YouTube videolarını farklı kalite ve formatlarda indirmeye yarayan **masaüstü GUI uygulaması**. `yt-dlp` motorunu kullanan, sade ve kullanımı kolay bir araçtır.

![Python](https://img.shields.io/badge/Python-3.7%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Özellikler

| Özellik | Detay |
|---|---|
| 🎬 Video kalitesi | En İyi, 4K, 1080p, 720p, 480p, 360p |
| 🎵 Ses indirme | MP3 formatında yüksek kalite |
| 📊 Gerçek zamanlı ilerleme | Hız, kalan süre ve boyut göstergesi |
| 📁 Klasör seçimi | İndirme konumunu özelleştirin |
| ℹ️ Video bilgisi | İndirmeden önce başlık, kanal ve süre önizlemesi |
| ❌ İptal desteği | İndirme sırasında kolayca iptal |

---

## 📋 Gereksinimler

- **Python** 3.7 veya üzeri
- **yt-dlp** — video indirme motoru
- **ffmpeg** — video ve ses akışlarını birleştirmek için zorunlu
- **tkinter** — Python ile birlikte gelir (genellikle ayrıca kurulum gerekmez)

---

## 🚀 Kurulum ve Çalıştırma

Projeyi kullanmaya başlamak çok basittir, terminal komutlarıyla uğraşmanıza gerek yoktur. Hazırlanan başlatıcı dosyalar, gerekli kütüphaneleri sizin için otomatik olarak kurar ve uygulamayı açar.

### 📥 Dosyaları İndirme
1. Bu sayfanın sağ üst köşesindeki yeşil **Code** butonuna tıklayın.
2. **Download ZIP** seçeneği ile projeyi bilgisayarınıza indirin.
3. İndirdiğiniz `.zip` dosyasını klasöre çıkartın.

### 🍎 macOS / Linux İçin
Çıkardığınız klasörün içindeki **`start_mac.command`** dosyasına **çift tıklayın**.
- *Not: İlk çalıştırmada macOS uyarı verirse, dosyaya **sağ tıklayıp** menüden "Aç" (Open) seçeneğini kullanabilirsiniz.*

### 🪟 Windows İçin
Çıkardığınız klasörün içindeki **`start_windows.bat`** dosyasına **çift tıklayın**.
- *Not: Sisteminizde Python'un kurulu olması ve kurulum aşamasında "Add Python to PATH" (Python'u PATH'e Ekle) seçeneğinin işaretlenmiş olması gerekmektedir.*

---

### 🔧 İleri Düzey (Manuel) Kurulum

#### 1. ffmpeg Kurulumu

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Windows:**
[https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) adresinden indirip `PATH`'e ekleyin.

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

1. **URL Girin** → YouTube video linkini ilgili alana yapıştırın
2. **Bilgi Al** → Butona tıklayarak video başlığını, kanalı ve süreyi görün
3. **Kalite Seçin** → İstediğiniz çözünürlüğü veya ses modunu seçin
4. **Klasör Seçin** *(isteğe bağlı)* → "Değiştir" ile özel kayıt konumu belirleyin
5. **İndir** → İndirme başlar; ilerleme çubuğu ve log anlık güncellenir
6. **Tamamlandı!** → Klasörü doğrudan uygulamadan açabilirsiniz

---

## 🔧 Sorun Giderme

**`yt-dlp` veya `ffmpeg` bulunamadı hatası**
```bash
pip install --upgrade yt-dlp
```

**Video indirilemiyor / format hatası**
YouTube zaman zaman değişiklik yapar; yt-dlp'yi güncellemeniz yeterlidir:
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
├── youtube_downloader.py   # Ana uygulama
├── start_windows.bat       # Windows için tek tıkla başlatıcı
├── start_mac.command       # macOS/Linux için tek tıkla başlatıcı
├── requirements.txt        # Python bağımlılıkları
└── README.md
```

---

## ⚠️ Yasal Uyarı

Bu araç yalnızca **telif hakkı bulunmayan veya kendi içeriğiniz olan** videoları indirmek için kullanılmalıdır. YouTube'un Hizmet Şartlarını ([Terms of Service](https://www.youtube.com/t/terms)) ihlal etmemeye dikkat edin. Kullanıcı, indirilen içeriklerin yasal sorumluluğunu kendisi üstlenir.

---

## 📄 Lisans

MIT License — dilediğiniz gibi kullanabilir, değiştirebilir ve dağıtabilirsiniz.
