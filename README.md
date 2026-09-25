# Para Ne Diyor?

Instagram hesabı için Türkçe altyazılı finans klipleri ve içerik stratejisi.

## İçindekiler

| Klasör | Ne var? |
|---|---|
| `rapor/instagram-analiz.md` | Hesap ve rakip analizi, altyazı trendleri, büyüme önerileri, hazır açıklama metinleri |
| `altyazi/` | Videolara modern, kinetik Türkçe altyazı basan araç |

## Altyazı stili

- Altyazılar kelime kelime, hafif bir "zıplama" (pop) animasyonuyla giriyor.
- **Anahtar kelimeler** büyük, kalın, büyük harf ve altın sarısı. Bağlaçlar küçük ve beyaz.
- Duygu yüklü kelimeler *italik serif* fontla yazılıyor (editoryal görünüm).
- En kritik kelime (ör. DİSİPLİN, HAYIR) hafif eğik, sarı bir etiketin içinde.
- Altyazılar görselin hemen altında, Instagram arayüzünün kapatmadığı alanda duruyor.
- Çıktı 1080×1920 (Instagram Reels boyutu).

## Yeni bir video için (teknik)

1. `bash altyazi/fontlari_indir.sh` komutuyla fontları indir.
2. `pip install -r altyazi/requirements.txt` komutuyla gerekli paketleri kur. Bilgisayarında `ffmpeg` de kurulu olmalı.
3. Videoyu `girdi/` klasörüne koy.
4. Videoda altyazı yoksa konuşmayı yazıya dök:
   - Modeli bir kez indir: `bash altyazi/model_indir.sh` (Whisper-small, ~250 MB).
   - Çalıştır: `python3 altyazi/yaziya_dok.py girdi/video.mp4 tr`. İngilizce için `en` yaz.
   - Araç her kelimenin zamanını ve `make.py`'ye yapıştırılacak taslak altyazı satırlarını verir.
   - 30 saniyeden uzun videolar parça parça işlenir. Parçaların birleştiği yerde nadiren bir iki kelime kaçabilir, metni gözden geçir.
5. `altyazi/make.py` içine metni yaz. Kurallar:
   - Her satır bir altyazı bloğudur: `başlangıç bitiş metin`.
   - `*KELİME` anahtar kelimeyi büyük ve sarı yapar.
   - `**KELİME` kelimeyi sarı etiketin içine alır.
   - `~kelime` kelimeyi italik serif yapar.
   - `/` satır atlatır.
   - `kelime@12.3` kelimenin 12,3. saniyede görünmesini sağlar.
6. `make.py`'deki video ayarları:
   - `vf_in=R.HDR_TO_SDR`: iPhone'un HDR videolarını normal renklere çevirir. Parlaklık videoya göre değişir: iç mekân için 35, güneşli dış çekim için 150–200 uygundur. `R.auto_npl("girdi/video.mov")` uygun değeri ölçer, `R.hdr_to_sdr(değer)` ile kullanılır.
   - `python3 altyazi/yuz_takip.py girdi/video.mov 200`: yüzün ekrandaki yerini kare kare ölçer. Tam ekran videolarda altyazının yüzü kapatmaması için kullanılır.
   - `on_video=True`: altyazı görüntünün üstündeyse okunaklı kalması için kontur ve gölge ekler.
   - `cap_top`: altyazının başladığı yükseklik (720×1280 ölçeğinde).
7. Önce birkaç kareye bak: `python3 altyazi/make.py kevin preview 5 10 15`
8. Tam videoyu oluştur: `python3 altyazi/make.py kevin full`. Sonuç `videolar/` klasörüne yazılır.

Videolar (.mp4) telif ve dosya boyutu nedeniyle depoya eklenmez.
