# YouTube Video İndiricisi Teknik Raporu

## 1. Proje Özeti

Bu proje, YouTube videolarını masaüstü arayüzü üzerinden indirmek için geliştirilmiş bir Python uygulamasıdır. Kullanıcıdan alınan video adresi doğrulanır, video bilgileri çekilir ve seçilen kaliteye göre indirme işlemi başlatılır. Arayüz, indirme durumunu gerçek zamanlı gösterir ve işlem tamamlandığında kayıt klasörünü açma seçeneği sunar.

Projenin ana hedefi, komut satırı araçlarını kullanıcı dostu bir grafik arayüzle birleştirerek YouTube indirme sürecini sadeleştirmektir.

## 2. Temel Amaç

Uygulamanın ana amacı şunlardır:

- YouTube video bilgisini hızlıca almak
- Farklı çözünürlüklerde indirme seçeneği sunmak
- Sadece ses indirme desteği vermek
- İndirme sürecini görsel olarak takip edilebilir hale getirmek
- Kullanıcıya indirilen dosyanın kaydedildiği klasörü yönetme imkanı vermek

## 3. Kullanılan Teknolojiler

### 3.1 Python

Proje tamamen Python ile yazılmıştır. Hem arayüz hem de dış komut çalıştırma, veri ayrıştırma ve dosya yolu yönetimi Python standart kütüphaneleriyle yapılmaktadır.

### 3.2 Tkinter

Kullanıcı arayüzü için standart `tkinter` ve `ttk` bileşenleri kullanılmıştır. Arayüzde:

- URL giriş alanı
- Bilgi alma butonu
- Hazır kalite seçenekleri
- Kayıt klasörü seçimi
- İndirme ve iptal kontrolleri
- İlerleme çubuğu
- Durum günlüğü

bulunmaktadır.

### 3.3 yt-dlp

İndirme motoru olarak `yt-dlp` kullanılmaktadır. Proje, video bilgisini almak için `yt-dlp -j` komutunu, indirme için ise format seçimiyle birlikte `yt-dlp` komutunu kullanır. Kalite seçimi ve ses çıkarma işlemleri doğrudan bu araç üzerinden yönetilir.

### 3.4 ffmpeg

Video ve ses akışlarını birleştirmek için `ffmpeg` gerekir. Özellikle video indirmelerinde ayrı akışların birleştirilmesi bu araçla yapılır. Ses indirme modunda da dönüştürme işlemi için dolaylı olarak kullanılır.

### 3.5 Standart Kütüphaneler

Projede aşağıdaki Python standart modülleri aktif olarak kullanılır:

- `threading` : GUI'nin kilitlenmemesi için arka plan işlemleri
- `subprocess` : `yt-dlp` ve sistem komutlarını çalıştırmak için
- `json` : video meta verisini ayrıştırmak için
- `os` ve `pathlib` : dosya ve klasör yolları için
- `re` : indirme ilerleme satırlarını okumak için
- `sys` : işletim sistemi kontrolü ve platforma göre klasör açma için

## 4. Proje Yapısı

Proje küçük ve tek giriş noktalı bir yapıya sahiptir. Ana bileşenler şöyledir:

- `youtube_downloader.py` : uygulamanın tamamı burada yer alır
- `run.sh` : kurulumu kontrol eden ve uygulamayı başlatan yardımcı betik
- `requirements.txt` : Python bağımlılığı tanımı
- `README.md` : kullanıcıya yönelik kısa kullanım dokümantasyonu
- `clip/` : örnek çıktı dosyalarının bulunduğu klasör

Bu yapı, uygulamanın bakımını kolaylaştıran sade bir mimari sunar. Ayrı servis katmanları, test altyapısı veya modüler paketleme bulunmamaktadır.

## 5. Çalışma Mantığı

Uygulama, tek sınıf üzerinden yönetilir: `YouTubeDownloader`.

### 5.1 Başlatma

Uygulama çalıştırıldığında ana pencere oluşturulur, stil ayarları uygulanır ve arayüz bileşenleri kurulur. Ardından temel bağımlılıklar kontrol edilir. `yt-dlp` veya `ffmpeg` eksikse durum günlüğüne uyarı yazılır.

### 5.2 Video Bilgisi Alma

Kullanıcı bir YouTube URL’si girip bilgi alma işlemini başlattığında uygulama arka planda bir thread açar. Bu thread:

1. `yt-dlp --no-check-certificate -j --no-playlist <url>` komutunu çalıştırır
2. Dönen JSON çıktısını ayrıştırır
3. Video başlığı, kanal adı, süre ve görüntülenme sayısı gibi bilgileri arayüze yansıtır

Bu işlem arka planda yürütüldüğü için arayüz donmaz.

### 5.3 Kalite Seçimi

Uygulama içinde önceden tanımlanmış kalite presetleri vardır:

- En İyi
- 4K
- 1080p
- 720p
- 480p
- 360p
- Ses (MP3)

Her preset, `yt-dlp` format seçici ile eşleştirilmiştir. Video modunda en iyi video ve ses akışları seçilip birleştirilir. Ses modunda ise sadece ses indirilip MP3’e dönüştürülür.

### 5.4 İndirme Süreci

İndirme başladığında uygulama yine ayrı bir thread kullanır. Bu thread:

1. Çıktı dosya şablonunu kullanıcı klasörüne göre hazırlar
2. Seçili preset’e uygun `yt-dlp` komutunu kurar
3. Gerekirse `--merge-output-format mp4` ile video ve ses birleştirmesi yapar
4. Ses modu seçildiyse `--extract-audio --audio-format mp3` kullanır
5. Komut çıktısını satır satır okuyarak ilerlemeyi arayüze yansıtır

İlerleme satırları düzenli ifade ile ayrıştırılır ve yüzde, hız, tahmini kalan süre gibi bilgiler ilerleme alanında gösterilir.

### 5.5 Arayüz Güncelleme Modeli

Tkinter tek ana iş parçacığında çalıştığı için, arka plan thread’lerinden doğrudan arayüz güncellemesi yapılmaz. Bunun yerine `root.after(0, ...)` çağrılarıyla GUI güncellemeleri ana döngüye güvenli biçimde aktarılır. Bu yaklaşım, uygulamanın stabil kalmasını sağlar.

## 6. Önemli Durum Değişkenleri

Uygulama içinde üç temel durum değişkeni vardır:

- `selected_idx`: seçili kalite preset indeksini tutar
- `video_info`: `yt-dlp` tarafından dönen video meta verisini saklar
- `download_process`: aktif indirme işlemini temsil eden `subprocess.Popen` nesnesidir

Bu değişkenler uygulamanın akışını yönetir ve iptal, yeniden başlatma gibi işlemlerde kullanılır.

## 7. Kullanıcı Deneyimi ve Davranış

Arayüzde kullanıcıyı yönlendiren temel davranışlar şunlardır:

- URL girilmeden indirme başlatılmaz
- Video bilgisi alınmadan indirme butonu aktif olmaz
- İndirme sırasında iptal butonu görünür hale gelir
- İndirme tamamlandığında klasörü açma seçeneği sunulur
- Durum alanı tüm olayları kronolojik olarak listeler

Bu yapı, teknik detayları kullanıcıdan gizleyip basit bir kullanım akışı sunmayı hedefler.

## 8. Platform ve Bağımlılık Kontrolü

`run.sh` betiği, uygulamayı başlatmadan önce Python 3 varlığını ve `yt-dlp` kurulumunu kontrol eder. Eksikse `requirements.txt` üzerinden kurulum yapar ve ardından `youtube_downloader.py` dosyasını çalıştırır.

Uygulama ayrıca platforma göre klasör açma işlemini farklı şekilde gerçekleştirir:

- macOS: `open`
- Windows: `os.startfile`
- Linux: `xdg-open`

## 9. Güçlü Yönler

- Tek dosyalı ve anlaşılır mimari
- Basit kurulum süreci
- Thread tabanlı, donmayan arayüz
- Hem video hem ses indirme desteği
- İndirme durumunu anlık gösteren kullanıcı deneyimi

## 10. Sınırlılıklar ve Geliştirme Alanları

- Test altyapısı bulunmuyor
- Kod tek dosyada toplandığı için büyüdükçe bakım zorlaşabilir
- Gelişmiş hata raporlama ve log seviyesi ayrımı yok
- İndirme geçmişi veya kuyruk sistemi bulunmuyor
- Çoklu indirme veya oynatma listesi yönetimi yok

## 11. Sonuç

Bu proje, YouTube içeriklerini kalite seçimiyle indirmeye odaklanan, bağımlılığı düşük ve kullanıcı dostu bir masaüstü uygulamasıdır. Mimarisi sade olsa da, arka plan iş parçacıkları, `yt-dlp` entegrasyonu ve gerçek zamanlı ilerleme takibi sayesinde pratik bir kullanım sağlar. Mevcut yapısı, küçük ve orta ölçekli kişisel kullanım senaryoları için uygundur.