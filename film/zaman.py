"""Metin, altyazı sayfaları ve zamanlama.

Seslendirme yoksa süreler hece sayısından tahmin edilir (Türkçede her hecede bir ünlü var).
Seslendirme gelince `ses_zamanlari(json)` ile kelime zamanları gerçek sese oturtulur.
"""
import difflib, json, re

VOWELS = set("aeıioöuüâîûAEIİOÖUÜÂÎÛ")
SYL_OVERRIDE = {"100": 1, "3-4": 2}           # "yüz", "üç dört"
SYL_PER_SEC = 6.4                              # enerjik anlatım hızı (hece/sn)

# (sahne, konuşulan cümle, bekleme sn, altyazı sayfaları; None = altyazıyı sahne kendisi yazar)
LINES = [
    ("kanca", "Hesabındaki paranın çoğu aslında hiç basılmadı.", 0.55,
     ["Hesabındaki / paranın *ÇOĞU", "~aslında / **HİÇ_BASILMADI."]),
    ("matbaa", "Türkiye'de kâğıt paralar Ankara'daki Merkez Bankası matbaasında basılır.", 0.3,
     ["Türkiye'de / *KÂĞIT paralar", "*ANKARA'daki / Merkez Bankası", "*MATBAASINDA / ~basılır."]),
    ("pamuk", "Sıradan kâğıt değil, pamuklu özel bir kâğıt kullanılır.", 0.3,
     ["Sıradan kâğıt ~değil,", "*PAMUKLU özel bir / kâğıt kullanılır."]),
    ("filigran", "İçine filigran ve güvenlik şeridi gömülür.", 0.3,
     ["İçine *FİLİGRAN", "ve *GÜVENLİK_ŞERİDİ / ~gömülür."]),
    ("baski", "Sonra renkli zemin ve parmakla hissedilen kabartma baskı gelir.", 0.3,
     ["Sonra *RENKLİ ~zemin", "ve parmakla ~hissedilen", "**KABARTMA / baskı gelir."]),
    ("seri", "Seri numarası verilir, kesilir, paketlenir.", 0.35,
     ["*SERİ_NUMARASI / verilir,", "*KESİLİR, / *PAKETLENİR."]),
    ("darphane", "Bozuk paraları ise Merkez Bankası değil, Darphane basar.", 0.45,
     ["Bozuk paraları ise / Merkez Bankası ~değil,", "**DARPHANE / ~basar."]),
    ("soru", "Peki ne kadar para basılacağına kim karar veriyor?", 0.7,
     ["Peki ne kadar para / ~basılacağına", None]),
    ("sen", "Aslında sen.", 0.7, [None]),
    ("dolasim", "Bankalar, insanların nakit ihtiyacı kadar parayı Merkez Bankası'ndan çeker.", 0.45,
     ["*BANKALAR,", "insanların / *NAKİT_İHTİYACI kadar", "parayı Merkez / Bankası'ndan *ÇEKER."]),
    ("donusum", "Ama asıl para burada doğar:", 0.35, ["Ama asıl para / **BURADA ~doğar:"]),
    ("kredi", "Banka sana kredi verdiğinde, hesabına yazılan para o an yaratılır.", 0.3,
     ["Banka sana / *KREDİ verdiğinde,", "hesabına ~yazılan para", "o an / **YARATILIR."]),
    ("ugramaz", "Hiçbir matbaaya uğramaz.", 0.45, ["Hiçbir ~matbaaya / *UĞRAMAZ."]),
    ("grid", "Türkiye'de her 100 liranın sadece 3-4 lirası nakit. Gerisi, ekrandaki rakamlar.", 0.5,
     ["Türkiye'de her / *100_LİRANIN", "sadece **3-4_LİRASI / nakit.", "Gerisi, / ekrandaki *RAKAMLAR."]),
    ("grafik", "Yani \"para basılıyor\" denince genelde kastedilen, paranın üretimden hızlı çoğalmasıdır.", 0.35,
     ["Yani “para basılıyor” / ~denince", "genelde ~kastedilen,", "paranın *ÜRETİMDEN / hızlı *ÇOĞALMASIDIR."]),
    ("terazi", "Para çoğalır ama mal aynı kalırsa, fiyatlar yükselir.", 0.3,
     ["Para *ÇOĞALIR / ama mal ~aynı kalırsa,", "*FİYATLAR / **YÜKSELİR."]),
    ("enflasyon", "İşte buna enflasyon diyoruz.", 0.5, [None]),
    ("simit", "Simitten kiraya, her fiyatta gördüğün bu.", 0.45,
     ["*SİMİTTEN / ~kiraya,", "her fiyatta / ~gördüğün **BU."]),
    ("final", "Para her zaman bir şey söyler.", 2.2, [None]),
]


def words_of(text):
    return [w for w in re.split(r"\s+", text.strip()) if w]


def syllables(word):
    core = re.sub(r"[^\wÇĞİÖŞÜçğıöşüâîû0-9-]", "", word)
    if core in SYL_OVERRIDE:
        return SYL_OVERRIDE[core]
    return max(1, sum(ch in VOWELS for ch in core))


def norm(w):
    return re.sub(r"[^a-zçğıöşü0-9]", "", w.replace("İ", "i").replace("I", "ı").lower())


def build(start=0.35, vo_words=None):
    """Zaman çizelgesi: her satır için kelime zamanları, sahne başlangıç/bitişleri."""
    timeline, t = [], start
    for scene, text, pause, pages in LINES:
        ws = words_of(text)
        times = []
        for w in ws:
            times.append(t)
            t += syllables(w) / SYL_PER_SEC
            if w[-1] in ",:":
                t += 0.18
        timeline.append(dict(scene=scene, text=text, words=ws, t=times, end_speech=t, pages=pages))
        t += pause
    if vo_words:
        _align(timeline, vo_words)
    for i, ln in enumerate(timeline):                       # sahne sınırları: cümle başından hemen önce
        ln["start"] = max(0.0, ln["t"][0] - 0.2) if i else 0.0
    for i, ln in enumerate(timeline):
        ln["end"] = timeline[i + 1]["start"] if i + 1 < len(timeline) else ln["end_speech"] + LINES[-1][2]
    return timeline


def _align(timeline, vo_words):
    """Tahmini kelime zamanlarını gerçek seslendirmenin kelime zamanlarıyla değiştir."""
    script = [(li, wi, norm(w)) for li, ln in enumerate(timeline) for wi, w in enumerate(ln["words"])]
    heard = [norm(w["w"]) for w in vo_words]
    sm = difflib.SequenceMatcher(None, [s[2] for s in script], heard, autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            li, wi, _ = script[a + k]
            timeline[li]["t"][wi] = vo_words[b + k]["s"]
    for ln in timeline:                                      # eşleşmeyenleri komşulardan doldur
        ts = ln["t"]
        for i in range(1, len(ts)):
            if ts[i] < ts[i - 1]:
                ts[i] = ts[i - 1] + 0.12
        ln["end_speech"] = ts[-1] + 0.35


def caption_cues(timeline):
    """Altyazı sayfalarını (render.py biçiminde) zamanlarıyla üret."""
    cues = []
    for ln in timeline:
        wi = 0
        pages = []
        for page in ln["pages"]:
            if page is None:
                n = len(ln["words"]) - wi if page is None and len(ln["pages"]) == 1 else len(ln["words"]) - wi
                pages.append((None, wi, len(ln["words"])))
                wi = len(ln["words"])
                continue
            toks, out = page.split(), []
            first = wi
            for tok in toks:
                if tok == "/":
                    out.append("/")
                    continue
                k = len(tok.split("_"))
                out.append(f"{tok}@{ln['t'][wi]:.2f}")
                wi += k
            pages.append((" ".join(out), first, wi))
        for i, (markup, a, b) in enumerate(pages):
            if markup is None:
                continue
            start = ln["t"][a] - 0.05
            end = ln["t"][pages[i + 1][1]] - 0.04 if i + 1 < len(pages) else ln["end"] - 0.02
            cues.append((start, end, markup))
    return cues


if __name__ == "__main__":
    tl = build()
    for ln in tl:
        print(f'{ln["start"]:6.2f}-{ln["end"]:6.2f}  {ln["scene"]:10s} {ln["text"][:60]}')
    print("toplam:", round(tl[-1]["end"], 1), "sn")
    for c in caption_cues(tl)[:6]:
        print(c)
