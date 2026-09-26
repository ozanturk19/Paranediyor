# Para Ne Diyor?

Instagram hesabı için Türkçe altyazılı finans klipleri ve içerik stratejisi.

## İçindekiler

| Klasör | Ne var? |
|---|---|
| `rapor/instagram-analiz.md` | Hesap ve rakip analizi, altyazı trendleri, büyüme önerileri, hazır açıklama metinleri |
| `altyazi/` | Videolara modern, kinetik Türkçe altyazı basan araç |
| `film/` | "Para nasıl basılır?" animasyon filmi: sahneler, geçişler, ses efektleri |
| `tekstil/` | "Tekstil Suriye'ye mi kayıyor?" gerçekçi 3D + harita filmi |

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
   - `python3 altyazi/yuz_takip.py girdi/video.mov 200`: yüzün ekrandaki yerini kare kare ölçer ve `girdi/video_yuz.json` dosyasına yazar. `make.py`'de `yuz="girdi/video_yuz.json"` verilirse her altyazı sayfası yüzün hemen altına yerleşir. Yüz çok aşağı indiğinde (örneğin kameraya eğilince) o sayfa yüzün üstüne geçer. `ust_sinir` ile videonun kendi başlık yazısının altında kalması sağlanır.
   - Video parça parça geldiyse: parçaları sırayla bir listeye yaz (her satır `file 'parca1.mov'`), sonra `ffmpeg -f concat -safe 0 -i girdi/liste.txt -c copy girdi/video.mov` ile kayıpsız birleştir. Parçaların sınırında kelime tekrarı ya da boşluk olup olmadığını kontrol et.
   - `on_video=True`: altyazı görüntünün üstündeyse okunaklı kalması için kontur ve gölge ekler.
   - `cap_top`: altyazının başladığı yükseklik (720×1280 ölçeğinde).
7. Önce birkaç kareye bak: `python3 altyazi/make.py kevin preview 5 10 15`
8. Tam videoyu oluştur: `python3 altyazi/make.py kevin full`. Sonuç `videolar/` klasörüne yazılır.

Videolar (.mp4) telif ve dosya boyutu nedeniyle depoya eklenmez.

## "Para nasıl basılır?" filmi (`film/`)

Tamamen kodla çizilen, 66 saniyelik dikey animasyon film. Hiç kredi harcanmadı, dışarıdan görüntü ya da ses kullanılmadı.

- 19 sahne: bakiye ekranı, matbaa, pamuk kâğıt, filigran ve güvenlik şeridi, kabartma baskı, seri no ve kesim, darphane, dönen harf tabelası, parmak izi, para dolaşımı, banknotun rakama dönüşmesi, kredi onayı, 100 liranın 3-4'ü, para-üretim grafiği, terazi, enflasyon, simit ve kira, final.
- Banknot hayalidir ("PARA NE DİYOR? 100"); gerçek bir banknotun kopyası değildir.
- Geçişler: sert kesme ve parlama, içine dalma (zoom), hızlı kamera savurma, ışık sızıntısı, dijital bozulma (glitch), karartma.
- Ses efektleri (`film/ses.py`) sayısal olarak üretilir ve her biri görüntüdeki olayla aynı anda çalar. Müzik yoktur, Instagram'da eklenir.

Dosyalar:

| Dosya | Görevi |
|---|---|
| `zaman.py` | Metin, altyazı sayfaları ve zamanlama. Seslendirme yokken süreler hece sayısından tahmin edilir. |
| `banknot.py`, `gfx.py`, `ortak.py` | Banknot çizimi, ışık/renk işlemleri, ortak araçlar |
| `sahne1.py`, `sahne2.py` | Sahneler |
| `gecis.py` | Sahne geçişleri |
| `ses.py` | Ses efektleri |
| `film.py` | Hepsini birleştirip MP4 üretir |

Komutlar:

1. Ses efektleri: `python3 film/ses.py sfx.wav` (seslendirme varsa sona kelime dosyasını ekle)
2. Hızlı kontrol (her yarım saniyeden bir kare): `python3 film/film.py kontrol kontrol_klasoru`
3. Tam film: `python3 film/film.py tam film.mp4 --ses sfx.wav`
4. Seslendirme gelince: önce `python3 altyazi/yaziya_dok.py seslendirme.m4a tr` ile kelime zamanlarını çıkar. Sonra `python3 film/ses.py sfx.wav seslendirme_kelimeler.json` ve `python3 film/film.py tam film.mp4 --ses sfx.wav --vo seslendirme_kelimeler.json` çalıştır. Bu şekilde bütün sahneler ve altyazılar gerçek sese oturur.

## "Tekstil Suriye'ye mi kayıyor?" filmi (`tekstil/`)

Kullanıcının kendi okuduğu metne göre hazırlanan, gerçekçi görünümlü 60 saniyelik film.

- Gerçekçi sahneler Blender (Cycles) ile kodla modellenip çizilir (`tekstil/b3d/`): tekstil atölyesi, dikiş makinesi yakın çekim, konteyner limanı ve gümrük bariyeri, temsili Suriye şehri (akşam, gece, sokak), kilit-zincir, bankamatik. Hepsi "TEMSİLİ GÖRSEL" etiketiyle gösterilir.
- Haritalar gerçek sınır verisiyle çizilir (Natural Earth 1:10m). Veri bir kez indirilir:
  `mkdir -p tekstil/veri && cd tekstil/veri && for f in ne_10m_admin_0_countries ne_10m_lakes ne_10m_rivers_lake_centerlines; do curl -sSfLO https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/$f.geojson; done`
- Grafiklerdeki rakamlar kaynaklarıyla gösterilir (SGK, Eurostat/İHKİB, resmi asgari ücretler).

Adımlar:

1. Blender modülü: `pip install bpy OpenEXR` (bpy numpy<2 ister).
2. 3D plakalar: `cd tekstil/b3d && TEKSTIL_3D_OUT=../plakalar python3 fabrika.py genis 100 0` (diğerleri: `fabrika.py yakin 100 0 1 2 3 4 5 6 7`, `liman.py koridor|bariyer 100`, `sehir.py aksam|sokak|gece_acik|gece_kapali 100`, `detay.py kilit 100 0 1 2 3 4 5 6 7`, `detay.py atm 100`).
3. Zamanlama: `python3 tekstil/zamanlama.py` (Instagram Edits'in altyazı ekranındaki cümle saniyelerinden hesaplanır).
4. Ses efektleri: `python3 tekstil/ses.py sfx.wav`
5. Film: `TEKSTIL_3D_OUT=tekstil/plakalar python3 tekstil/film.py tam film.mp4`, ardından `python3 film/teslim.py film.mp4 sfx.wav cikti.mp4`.
6. Seslendirme kaydı gelince `yaziya_dok.py` ile kelime zamanlarını çıkarıp `--vo` ile ver; her şey kelimesi kelimesine sese oturur.
