"""Tekstil filmi sahneleri: 3D plakalar (gerçekçi çizimler) + harita + veri grafikleri.

Her sahne: f(p, t, d, wt, lt) -> (doğrusal görüntü, post)
  wt: sahnedeki bütün kelimelerin sahne içi zamanları, lt: cümle başlarının sahne içi zamanları,
  post: renk işleminden sonra çizilecek keskin katman (yazı, grafik) ya da None.
"""
import math, os, sys
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "film"))
import gfx as G                                            # noqa: E402
import ortak as O                                          # noqa: E402
from ortak import W, H, ONE, seg, ease_out, ease_in, ease_io, spring, lerp   # noqa: E402
import exr                                                 # noqa: E402
import harita as HM                                        # noqa: E402

PLAKA = os.environ.get("TEKSTIL_3D_OUT", os.path.join(HERE, "plakalar"))
YELLOW, CYAN, RED = G.YELLOW, G.CYAN, G.hexc("#E0463A")
GREEN = G.hexc("#3DDC84")
WARM = G.hexc("#FFB45A")
_XX, _YY = G.grid(W, H)


# ================================================================== plaka araçları
_PL = {}


def plate(name):
    if name not in _PL:
        _PL[name] = exr.oku(os.path.join(PLAKA, name + ".exr"))
    return _PL[name]


def loop_frame(prefix, k):
    """Kısmi çizilmiş döngü karesini tam kareye yumuşak kenarla yerleştir."""
    base = plate(f"{prefix}_0000")
    if k == 0:
        return base["rgb"]
    key = (prefix, k)
    if key not in _PL:
        e = exr.oku(os.path.join(PLAKA, f"{prefix}_{k:04d}.exr"))["rgb"]
        m = e.sum(2) > 0
        ys, xs = np.nonzero(m)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        fe = np.zeros(m.shape, np.float32)
        fe[y0 + 10:y1 - 10, x0 + 10:x1 - 10] = 1
        fe = G.blur(fe, 5)[y0:y1, x0:x1][..., None]
        _PL[key] = (y0, y1, x0, x1, e[y0:y1, x0:x1], fe)
    y0, y1, x0, x1, crop, fe = _PL[key]
    out = base["rgb"].copy()
    out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - fe) + crop * fe
    return out


def push(rgb, depth, u, z0=1.0, z1=1.07, k=0.0, c=(540, 960), dx=0.0, dy=0.0, dref=6.0):
    """2.5D kamera: yavaş yaklaşma; k>0 ise yakın nesneler daha çok büyür (derinlik paralaksı)."""
    s = (z0 + (z1 - z0) * u) * 1.012                        # sallantı için kenarlarda küçük pay
    sx = (c[0] + (_XX - c[0]) / s - dx).astype(np.float32)
    sy = (c[1] + (_YY - c[1]) / s - dy).astype(np.float32)
    if k and depth is not None:
        d = cv2.remap(depth, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        f = 1 + k * u * (1 / np.maximum(d, 1.5) - 1 / dref)            # çok yakın nesneler bükülmesin
        sx = (c[0] + (sx - c[0]) / f).astype(np.float32)
        sy = (c[1] + (sy - c[1]) / f).astype(np.float32)
    out = cv2.remap(rgb, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    dep = cv2.remap(depth, sx, sy, cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE) if depth is not None else None
    return out, dep


def hand(t, amp=3.0, seed=0.0):
    """Elde tutulan kamera gibi çok hafif, yavaş sallantı (piksel)."""
    dx = amp * (math.sin(t * 0.83 + seed) + 0.6 * math.sin(t * 1.71 + 2 * seed) + 0.3 * math.sin(t * 3.1 + seed))
    dy = amp * (math.sin(t * 0.67 + 1.3 + seed) + 0.5 * math.sin(t * 1.43 + seed) + 0.25 * math.sin(t * 2.9 + 3 * seed))
    return dx, dy


def haze(rgb, depth, color, dens, dmax=3000.0):
    d = np.minimum(depth, dmax)
    h = (1 - np.exp(-dens * d))[..., None]
    sky = (depth > 1e5)[..., None]
    return np.where(sky, rgb, rgb * (1 - h) + np.asarray(color, np.float32) * h)


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055).astype(np.float32)


def finish(lin, seed, exposure=1.0, bloom_k=0.35, vig=0.5, sat=0.92, lift=(0.0, 0.008, 0.014),
           gain=(1.03, 1.0, 0.95), grain_amt=0.028):
    """Fotoğraf gibi renk işlemi: ışık taşması, vinyet, ACES ton eğrisi, sRGB, renk tonu, lens, tane."""
    x = np.maximum(lin * exposure, 0)
    x = G.bloom(x, 0.9, strength=bloom_k)
    x = G.vignette(x, vig)
    x = srgb(G.filmic(x, 1.0))
    lum = x.mean(2, keepdims=True)
    x = lum + (x - lum) * sat
    x = x * np.asarray(gain, np.float32) + np.asarray(lift, np.float32) * (1 - x)
    x = G.chroma(x, 1.6)
    return G.grain(x, grain_amt, seed)


def tag(im, txt, x=1010, y=250, a=1.0):
    """Sağ üstte küçük etiket (TEMSİLİ GÖRSEL, kaynak)."""
    if a > 0.01:
        O.text(im, txt, x, y, 20, "Inter.ttf", 600, ONE * 0.8, "rm", alpha=0.75 * a, tracking=3)
    return im


def source(im, txt, a=1.0, y=1255):
    """Küçük kaynak notu (koyu yarı saydam zeminle her arka planda okunur)."""
    if a > 0.01:
        m = G.text_mask(txt, "Inter.ttf", 21, 500)
        w, h = m.shape[1] + 28, m.shape[0] + 14
        x0 = int(540 - w / 2)
        O.rect_fill(im, x0, int(y - h / 2), w, h, np.zeros(3, np.float32), 0.55 * a, r=h // 2)
        G.over(im, ONE * 0.85, m * a, x0 + 14, int(y - m.shape[0] / 2))
    return im


_TOPG = np.clip(1 - _YY / 820, 0, 1)[..., None] ** 1.6


def shade_top(im, k=0.45):
    """Üstteki yazılar okunsun diye görüntünün üst kısmını hafifçe karart."""
    im *= 1 - k * _TOPG
    return im


def chip(im, txt, x, y, color=YELLOW, a=1.0, px=30, dark=True, anchor="lm", icon=None):
    """Yuvarlak köşeli etiket (sarı zemin, koyu yazı); icon: "check" ya da "cross" (solda çizilir)."""
    if a <= 0.01:
        return im
    m = G.text_mask(txt, "Montserrat.ttf", px, 800)
    ic = int(px * 1.1) if icon else 0
    w, h = m.shape[1] + 34 + ic, m.shape[0] + 18
    x0 = int(x if anchor[0] == "l" else x - w / 2 if anchor[0] == "m" else x - w)
    O.rect_fill(im, x0, int(y - h / 2), w, h, color, a, r=h // 2)
    fg = G.hexc("#111111") if dark else ONE
    G.over(im, fg, m * a, x0 + 17 + ic, int(y - m.shape[0] / 2))
    if icon == "check":
        s = px * 0.5
        O.poly(im, [[x0 + 20, y], [x0 + 20 + s * 0.45, y + s * 0.45], [x0 + 20 + s * 1.2, y - s * 0.55]], fg, max(4, px // 7), a)
    elif icon == "cross":
        s = px * 0.42
        cx = x0 + 20 + s
        O.poly(im, [[cx - s, y - s], [cx + s, y + s]], fg, max(4, px // 7), a)
        O.poly(im, [[cx + s, y - s], [cx - s, y + s]], fg, max(4, px // 7), a)
    return im


def arrow(im, x, y, size, up=True, color=RED, a=1.0, thick=None):
    """Çizilmiş ok (fontta ok işareti olmadığı için)."""
    if a <= 0.01:
        return im
    s = size
    th = thick or max(4, int(s * 0.16))
    d = 1 if up else -1                                     # ekranda y aşağı doğru artar
    O.poly(im, [[x, y - d * s * 0.5], [x, y + d * s * 0.45]], color, th, a)
    O.poly(im, [[x - s * 0.34, y + d * (-s * 0.12)], [x, y - d * s * 0.5], [x + s * 0.34, y + d * (-s * 0.12)]],
           color, th, a)
    return im


def counter_text(v, fmt="{:,.0f}"):
    return fmt.format(v).replace(",", ".")


# ================================================================== 1) FABRİKA: 350.000 iş kaybı
def fabrika(p, t, d, wt, lt):
    pl = plate("fabrika_genis_0000")
    img, dep = push(pl["rgb"], pl["depth"], ease_io(p), 1.0, 1.08, k=0.25, c=(430, 980), dx=hand(t)[0], dy=hand(t)[1])
    img = haze(img, dep, (0.05, 0.055, 0.06), 0.012)
    t_yil = wt[5] if len(wt) > 5 else d * 0.4
    t_num = wt[9] if len(wt) > 9 else d * 0.7

    def post(im):
        shade_top(im, 0.25)
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "TÜRKİYE  ·  TEKSTİL", color=G.GOLD, alpha=seg(t, 0.1, 0.5))
        a = seg(t, t_yil - 0.1, t_yil + 0.25)
        O.text(im, "SON 3,5 YILDA", 540, 420, 34, "Inter.ttf", 700, ONE * 0.9, alpha=a, tracking=6)
        k = seg(t, t_num - 0.15, t_num + 0.9)
        if k > 0:
            v = 350000 * ease_out(k)
            sc = lerp(1.25, 1.0, ease_out(seg(t, t_num - 0.15, t_num + 0.3)))
            O.text(im, "−" + counter_text(v), 540, 540, 150, "Montserrat.ttf", 900, RED, alpha=min(1, k * 4),
                   scale=sc, glow=0.35)
            O.text(im, "İŞ KAYBI", 540, 660, 40, "Montserrat.ttf", 800, ONE, alpha=seg(t, t_num + 0.3, t_num + 0.6),
                   tracking=10)
            source(im, "Kaynak: SGK sigortalı çalışan verisi (2022 sonu – Haziran 2026)", seg(t, t_num + 0.5, t_num + 0.9),
                   y=730)
        return im
    return img, post


# ================================================================== harita ortak
CAM_WIDE = (33.8, 38.0, 88.0)
CAM_BORDER = (37.25, 36.75, 640.0)
TILT = None


def tilt_matrix(strength=0.22):
    """Haritaya hafif 3D eğim: üst kenar uzağa gider (sinematik perspektif)."""
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    inset = W * strength
    dst = np.float32([[inset, 140], [W - inset, 140], [W + 60, H + 40], [-60, H + 40]])
    return cv2.getPerspectiveTransform(src, dst)


TILT = tilt_matrix()


_MASK = None


def map_mask():
    """Eğik haritanın yumuşak kenarlı maskesi (kenarlar karanlıkta kaybolur)."""
    global _MASK
    if _MASK is None:
        m = cv2.warpPerspective(np.ones((H, W), np.float32), TILT, (W, H), flags=cv2.INTER_LINEAR)
        m = cv2.erode(m, np.ones((61, 61), np.uint8))
        _MASK = G.blur(m, 40)[..., None]
    return _MASK


def warp_pt(M, xy):
    v = M @ np.array([xy[0], xy[1], 1.0])
    return v[:2] / v[2]


def map_frame(cam, hi, extra=None):
    """Harita + hafif eğim; extra(img, cam) düz haritaya çizim yapar (oklar, pinler)."""
    img, masks = HM.base(cam, hi)
    if extra:
        extra(img, cam, masks)
    img = cv2.warpPerspective(img, TILT, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
                              borderValue=(0.0, 0.0, 0.0))
    mask = map_mask()
    bg = np.array([0.008, 0.012, 0.02], np.float32)
    img = img * mask + bg * (1 - mask)
    fog = np.clip(1 - (_YY - 120) / 700, 0, 1)[..., None] ** 1.5              # ufka doğru sis
    img = img * (1 - 0.75 * fog) + bg * 0.75 * fog
    return img, masks


def screen_of(name, cam):
    return warp_pt(TILT, HM.city_xy(name, cam))


def arrow_curve(a, b, bend=0.25, n=40):
    a, b = np.asarray(a, float), np.asarray(b, float)
    mid = (a + b) / 2
    nrm = np.array([-(b - a)[1], (b - a)[0]])
    ctrl = mid + nrm * bend
    u = np.linspace(0, 1, n)[:, None]
    return (1 - u) ** 2 * a + 2 * (1 - u) * u * ctrl + u ** 2 * b


def draw_arrows(img, cam, progress, color=WARM, alpha=1.0, target="El-Rai", stall=0.0, hubs=None):
    """Tekstil merkezlerinden hedefe akan oklar (düz haritaya, sonra eğilir)."""
    glow = np.zeros_like(img)
    tgt = HM.city_xy(target, cam)
    for i, hname in enumerate(hubs or HM.HUBS):
        a = HM.city_xy(hname, cam)
        path = arrow_curve(a, tgt, 0.18 + 0.05 * (i % 3))
        u = np.clip(progress * 1.25 - i * 0.03, 0, 1)
        if u <= 0:
            continue
        u = u * (1 - stall)
        n = max(2, int(len(path) * u))
        seg_ = path[:n]
        O.poly(img, seg_, color * 0.9, 5, alpha)
        O.poly(glow, seg_, color, 10, alpha * 0.7)
        head = seg_[-1]
        O.circle(img, head[0], head[1], 7, color, fill=True, alpha=alpha)
        O.circle(glow, head[0], head[1], 16, color, fill=True, alpha=alpha * 0.6)
    img += G.blur(glow, 6) * 0.8
    return img


def city_dots(img, cam, names, color=(0.9, 0.85, 0.7), r=5, a=1.0):
    for n in names:
        x, y = HM.city_xy(n, cam)
        O.circle(img, x, y, r, np.asarray(color, np.float32) * 0.9, fill=True, alpha=a)


def label_city(im, name, cam, dx=14, dy=0, a=1.0, px=24, color=ONE, anchor="lm", weight=600):
    x, y = screen_of(name, cam)
    if a > 0.01 and -50 < x < W + 50 and 100 < y < H:
        O.text(im, name.upper(), x + dx, y + dy, px, "Inter.ttf", weight, color, anchor, alpha=a, tracking=2)


HI_BASE = {"TUR": ((0.07, 0.03, 0.025), 1.0), "SYR": ((0.06, 0.05, 0.025), 1.0)}


# ================================================================== 2) SÖYLENTİ: herkes Suriye diyor
BUBBLES = [("Fabrikalar Suriye'ye kayıyor!", 90, 330, -3), ("Herkes oraya gidiyor…", 560, 440, 2),
           ("Üretim sınırın ötesine taşınıyor", 90, 1000, -2)]


def soylenti(p, t, d, wt, lt):
    cam = HM.lerp_cam(CAM_WIDE, (35.2, 37.6, 120.0), ease_io(p))
    prog = ease_io(seg(p, 0.15, 1.0))
    img, _ = map_frame(cam, HI_BASE, lambda im, c, m: (city_dots(im, c, HM.HUBS), draw_arrows(im, c, prog)))

    def post(im):
        O.label(im, "HARİTA  ·  TÜRKİYE → SURİYE", color=WARM, alpha=seg(t, 0.1, 0.4))
        label_city(im, "İstanbul", cam, a=0.8)
        label_city(im, "Gaziantep", cam, dy=-22, a=0.8)
        O.text(im, "SURİYE", *screen_of("Şam", cam) + np.array([0, -60]), 30, "Montserrat.ttf", 800, ONE * 0.8,
               alpha=0.9, tracking=8)
        O.text(im, "TÜRKİYE", *screen_of("Ankara", cam) + np.array([0, -30]), 34, "Montserrat.ttf", 800, ONE * 0.85,
               alpha=0.9, tracking=10)
        for i, (txt, x, y, rot) in enumerate(BUBBLES):
            k = spring(seg(t, 0.25 + i * 0.35, 0.6 + i * 0.35), 1.6, 5)
            if k <= 0:
                continue
            m = G.text_mask(txt, "Inter.ttf", 30, 700)
            w, h = m.shape[1] + 44, m.shape[0] + 30
            bx, by = int(x), int(y)
            O.glass(im, bx, by, w, h, r=h // 2, frost=10, tint=0.08, alpha=min(1, k))
            G.over(im, ONE, m * min(1, k), bx + 22, by + 15)
        return im
    return img, post


# ================================================================== 3) İLK FABRİKA: El-Rai, ~150 kişi  (ve 350.000 ile kıyas)
_DOTS = None


def dot_field():
    """350.000 nokta (700 x 500): her nokta kaybedilen bir iş; sol üstteki 150'si sarı."""
    global _DOTS
    if _DOTS is None:
        cols, rows, sp = 500, 700, 3
        img = np.zeros((rows * sp, cols * sp), np.float32)
        img[1::sp, 1::sp] = 1.0
        img = cv2.dilate(img, np.ones((2, 2), np.uint8))
        hl = np.zeros_like(img)
        hl[:10 * sp, :15 * sp] = img[:10 * sp, :15 * sp]
        _DOTS = (img, hl)
    return _DOTS


def ilk(p, t, d, wt, lt):
    t_ilk = wt[3] if len(wt) > 3 else d * 0.3              # "ilk"
    t_150 = wt[8] if len(wt) > 8 else d * 0.7              # "150" (0:Suriye'de ... 8:150, 9:kişi)
    t_cmp = t_150 + 0.25
    zc = ease_io(seg(t, 0.0, t_ilk + 0.4))
    cam = HM.lerp_cam((35.2, 37.6, 120.0), CAM_BORDER, zc)

    def extra(im, c, masks):
        bl = HM.border_line(masks, "TUR", "SYR").astype(np.float32)
        im += G.blur(bl, 2)[..., None] * WARM * 0.5 * zc
        city_dots(im, c, ["Gaziantep", "Kilis", "Halep"], r=6)
        x, y = HM.city_xy("El-Rai", c)
        pulse = (t * 1.2) % 1
        O.circle(im, x, y, 10 + 40 * pulse, YELLOW, 3, (1 - pulse) * seg(t, t_ilk - 0.3, t_ilk))
        O.circle(im, x, y, 11, YELLOW, fill=True, alpha=seg(t, t_ilk - 0.3, t_ilk))
    img, _ = map_frame(cam, HI_BASE, extra)
    cmp_k = seg(t, t_cmp, t_cmp + 0.35)
    if cmp_k > 0:                                          # 150 sarı nokta -> uzaklaşınca 350.000 gri nokta
        dots, hl = dot_field()
        z = seg(t, t_cmp + 0.3, d - 0.05)
        ez = ease_io(z)
        scale = math.exp(math.log(9.0) * (1 - ez) + math.log(1080 / dots.shape[1] * 0.92) * ez)
        ax, ay = lerp(22, dots.shape[1] / 2, ez), lerp(15, dots.shape[0] / 2, ez)      # odak: 150'lik blok -> tüm alan
        sx_, sy_ = 540, lerp(700, 1000, ez)
        M = np.float32([[scale, 0, sx_ - ax * scale], [0, scale, sy_ - ay * scale]])
        dm = cv2.warpAffine(dots, M, (W, H), flags=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        hm = cv2.warpAffine(hl, M, (W, H), flags=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)
        bg = np.zeros_like(img) + np.array([0.012, 0.014, 0.018], np.float32)
        layer = bg + dm[..., None] * 0.16 + hm[..., None] * YELLOW * 1.6
        img = img * (1 - cmp_k) + layer * cmp_k
        hx, hy = M @ np.array([22.0, 15.0, 1.0])                  # 150'lik blok: uzaklaştıkça halka ile göster
        ring = seg(ez, 0.35, 0.7)
        if ring > 0:
            pulse = (t * 1.6) % 1
            O.circle(img, hx, hy, 26 + 10 * pulse, YELLOW * 2.0, 5, ring * cmp_k)
            O.circle(img, hx, hy, 60 + 40 * pulse, YELLOW, 3, ring * cmp_k * (1 - pulse))

    def post(im):
        O.label(im, "SURİYE  ·  EL-RAİ SANAYİ BÖLGESİ", color=WARM, alpha=seg(t, 0.1, 0.4) * (1 - cmp_k))
        if cmp_k < 1:
            a = (1 - cmp_k)
            label_city(im, "Kilis", cam, dy=-20, a=a * zc)
            label_city(im, "Gaziantep", cam, dy=-20, a=a * zc)
            label_city(im, "Halep", cam, dy=20, a=a * zc)
            x, y = screen_of("El-Rai", cam)
            k = seg(t, t_ilk - 0.2, t_ilk + 0.2)
            if k > 0:
                cxl = min(x, 700)
                chip(im, "İLK TÜRK FABRİKASI", cxl, y - 120, YELLOW, k * a, 30, anchor="mm")
                O.text(im, "(bildirilen)", cxl, y - 78, 24, "InstrumentSerif-Italic.ttf", None, ONE * 0.85, alpha=k * a)
                O.text(im, "EL-RAİ", x + 26, y - 18, 28, "Montserrat.ttf", 800, YELLOW, "lm", alpha=k * a, tracking=3)
            k2 = seg(t, t_150 - 0.1, t_150 + 0.25)
            O.text(im, "~150 ÇALIŞAN", min(x - 60, 640), y + 50, 40, "Montserrat.ttf", 900, ONE, "lm", alpha=k2 * a,
                   glow=0.2)
            O.text(im, "TÜRKİYE", 540, 520, 36, "Montserrat.ttf", 800, ONE * 0.7, alpha=a * zc, tracking=12)
            O.text(im, "SURİYE", 540, 1180, 36, "Montserrat.ttf", 800, ONE * 0.7, alpha=a * zc, tracking=12)
        if cmp_k > 0:
            z = seg(t, t_cmp + 0.3, d - 0.05)
            O.text(im, "150 KİŞİ", 540, 330, 54, "Montserrat.ttf", 900, YELLOW, alpha=cmp_k * (1 - seg(z, 0.5, 0.8)), glow=0.3)
            k3 = seg(z, 0.55, 0.85)
            O.text(im, "150", 300, 300, 60, "Montserrat.ttf", 900, YELLOW, alpha=k3, glow=0.3)
            O.text(im, "SURİYE'DE", 300, 360, 24, "Inter.ttf", 700, ONE * 0.8, alpha=k3, tracking=4)
            O.text(im, "350.000", 760, 300, 60, "Montserrat.ttf", 900, ONE, alpha=k3)
            O.text(im, "TÜRKİYE'DE KAYIP", 760, 360, 24, "Inter.ttf", 700, ONE * 0.8, alpha=k3, tracking=4)
            O.text(im, "vs", 540, 300, 34, "InstrumentSerif-Italic.ttf", None, ONE * 0.7, alpha=k3)
        return im
    return img, post


# ================================================================== 4-5) NEDEN / İŞÇİLİK: dikiş makinesi yakın çekim + 3 neden
REASONS = [("1", "İŞÇİLİK MALİYETİ", "↑"), ("2", "FAİZ", "↑"), ("3", "AVRUPA SİPARİŞİ", "↓")]


def needle_plate(t):
    k = int(t * 30) % 8                                    # 8 karelik dikiş döngüsü
    pl = plate("fabrika_yakin_0000")
    return loop_frame("fabrika_yakin", k), pl["depth"]


def reason_cards(im, t, t0, focus=None, fk=0.0):
    for i, (n, txt, arr) in enumerate(REASONS):
        k = ease_out(seg(t, t0 + i * 0.22, t0 + i * 0.22 + 0.35))
        if k <= 0:
            continue
        y = 380 + i * 120
        x = int(80 - 60 * (1 - k))
        dim = 1.0 if focus is None else (1.0 if i == focus else 1 - 0.65 * fk)
        O.glass(im, x, y, 700, 96, r=30, frost=14, tint=0.06, alpha=k * dim)
        O.text(im, n, x + 50, y + 48, 44, "Montserrat.ttf", 900, YELLOW, alpha=k * dim)
        O.text(im, txt, x + 100, y + 48, 38, "Montserrat.ttf", 800, ONE, "lm", alpha=k * dim)
        arrow(im, x + 650, y + 48, 46, arr == "↑", RED if arr == "↑" else CYAN, k * dim)


def neden(p, t, d, wt, lt):
    rgb, dep = needle_plate(t)
    img, dep2 = push(rgb, dep, ease_io(p), 1.0, 1.05, c=(600, 700), dx=hand(t, 2.0, 1)[0], dy=hand(t, 2.0, 1)[1])
    t_n = wt[2] if len(wt) > 2 else d * 0.4

    def post(im):
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "SEKTÖRÜN SÖZÜ", color=G.GOLD, alpha=seg(t, 0.1, 0.4))
        reason_cards(im, t, t_n)
        return im
    return img, post


def iscilik(p, t, d, wt, lt):
    rgb, dep = needle_plate(t + 2.7)
    img, _ = push(rgb, dep, 1.0, 1.05, 1.12, c=(600, 700), dx=hand(t + 2.7, 2.0, 1)[0], dy=hand(t + 2.7, 2.0, 1)[1])

    def post(im):
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "NEDEN 1  ·  İŞÇİLİK", color=G.GOLD)
        reason_cards(im, 99, 0, focus=0, fk=ease_out(seg(t, 0.0, 0.3)))
        k = spring(seg(t, 0.15, 0.7), 1.3, 5)
        if k > 0:                                           # 1. neden büyüyüp öne çıkar
            O.glass(im, 110, 800, 860, 170, r=50, frost=16, tint=0.1, alpha=min(1, k * 2))
            O.text(im, "İŞÇİLİK MALİYETİ", 160, 885, 52, "Montserrat.ttf", 900, ONE, "lm", alpha=min(1, k * 2))
            arrow(im, 880, 885, 90, True, RED, min(1, k * 2))
        return im
    return img, post


# ================================================================== 6) FAİZ
def faiz(p, t, d, wt, lt):
    pl = plate("fabrika_genis_0000")
    img, _ = push(pl["rgb"], pl["depth"], ease_io(p), 1.25, 1.32, c=(700, 1000))
    img = G.blur(img, 10) * 0.5
    t_f = wt[4] if len(wt) > 4 else d * 0.55              # "faizler"

    def post(im):
        O.label(im, "NEDEN 2  ·  FAİZ", color=G.GOLD)
        k = ease_out(seg(t, 0.05, 0.45))
        O.glass(im, 140, 330, 800, 760, r=48, frost=18, tint=0.05, alpha=k)
        O.text(im, "YATIRIM KREDİSİ", 540, 420, 34, "Inter.ttf", 700, ONE * 0.85, alpha=k, tracking=6)
        O.text(im, "%", 540, 640, 300, "Montserrat.ttf", 900, ONE, alpha=k, glow=0.15)
        u = ease_io(seg(t, t_f - 0.4, t_f + 0.8))
        if u > 0:                                           # yükselen eğri (rakam uydurmadan: yalnız yön)
            xs = np.linspace(220, 860, 60)
            ys = 1000 - (np.exp(np.linspace(0, 2.2, 60)) - 1) / (math.e ** 2.2 - 1) * 220
            n = max(2, int(60 * u))
            O.poly(im, np.stack([xs[:n], ys[:n]], 1), RED, 10, k, glow=0.6)
            O.circle(im, xs[n - 1], ys[n - 1], 12, RED, fill=True, alpha=k)
            O.text(im, "FAİZ", xs[n - 1] - 50, ys[n - 1] - 50, 44, "Montserrat.ttf", 900, RED, "rm", alpha=k * seg(u, 0.5, 0.8))
            arrow(im, xs[n - 1] - 20, ys[n - 1] - 52, 44, True, RED, k * seg(u, 0.5, 0.8))
        return im
    return img, post


# ================================================================== 7) İHRACAT: liman, AB alımı -%16
def ihracat(p, t, d, wt, lt):
    pl = plate("liman_koridor")
    img, dep = push(pl["rgb"], pl["depth"], ease_io(p), 1.0, 1.08, k=0.3, c=(540, 1000), dx=hand(t, 3, 2)[0], dy=hand(t, 3, 2)[1])
    img = haze(img, dep, (0.22, 0.14, 0.08), 0.004)
    t_ab = wt[1] if len(wt) > 1 else d * 0.15              # "Avrupa'nın"
    t_16 = wt[10] if len(wt) > 10 else d * 0.75            # "%16" (0:Üstüne ... 10:%16, 11:düştü)

    def post(im):
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "NEDEN 3  ·  AVRUPA SİPARİŞLERİ", color=WARM, alpha=seg(t, 0.1, 0.4))
        k = ease_out(seg(t, t_ab - 0.1, t_ab + 0.4))
        if k <= 0:
            return im
        O.glass(im, 90, 300, 900, 700, r=44, frost=18, tint=0.04, alpha=k)
        O.rect_fill(im, 90, 300, 900, 700, np.zeros(3, np.float32), 0.45 * k, r=44)     # güneşe karşı okunaklı
        O.text(im, "AB'nin Türkiye'den hazır giyim alımı", 540, 370, 30, "Inter.ttf", 700, ONE * 0.95, alpha=k)
        O.text(im, "Ocak – Mayıs", 540, 415, 26, "Inter.ttf", 500, ONE * 0.75, alpha=k)
        u = ease_out(seg(t, t_ab + 0.3, t_ab + 1.2))
        u2 = ease_out(seg(t, t_16 - 0.9, t_16 - 0.1))
        base_y, hmax = 880, 360
        for i, (yr, val, frac, uu, col) in enumerate((("2025", "4,05 mlr €", 1.0, u, ONE * 0.75),
                                                      ("2026", "3,41 mlr €", 0.842, u2, RED))):
            x = 280 + i * 280
            h = int(hmax * frac * uu)
            if h > 2:
                O.rect_fill(im, x - 80, base_y - h, 160, h, col, 0.92 * k, r=10)
            O.text(im, yr, x, base_y + 42, 32, "Montserrat.ttf", 800, ONE, alpha=k)
            O.text(im, val, x, base_y - h - 34, 30, "Montserrat.ttf", 800, ONE, alpha=k * seg(uu, 0.6, 1.0))
        k3 = seg(t, t_16 - 0.1, t_16 + 0.25)
        if k3 > 0:
            sc = lerp(1.4, 1.0, ease_out(k3))
            O.text(im, "−%16", 815, 660, 96, "Montserrat.ttf", 900, RED, alpha=k3, scale=sc, glow=0.35)
        source(im, "Kaynak: Eurostat verisi (İHKİB raporu), değer bazında, 2026", seg(t, t_16, t_16 + 0.5), y=1045)
        return im
    return img, post


# ================================================================== 8) SURİYE: temsili şehir, akşam
def suriye(p, t, d, wt, lt):
    pl = plate("sehir_aksam")
    img, dep = push(pl["rgb"], pl["depth"], ease_io(p), 1.0, 1.06, k=0.0, c=(540, 900), dx=hand(t, 2, 3)[0], dy=hand(t, 2, 3)[1])
    img = haze(img, dep, (0.5, 0.33, 0.2), 0.0009)

    def post(im):
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "SURİYE", color=WARM, alpha=seg(t, 0.1, 0.4))
        k = spring(seg(t, 0.35, 0.9), 1.2, 5)
        O.text(im, "NEDEN", 540, 470, 60, "Montserrat.ttf", 900, ONE, alpha=min(1, k * 1.5), tracking=14)
        O.text(im, "SURİYE?", 540, 580, 120, "Montserrat.ttf", 900, YELLOW, alpha=min(1, k * 1.5), scale=max(0.6, k),
               glow=0.3)
        return im
    return img, post


# ================================================================== 9) ÜCRET: 575 $ vs 100 $
def ucret(p, t, d, wt, lt):
    a = plate("fabrika_genis_0000")["rgb"]
    b = plate("sehir_aksam")["rgb"]
    left = G.blur(cv2.resize(a[300:1620, 0:1080], (W, H)), 14) * 0.35
    right = G.blur(cv2.resize(b[400:1700, 0:1080], (W, H)), 14) * 0.25
    split = np.clip((_XX - 540) / 6 + 0.5, 0, 1)[..., None]
    img = left * (1 - split) + right * split
    t575 = wt[10] if len(wt) > 10 else d * 0.5             # 1. cümle 5 kelime; "575" 2. cümlenin 6. kelimesi
    t_asg = wt[7] if len(wt) > 7 else d * 0.35             # "asgari"
    t100 = wt[14] if len(wt) > 14 else d * 0.85            # "100" 3. cümlenin 3. kelimesi

    def post(im):
        O.label(im, "MALİYET FARKI", color=G.GOLD, alpha=seg(t, 0.1, 0.4))
        k0 = ease_out(seg(t, 0.1, 0.5))
        O.text(im, "NET ASGARİ ÜCRET", 540, 330, 40, "Montserrat.ttf", 900, ONE, alpha=k0, tracking=6)
        O.text(im, "(aylık, dolar)", 540, 385, 26, "Inter.ttf", 500, ONE * 0.7, alpha=k0)
        im[420:1180, 538:542] = im[420:1180, 538:542] * 0.3 + 0.7 * 0.5
        base_y, hmax = 1150, 470
        big = spring(seg(t, 0.15, 0.7), 1.2, 5) * (1 - seg(t, t_asg - 0.4, t_asg))
        if big > 0.01:
            O.text(im, "MALİYET", 540, 720, 110, "Montserrat.ttf", 900, ONE, alpha=min(1, big * 2), scale=max(0.5, big))
            O.text(im, "FARKI", 540, 850, 110, "Montserrat.ttf", 900, YELLOW, alpha=min(1, big * 2), scale=max(0.5, big),
                   glow=0.3)
        for side, name, val, t0_, tt, col, loc in ((0, "TÜRKİYE", 575, t_asg, t575, YELLOW, "28.075 TL"),
                                                   (1, "SURİYE", 100, t100 - 0.5, t100, WARM, "12.560 yeni SYP")):
            x = 270 + side * 540
            O.text(im, name, x, 470, 40, "Montserrat.ttf", 900, ONE, alpha=k0, tracking=8)
            u = ease_out(seg(t, t0_, tt + 0.3))
            h = int(hmax * val / 575 * u)
            if h > 2:
                O.rect_fill(im, x - 110, base_y - h, 220, h, col, 0.95, r=14)
            if u > 0:
                O.text(im, f"${int(val * u)}", x, base_y - h - 60, 84, "Montserrat.ttf", 900, col, alpha=min(1, u * 3),
                       glow=0.3)
                O.text(im, loc, x, base_y + 40, 26, "Inter.ttf", 600, ONE * 0.75, alpha=seg(u, 0.7, 1.0))
        source(im, "TR: 2026 net asgari ücret, kur ~48,9 · Suriye: Mart 2026 kararnamesi", seg(t, t100 + 0.5, t100 + 1.0),
               y=1240)
        return im
    return img, post


# ================================================================== 10) YAPTIRIM: kilit açılır
def yaptirim(p, t, d, wt, lt):
    t_k = wt[2] if len(wt) > 2 else d * 0.5               # "kısmı": kilit "kalktı" demeden hemen önce açılır
    k = int(np.clip((t - (t_k - 0.1)) * 30 / 1.0, 0, 7))
    rgb = loop_frame("kilit", k)
    img, _ = push(rgb, plate("kilit_0000")["depth"], ease_io(p), 1.0, 1.06, c=(540, 820), dx=hand(t, 2.5, 4)[0], dy=hand(t, 2.5, 4)[1])
    if t_k - 0.1 < t < t_k + 0.15:
        img = img + 0.06 * (1 - abs(t - t_k) / 0.2)
    dx, dy = O.shake(t, t_k, 10)
    img = O.camera(img, 1.0, dx=dx, dy=dy)

    def post(im):
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "YAPTIRIMLAR", color=G.GOLD, alpha=seg(t, 0.1, 0.4))
        kk = spring(seg(t, t_k - 0.05, t_k + 0.5), 1.4, 5)
        if kk > 0:
            chip(im, "BÜYÜK KISMI KALKTI", 540, 1080, GREEN, min(1, kk * 2), 40, anchor="mm")
            O.text(im, "ABD · AB · İNGİLTERE — 2025", 540, 1160, 26, "Inter.ttf", 700, ONE * 0.8,
                   alpha=seg(t, t_k + 0.2, t_k + 0.45), tracking=3)
        return im
    return img, post


# ================================================================== 11) TAŞINMA: hayır, henüz değil
def tasinma(p, t, d, wt, lt):
    cam = (35.6, 37.4, 150.0)
    t_h = (lt[1] if len(lt) > 1 else d * 0.55)             # "Hayır"
    prog = ease_io(seg(t, 0.2, t_h))
    stall = ease_out(seg(t, t_h, t_h + 0.5))
    img, _ = map_frame(cam, HI_BASE, lambda im, c, m: (city_dots(im, c, HM.HUBS),
                                                       draw_arrows(im, c, prog, stall=stall * 0.75)))

    def post(im):
        O.label(im, "FABRİKALAR TAŞINIYOR MU?", color=WARM, alpha=seg(t, 0.1, 0.4))
        k = spring(seg(t, t_h, t_h + 0.45), 1.3, 5)
        if k > 0:
            O.text(im, "HAYIR", 540, 560, 170, "Montserrat.ttf", 900, RED, alpha=min(1, k * 2), scale=max(0.5, k), glow=0.3)
            O.text(im, "henüz değil", 540, 690, 64, "InstrumentSerif-Italic.ttf", None, ONE, alpha=seg(t, t_h + 0.35, t_h + 0.7))
        return im
    return img, post


# ================================================================== 12) ALTYAPI: dolaşık kablolar
def altyapi(p, t, d, wt, lt):
    pl = plate("sehir_sokak")
    img, dep = push(pl["rgb"], pl["depth"], ease_io(p), 1.0, 1.07, k=0.25, c=(540, 700), dx=hand(t, 3, 5)[0], dy=hand(t, 3, 5)[1])
    fl = 1.0 if (int(t * 12) % 7) else 0.55                 # titreyen sokak lambası
    img = img * (0.85 + 0.15 * fl)

    def post(im):
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "SURİYE  ·  ALTYAPI", color=WARM, alpha=seg(t, 0.1, 0.4))
        return im
    return img, post


# ================================================================== 13) ELEKTRİK: şehrin ışıkları söner
_CELLS = None


def cells():
    global _CELLS
    if _CELLS is None:
        rng = np.random.default_rng(4)
        pts = rng.uniform(0, 1, (70, 2)) * [W, H * 0.8] + [0, H * 0.35]
        d = np.full((H, W), 1e9, np.float32)
        lab = np.zeros((H, W), np.int32)
        for i, (px, py) in enumerate(pts):
            dd = (_XX - px) ** 2 + ((_YY - py) * 1.6) ** 2
            m = dd < d
            d[m] = dd[m]
            lab[m] = i
        _CELLS = (lab, rng.uniform(0, 1, 70))
    return _CELLS


def elektrik(p, t, d, wt, lt):
    on = plate("sehir_gece_acik")
    off = plate("sehir_gece_kapali")
    t_y = wt[3] if len(wt) > 3 else d * 0.5                # "yarısından" (0:Talep 1:edilen 2:elektriğin 3:yarısından)
    lab, when = cells()
    prog = seg(t, t_y - 1.2, t_y + 0.4)
    gone = (when[lab] < prog * 0.62).astype(np.float32)     # sonunda bölgelerin ~%60'ı karanlık
    flick = ((when[lab] * 97 + t * 25) % 1 < 0.5) & (np.abs(when[lab] - prog * 0.62) < 0.03)
    gone = np.maximum(gone, flick.astype(np.float32) * 0.6)
    gone = G.blur(gone, 3)[..., None]
    rgb = on["rgb"] * (1 - gone) + off["rgb"] * 0.35 * gone              # sönen bölgeler iyice kararır
    img, _ = push(rgb, on["depth"], ease_io(p), 1.0, 1.05, c=(540, 900), dx=hand(t, 2, 6)[0], dy=hand(t, 2, 6)[1])

    def post(im):
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "SURİYE  ·  ELEKTRİK", color=WARM, alpha=seg(t, 0.1, 0.4))
        k = ease_out(seg(t, 0.2, 0.6))
        O.glass(im, 120, 300, 840, 250, r=40, frost=16, tint=0.05, alpha=k)
        O.text(im, "TALEP", 160, 370, 28, "Inter.ttf", 700, ONE * 0.85, "lm", alpha=k, tracking=4)
        O.rect_fill(im, 400, 352, 510, 36, ONE * 0.6, k, r=18)
        O.text(im, "KARŞILANAN", 160, 470, 28, "Inter.ttf", 700, ONE * 0.85, "lm", alpha=k, tracking=4)
        O.rect_fill(im, 400, 452, 510, 36, ONE * 0.12, k, r=18)
        fill = 0.48 * ease_out(seg(t, t_y - 0.8, t_y + 0.3))
        if fill > 0.02:
            O.rect_fill(im, 400, 452, int(510 * fill), 36, WARM, k, r=18)
        return im
    return img, post


# ================================================================== 14) BANKA: bankamatik uyarı ekranı
def banka(p, t, d, wt, lt):
    pl = plate("atm_0000")
    img, _ = push(pl["rgb"], pl["depth"], ease_io(p), 1.0, 1.06, c=(560, 760), dx=hand(t, 2.5, 7)[0], dy=hand(t, 2.5, 7)[1])
    if int(t * 10) % 9 == 0:                                # ekran arada bir titrer
        img = img * 0.97

    def post(im):
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "SURİYE  ·  BANKACILIK", color=WARM, alpha=seg(t, 0.1, 0.4))
        for i, txt in enumerate(("FATF gri listesinde", "Nakit çekim sınırı var", "Muhabir banka az")):
            k = ease_out(seg(t, 0.3 + i * 0.25, 0.6 + i * 0.25))
            chip(im, txt, 80 - 40 * (1 - k), 330 + i * 80, ONE * 0.92, k, 28)
        return im
    return img, post


# ================================================================== 15) VERGİ: gümrük kapısı, %0 mı %12 mi?
def vergi(p, t, d, wt, lt):
    pl = plate("liman_bariyer")
    img, dep = push(pl["rgb"], pl["depth"], ease_io(p), 1.0, 1.07, k=0.35, c=(540, 980), dx=hand(t, 3, 8)[0], dy=hand(t, 3, 8)[1])
    img = haze(img, dep, (0.22, 0.14, 0.08), 0.004)
    t_v = wt[3] if len(wt) > 3 else d * 0.3               # "vergiyle"

    def post(im):
        tag(im, "TEMSİLİ GÖRSEL")
        O.label(im, "AVRUPA'YA GİRİŞ", color=WARM, alpha=seg(t, 0.1, 0.4))
        k = ease_out(seg(t, t_v - 0.3, t_v + 0.2))
        if k <= 0:
            return im
        O.glass(im, 170, 330, 740, 420, r=44, frost=18, tint=0.05, alpha=k)
        O.text(im, "AB GÜMRÜK VERGİSİ", 540, 400, 34, "Inter.ttf", 800, ONE * 0.9, alpha=k, tracking=5)
        phase = (t - t_v) * 2.2
        shown = "%0" if int(phase) % 2 == 0 else "%12"
        frac = phase % 1
        sy = 1 - 0.7 * math.exp(-frac * 10) * abs(math.cos(frac * 30)) if phase > 0 else 1
        O.text(im, shown, 460, 560, 150, "Montserrat.ttf", 900, YELLOW, alpha=k, scale=max(0.3, sy))
        O.text(im, "?", 760, 560, 170, "Montserrat.ttf", 900, ONE, alpha=k * (0.6 + 0.4 * abs(math.sin(t * 5))))
        O.text(im, "Suriye menşeli sayılırsa %0, sayılmazsa ~%12", 540, 690, 26, "Inter.ttf", 600, ONE * 0.8, alpha=k)
        source(im, "AB–Suriye anlaşması Mayıs 2026'da yeniden yürürlüğe girdi; menşe kuralı belirleyici",
               seg(t, t_v + 0.8, t_v + 1.2), y=790)
        return im
    return img, post


# ================================================================== 16-17) BAŞLANGIÇ / FİNAL: bir fabrika var, göç yok; ikinci, üçüncü?
GHOSTS = [(36.55, 37.72, "2"), (36.43, 37.22, "3")]      # sınır boyunca muhtemel yerler (temsili)


def baslangic(p, t, d, wt, lt):
    cam = HM.lerp_cam((35.6, 37.4, 150.0), CAM_BORDER, ease_io(seg(p, 0.0, 0.6)))
    t_g = wt[6] if len(wt) > 6 else d * 0.7               # "göç"

    def extra(im, c, masks):
        bl = HM.border_line(masks, "TUR", "SYR").astype(np.float32)
        im += G.blur(bl, 2)[..., None] * WARM * 0.5
        x, y = HM.city_xy("El-Rai", c)
        O.circle(im, x, y, 12, YELLOW, fill=True)
    img, _ = map_frame(cam, HI_BASE, extra)

    def post(im):
        O.label(im, "ŞİMDİLİK", color=WARM, alpha=seg(t, 0.1, 0.4))
        x, y = screen_of("El-Rai", cam)
        k1 = ease_out(seg(t, wt[3] - 0.2 if len(wt) > 3 else 0.5, (wt[3] if len(wt) > 3 else 0.5) + 0.2))
        chip(im, "BAŞLANGIÇ VAR", 540, 520, GREEN, k1, 44, anchor="mm", icon="check")
        k2 = ease_out(seg(t, t_g - 0.2, t_g + 0.2))
        chip(im, "GÖÇ YOK", 540, 640, RED, k2, 44, anchor="mm", dark=False, icon="cross")
        O.text(im, "1 FABRİKA", x + 26, y - 20, 30, "Montserrat.ttf", 900, YELLOW, "lm", alpha=seg(t, 0.2, 0.6))
        return im
    return img, post


def final(p, t, d, wt, lt):
    cam = CAM_BORDER
    t2 = wt[2] if len(wt) > 2 else d * 0.2                # "ikinci"
    t3 = wt[4] if len(wt) > 4 else d * 0.3                # "üçüncü"
    t_h = wt[-1] if wt else d * 0.6                        # "hareketlenir"
    end_t = t_h + 0.9

    def extra(im, c, masks):
        e_ = seg(t, end_t, end_t + 0.5)
        bl = HM.border_line(masks, "TUR", "SYR").astype(np.float32)
        im += G.blur(bl, 2)[..., None] * WARM * 0.5
        x, y = HM.city_xy("El-Rai", c)
        O.circle(im, x, y, 12, YELLOW, fill=True)
        for (lat, lon, n), tt in zip(GHOSTS, (t2, t3)):
            gx, gy = HM.project((lon, lat), c)
            k = seg(t, tt - 0.1, tt + 0.3)
            pulse = (t * 1.5) % 1
            O.circle(im, gx, gy, 12, ONE * 0.8, 3, k * (1 - e_))
            O.circle(im, gx, gy, 12 + 30 * pulse, ONE * 0.6, 2, k * (1 - pulse) * (1 - e_))
        mv = seg(t, t_h - 0.2, t_h + 0.8)
        if mv > 0:
            draw_arrows(im, c, mv, color=WARM, alpha=0.8 * (1 - seg(t, end_t, end_t + 0.4)),
                        hubs=["Gaziantep", "Kahramanmaraş", "Şanlıurfa", "Kilis"])
    img, _ = map_frame(cam, HI_BASE, extra)
    e = seg(t, end_t, end_t + 0.5)
    if e > 0:
        img = img * (1 - 0.85 * e)

    def post(im):
        for (lat, lon, n), tt in zip(GHOSTS, (t2, t3)):
            gx, gy = warp_pt(TILT, HM.project((lon, lat), cam))
            O.text(im, f"{n}?", gx + 24, gy - 18, 44, "Montserrat.ttf", 900, ONE, "lm",
                   alpha=seg(t, tt - 0.1, tt + 0.3) * (1 - e))
        x, y = screen_of("El-Rai", cam)
        O.text(im, "1", x + 24, y - 18, 44, "Montserrat.ttf", 900, YELLOW, "lm", alpha=1 - e)
        if e > 0:
            O.text(im, "Takipte kal.", 540, 760, 92, "InstrumentSerif-Italic.ttf", None, ONE, alpha=e)
            O.text(im, "PARA NE DİYOR?", 540, 890, 64, "Montserrat.ttf", 900, YELLOW, alpha=seg(t, end_t + 0.2, end_t + 0.6),
                   tracking=10, glow=0.25)
            ln = seg(t, end_t + 0.3, end_t + 0.8)
            if ln > 0:
                im[948:952, int(540 - 210 * ln):int(540 + 210 * ln)] = YELLOW * 0.85
        return im
    return img, post


SAHNELER = dict(fabrika=fabrika, soylenti=soylenti, ilk=ilk, neden=neden, iscilik=iscilik, faiz=faiz,
                ihracat=ihracat, suriye=suriye, ucret=ucret, yaptirim=yaptirim, tasinma=tasinma, altyapi=altyapi,
                elektrik=elektrik, banka=banka, vergi=vergi, baslangic=baslangic, final=final)
BLOOM = dict(yaptirim=0.12, banka=0.2, elektrik=0.3)
EXPOSURE = dict(fabrika=1.0, soylenti=3.2, ilk=3.2, neden=1.0, iscilik=1.0, faiz=1.0, ihracat=0.9, suriye=1.0,
                ucret=1.0, yaptirim=1.05, tasinma=3.2, altyapi=4.0, elektrik=1.3, banka=2.2, vergi=0.9, baslangic=3.2,
                final=3.2)
