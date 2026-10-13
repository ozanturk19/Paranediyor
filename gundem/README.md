# Gündem Arşivi (Para Ne Diyor?)

Bu klasöre günlük gündem taraması (sabah 08:45 ve öğleden sonra 16:00) otomatik yazılır.
Bu dal (`gundem-arsivi`) yalnızca arşiv içindir; videolar ve kod burada değildir.

## Dosyalar

- `son-bulten.md`: her zaman en son bülten (metin yazarı ajan önce buna bakar).
- `YYYY/MM/YYYY-MM-DD-sabah.md` ve `YYYY/MM/YYYY-MM-DD-oglen.md`: o günün tam kaydı.
- `konular.csv`: tüm konuların tek satırlık listesi (tarih, bülten, kategori, puan, başlık). Tekrarı önlemek ve geçmişte ne çıktığını görmek için.

## Bir bülten dosyasının yapısı

Her konu için:

- **Kategori**: ekonomi / teknoloji / sosyal medya / küçük detay
- **Puan (1-10)**: içerik potansiyeli. 8 ve üstü "çok değerli".
- **Ne oldu**: kısa özet, tarih ve yer.
- **Detaylar ve rakamlar**: metin yazarı için ham malzeme.
- **Neden ilginç**: izleyicinin hayatıyla bağı.
- **Kaynaklar**: doğrulama için linkler (Telegram'a gitmez, yalnızca burada).

## Metin yazarı ajan için

1. `son-bulten.md` dosyasını ya da istenen tarihin dosyasını oku.
2. Puanı 8 ve üstü olan konuları seç.
3. Rakamları kaynaklardan bir kez daha doğrula, sonra metni yaz.
