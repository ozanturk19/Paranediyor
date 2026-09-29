# Proje kuralları (Para Ne Diyor?)

## Genel

- Kullanıcı teknik bilgi sahibi değil. Açıklamaları sade Türkçeyle yap.
- Her yeni oturumda makine boş açılır. `bash kurulum.sh` her şeyi kurar: Blender, fontlar, modeller, harita verisi. Uzun sürdüğü için arka planda başlat.

## Hazır videolara altyazı işleri

- Kaynak videodaki gömülü yazılara (İngilizce altyazılar vb.) dokunma. Silme, bulanıklaştırma ya da rötuş yapma, çünkü bulanık iz bırakıyor. Sadece gerçekten gerekliyse, önce kullanıcıya sorarak yap.
- Türkçe altyazılar görselin hemen bitimine, Instagram arayüzünün kapatmadığı alana konur.
- Tam ekran videolarda (görselin altında boş alan yoksa) altyazı yüzün hemen altına, göğüs hizasına konur, kontur ve gölgeyle (`on_video=True`). Kullanıcı bu düzeni onayladı.
- Altyazısız videolarda konuşma `altyazi/yaziya_dok.py` ile yazıya dökülür. Türkçe konuşma çevrilmez, söylendiği gibi yazılır.

## Film / kurgu / animasyon işleri (zorunlu)

- Kullanıcı film, kurgu, animasyon ya da "bu metne / seslendirmeme video" istediğinde, işe başlamadan önce `.claude/skills/film-kurgu/SKILL.md` rehberini (`film-kurgu` becerisi) baştan sona oku ve adım adım uygula. Okurken `bash kurulum.sh`'ı arka planda çalıştır.
- **ULTRA CREATIVE MOD ZORUNLU.** Kurgu akıcı, sinematik ve çocuksu olmayan bir hareketli grafik filmi olmalı. İzleyiciyi ilk karede yakalamalı ve sonuna kadar akışta tutmalı (yüksek retention). Her cümlenin kendi görsel fikri, her önemli kelimenin kendi görsel vuruşu olmalı. Sıradan, şablon, slayt gibi iş kabul edilmez.
- Filmlerde altyazı konumu sabittir ve rehberde yazar (`CAP_TOP = 890`). Yukarıdaki "görselin altı" ve "yüzün altı" kuralları yalnızca hazır videolar içindir.
- Köşeye "TEMSİLİ GÖRSEL" gibi etiket koyma. Filmin içine kaynak ya da dipnot yazısı koyma; kaynakları yalnızca sohbette bildir. Gerçek banknot, logo, marka ve kişileri kopyalama. Ekrandaki her rakamı perde arkasında güncel kaynakla doğrula.
- Higgsfield kredisi harcama; her şeyi kodla, ücretsiz üret. Gerekirse önce maliyetiyle birlikte kullanıcıya sor.
- Teslim: kalite kontrolü bitmiş, en fazla 29 MiB MP4 (SendUserFile), ardından sade Türkçe kısa özet. Kodu commit + push et; videolar depoya girmez.
