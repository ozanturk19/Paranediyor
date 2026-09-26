"""Tekstil filmi: metin, altyazı sayfaları ve zamanlama.

Seslendirme kaydı henüz elimizde değil; Instagram Edits'in altyazı ekranındaki cümle başlangıç
saniyeleri (tam saniyeye yuvarlanmış) biliniyor. Her cümlenin gerçek başlangıcı bu saniyenin içinde
bir yerde. Hece sayısıyla konuşma hızı modeli kurulup cümle başları o saniye aralıklarına en iyi
oturacak biçimde seçilir (dinamik programlama). Kayıt gelince `vo=` ile kelime kelime hizalanır.
"""
import importlib.util, os, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("film_zaman", os.path.join(HERE, "..", "film", "zaman.py"))
FZ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FZ)

SYL_OVERRIDE = {"3": 1, "350.000": 5, "150": 3, "5": 1, "%16": 5, "575": 5, "100": 1}

# (sahne, ekrandaki saniye, konuşulan cümle, altyazı sayfaları)
LINES = [
    ("fabrika", 0, "Türkiye'de tekstil ve hazır giyim 3 buçuk yılda yaklaşık 350.000 iş kaybetti.",
     ["Türkiye'de / *TEKSTİL ve hazır giyim", "3_buçuk yılda / yaklaşık", "**350.000_İŞ / ~kaybetti."]),
    ("soylenti", 5, "Herkes fabrikalar Suriye'ye kayıyor diyor.",
     ["Herkes / *FABRİKALAR", "*SURİYE'YE / ~kayıyor diyor."]),
    ("ilk", 7, "Suriye'de açıldığı bildirilen ilk Türk fabrikasında ise yaklaşık 150 kişi çalışıyor.",
     ["Suriye'de ~açıldığı / bildirilen", "*İLK_TÜRK / fabrikasında ise", "yaklaşık / **150_KİŞİ ~çalışıyor."]),
    ("neden", 12, "Türkiye'deki sektör nedenini kendisi söylüyor.",
     ["Türkiye'deki / *SEKTÖR", "nedenini / ~kendisi söylüyor."]),
    ("iscilik", 15, "İşçilik maliyetleri çok yüksek.",
     ["*İŞÇİLİK / maliyetleri **ÇOK_YÜKSEK."]),
    ("faiz", 16, "Yatırım yapabilmek için de faizler yüksek.",
     ["Yatırım yapabilmek / için de", "*FAİZLER / ~yüksek."]),
    ("ihracat", 19, "Üstüne Avrupa'nın Türkiye'den giyim alımı bu yıl ilk 5 ayda %16 düştü.",
     ["Üstüne *AVRUPA'NIN / Türkiye'den", "giyim alımı / bu yıl ilk 5 ayda", "**%16 / ~düştü."]),
    ("suriye", 25, "Peki neden Suriye konuşuluyor?",
     ["Peki neden / *SURİYE ~konuşuluyor?"]),
    ("ucret", 26, "Çünkü maliyet farkı çok büyük.",
     ["Çünkü / *MALİYET_FARKI", "~çok büyük."]),
    ("ucret", 29, "Türkiye'de net asgari ücret yaklaşık 575 dolar.",
     ["Türkiye'de net / *ASGARİ_ÜCRET", "yaklaşık / **575_DOLAR."]),
    ("ucret", 32, "Suriye'de ise 100 dolar civarında.",
     ["Suriye'de ise / **100_DOLAR ~civarında."]),
    ("yaptirim", 34, "Yaptırımların büyük kısmı kalktı.",
     ["*YAPTIRIMLARIN / büyük kısmı ~kalktı."]),
    ("tasinma", 36, "Peki fabrikalar taşınıyor mu?",
     ["Peki fabrikalar / *TAŞINIYOR_MU?"]),
    ("tasinma", 37, "Hayır, henüz değil.",
     [None]),                                             # sahne "HAYIR / henüz değil" yazısını kendisi gösterir
    ("altyapi", 39, "Çünkü Suriye'de altyapı hala çok zayıf.",
     ["Çünkü Suriye'de / *ALTYAPI", "~hâlâ çok zayıf."]),
    ("elektrik", 42, "Talep edilen elektriğin yarısından azı karşılanabiliyor.",
     ["Talep edilen / *ELEKTRİĞİN", "**YARISINDAN_AZI / ~karşılanabiliyor."]),
    ("banka", 45, "Bankacılık sistemi de çok zayıf.",
     ["*BANKACILIK / sistemi de ~çok zayıf."]),
    ("vergi", 47, "Ayrıca Avrupa'ya hangi vergiyle girileceği bile belli değil.",
     ["Ayrıca Avrupa'ya / *HANGİ_VERGİYLE", "girileceği bile / ~belli değil."]),
    ("baslangic", 50, "Yani şimdilik bir başlangıç var ama göç yok.",
     ["Yani şimdilik bir / *BAŞLANGIÇ var", "ama **GÖÇ_YOK."]),
    ("final", 53, "Hikaye ancak ikinci ve üçüncü fabrikanın haberi gelirse hareketlenir.",
     ["Hikâye ancak / *İKİNCİ ve *ÜÇÜNCÜ", "fabrikanın haberi / ~gelirse", "**HAREKETLENİR."]),
]
TAIL = 2.4          # son cümleden sonra kapanış kartı için

# gelen sahne -> (geçiş türü, yarım süre sn, ayar); film.py (görüntü) ve ses.py (ses) birlikte kullanır
GECIS = {
    "soylenti": ("erit", 0.25, None), "ilk": ("kes", 0.0, None), "neden": ("savur", 0.18, "sol"),
    "iscilik": ("kes", 0.0, None), "faiz": ("erit", 0.2, None), "ihracat": ("zoom", 0.22, (540, 800)),
    "suriye": ("karart", 0.25, None), "ucret": ("erit", 0.22, None), "yaptirim": ("savur", 0.18, "sol"),
    "tasinma": ("erit", 0.22, None), "altyapi": ("karart", 0.25, None), "elektrik": ("erit", 0.22, None),
    "banka": ("savur", 0.18, "sag"), "vergi": ("savur", 0.18, "sol"), "baslangic": ("zoom", 0.22, (540, 800)),
    "final": ("kes", 0.0, None),
}


def syllables(word):
    core = re.sub(r"[^\wÇĞİÖŞÜçğıöşüâîû0-9.%-]", "", word).strip(".")
    if core in SYL_OVERRIDE:
        return SYL_OVERRIDE[core]
    return FZ.syllables(word)


def _fit_starts():
    """Cümle başlarını, ekrandaki tam saniyelerin içine hece hızı modeliyle yerleştir."""
    S = np.array([ln[1] for ln in LINES], float)
    syl = np.array([sum(syllables(w) for w in FZ.words_of(ln[2])) for ln in LINES], float)
    commas = np.array([ln[2].count(",") for ln in LINES], float)
    offs = np.arange(0.0, 0.96, 0.05)
    best = None
    for rate in np.arange(5.0, 8.01, 0.05):
        for pause in (0.2, 0.3, 0.4, 0.5):
            dur = syl / rate + commas * 0.18 + pause
            n = len(LINES)
            cost = np.zeros((n, len(offs)))
            back = np.zeros((n, len(offs)), int)
            cost[0] = (offs - 0.3) ** 2 * 0.2               # ilk cümle genelde biraz geç başlar
            for i in range(1, n):
                gap = (S[i] + offs)[None, :] - (S[i - 1] + offs)[:, None]
                c = cost[i - 1][:, None] + (gap - dur[i - 1]) ** 2 + np.where(gap < 0.3, 99, 0)
                back[i] = c.argmin(0)
                cost[i] = c.min(0)
            k = int(cost[-1].argmin())
            if best is None or cost[-1][k] < best[0]:
                path = [k]
                for i in range(n - 1, 0, -1):
                    path.append(back[i][path[-1]])
                best = (cost[-1][k], rate, pause, S + offs[path[::-1]])
    return best


def build(vo_words=None):
    _, rate, pause, starts = _fit_starts()
    tl = []
    for i, (scene, sec, text, pages) in enumerate(LINES):
        ws = FZ.words_of(text)
        t0 = starts[i]
        t1 = starts[i + 1] - pause if i + 1 < len(LINES) else t0 + sum(syllables(w) for w in ws) / rate
        w_syl = np.array([syllables(w) + (0.9 if w[-1] in ",:" else 0) for w in ws], float)
        span = max(0.3, t1 - t0)
        times = list(t0 + span * np.concatenate([[0], np.cumsum(w_syl)[:-1]]) / w_syl.sum())
        tl.append(dict(scene=scene, text=text, words=ws, t=times, end_speech=t1, pages=pages))
    if vo_words:
        FZ._align(tl, vo_words)
    for i, ln in enumerate(tl):
        ln["start"] = max(0.0, ln["t"][0] - 0.2) if i else 0.0
    for i, ln in enumerate(tl):
        ln["end"] = tl[i + 1]["start"] if i + 1 < len(tl) else ln["end_speech"] + TAIL
    return tl


def scenes(tl):
    """Aynı sahneye ait ardışık cümleleri tek sahnede topla."""
    out = []
    for ln in tl:
        if out and out[-1]["scene"] == ln["scene"]:
            sc = out[-1]
            sc["end"] = ln["end"]
            sc["lines"].append(ln)
        else:
            out.append(dict(scene=ln["scene"], start=ln["start"], end=ln["end"], lines=[ln]))
    for sc in out:
        sc["t"] = [w for ln in sc["lines"] for w in ln["t"]]
        sc["line_t"] = [ln["t"][0] for ln in sc["lines"]]
    return out


def caption_cues(tl):
    return FZ.caption_cues(tl)


def vo_yukle(path):
    return FZ.vo_yukle(path)


if __name__ == "__main__":
    cost, rate, pause, starts = _fit_starts()
    print(f"hız {rate:.2f} hece/sn, cümle arası {pause:.2f} sn, hata {cost:.3f}")
    tl = build()
    for ln in tl:
        print(f'{ln["start"]:6.2f}-{ln["end"]:6.2f}  {ln["scene"]:10s} {ln["text"][:58]}')
    for sc in scenes(tl):
        print(f'SAHNE {sc["scene"]:10s} {sc["start"]:6.2f}-{sc["end"]:6.2f}  ({sc["end"] - sc["start"]:.2f} sn)')
    bad = []
    for ln in tl:
        if None in ln["pages"]:
            continue
        n_tok = sum(len(tok.split("_")) for p in ln["pages"] if p for tok in p.split() if tok != "/")
        if n_tok != len(ln["words"]):
            bad.append((ln["text"][:30], n_tok, len(ln["words"])))
    print("sayfa/kelime uyumsuzluğu:", bad or "yok")
    print("toplam", round(tl[-1]["end"], 2), "sn")
