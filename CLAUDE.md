# Proje kuralları (Para Ne Diyor?)

- Kaynak videodaki gömülü yazılara (İngilizce altyazılar vb.) dokunma. Silme, bulanıklaştırma ya da rötuş yapma, çünkü bulanık iz bırakıyor. Sadece gerçekten gerekliyse, önce kullanıcıya sorarak yap.
- Türkçe altyazılar görselin hemen bitimine, Instagram arayüzünün kapatmadığı alana konur.
- Tam ekran videolarda (görselin altında boş alan yoksa) altyazı yüzün hemen altına, göğüs hizasına konur, kontur ve gölgeyle (`on_video=True`). Kullanıcı bu düzeni onayladı.
- Altyazısız videolarda konuşma `altyazi/yaziya_dok.py` ile yazıya dökülür. Türkçe konuşma çevrilmez, söylendiği gibi yazılır.
- Kullanıcı teknik bilgi sahibi değil. Açıklamaları sade Türkçeyle yap.

## Film / kurgu / animasyon işleri (zorunlu)

- Kullanıcı film, kurgu, animasyon ya da "bu metne / seslendirmeme video" istediğinde, işe başlamadan önce `.claude/skills/film-kurgu/SKILL.md` rehberini (`film-kurgu` becerisi) baştan sona oku ve adım adım uygula.
- **ULTRA CREATIVE MOD ZORUNLU.** Kurgu akıcı, sinematik ve çocuksu olmayan bir hareketli grafik filmi olmalı. İzleyiciyi ilk karede yakalamalı ve sonuna kadar akışta tutmalı (yüksek retention). Her cümlenin kendi görsel fikri, her önemli kelimenin kendi görsel vuruşu olmalı. Sıradan, şablon, slayt gibi iş kabul edilmez.
- Yeni oturumda önce `bash kurulum.sh` ile ortamı kur (Blender, fontlar, modeller, harita verisi).
- Köşeye "TEMSİLİ GÖRSEL" gibi etiket koyma. Gerçek banknot, logo, marka ve kişileri kopyalama. Ekrandaki her rakamı güncel kaynakla doğrula.
- Higgsfield kredisi harcama; her şeyi kodla, ücretsiz üret. Gerekirse önce maliyetiyle birlikte kullanıcıya sor.
- Teslim: kalite kontrolü bitmiş, 29 MB altı MP4 (SendUserFile), ardından sade Türkçe kısa özet. Kod commit + push; videolar depoya girmez.
