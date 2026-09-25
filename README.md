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
4. `altyazi/make.py` içine metni yaz. Kurallar:
   - Her satır bir altyazı bloğudur: `başlangıç bitiş metin`.
   - `*KELİME` anahtar kelimeyi büyük ve sarı yapar.
   - `**KELİME` kelimeyi sarı etiketin içine alır.
   - `~kelime` kelimeyi italik serif yapar.
   - `/` satır atlatır.
   - `kelime@12.3` kelimenin 12,3. saniyede görünmesini sağlar.
5. Önce birkaç kareye bak: `python3 altyazi/make.py kevin preview 5 10 15`
6. Tam videoyu oluştur: `python3 altyazi/make.py kevin full`. Sonuç `videolar/` klasörüne yazılır.

Videolar (.mp4) telif ve dosya boyutu nedeniyle depoya eklenmez.
