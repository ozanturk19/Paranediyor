"""Telefon filmi: sahne kayıtları. Sahneler sahne_a.py (1-11) ve sahne_b.py (12-22) içinde.

Her sahne: f(p, t, d, wt, lt) -> (görüntü, post). film.py buradaki SAHNELER, ANIMASYON, EXPOSURE, BLOOM,
finish ve shade_top adlarını kullanır.
"""
from yardim import finish, shade_top          # noqa: F401  (film.py kullanır)
import sahne_a as A
import sahne_b as B

SAHNELER = dict(kanca=A.kanca, satis=A.satis, vestel=A.vestel, soru=A.soru, yuzde7=A.yuzde7, satamamak=A.satamamak,
                hata=A.hata, cekilme=A.cekilme, strateji=A.strateji, garanti=A.garanti, kripto=A.kripto,
                devlet=B.devlet, telekom=B.telekom, fatura=B.fatura, zamanlama=B.zamanlama, milyonlar=B.milyonlar,
                uydu=B.uydu, ama=B.ama, pazar=B.pazar, ozet=B.ozet, yasar=B.yasar, final=B.final)
# ANIMASYON: doğrudan ekran renkleriyle çizilen (gfx.finish renk işlemi alan) sahneler
ANIMASYON = {"soru", "yuzde7", "satamamak", "strateji", "kripto", "fatura", "zamanlama", "milyonlar", "ama", "pazar",
             "yasar"}
BLOOM = dict(kanca=0.12, satis=0.12, garanti=0.12, ozet=0.12, telekom=0.35, uydu=0.22)
EXPOSURE = dict(kanca=0.72, satis=0.72, vestel=0.8, hata=0.8, cekilme=1.3, garanti=0.75, devlet=0.8, telekom=2.2,
                uydu=2.2, ozet=0.72, final=1.0)
