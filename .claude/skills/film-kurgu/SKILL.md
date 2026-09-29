---
name: film-kurgu
description: "Para Ne Diyor?" Instagram Reels'i için ultra yaratıcı, sinematik animasyon ve gerçekçi 3D kurgu (film) üretir. Metinden, kullanıcının ses kaydından ya da Instagram Edits ekran görüntüsünden 1080x1920, 30 fps, altyazılı ve efekt sesli MP4 çıkarır. Kullanıcı "film yap", "kurgu yap", "animasyon", "bu metne video", "seslendirmeme görüntü" gibi bir şey istediğinde, işe başlamadan ÖNCE bu rehberi baştan sona oku ve adım adım uygula.
---

# Para Ne Diyor? — Film ve Kurgu Rehberi

> ## ULTRA CREATIVE MOD ZORUNLU
> Bu kanalda sıradan, şablon, "slayt gösterisi" gibi kurgu kabul edilmez. Her film, izleyiciyi ilk karede
> yakalayıp son kareye kadar akışın içinde tutan, **akıcı, sinematik, çocuksu olmayan** bir hareketli grafik
> filmi olmalı. Her cümle kendi görsel fikrini, her önemli kelime kendi görsel vuruşunu hak eder.
> Emin olmadığın her yerde daha yaratıcı, daha net ve daha az çocuksu olan seçeneği seç.
> Aşağıdaki kurallar bu modun ölçülebilir tanımıdır. Hepsi bağlayıcıdır.

Bu rehber, daha önce teslim edilip kullanıcının beğendiği iki filmden çıkarıldı:

- `film/`: "Para nasıl basılır?" — tamamen kodla çizilmiş animasyon, 66 sn, 19 sahne.
- `tekstil/`: "Tekstil Suriye'ye mi kayıyor?" — gerçekçi 3D (Blender) + eğik haber haritası + veri grafikleri, 60 sn.

Görsel çıtayı görmek için önce şu iki kontrol sayfasını **Read ile aç**:

- `.claude/skills/film-kurgu/ornekler/para-nasil-basilir.jpg`
- `.claude/skills/film-kurgu/ornekler/tekstil-suriye.jpg`

---

## 0. İlk adımlar (her yeni işte, sırayla)

1. Bu dosyayı sonuna kadar oku. `CLAUDE.md` kurallarını da uygula.
2. Ortamı kur: `bash kurulum.sh` (ilk seferde 3-5 dk; Blender modülü, fontlar, Whisper modeli, harita verisi).
3. Örnek kontrol sayfalarını aç (yukarıda).
4. Kullanıcıdan gelenleri topla:
   - **Metin** (zorunlu). Metin yoksa önce 45-60 sn'lik bir metin taslağı yaz ve onay al; seslendirmeyi kullanıcı kendisi yapar.
   - **Ses kaydı** (en iyisi). Kullanıcı Instagram Edits'te okur. Kayıt yoksa işi bekletme, ekran görüntüsündeki saniyelerle ya da hece tahminiyle başla. Teslimde kaydı iste.
   - **Edits ekran görüntüsü**: cümle başlangıç saniyelerini verir (bkz. §7.2).
5. Arka planda bir alt-ajan (Agent, general-purpose) ile metindeki bütün rakam ve iddiaları web'de doğrulat (§6). Sen bu sırada senaryo tablosunu yaz.
6. Kullanıcıya bir cümleyle ne yapacağını söyle ve işe koyul. Kullanıcı genelde "yap, bitince tam kontrol edip at" der. Ara onay isteme; yalnızca gerçekten engelleyen bir konuda soru sor.

---

## 1. Kullanıcı ve kanal

- **Kanal:** Para Ne Diyor? — Türkçe ekonomi/finans açıklayıcı Reels. Seyirci telefonda izliyor ve çoğu sesi kapalı izliyor. Bu yüzden altyazı her zaman ekranda.
- **Kullanıcı teknik değil.** Mesajlar sade Türkçe, kısa ve jargonsuz olur. Uzun sessizlik yapma: birkaç dakikada bir tek cümlelik durum bildir.
- **Seslendirmeyi kullanıcı yapar.** Müzik koyma; müziği kullanıcı Instagram'da ekler. Sen efekt sesi (SFX) üretirsin.
- **Kullanıcının onayladığı ve istediği şeyler (değiştirme):**
  - Kinetik altyazı stili (§3.4) ve konumu (Instagram arayüzünün kapatmadığı alan).
  - Köşeye "TEMSİLİ GÖRSEL" gibi etiket **koyma**. Kullanıcı "saçma duruyor" dedi.
  - Kaynak videolardaki gömülü yazılara (İngilizce altyazı vb.) dokunma, silme, bulanıklaştırma.
  - Higgsfield (Paranediyor bağlayıcısı) kredisi harcama. Her şeyi kodla, ücretsiz üret. Yapay zekâ videosu gerçekten gerekiyorsa önce maliyetiyle birlikte sor. Not: Higgsfield'ın ürettiği dosyalar bu bulut ortamından indirilemiyor.
  - Teslim: "full kontrol sonrası" bitmiş iş. Yarım iş gönderme.

---

## 2. ULTRA CREATIVE MOD — ölçülebilir tanım

1. **Her cümle = bir görsel fikir.** Senaryo tablosunda her cümle için en az 3 alternatif fikir yaz. İlk akla geleni değil, en şaşırtıcı ve en net olanı seç. Aynı görsel fikir filmde iki kez kullanılmaz.
2. **Soyut kavram → somut metafor.** Örnekler (hepsi yapıldı, kodda var):

   | Kavram | Metafor |
   |---|---|
   | "Hesaptaki para basılmadı" | Bakiye rakamları sayıya dönüşüp veriye dağılıyor |
   | "Karar veren sensin" | Parmak izi çiziliyor, dev "SEN." ekrana çarpıyor |
   | Kredi = para yaratmak | Banknot rakamlara ayrışıp telefona akıyor, bakiye doluyor |
   | Enflasyon | "ENFLASYON" kelimesi balon gibi şişiyor |
   | Yaptırımlar kalktı | Paslı parmaklıktaki kilit açılıyor |
   | Elektrik yetmiyor | Gece şehrinin ışıkları bölge bölge sönüyor |
   | 150 kişi vs 350.000 iş | 150 sarı nokta, kamera uzaklaşınca 350.000 gri nokta |
   | Vergi belirsiz | Gümrük bariyeri önünde "%0" ↔ "%12" dönüp duruyor |

3. **Ekrandaki her rakam canlanır.** Sayaç, büyüyen çubuk, nokta alanı, karşılaştırma, sayı ölçeği şoku gibi. Rakamı düz yazı olarak koymak yasak.
4. **Teknik çeşitliliği.** Bir filmde en az 4 farklı görsel dünya kullan ve ritimle karıştır:
   - gerçekçi 3D mekân
   - eğik haber haritası
   - veri grafiği
   - kinetik tipografi
   - cam (liquid glass) arayüz panelleri
   - parçacık dönüşümü
   - dönen harf tabelası
   - makro yakın çekim
5. **Her sahnede bir "vay" anı.** Bunlardan biri: dönüşüm, ölçek şoku, beklenmedik kamera, gizli detayın ortaya çıkması ya da ters köşe.
6. **Geçişler anlam taşır.** Hareket yönünde savurma, bir nesnenin içine dalma, eşleşen kesme (rakamlar → matbaa). Anahtar anlarda sert kesme + flaş.
7. **Ses görüntünün yarısıdır.** Her görsel olayın bir sesi var (§5). Sessiz boşluk yok.
8. **Son söz akılda kalır.** Güçlü kapanış cümlesi + "PARA NE DİYOR?" kartı. Mümkünse son kare başa bağlanır (döngü = tekrar izlenme).
9. **Kalite çıtası:** Bloomberg Quicktake, Vox, The Economist Films, Johnny Harris harita anlatımı, Apple keynote hareket grafikleri. Kopyalama; çıta olarak kullan.

---

## 3. Görsel dil: akıcı ama çocuksu değil

### 3.1 Yap / yapma

| Yap | Yapma |
|---|---|
| Sinematik ışık, koyu zemin, sarı vurgu | Çizgi film karakteri, maskot, emoji |
| Gerçekçi malzeme (metal, kumaş, beton, pas) | Clip-art ikon, düz renk çocuk kitabı çizimi |
| ACES ton eğrisi, film greni, vinyet, bloom, alan derinliği | Gökkuşağı renkler, zıplayan her şey |
| İnce, premium tipografi; az ama büyük yazı | Ekranı dolduran yazı yığını |
| Çizgi-ikon (ince, tek renk, hareketli) | PowerPoint geçişleri (yıldız, perde, dönen küp) |
| Hayali banknot "PARA NE DİYOR? 100" | Gerçek banknot, logo, marka, gerçek kişi kopyası |
| Genel/temsili mekân (atölye, liman, şehir) | Belirli bir olayın gerçek görüntüsüymüş gibi sunmak |

### 3.2 Renkler

Renkler `film/gfx.py` ve `tekstil/sahneler.py` içinde tanımlı; renk işleminden önce doğrusal değerlerdir.

| Ad | Hex | Kullanım |
|---|---|---|
| YELLOW | `#FFD21A` | Ana vurgu, anahtar kelime, olumlu rakam |
| CYAN | `#3CF0FF` | Dijital dünya, ekran, veri |
| GOLD | `#B8902B` | Bölüm etiketi, fiziksel para dünyası |
| RED | `#E0463A` (film/: `#C8452B`) | Düşüş, kayıp, "HAYIR" |
| GREEN | `#3DDC84` | Olumlu durum çipi |
| WARM | `#FFB45A` | Harita okları, akşam ışığı |

Zeminler çok koyudur. Hazır zeminler: `ortak.WARM`, `COOL`, `NIGHT` (radyal ışıklı).

### 3.3 Yazı tipleri

- **Montserrat:** 800-900 ağırlık; başlık, rakam, sayaç.
- **Inter:** 500-700 ağırlık; etiket, kaynak notu, arayüz.
- **Instrument Serif Italic:** duygu ve vurgu kelimeleri ("aslında", "henüz değil", "söyler.").

Fontlar `altyazi/fonts/` altındadır (`kurulum.sh` indirir). Türkçe büyük harf için `tr_upper` kullan (i→İ, ı→I).

### 3.4 Kinetik altyazı (motor: `altyazi/render.py`)

- Kelimeler konuşulduğu anda hafif bir "pop" ile girer.
- İşaretleme:
  - `*KELİME` → büyük, sarı, kalın; anahtar kelime.
  - `**KELİME` → sarı etiket içinde, hafif eğik; kahraman kelime. Az kullan, 5-8 sn'de bir.
  - `~kelime` → italik serif; duygu kelimesi.
  - `/` → satır sonu.
  - `_` → birleşik kelime (`**350.000_İŞ`).
  - `kelime@12.3` → açık zaman. Zaman modülleri bunu otomatik yazar.
- Sayfa başına en fazla 2 satır ve 1-3 vurgu.
- Sahne yazıyı kendisi çiziyorsa (dev "SEN.", "HAYIR", "ENFLASYON") o cümlenin sayfası `None` yapılır ve altyazı gösterilmez.
- Konum: `CAP_TOP = 890` (tasarım pikseli, ×1.5 = y≈1335), `R.ON_VIDEO = True` (kontur + gölge), `R.MAXW = 560`.

### 3.5 Güvenli alanlar (1080x1920)

- **Üst 0-200 px:** Reels başlığı. Önemli bir şey koyma.
- **Alt 1600-1920 px:** kullanıcı adı, açıklama, müzik. Yazı koyma.
- **Sağ sütun (x > 960, y 1000-1600):** beğeni ve yorum düğmeleri.
- **Bölüm etiketi:** sol üst, x=70, y≈235 (`ortak.label`, "01 · MATBAA" biçiminde).
- **Altyazı:** y≈1335-1500. Sahnedeki ana nesneleri y 300-1250 arasına kur.

---

## 4. Hareket kuralları (akıcılık)

- **Doğrusal hareket yasak.**
  - Giriş: `ease_out`.
  - Kamera: `ease_io`.
  - Vurgulu nesneler: `spring` (yaylanma) ya da `back` (hafif taşma).
  - Hepsi `film/ortak.py` içinde.
- **Kamera hiç durmaz.**
  - Sahne boyunca %4-9 yavaş itme (`ortak.camera` ya da `push`).
  - 3D plakalarda derinlik paralaksı (`push(..., k=0.25)`).
  - El kamerası sallantısı: `hand(t)`, 2-3 px.
- **Olaylar kelimeye kilitlidir.** Bir görsel olay, ilgili kelimenin söylendiği ana ±0.1 sn oturur. Sahne fonksiyonu kelime zamanlarını `wt` listesiyle alır.
  - Kelime numarasını her zaman kodla kontrol et (§7.3 sonu).
- **Vuruşlar:**
  - Anahtar kelimede flaş (`ortak.flash`), sarsıntı (`ortak.shake`), sayaç bitişi ya da yazı çarpması.
  - Vuruştan sonra kısa bir sakinlik bırak; ritim sert-yumuşak-sert olmalı.
- **Hareket bulanıklığı:** hızlı nesnede (savurma, dönen para, fırlayan kilit) bulanıklık ya da hayalet iz kullan. 3D'de `use_motion_blur`.
- **Ritim:**
  - 60 sn'de 15-20 sahne; sahne başına 1.5-5 sn.
  - 2 sn'den uzun hareketsiz kare yok.
  - Aynı tip sahne arka arkaya gelmez (harita → 3D → veri → harita).
- **Geçişler** (`film/gecis.py`):

  | Geçiş | Ne yapar |
  |---|---|
  | `flas` | Sert kesme + beyaz parlama + itme |
  | `zoom` | İçine dalma |
  | `savur` | Hareket bulanıklıklı kamera savurma (yön: `sol`/`sag`/`yukari`/`asagi`) |
  | `isik` | Işık sızıntısı |
  | `bozul` | Dijital bozulma, fiziksel dünyadan dijitale geçerken |
  | `erit` | Yumuşak geçiş |
  | `karart` | Karartma |
  | `kes` | Düz kesme |

  Geçiş yarım süresi 0.16-0.35 sn. Her geçişin sesi var (`ses.py` aynı tabloyu okur).

---

## 5. Retention (izleyiciyi tutma) şablonu — 60 sn

| Zaman | Görev | Nasıl |
|---|---|---|
| 0-1.5 sn | **Kanca** | Logo/giriş yok. En şaşırtıcı iddia + görsel çelişki. İlk kare bile hareketli ve dolu olsun. |
| 1.5-5 sn | Merak açılır | Açık döngü: "Peki nasıl?", "Kim karar veriyor?" |
| 5-20 sn | Mekanizma | Hızlı sahneler, her 2-3 sn yeni görüntü; bölüm etiketleri ilerleme hissi verir. |
| ~20-30 sn | **İkinci kanca** | Soru anı: harf tabelası, sessizlik + dev vuruş ("SEN.", "HAYIR"). |
| 25-45 sn | Karşılaştırma ve çatışma | Rakam savaşları, harita, önce/sonra. |
| 45-55 sn | Sonuç / ters köşe | "Aslında…" anı. |
| son 3-5 sn | Kapanış | Akılda kalan cümle + "PARA NE DİYOR?" kartı (+ "Takipte kal."). |

Ek kurallar:

- **Her 2-3 sn'de bir desen kırılımı:** yeni sahne, zoom, renk değişimi, sayaç ya da flaş.
- **Hiçbir cümle görselsiz kalmaz.** Hiçbir önemli kelime vuruşsuz kalmaz.
- **Toplam süre 45-70 sn.** Seslendirme ne kadarsa film o kadar; kapanış kartı için +2 sn.
- **Ses tasarımı:**
  - Her olayın bir sesi var: darbe, whoosh, tık, çan, parçacık dokusu, ortam sesi.
  - Hafif oda sesi sayesinde hiç tam sessizlik olmaz.
  - Efektler konuşmanın altında kalır (§7.7).

---

## 6. Doğruluk ve etik

- **Rakamları doğrulat.** Metindeki her rakamı ve iddiayı alt-ajana web'de doğrulat. Alt-ajan kaynak adı, tarih ve rakamla, "Doğru / Büyük ölçüde doğru / Şüpheli / Yanlış" diye rapor versin. Haber sitelerini WebFetch açamayabilir, arama sonuçları yeterli olur.
- **Kaynağı göster.** Ekranda küçük kaynak notu koy: `source()` ("Kaynak: SGK …, 2026").
- **Sınırdaki iddia:** Metindeki iddia sınırdaysa ekranda doğru nüansı göster. Örnek: "%0 mı %12 mi? Menşe kuralı belirleyici". Teslim mesajında kullanıcıya kısaca not düş. Kullanıcı kaydı zaten okuduysa metni değiştirme.
- **Çekinceleri koru:** "bildirilen", "yaklaşık", "civarında" gibi ifadeleri kaldırma.
- **Uydurma yok:** Uydurma rakam, grafik ekseni ya da tarih koyma. Veri yoksa grafik yalnızca yönü göstersin (ör. yükselen faiz eğrisi, eksen değeri yok).
- **Görsel etik:** Gerçek kişi, logo, marka ve banknot kopyalanmaz. Şirket adı gerekmedikçe ekrana yazılmaz.

---

## 7. İş akışı (adım adım)

### 7.1 Klasör

Yeni film için en güncel şablonu kopyala. Kök dizinde olmalı ki `../film` ve `../altyazi` içe aktarmaları çalışsın:

```bash
cp -r tekstil <kisa-konu-adi>      # örn: altin, kira, borsa
```

- Fiziksel dünya çoksa 3D (`b3d/`), coğrafya varsa harita (`harita.py`), soyut/finansal anlatım çoksa `film/` modülleri (`ortak.py`, `gfx.py`, sahne örnekleri) kullanılır. Hepsi birlikte kullanılabilir.
- `.gitignore`, `veri/` ve `plakalar/` klasörlerini her yerde yok sayar.
- 3D çıktı klasörünü `TEKSTIL_3D_OUT` ortam değişkeniyle ver (adı böyle kalabilir). Çıktıyı scratchpad'e yaz; büyük EXR dosyaları depoya girmez.

### 7.2 Zaman çizelgesi (`zamanlama.py`)

- `LINES` listesi `(sahne, ekrandaki_saniye, cümle, altyazı_sayfaları)` biçimindedir.
- Aynı sahneye art arda birden çok cümle verilebilir; `scenes()` bunları birleştirir.
- Zamanlama üç yoldan birinden gelir, en iyiden kötüye:
  1. **Ses kaydı:** `python3 altyazi/yaziya_dok.py kayit.m4a tr` → `kayit_kelimeler.json`. Sonra `--vo kayit_kelimeler.json`; kelime kelime hizalanır (`film/zaman.py::_align`, eşleşmeyen kelimeleri komşularından doldurur).
  2. **Edits ekran görüntüsü:** cümle başlarının tam saniyeleri `LINES`'a yazılır. `_fit_starts()` hece hızı modeliyle gerçek başlangıçları o saniyelerin içine oturtur.
  3. **Hiçbiri yoksa:** hece sayısından tahmin (`film/zaman.py`, 6.4 hece/sn).
- `GECIS` tablosu (gelen sahne → geçiş türü, yarım süre, ayar) görüntü ve sesin ortak kaynağıdır.
- `python3 zamanlama.py` çalıştır. "sayfa/kelime uyumsuzluğu: yok" görmelisin.

### 7.3 Senaryo tablosu

Kod yazmadan önce her cümle için bir satır yaz. Tekstil filminden örnek:

| Cümle | Görsel fikir | Teknik | Geçiş | Ses |
|---|---|---|---|---|
| "…3,5 yılda 350.000 iş kaybetti." | Boş atölyede kamera ilerler, kırmızı "−350.000" sayacı | 3D + sayaç | — | floresan vızıltısı, darbe, sayaç tıkları |
| "Herkes Suriye'ye kayıyor diyor." | Eğik harita, merkezlerden sınıra ışık okları, cam söylenti balonları | harita | erit | whoosh, pop |
| "…ilk Türk fabrikasında 150 kişi" | El-Rai'ye yakınlaşma, nabız atan pin; 150 sarı nokta → 350.000 nokta | harita + veri | kes | çan, yükselen gerilim, darbe |
| "İşçilik maliyetleri çok yüksek." | Dikiş makinesi makro, iğne döngüsü, neden kartları | 3D makro + cam panel | savur | dikiş makinesi sesi |
| "…ilk 5 ayda %16 düştü." | Gün batımı liman, iki çubuk, "−%16" | 3D + grafik | zoom | gemi düdüğü, darbe |
| "Yaptırımların büyük kısmı kalktı." | Kilit açılır, yeşil çip | 3D makro | savur | kilit + zincir şıkırtısı |
| "Peki taşınıyor mu? Hayır…" | Oklar yola çıkar, "HAYIR"da durur | harita | erit | bant durması + darbe |
| "Elektriğin yarısından azı…" | Gece şehri bölge bölge söner, talep/karşılanan çubuğu | 3D + veri | erit | tık tık sönme, inen ton |

### 7.4 3D plakalar (`b3d/`, Blender 5.0.1 Python modülü, Cycles CPU)

- **Hazır sahneler:**
  - `fabrika.py genis|yakin`: atölye, dikiş makinesi makro, iğne döngüsü.
  - `liman.py koridor|havadan|bariyer`: konteyner limanı, gümrük bariyeri.
  - `sehir.py aksam|gece_acik|gece_kapali|sokak`: temsili şehir, kablolu sokak.
  - `detay.py kilit|atm`: kilit ve zincir, bankamatik.
- **Yardımcılar** (`ortak3d.py`):
  - Malzeme: `mat()` (gürültüyle ton farkı ve pürüz), `emission`, `kelvin`.
  - Şekil: `box/cyl/cone/sphere/torus/plane/curve`.
  - Kopyalama: `collect` + `instance` + `hide_source` (binlerce nesne için hafif kopya).
  - Işık: `area_light/point_light/spot_light/sun`, `sky_world` (Nishita gökyüzü).
  - Kamera ve çizim: `camera(loc, hedef, lens, fstop, focus)`, `render(ad, kare)`.
  - Kısmi çizim: `border_for` + `set_border`.
- **Önce hızlı kadraj denemesi:** %25 çözünürlük, 12 örnek, birkaç kamera açısı yan yana (`fabrika.dene()` örneği). Beğendiğin açıyı seç.
- **Son çizim:** %100 çözünürlük, 48-96 örnek. `nohup` ile arka plan kuyruğunda çalıştır. Kuyruk dosyasını Write ile yaz, bash ile başlat; kuyruk bitmeden sıradakini kontrol et. Beklerken sahne kodunu yaz.
- **Döngü animasyonları** (iğne, kilit dili): 0. kare tam, diğer kareler yalnızca hareket eden bölge (`border_for`). Montajda `loop_frame()` birleştirir.
- **Süreler (4 CPU):** tam kare 1.5-5 dk; kısmi kare ~40 sn.
- **Çıktı:** çok katmanlı EXR (renk + derinlik + nesne no). `tekstil/exr.py::oku()` okur; `onizleme()` hızlı PNG verir.
- **Gerçekçilik ipuçları:**
  - Kusursuz yüzey yok; `mat(var=…, bump=…)` ile ton farkı ve pürüz ekle.
  - Kenar pahı: `bevel`.
  - Sıcak ve soğuk ışığı karıştır; arkadan ışık ver.
  - Alan derinliği kullan (f/1.8-3.2).
  - Sahneyi "yaşanmış" göster: yamuk sandalye, sönük lamba, örtülü makine.
  - Tek parlak nokta yerine birkaç yumuşak ışık kullan.

### 7.5 Sahneler (`sahneler.py`)

- **İmza:** `f(p, t, d, wt, lt) -> (doğrusal_görüntü, post)`.
  - `p`: 0-1 ilerleme; `t`: sahne içi saniye; `d`: süre.
  - `wt`: kelime zamanları; `lt`: cümle başları.
  - `post`: renk işleminden sonra çizilen keskin yazı ve grafik katmanı.
- **Plaka araçları:**
  - `plate(ad)`, `loop_frame(önek, k)`.
  - `push(rgb, derinlik, u, z0, z1, k, c, dx, dy)`: 2.5D kamera ve paralaks.
  - `haze()`: derinlik sisi; `hand(t)`: el kamerası sallantısı.
- **Harita** (`harita.py` + sahneler):
  - `HM.base(kamera, vurgu)`: kamera = (boylam, enlem, derece başına piksel).
  - `map_frame()`: eğik perspektif, kenar sisi.
  - Çizim: `draw_arrows`, `city_dots`, `label_city`, `screen_of`, `HM.border_line`, `HM.lerp_cam` (yumuşak yakınlaşma).
  - Şehir koordinatları `HM.CITIES` içinde; yeni şehir eklenebilir.
- **Veri ve arayüz:**
  - `chip(yazı, ikon="check"/"cross")`, `arrow(yukarı/aşağı)` (fontta ok işareti yok, çizilir), `source()`, `counter_text()`.
  - Hazır desenler: `reason_cards`, `dot_field` (nokta alanı), çubuk karşılaştırma (ihracat/ücret), dönen gösterge (vergi), bölge bölge sönme (`cells`).
- **Genel araçlar** (`film/ortak.py`):
  - Yazı ve etiket: `text(... glow=, scale=, tracking=)`, `label()`.
  - Cam panel: `glass()`.
  - Şekil: `rounded`, `rect_fill`, `poly`, `circle`, `arc`.
  - Parçacık: `digit_sprite` + `add_glow`, `mask_points`.
  - Kamera: `camera`, `shake`, `flash`.
  - Yerleştirme: `project_quad` + `place` (dokuyu perspektifle yerleştirme).
- **Animasyon sahne örnekleri** (`film/sahne1.py`, `film/sahne2.py`):
  - banknot matbaası, pamuk → kâğıt, filigran, kabartma baskı + büyüteç, seri no + lazer kesim + paket
  - darphane (kalıp + kıvılcım + para yağmuru)
  - dönen harf tabelası, parmak izi + dev yazı, ağ akışı, banknot → rakam → telefon
  - kredi onay halkası + bakiye sayacı, 100 mini banknot ızgarası, üstel ve doğrusal eğri, terazi
  - şişen kelime, fiyat sayaçları, amblem kapanışı
- **Renk işlemi:**
  - Gerçekçi sahne: `sahneler.finish()` (bloom, vinyet, ACES, sRGB, renk tonu, lens, gren).
  - Animasyon: `gfx.finish()`.
  - Sahne başına pozlama: `EXPOSURE`; ışık taşması: `BLOOM` sözlüğü.
- **Kelime numarası kontrolü (her zaman yap):**

  ```python
  import zamanlama as Z
  sc = {s["scene"]: s for s in Z.scenes(Z.build())}
  kel = lambda n: [w for ln in sc[n]["lines"] for w in ln["words"]]
  assert kel("ihracat")[10] == "%16"      # sahnede wt[10] kullanılıyorsa
  ```

### 7.6 Montaj ve çizim (`film.py`)

- **Tek kare:** `python3 <klasör>/film.py kare cikti.png 3.8 12.2 35.6` (sık sık kullan, ucuz).
- **Kontrol sayfaları:** `python3 <klasör>/film.py kontrol klasor --adim 10` (her 1/3 sn bir kare).
- **Tam film:** `python3 <klasör>/film.py tam master.mp4 [--vo kelimeler.json]`.
  - 60 sn ≈ 12-14 dk, 4 işlemciyle paralel. Arka planda çalıştır.
  - CRF 16 ana kopya üretir.

### 7.7 Ses

1. **Efektler:** `python3 <klasör>/ses.py sfx.wav [kelimeler.json]`
   - Olay zamanları, görüntüyle aynı formüllerden hesaplanır (aynı `wt` indeksleri).
   - Kütüphane `film/ses.py`: whoosh, riser, boom, clang, clink, tick, flap, blip, pop, slap, chunk, crackle, grains, laser, heartbeat, bell, scratch, flutter, creak, rubber, glitch, hum, pad.
   - `tekstil/ses.py` ekleri: gemi düdüğü, jeneratör, vızıltı, dikiş makinesi, bankamatik bip, bant durması, kilit.
   - Efekt izi tek başına -19 LUFS olarak ustalanır.
2. **Kullanıcının kaydı varsa:** `python3 film/miks.py kayit.m4a sfx.wav miks.wav`
   - Kayıt temizlenir; efektler konuşurken ~9 dB kısılır; sonuç -14 LUFS, tepe -2 dBTP.
3. **Teslim kodlaması:** `python3 film/teslim.py master.mp4 miks.wav cikti.mp4 29` (kayıt yoksa `sfx.wav`)
   - İki geçişli H.264, 29 MiB sınırı. SendUserFile en fazla 30 MiB kabul eder.

### 7.8 Kalite kontrolü (teslimden önce hepsi tamam olmalı)

**Görüntü**
- [ ] Kontrol sayfalarında her sahne. Her geçişin ±0.15 sn çevresi ayrıca `kare` ile.
- [ ] İlk kare dolu ve hareketli (kanca). Son kare temiz kapanış.
- [ ] Hiçbir yazı üst üste binmiyor. Altyazı ile sahne yazısı çakışmıyor.
- [ ] Güvenli alanlar (§3.5) korunuyor. Yazılar koyu ve açık zeminde okunuyor (`shade_top`, koyu panel).
- [ ] Türkçe karakterler doğru (İ, ı, ş, ğ, ç, ö, ü). Yazım hatası yok.
- [ ] Rakamlar metinle ve doğrulanmış kaynakla aynı. Kaynak notu var.
- [ ] Tam çözünürlükte en az iki kırpıntıya bakıldı (sıkıştırma kalitesi, ince yazılar).
- [ ] Çocuksu, emoji, clip-art, "TEMSİLİ GÖRSEL" etiketi yok.

**Ses**
- [ ] Efektler olaylarla aynı anda: flaş/darbe karesi ile ses başlangıcı arasında 0.05 sn'den az fark.
- [ ] `ffmpeg -i cikti.mp4 -af ebur128=peak=true -f null -` → kayıtlıysa ~-14 LUFS, değilse ~-19 LUFS; tepe ≤ -1 dBFS.
- [ ] Cızırtı ya da ani tık yok.

**Dosya**
- [ ] 1080x1920, 30 fps, H.264 High, yuv420p, bt709, AAC 48 kHz stereo, ≤ 29 MiB.

### 7.9 Teslim

1. SendUserFile ile MP4'ü gönder (`display: render`).
2. Kodu commit + push et. Videolar (mp4), plakalar (EXR) ve veri depoya girmez.
3. Kullanıcıya sade Türkçe özet yaz:
   - Film ne içeriyor (kısa madde listesi).
   - Seslendirme durumu (kayıt yoksa: "kaydı gönderin, kelimesi kelimesine oturturum").
   - Rakam kontrolü notları (doğru, sınırda, düzeltme önerisi).
4. Düzeltme gelirse değişikliği yap, etkilenen kareleri test et, tam filmi yeniden çiz, yeniden kontrol et, gönder.

---

## 8. Ortam bilgisi ve bilinen tuzaklar

- **Ağ erişimi:**
  - Açık: pypi, npm registry, raw.githubusercontent.com (fontlar, Natural Earth).
  - Kapalı: HuggingFace, Google storage, jsdelivr, cloudfront (Higgsfield medya), tcmb.gov.tr.
  - Modeller bu yüzden npm'den iner (`altyazi/model_indir.sh`).
- **Makine:** 4 CPU, ~15 GB RAM, GPU yok. Cycles CPU'da çalışır; örnek sayısını ve çözünürlüğü ölçülü tut.
- **bpy 5.0.1 ve numpy:** bpy numpy<2 ister. `kurulum.sh` hepsini tek pip komutuyla kurar (numpy 1.26 + opencv 4.11 uyumlu). Paketleri ayrı ayrı kurma.
- **Blender 5 API farkları:**
  - Çok katmanlı EXR için önce `image_settings.media_type = "MULTI_LAYER_IMAGE"`.
  - EXR çok parçalı gelir; `exr.oku()` bunu çözer.
  - Nishita gökyüzünde güneş lambasının yönü: `sun(elev, 180 - sky_rot)`.
  - `world_to_camera_view` öncesi `view_layer.update()`.
  - Ebeveyn bağlarken `matrix_parent_inverse` için önce `view_layer.update()`.
- **Kısmi çizim:** `use_crop_to_border=False` ile tam boy kare döner; boş yerler siyah kalır ve `loop_frame` yumuşak kenarla birleştirir.
- **glass():** panel ekran dışına taşarsa kırpma artık güvenli (düzeltildi). Yeni benzer araç yazarken ekran kenarını hesaba kat.
- **SendUserFile en fazla 30 MiB.** `teslim.py` 29 MiB hedefler.
- **Kullanıcının büyük dosyaları:** 30 MB üstünü parça parça gönderir. Parçaları `ffmpeg -f concat` ile birleştir.
- **iPhone HDR videolar:** `altyazi/render.py::hdr_to_sdr` ve `auto_npl` kullan.
- **Bash `sleep` zinciri engelli.** Uzun işi `run_in_background` ile başlat ya da `until …; do sleep 5; done` döngüsüyle bekle.
- **Stop hook** commit edilmemiş değişiklik bırakmamanı ister: işi bitirince commit + push.

---

## 9. Maliyet disiplini (Claude kullanımı)

- **Ölçülen:**
  - Sıfırdan kurulan animasyon filmi ~33 $.
  - Sıfırdan kurulan 3D film ~37 $, sonradan küçük bir düzeltme ~6 $.
  - Altyazı işleri video başına ~4-5 $.
- **Uzun oturum pahalıdır.** 1 saatten uzun aradan sonra ilk adım, tüm geçmişin yeniden işlenmesi yüzünden ~4 $ tutar. **Her yeni video için yeni oturum** önerilir; hazır araçlarla hedef film başına 15-25 $.
- **Önce tek kare test et.** Tam filmi yalnızca kontrol edilmiş değişikliklerden sonra çiz.
- **Küçük önizleme kullan.** Kontrol sayfaları küçük olsun; tam çözünürlüğe yalnızca kırpıntıyla bak. Aynı büyük görseli tekrar tekrar açma.
- **Doğrulama işini alt-ajana ver**, paralel çalışsın.
- **Kullanıcıdan düzeltmeleri toplu iste.** Her tur yeniden çizim demektir.

---

## 10. Hızlı başlangıç özeti

```bash
bash kurulum.sh
SCRATCHPAD=<bu oturumun scratchpad klasörü>             # sistem isteminde yazar
cp -r tekstil yeni_konu && cd yeni_konu
# 1) zamanlama.py: LINES + GECIS   2) b3d/ yeni 3D sahneler (gerekirse)   3) sahneler.py: sahne fonksiyonları
export TEKSTIL_3D_OUT=$SCRATCHPAD/plaka
python3 zamanlama.py                                   # kelime/sayfa uyumu
python3 film.py kare $SCRATCHPAD/t.png 1.0 5.0 12.0    # tek kare testleri
python3 film.py kontrol $SCRATCHPAD/kontrol --adim 10  # kontrol sayfaları
python3 ses.py $SCRATCHPAD/sfx.wav
python3 film.py tam $SCRATCHPAD/master.mp4
python3 ../film/teslim.py $SCRATCHPAD/master.mp4 $SCRATCHPAD/sfx.wav ../videolar/yeni-konu.mp4 29
```

Unutma: **ULTRA CREATIVE MOD.** Her sahne sorusu: "Bu, izleyiciyi bir sonraki saniyeye taşıyor mu?" Cevap "belki" ise sahneyi yeniden düşün.
