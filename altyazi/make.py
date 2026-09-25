import os, sys, cv2, numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render as R
np.random.seed(7)

KEVIN_CUES = """
0.20 2.45   *SERVET yaratmak
2.50 4.65   tek bir ~kelimeye dayanır:
4.70 6.25   **DİSİPLİN.
6.40 8.35   Bu,@6.4 şu@7.7 *YETENEKTİR:@7.9
8.40 10.15  bir şeye bakıp / şunu@9.2 ~diyebilmek:@9.45
10.20 11.95 “Bunu / **ALMAYACAĞIM.”@10.5
12.00 12.95 O *PARA / benim için
13.00 14.55 *ÇALIŞMAYA / ~devam ~edecek.
14.60 17.25 Pek@14.6 *AZ@14.85 insanda@15.1 / bu@15.5 *DİSİPLİN@16.1 var.@16.55
18.30 20.55 *ZENGİNLERDE@18.3 / ise@18.9 bu@19.1 *DİSİPLİN@19.5 var.@19.95
20.60 22.35 Onlarla@20.6 *İLERİKİ@21.1 / yaşlarında@21.5 tanışırsın.@21.8
22.40 23.85 Fark@22.4 edersin@22.55 ki@22.75 / *GENÇKEN@23.3
23.90 25.55 **HİÇBİR_ŞEYLERİ@23.9 / ~yoktu.@24.7
25.60 27.25 Ömür@25.6 boyu@25.8 *MAAŞLI@26.1 çalışıp@26.7
27.30 29.55 şimdi@27.3 finansal@27.9 *ÖZGÜRLÜĞE@28.1 / kavuşanlar@28.7 ~bile.@29.05
29.60 31.30 **“HAYIR”@29.6 / ~diyebilme@30.0 *DİSİPLİNİ.@30.35
"""

BUFFETT_CUES = """
0.00 1.55   **KAPİTALİZM
1.60 3.85   sizi *MİLYARDER / yaptı, Warren.
3.90 5.75   Kapitalizm, ~bilirsiniz,
5.80 8.25   *Donald_Trump'ı da / *MİLYARDER yaptı.
8.30 9.75   Peki neden / işe *YARAMIYOR
9.80 11.45  daha fazla *GENÇ ~için?
11.50 13.45 Çünkü *PİYASA / sistemi
13.50 15.75 zamanla giderek / *UZMANLAŞIYOR.
15.80 18.75 IQ'nuz *130 olsa / ve bir *ÇİFTLİKTE çalışsanız,
18.80 21.85 yanınızdakinin de / IQ'su *90 olsa,
21.90 23.35 o kişi ~muhtemelen
23.40 25.25 sizin *%90'ınız kadar / *DEĞERLİYDİ.
25.30 26.45 Yani arada pek / *FARK yoktu.
26.50 28.45 Elde hiçbir / *ARAÇ yoktu,
28.50 29.55 ne *PLANLAMA / ne de başka bir şey.
29.60 31.25 Bir *TARIM / ~toplumuyduk.
31.30 33.95 Sonra@31.3 *SANAYİ@32.5 / toplumuna@32.9 geçtik.@33.3
34.00 37.05 Ve@34.0 1915'te@34.3 *Ford'un@35.5 / montaj@35.9 hattındaysanız,@36.2
37.10 40.75 zekâ farkları gibi şeyler / yine de *ÖNEMLİYDİ,@39.4
40.80 42.45 ama *50'ye_1
42.50 44.45 ya da *100'e_1 / *FARK yaratmıyordu.
44.50 47.45 Artık öyle bir / *EKONOMİDEYİZ ki
47.50 49.55 *UZMANLAŞMIŞ / yetenekler
49.60 51.85 **İNANILMAZ / paralar ~kazandırıyor.
51.90 54.55 Ve eğer ~azıcık bile,
54.60 57.35 *PİYASA sistemine / tam *UYUM sağlayamıyorsanız,
57.40 58.75 **GERİDE / ~kalırsınız.
"""

# Türkçe konuşma (iPhone, HDR). Kelime zamanları whisper-small ile çıkarıldı.
YALNIZ_CUES = """
0.00 1.95   Şu@0.00 ~adamdan@0.34 / **KORKACAKSIN.@0.80
2.00 3.84   ~Yalnız@2.02 ~başına@2.28 / *YEMEK@2.90 yiyen,@3.20
3.86 6.40   ~yalnız@3.88 ~başına@4.36 / *EĞLENCEYE@4.96 giden,@5.94
6.44 8.60   *SİNEMAYA@6.50 giden@7.04 / veya@7.66 *TİYATROYA@7.86 giden@8.44
8.62 10.58  veya@8.64 *KENDİ@8.84 *BAŞINA@9.24 / zaman@9.86 geçiren@10.20
10.60 12.00 adamdan@10.64 / **KORKACAKSIN.@11.12
12.02 13.58 Çünkü@12.08 bu@12.28 adam@12.52 / *HİÇBİR@12.72 *ZAMAN@13.20
13.60 18.00 hiç@13.62 kimseye@13.92 / **MUHTAÇ@14.44 ~olmaz.@15.12
"""

WHITE, RED = (255, 255, 255), (237, 28, 36)

def kevin_frame(fr):
    fr = fr.copy()
    fr[236:352, :] = 0          # remove English title
    return fr

def buffett_frame(fr):
    out = np.zeros_like(fr)
    out[0:840] = fr[0:840]      # keep picture above the burned-in English captions
    return out

JOBS = {
    "kevin": dict(src="girdi/kevin.mp4", cues=KEVIN_CUES, frame=kevin_frame, cap_top=903,
                  title=[[("Kevin O'Leary'ye göre ", WHITE), ("servet", RED), (" yaratmak", WHITE)],
                         [("tek bir şeye bağlı", WHITE)]]),
    "buffett": dict(src="girdi/buffett.mp4", cues=BUFFETT_CUES, frame=buffett_frame, cap_top=864, title=None),
    # tam ekran video: altyazı yüzün altında, göğüs hizasında, görüntünün üstünde
    "yalniz": dict(src="girdi/yalniz.mp4", cues=YALNIZ_CUES, frame=lambda fr: fr, cap_top=767, title=None,
                   vf_in=R.HDR_TO_SDR, on_video=True, maxw=560),
}

def build(name):
    j = JOBS[name]
    R.ON_VIDEO = j.get("on_video", False)
    R.MAXW = j.get("maxw", 600)
    cues = R.parse_cues(j["cues"])
    ov = R.draw_title(j["title"], 36, 240, 36, 650) if j["title"] else None
    return j, cues, ov

if __name__ == "__main__":
    name, mode = sys.argv[1], sys.argv[2]
    j, cues, ov = build(name)
    if mode == "preview":
        for c in cues:
            c.layout(j["cap_top"])
        want = {int(round(float(ts) * R.FPS)): ts for ts in sys.argv[3:]}
        outs = []
        frames = R.read_frames(j["src"], j.get("vf_in"))
        for i, fr in enumerate(frames):
            if i in want:
                t = i / R.FPS
                base = j["frame"](fr)
                if base.shape[:2] != (R.H, R.W):
                    base = cv2.resize(base, (R.W, R.H), interpolation=cv2.INTER_LANCZOS4)
                img = Image.fromarray(base).convert("RGBA")
                if ov is not None:
                    img.alpha_composite(ov)
                for c in cues:
                    if c.start - 0.5 <= t <= c.end:
                        c.draw(img, t)
                os.makedirs("onizleme", exist_ok=True)
                p = f"onizleme/{name}_{want[i]}.png"
                img.convert("RGB").resize((360, 640), Image.LANCZOS).save(p)
                outs.append(p)
            if i >= max(want):
                break
        frames.close()
        print(" ".join(outs))
    else:
        os.makedirs("videolar", exist_ok=True)
        R.run(j["src"], f"videolar/{name}_tr.mp4", cues, j["frame"], j["cap_top"], ov, vf_in=j.get("vf_in"))
