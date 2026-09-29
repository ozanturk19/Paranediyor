"""Telefon filmi: metin, altyazı sayfaları ve zamanlama ("ASELSAN ve Türk Telekom telefon üretiyor").

Zamanlama üç yoldan biriyle gelir (en iyiden kötüye):
  1. Ses kaydı: altyazi/yaziya_dok.py ile çıkan kelime zamanları `build(vo_words)` ile kelime kelime oturur.
  2. Instagram Edits ekran görüntüsü: LINES'taki ikinci alan = cümlenin ekranda yazan başlangıç saniyesi
     (tam saniye). Hece hızı modeliyle gerçek başlangıçlar o saniyelerin içine oturtulur (dinamik programlama).
  3. Yalnız metin: LINES'taki saniyeleri None yaz; cümle başları hece sayısından tahmin edilir.
Rakamlar okunuşlarındaki hece sayısıyla SYL_OVERRIDE'a eklenir ("350.000" = üç-yüz-el-li-bin = 5).
"""
import importlib.util, os, re
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("film_zaman", os.path.join(HERE, "..", "film", "zaman.py"))
FZ = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FZ)

# rakamların okunuş hece sayısı (kesme işareti çıkarılmış hâliyle: "2016'da" -> "2016da")
SYL_OVERRIDE = {"2016da": 6, "2027de": 7, "100": 1, "7si": 3, "11": 2, "200": 3, "5Gye": 3}

# (sahne, ekrandaki saniye ya da None, konuşulan cümle, altyazı sayfaları; sayfa None = sahne yazıyı kendisi çizer)
# Saniyeler kullanıcının Instagram Edits altyazı ekranından (ekran görüntüsü) alındı.
# Art arda aynı sahne adı verilen cümleler tek sahnede birleşir (scenes()).
LINES = [
    ("kanca", 1, "Aselsan ve Türk Telekom telefon üretmeye başlıyor.",
     ["*ASELSAN ve / *TÜRK_TELEKOM", "telefon / **ÜRETMEYE ~başlıyor."]),
    ("satis", 4, "2027'de satışta.", [None]),                  # sahne "2027 · SATIŞTA" etiketini kendisi çizer
    ("vestel", 6, "Ama bir dakika, bunu daha önce Vestel denedi ve olmadı.",
     ["Ama ~bir_dakika,", "bunu daha önce / *VESTEL denedi", "ve **OLMADI."]),
    ("soru", 10, "Bu sefer farklı olan ne?", [None]),          # harf tabelası
    ("yuzde7", 11, "2016'da Türkiye'de satılan 100 telefondan 7'si Venüs'tü.",
     ["*2016'DA Türkiye'de / satılan *100_TELEFONDAN", "**7'Sİ / ~Venüs'tü."]),
    ("satamamak", 15, "Sorun satamamak değildi,", [None]),     # sahne yazıyı kendisi çizer (üstü çizilen kelime)
    ("hata", 17, "ama yazılımsal hatalar ve yavaşlık konuları ciddi sıkıntı yaratıyordu.",
     ["ama *YAZILIMSAL / *HATALAR", "ve **YAVAŞLIK / konuları", "~ciddi sıkıntı / yaratıyordu."]),
    ("cekilme", 24, "Tamamen zararına satılmaya başlandı ve piyasadan çekildiler.",
     ["Tamamen / **ZARARINA", "satılmaya başlandı", "ve piyasadan / *ÇEKİLDİLER."]),
    ("strateji", 28, "Strateji farklı.", [None]),
    ("garanti", 30, "Bir garanti müşteri var.", ["Bir **GARANTİ / müşteri var."]),
    ("garanti", 31, "Modellerden biri kamu çalışanlarına özel.", ["Modellerden biri", "*KAMU / çalışanlarına ~özel."]),
    ("kripto", 34, "Bu yüzden de güvenlik çok öncelikli.", ["Bu yüzden de / **GÜVENLİK", "çok ~öncelikli."]),
    ("devlet", 37, "Vestel özel bir şirketti.", ["*VESTEL / ~özel bir şirketti."]),
    ("devlet", 39, "Bu sefer arkasında tamamen devlet var.", ["Bu sefer / arkasında", "tamamen **DEVLET_VAR."]),
    ("telekom", 41, "Diğer yandan", ["Diğer ~yandan"]),
    ("telekom", 42, "ortaklardan biri direkt Türk Telekom.", ["ortaklardan biri / direkt", "**TÜRK_TELEKOM."]),
    ("telekom", 45, "Bu yüzden de müşteri ağı çok daha geniş.",
     ["Bu yüzden de / *MÜŞTERİ_AĞI", "çok daha **GENİŞ."]),
    ("fatura", 47, "Telefonu faturana ekleyip", ["*TELEFONU / **FATURANA ~ekleyip"]),
    ("fatura", 49, "seni sisteme bağlayabilir.", ["seni *SİSTEME / ~bağlayabilir."]),
    ("zamanlama", 51, "En önemli sebeplerden biri de zamanlama.",
     ["En önemli / sebeplerden biri de", "**ZAMANLAMA."]),
    ("zamanlama", 53, "Şu an 5G'ye geçildi.", ["Şu an / *5G'YE ~geçildi."]),
    ("milyonlar", 55, "Ama geçmeyen", ["Ama ~geçmeyen"]),
    ("milyonlar", 56, "uyumlu olmayan", ["*UYUMLU / olmayan"]),
    ("milyonlar", 57, "milyonlarca telefon var.", ["**MİLYONLARCA / telefon var."]),
    ("milyonlar", 58, "Bu da yeni bir pazar demek.", ["Bu da yeni bir / **PAZAR ~demek."]),
    ("uydu", 60, "Ayrıca depremde şebeke çökerse uydu üzerinden de haberleşme imkanı olacak.",
     ["Ayrıca *DEPREMDE / şebeke ~çökerse", "**UYDU / üzerinden de", "haberleşme / imkânı olacak."]),
    ("ama", 65, "Ama değişmeyen olumsuz şartlar da var.", [None]),   # sahne "AMA" yazısını kendisi çarptırır
    ("pazar", 68, "Türkiye'de yılda 11 milyon telefon satılıyor.",
     ["Türkiye'de yılda / **11_MİLYON", "telefon ~satılıyor."]),
    ("pazar", 71, "Apple ve Samsung her biri yılda 200 milyondan fazla telefon satıyor.",
     ["*APPLE ve *SAMSUNG / her biri yılda", "**200_MİLYONDAN / fazla telefon satıyor."]),
    ("ozet", 75, "Kısacası bu aslında bir telefon projesinden çok",
     ["Kısacası bu ~aslında", "bir *TELEFON / projesinden çok"]),
    ("ozet", 79, "güvenlik ve abone projesi diyebiliriz.", ["*GÜVENLİK ve / *ABONE projesi", "~diyebiliriz."]),
    ("yasar", 82, "En büyük alıcısı kamu", ["En büyük alıcısı / **KAMU"]),
    ("yasar", 84, "ve arkasında devlet olduğu", ["ve arkasında / *DEVLET olduğu"]),
    ("yasar", 86, "için proje bu sefer büyük ihtimalle yaşayacak.",
     ["için proje / bu sefer", "~büyük_ihtimalle / **YAŞAYACAK."]),
    ("final", 89, "Peki senin cebine girer mi?", ["Peki senin / **CEBİNE ~girer_mi?"]),
    ("final", 91, "Sen alır mısın?", [None]),                  # kapanış yazısı sahnede
]
TAIL = 2.4          # son cümleden sonra kapanış kartı için

# gelen sahne -> (geçiş türü, yarım süre sn, ayar); film.py (görüntü) ve ses.py (ses) birlikte kullanır
# "geri": önceki sahne hızla geri sarılır (VHS), telefon.film.py'de tanımlı.
GECIS = {
    "satis": ("kes", 0.0, None), "vestel": ("geri", 0.4, None), "soru": ("flas", 0.0, None),
    "yuzde7": ("savur", 0.18, "sol"), "satamamak": ("kes", 0.0, None), "hata": ("bozul", 0.16, None),
    "cekilme": ("savur", 0.18, "sag"), "strateji": ("karart", 0.25, None), "garanti": ("isik", 0.28, None),
    "kripto": ("zoom", 0.22, (540, 760)), "devlet": ("savur", 0.18, "yukari"), "telekom": ("erit", 0.25, None),
    "fatura": ("savur", 0.18, "sol"), "zamanlama": ("isik", 0.25, None), "milyonlar": ("kes", 0.0, None),
    "uydu": ("karart", 0.25, None), "ama": ("kes", 0.0, None), "pazar": ("savur", 0.18, "asagi"),
    "ozet": ("karart", 0.25, None), "yasar": ("erit", 0.22, None), "final": ("zoom", 0.22, (540, 900)),
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


def _estimate_starts(rate=FZ.SYL_PER_SEC, pause=0.35, start=0.3):
    """Ne ses kaydı ne ekran saniyesi varsa: cümle başlarını hece sayısından tahmin et (enerjik okuma hızı)."""
    starts, t = [], start
    for _, _, text, _ in LINES:
        starts.append(t)
        t += sum(syllables(w) for w in FZ.words_of(text)) / rate + text.count(",") * 0.18 + pause
    return 0.0, rate, pause, np.array(starts)


def _starts():
    """LINES'taki saniyelerden biri None ise hece tahmini, hepsi doluysa ekran saniyelerine oturtma."""
    return _estimate_starts() if any(ln[1] is None for ln in LINES) else _fit_starts()


def build(vo_words=None):
    _, rate, pause, starts = _starts()
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
    cost, rate, pause, starts = _starts()
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
