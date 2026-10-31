# Gündem Arşivi (Para Ne Diyor?)

Bu klasöre günlük gündem taraması (sabah 08:45 ve öğleden sonra 16:00) otomatik yazılır.
Bu dal (`gundem-arsivi`) yalnızca arşiv içindir; videolar ve kod burada değildir.

**1 Kasım 2026'dan itibaren yeni düzen (v2).** Bot artık "kimsenin bilmediği haber" yerine "herkesin konuştuğu haberin kimsenin anlatmadığı tarafını" arıyor. Puanlar 13 üzerinden. Bu tarihten önceki kayıtlar eski düzende (1-10 puan, farklı kategoriler).

## Dosyalar

- `son-bulten.md`: her zaman en son bülten. Metin yazarı ajan önce buna bakar.
- `YYYY/MM/YYYY-MM-DD-sabah.md` ve `YYYY/MM/YYYY-MM-DD-oglen.md`: o günün tam kaydı.
- `suren_hikayeler.md`: haftalarca süren büyük hikâyeler (ör. tasfiye edilen fonlar), zaman çizelgesiyle. Her gün güncellenir.
- `konular.csv`: tüm konuların tek satırlık listesi (tarih, bülten, kategori, puan, başlık). Tekrarı önlemek için bot her çalışmada dosyanın tamamını okur.

## Puan (13 üzerinden, v2)

| Ölçü | Puan |
|---|---|
| Tanıdık isim (Türk marka, kişi, kurum, şehir) | 0-3 |
| Cebe etkisi (maaş, kira, birikim, borç, alışveriş) | 0-3 |
| Tazelik (son 24 saat = 3) | 0-3 |
| Açıklama boşluğu (insanlar "neden?" diye soruyor) | 0-2 |
| Bizim açımız (kimsenin anlatmadığı doğrulanmış taraf) | 0-2 |

10 ve üstü güçlü aday, 8-9 açısı güçlenirse aday, 7 ve altı zayıf.

## Bir bülten dosyasının yapısı

Her ana konu için: kategori, puan ve kırılımı, tarih / yer, ne oldu, detaylar ve rakamlar, kimsenin anlatmadığı taraf, kim kazanıyor / kim kaybediyor, izleyicinin sorusu, kaynaklar.
Dosyanın sonunda: **Video adayları** (yalnız arşivde; başlık taslağı + ilk cümle), **Rakip radarı** (Abdulkadir Genç, Yatırım 101, Melda Yücel Kocaalp ve bizim kanalın son videoları, izlenmeleriyle) ve **Takvim**.

## Metin yazarı ajan için

1. `son-bulten.md` dosyasını ya da istenen tarihin dosyasını oku.
2. "Video adayları" bölümünden ya da puanı 10 ve üstü olan konulardan başla.
3. Rakamları kaynaklardan bir kez daha doğrula, sonra metni yaz.
