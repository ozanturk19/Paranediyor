"""Fiziksel dünya sahneleri: kanca, matbaa, pamuk, filigran, baskı, seri, darphane.

Her sahne: f(p, t, d, wt) -> (görüntü, post)
  p: sahne ilerlemesi 0-1, t: sahne içi saniye, d: sahne süresi,
  wt: cümledeki kelimelerin sahne içi başlama zamanları,
  post: renk işleminden SONRA çizilecek keskin katman (yazı, etiket) ya da None.
"""
import math
import cv2
import numpy as np
import gfx as G
import banknot as B
import ortak as O
from ortak import W, H, ONE, seg, ease_out, ease_in, ease_io, back, spring, lerp

rng0 = np.random.default_rng(11)

# ================================================================== ortak varlıklar
NOTE = B.banknote()
NOTE_LIT = G.relief(NOTE["color"], NOTE["height"], light=(-0.6, -0.7, 0.85), strength=4, spec=0.25) * 0.86
PORTRAIT = cv2.resize(np.ascontiguousarray(np.rot90(NOTE_LIT)), (500, 1053), interpolation=cv2.INTER_AREA)
PAPER_DARK = G.PAPER * 0.8


def _strip(rows=8, gap=26):
    """Baskı tabakası: 2 sütun x n satır yatay banknot (gerçek tabakalar gibi)."""
    nt = cv2.resize(NOTE_LIT, (520, 247), interpolation=cv2.INTER_AREA)
    nh, nw = nt.shape[:2]
    s = np.ones((rows * (nh + gap), 2 * nw + 3 * gap, 3), np.float32) * PAPER_DARK
    for r in range(rows):
        for c in range(2):
            y, x = r * (nh + gap) + gap // 2, gap + c * (nw + gap)
            s[y:y + nh, x:x + nw] = nt
    return s


STRIP = _strip()


# ================================================================== 1) KANCA
def _aurora():
    img = G.canvas(G.hexc("#030406"))
    xx, yy = G.grid(W, H)
    for c, (px, py, s) in zip(["#0E5561", "#3B1F6E", "#8A5A06", "#0B2150"],
                              [(250, 420, 420), (850, 700, 460), (700, 1500, 380), (200, 1250, 420)]):
        img += np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / (2 * s ** 2))[..., None] * G.hexc(c) * 0.62
    return img


CARD = (90, 560, 900, 480)
KANCA_BG = O.glass(_aurora(), *CARD, r=60)
CARD_MASK = np.zeros((H, W), np.float32)
CARD_MASK[CARD[1]:CARD[1] + CARD[3], CARD[0]:CARD[0] + CARD[2]] = O.rounded(CARD[2], CARD[3], 60)
BOKEH = []
for _ in range(70):
    ch = O.RAMP[rng0.integers(2, len(O.RAMP))]
    sc = rng0.uniform(0.7, 2.6)
    m = cv2.resize(O.glyph(ch, 26), None, fx=sc, fy=sc)
    BOKEH.append(dict(m=G.blur(np.pad(m, 12), rng0.uniform(0.5, 4) * sc), x=rng0.uniform(0, W),
                      y=rng0.uniform(0, H), v=rng0.uniform(12, 45), a=rng0.uniform(0.08, 0.3)))
AMOUNT = "₺48.250,00"
NUM_POS = (540, 820)
_num_mask = G.text_mask(AMOUNT, "Montserrat.ttf", 136, 900)
_nm_full = np.zeros((H, W), np.float32)
_nh, _nw = _num_mask.shape
_nm_full[NUM_POS[1] - _nh // 2:NUM_POS[1] - _nh // 2 + _nh, NUM_POS[0] - _nw // 2:NUM_POS[0] - _nw // 2 + _nw] = _num_mask
NUM_PTS = O.mask_points(_nm_full, 1400, seed=3)
NUM_SEEDS = rng0.uniform(0, 1, (len(NUM_PTS), 4)).astype(np.float32)


def kanca(p, t, d, wt):
    img = KANCA_BG.copy()
    lay = np.zeros_like(img)
    for b in BOKEH:
        y = (b["y"] - b["v"] * t) % (H + 200) - 100
        G.add(lay, (b["m"][..., None] * G.CYAN * b["a"]).astype(np.float32), int(b["x"]), int(y))
    img += lay * (1 - CARD_MASK)[..., None]
    t_dis = (wt[4] if len(wt) > 4 else d * 0.6) - 0.05          # "hiç" kelimesi
    q = seg(t, t_dis, t_dis + 1.1)
    # rakamlar önce karışıp oturur (slot makinesi), sonra veriye dağılır
    shown = []
    for i, ch in enumerate(AMOUNT):
        settle = 0.12 + 0.07 * i
        if ch.isdigit() and t < settle:
            ch = str(np.random.default_rng(int(t * 24) * 31 + i).integers(0, 10))
        shown.append(ch)
    O.text(img, "HESAP BAKİYESİ", 150, 640, 30, "Inter.ttf", 600, ONE * 0.75, "lm", tracking=5, alpha=1 - q)
    O.text(img, "".join(shown), NUM_POS[0], NUM_POS[1], 136, wght=900, alpha=(1 - q) ** 1.5, glow=0.25)
    O.text(img, "Vadesiz hesap", 150, 960, 30, "Inter.ttf", 500, ONE * 0.55, "lm", alpha=1 - q)
    if q > 0:
        glow = np.zeros_like(img)
        s = NUM_SEEDS
        dx = np.sin(s[:, 0] * 20 + t * 3) * 60 * q + (s[:, 1] - 0.5) * 140 * q
        dy = -(120 + 520 * s[:, 2]) * q ** 1.25
        a = np.clip(1 - q * (0.6 + 0.8 * s[:, 3]), 0, 1)
        for (x, y), ddx, ddy, aa, ss in zip(NUM_PTS, dx, dy, a, s):
            if aa > 0.03 and ss[3] < 0.5:
                col = G.CYAN * (1 - ss[1]) + G.YELLOW * ss[1]
                O.digit_sprite(img, glow, O.RAMP[int(ss[0] * 11.99)], x + ddx, y + ddy, col, aa, 14)
        img = O.add_glow(img, glow)
    img = O.camera(img, 1 + 0.05 * ease_io(p))
    return img, None


# ================================================================== 2) MATBAA
QUAD_SHEET = np.float32([[300, 480], [780, 480], [1080, 1330], [0, 1330]])
SHEET_MASK = np.zeros((H, W), np.uint8)
cv2.fillPoly(SHEET_MASK, [QUAD_SHEET.astype(np.int32)], 255, cv2.LINE_AA)
SHEET_MASK = SHEET_MASK.astype(np.float32) / 255
DUST = rng0.uniform(0, 1, (160, 4)).astype(np.float32)


def _roller(img, t, y0, h, x0, x1, speed, tone=0.78):
    """Dönen metal merdane: silindir gölgesi + dönen gravür halkaları."""
    Y = np.arange(h, dtype=np.float32)
    phi = (Y / h) * math.pi
    shade = 0.18 + 0.82 * np.sin(phi) ** 1.4
    spec = np.exp(-((Y - h * 0.32) / (h * 0.09)) ** 2) * 0.55
    col = (shade[:, None] * np.array([tone, tone * 0.96, tone * 0.88]) + spec[:, None])[:, None, :]
    band = np.repeat(col, x1 - x0, axis=1).astype(np.float32)
    for k in range(14):
        ph = (k / 14 * 2 * math.pi + speed * t) % (2 * math.pi)
        if ph < math.pi:
            yy = int(h / 2 - math.cos(ph) * h / 2)
            if 0 <= yy < h - 2:
                band[yy:yy + 2] *= 1 - 0.45 * math.sin(ph)
    cap = np.linspace(0, 1, x1 - x0, dtype=np.float32)
    band *= (0.55 + 0.45 * np.clip(np.sin(cap * math.pi), 0, 1) ** 0.3)[None, :, None]
    img[y0:y0 + h, x0:x1] = band
    return img


def matbaa(p, t, d, wt):
    img = O.WARM.copy()
    off = 2600 * (1 - math.exp(-t / 1.1)) + 150 * t
    speed = 2600 / 1.1 * math.exp(-t / 1.1) + 150
    sh = STRIP.shape[0]
    rows = (np.arange(1200) + int(off)) % sh
    win = STRIP[rows]
    k = int(np.clip(speed / 70, 1, 36))
    if k > 1:
        win = cv2.blur(win, (1, k))
    O.place(img, win, QUAD_SHEET, shadow=0.4, sdx=0, sdy=30)
    band_y = 470 + ((t * 0.55) % 1) * 870
    yy = np.arange(H, dtype=np.float32)[:, None]
    sheen = np.exp(-((yy - band_y) / 60) ** 2) * SHEET_MASK * 0.22
    img += sheen[..., None] * G.hexc("#FFF1D0")
    O.rect_fill(img, 250, 330, 580, 12, ONE * 0.05)
    _roller(img, t, 280, 70, 300, 780, speed / 60, 0.5)
    _roller(img, t, 360, 130, 250, 830, speed / 45)
    dm = np.zeros((H, W), np.uint8)                                # ışıkta uçuşan toz (tek maske)
    for x, y, v, s_ in DUST:
        cv2.circle(dm, (int(x * W * 4), int(((y * H - t * 18 * (0.5 + v)) % H) * 4)), int((1.2 + 2 * s_) * 4),
                   int(40 + 60 * s_), -1, cv2.LINE_AA, shift=2)
    img += G.blur(dm.astype(np.float32) / 255, 0.8)[..., None] * G.hexc("#FFE7B0") * 0.6
    img = O.camera(img, 1.0 + 0.04 * ease_io(p), 540, 800, rot=-0.6 * (1 - p))

    def post(im):
        O.label(im, "01  ·  MATBAA  —  ANKARA", alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 3) PAMUK LİFİ
N_FIB = 1800
_fs = rng0.normal(0, 1, (N_FIB, 3))
_fs /= np.linalg.norm(_fs, axis=1, keepdims=True)
_rad = rng0.uniform(0.35, 1.0, N_FIB) ** 0.5
FIB = []
for i in range(N_FIB):
    L = rng0.uniform(35, 95)
    ang = np.cumsum(rng0.normal(0, 0.5, 10))
    pts = np.cumsum(np.stack([np.cos(ang), np.sin(ang)], 1) * L / 10, 0)
    pts -= pts.mean(0)
    cloud = np.array([540 + _fs[i, 0] * 300 * _rad[i], 800 + _fs[i, 1] * 250 * _rad[i]])
    FIB.append(dict(shape=pts.astype(np.float32), s=cloud, z=1.0 + 0.55 * _fs[i, 2] * _rad[i],
                    f=np.array([rng0.uniform(185, 895), rng0.uniform(575, 1045)]),
                    a0=rng0.uniform(0, 6.28), a1=rng0.uniform(-0.25, 0.25), ph=rng0.uniform(0, 6.28),
                    b=rng0.uniform(0.35, 1.0)))
PAPER_RECT = (170, 560, 740, 500)
_pap = cv2.resize(NOTE["base"][100:600, 200:940], (PAPER_RECT[2], PAPER_RECT[3])) * 0.82


def pamuk(p, t, d, wt):
    """Yumuşak bir pamuk bulutu yavaşça döner, sonra lifler yassılaşıp kâğıda dönüşür."""
    img = O.WARM.copy() * 0.7
    q = ease_io(seg(p, 0.2, 0.85))
    paper_a = seg(p, 0.62, 0.92)
    layers = [np.zeros((H, W), np.uint8) for _ in range(3)]
    spin = t * 0.35
    for f in FIB:
        sx, sy = f["s"] - (540, 800)
        cs, sn = math.cos(spin * (1 - q)), math.sin(spin * (1 - q))
        cloud = np.array([540 + sx * cs - (f["z"] - 1) * 200 * sn, 800 + sy])
        breathe = 1 + 0.04 * math.sin(t * 1.3 + f["ph"])
        pos = lerp(cloud * breathe + (1 - breathe) * np.array([540, 800]), f["f"], q)
        ang = lerp(f["a0"] + 0.3 * math.sin(t * 0.7 + f["ph"]), f["a1"], q)
        sc = lerp(1.0 + 0.35 * (f["z"] - 1), 1.0, q)
        c, s_ = math.cos(ang), math.sin(ang)
        pts = f["shape"] @ np.array([[c, s_], [-s_, c]]) * sc + pos
        li = 1 if q > 0.65 else (0 if f["z"] > 1.2 else (2 if f["z"] < 0.8 else 1))
        cv2.polylines(layers[li], [np.round(pts * 4).astype(np.int32)], False, int(90 + 140 * f["b"]), 1,
                      cv2.LINE_AA, shift=2)
    fib = np.zeros((H, W), np.float32)
    for li, (bl, br) in enumerate([(3.0, 1.0), (0.4, 0.9), (1.6, 0.4)]):
        fib += G.blur(layers[li].astype(np.float32) / 255, bl * (1 - q) + 0.3) * br
    fib = fib * (1 - 0.8 * paper_a)
    haze = G.blur(fib, 25) * 0.6
    x, y, w, h = PAPER_RECT
    if paper_a > 0:
        m = O.rounded(w, h, 6) * paper_a
        shadow = np.zeros((H, W), np.float32)
        shadow[y:y + h, x:x + w] = m
        img *= (1 - 0.5 * G.blur(np.roll(shadow, 30, 0), 24))[..., None]
        sweep = np.exp(-(((np.arange(w)[None, :] + np.arange(h)[:, None] * 0.5) - (p * 1.6 - 0.4) * w) / 120) ** 2) * 0.2
        G.over(img, _pap + sweep[..., None], m, x, y)
    img += (fib + haze)[..., None] * G.hexc("#FFF4DE") * 0.75
    img = O.camera(img, 1.02 + 0.05 * ease_io(p))

    def post(im):
        O.label(im, "02  ·  KÂĞIT", alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 4) FİLİGRAN ve GÜVENLİK ŞERİDİ
_X, _Y = G.grid(B.BW, B.BH)
_low = G.blur(rng0.normal(0, 1, (B.BH, B.BW)).astype(np.float32), 30) * 5
T_BASE = 0.42 * (1 + 0.14 * _low) * (1 - 0.4 * NOTE["fibers"])
_bub, _gly = B.emblem_mask((420, 330))
WM = np.zeros((B.BH, B.BW), np.float32)
WM[385 - 165:385 + 165, 360 - 210:360 + 210] = G.blur(_bub * (1 - 0.75 * _gly), 4)
_wm_shade = G.blur(WM, 10)
THREAD = ((_X > 700) & (_X < 728)).astype(np.float32)
INK = np.clip(sum(l[2] for l in NOTE["layers"]), 0, 1)
QUAD_WM = O.project_quad(540, 790, 980, rx=10, ry=-8, rz=-3)


def filigran(p, t, d, wt):
    """Kâğıdın arkasından geçen ışık: filigran belirir, güvenlik şeridi yukarıdan aşağı gömülür."""
    img = G.canvas(G.hexc("#020202"))
    lx = lerp(-150, 1100, ease_io(seg(p, 0.0, 0.95)))
    ly = 380 + 60 * math.sin(t * 0.9)
    L = 0.06 + 2.2 * np.exp(-((_X - lx) ** 2 + (_Y - ly) ** 2) / (2 * 330 ** 2))
    r_wm = ease_out(seg(p, 0.06, 0.4))
    r_th = ease_io(seg(p, 0.42, 0.78))
    trans = T_BASE * (1 + 1.7 * WM * r_wm - 0.35 * (_wm_shade - WM).clip(0, 1) * r_wm)
    th_vis = THREAD * G.smoothstep(0, 30, r_th * (B.BH + 60) - _Y)
    trans = trans * (1 - 0.9 * th_vis) * (1 - 0.1 * INK)
    col = G.PAPER * 0.08 + (L * trans)[..., None] * G.hexc("#FFD9A0")
    glint = th_vis * (0.5 + 0.5 * np.sin(_Y / 9 + t * 8)) * 0.35
    col += glint[..., None] * G.hexc("#E8F4FF")
    halo = np.zeros((H, W), np.float32)
    cv2.fillPoly(halo, [QUAD_WM.astype(np.int32)], 1.0)
    img += G.blur(halo, 50)[..., None] * G.hexc("#FF9E40") * 0.25
    O.place(img, col, QUAD_WM, shadow=0)
    img = O.camera(img, 1.0 + 0.06 * ease_io(p), 470, 780)

    def post(im):
        O.label(im, "03  ·  GÜVENLİK", alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 5) BASKI (renkli zemin + kabartma)
_ang = (np.arctan2(_Y - 380, _X - 330) + math.pi) / (2 * math.pi)
QUAD_B = O.project_quad(540, 760, 960, rx=22, ry=-6, rz=-5)


def _compose(p):
    rev = {
        "mesh": np.float32(seg(p, 0.0, 0.12)),
        "rosette": G.smoothstep(0, 0.02, seg(p, 0.03, 0.34) - _ang),
        "waves": G.smoothstep(0, 60, seg(p, 0.08, 0.38) * B.BW * 1.05 - _X),
        "emblem": G.smoothstep(0, 40, seg(p, 0.18, 0.42) * B.BH * 1.1 - (_Y - 120)),
        "num100": np.float32(seg(p, 0.3, 0.44)),
        "small100": np.float32(seg(p, 0.34, 0.46)),
        "texts": np.float32(seg(p, 0.36, 0.48)),
        "serial": np.float32(seg(p, 0.4, 0.5)),
    }
    color, height = NOTE["base"].copy(), 0.06 * NOTE["fibers"]
    for name, c, a, hw in NOTE["layers"]:
        ae = a * rev[name]
        color = color * (1 - ae[..., None]) + np.asarray(c, np.float32) * ae[..., None]
        height = height + hw * ae
    tcol, ta = NOTE["thread"]
    color = color * (1 - ta[..., None]) + tcol * ta[..., None]
    fronts = []
    if 0.03 < p < 0.36:
        fronts.append(np.exp(-((_ang - seg(p, 0.03, 0.34)) / 0.006) ** 2) * (np.hypot(_X - 330, _Y - 380) < 260))
    if 0.08 < p < 0.4:
        fronts.append(np.exp(-((_X - seg(p, 0.08, 0.38) * B.BW * 1.05) / 14) ** 2) * ((_Y < 130) | (_Y > B.BH - 130)))
    glow = sum(fronts) if fronts else None
    return color, G.blur(height + 0.5 * ta, 0.8), glow


def baski(p, t, d, wt):
    img = O.WARM.copy()
    color, height, front = _compose(p)
    pb = seg(p, 0.5, 1.0)
    th = lerp(-2.6, -0.5, ease_io(pb))
    light = (math.cos(th), math.sin(th), 0.55) if pb > 0 else (-0.6, -0.7, 0.85)
    lit = G.relief(color, height, light=light, strength=4 + 5 * pb, spec=0.25 + 0.3 * pb) * 0.86
    if front is not None:
        lit += front[..., None].astype(np.float32) * G.hexc("#FFE9A8") * 1.4
    O.place(img, lit, QUAD_B)
    img = O.camera(img, 1.0 + 0.1 * ease_io(pb), 700, 700)
    if pb > 0.15:
        img = _loupe(img, color, height, light, ease_out(seg(pb, 0.15, 0.55)), t)

    def post(im):
        O.label(im, "04  ·  BASKI", alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


def _loupe(img, color, height, light, k, t):
    bub, glyph, ex, ey = NOTE["emblem"]
    x0, y0 = ex - 60, ey - 60
    crop_c = color[y0:y0 + 440, x0:x0 + 520]
    crop_h = height[y0:y0 + 440, x0:x0 + 520]
    macro = G.relief(crop_c, crop_h, light=(light[0], light[1], 0.5), strength=12, spec=0.6, shininess=26) * 0.85
    Cx, Cy, Rl, zoom = int(lerp(1250, 720, k)), 1080, 230, 1.15
    lx, ly = 255, 215
    X, Y = G.grid(2 * Rl, 2 * Rl)
    qx, qy = X - Rl, Y - Rl
    r = np.hypot(qx, qy) / Rl
    s = (0.72 + 0.28 * r ** 2) / zoom
    lens = cv2.remap(macro, (lx + qx * s).astype(np.float32), (ly + qy * s).astype(np.float32), cv2.INTER_CUBIC,
                     borderMode=cv2.BORDER_REFLECT)
    disk = G.smoothstep(1.0, 0.985, r)
    ring = np.exp(-((r - 0.995) / 0.018) ** 2)
    ang = np.arctan2(qy, qx)
    rim = ring[..., None] * (0.55 + 0.45 * np.cos(ang + 2.4))[..., None] * G.hexc("#FFF6E0")
    full = np.zeros((H, W), np.float32)
    ys, xs = slice(max(0, Cy - Rl), min(H, Cy + Rl)), slice(max(0, Cx - Rl), min(W, Cx + Rl))
    sub = disk[ys.start - (Cy - Rl):ys.stop - (Cy - Rl), xs.start - (Cx - Rl):xs.stop - (Cx - Rl)]
    full[ys, xs] = sub
    img *= (1 - 0.6 * G.blur(np.roll(np.roll(full, 30, 0), 18, 1), 22))[..., None]
    G.over(img, lens, disk, Cx - Rl, Cy - Rl)
    G.add(img, (rim * 0.9).astype(np.float32), Cx - Rl, Cy - Rl)
    hi = np.exp(-(((qx + 90) / 120) ** 2 + ((qy + 140) / 45) ** 2)) * disk * 0.2
    G.add(img, (hi[..., None] * ONE).astype(np.float32), Cx - Rl, Cy - Rl)
    return img


# ================================================================== 6) SERİ NO, KESİM, PAKET
SER_CROP = NOTE_LIT[610:730, 660:1100]          # alttaki seri numarası bölgesi
SHEET3 = np.ones((1053 + 40, 3 * 500 + 80, 3), np.float32) * PAPER_DARK
for _i in range(3):
    SHEET3[20:1073, 20 + _i * 520:520 + _i * 520] = PORTRAIT
SMALL_NOTE = cv2.resize(NOTE_LIT, (700, 333), interpolation=cv2.INTER_AREA)


def _rolling(img, x, y, px, digits, settle, t, color):
    """Slot makinesi gibi dönen rakamlar; her hane kendi anında oturur."""
    cw = px * 0.62
    for i, (dg, st) in enumerate(zip(digits, settle)):
        cx = x + i * cw
        if dg == " ":
            continue
        if not dg.isdigit() or t >= st:
            O.text(img, dg, cx, y, px, G.MONO, None, color, glow=0.2 if (dg.isdigit() and t - st < 0.15) else 0)
            continue
        v = (t * 22 + i * 3.3) % 10
        a, frac = int(v), v - int(v)
        dg_now = a if frac < 0.5 else (a + 1) % 10
        off = (frac if frac < 0.5 else frac - 1) * px * 0.45
        for k, al in ((-0.18, 0.3), (0.0, 0.85), (0.18, 0.3)):
            O.text(img, str(dg_now), cx, y - off + k * px, px, G.MONO, None, color * 0.9, alpha=al)
    return img


def seri(p, t, d, wt):
    t_kes = (wt[3] if len(wt) > 3 else d * 0.5) - 0.05
    t_pak = (wt[4] if len(wt) > 4 else d * 0.75) - 0.05
    img = O.WARM.copy()
    post = None
    if t < t_kes:                                                 # 1) seri numarası
        crop = cv2.resize(SER_CROP, (1000, 272), interpolation=cv2.INTER_CUBIC)
        crop[40:230, 80:900] = G.PAPER * 0.84                     # basılı numarayı kapat, canlı yaz
        quad = np.float32([[40, 620], [1040, 610], [1040, 900], [40, 900]])
        O.place(img, crop, quad, shadow=0.5)
        settle = [0, 0, 0, 0] + [t_kes * (0.35 + 0.1 * i) for i in range(6)]
        digits = "PND 004721"
        _rolling(img, 170, 765, 120, digits, settle, t, G.RED)
        last = max(settle)
        img = O.flash(img, t, last, 0.14, 0.35, G.hexc("#FFE2B0"))
        dx, dy = O.shake(t, last, 10)
        img = O.camera(img, 1.04, dx=dx, dy=dy)
    elif t < t_pak:                                                # 2) kesim (lazer)
        tt = t - t_kes
        q = ease_io(seg(tt, 0.0, (t_pak - t_kes) * 0.7))
        sep = ease_out(seg(tt, (t_pak - t_kes) * 0.65, t_pak - t_kes)) * 36
        sh_h, sh_w = SHEET3.shape[:2]
        scale = 960 / sh_w
        y_top, y_bot = 380, 380 + sh_h * scale
        for i in range(3):
            piece = SHEET3[:, i * 520:i * 520 + 540]
            x0 = 60 + i * 520 * scale + (i - 1) * sep
            quad = np.float32([[x0, y_top], [x0 + 540 * scale, y_top], [x0 + 540 * scale, y_bot], [x0, y_bot]])
            O.place(img, piece, quad, shadow=0.45)
        glow = np.zeros_like(img)
        yl = lerp(y_top - 20, y_bot + 20, q)
        for gx in (60 + 520 * scale, 60 + 1040 * scale):
            if 0 < q < 1:
                O.poly(glow, [[gx, y_top - 20], [gx, yl]], G.hexc("#FFE8A0"), 3, 1.0)
                for s_ in range(6):
                    rr = np.random.default_rng(int(t * 60) + s_ + int(gx))
                    ex, ey = gx + rr.normal(0, 18), yl + rr.normal(-10, 14)
                    O.poly(glow, [[gx, yl], [ex, ey]], G.hexc("#FFD27A"), 2, 0.8)
        img = O.add_glow(img, glow, (0.9, 1.2, 0.8))
    else:                                                          # 3) paket
        tt = t - t_pak
        n = 8
        band = ease_out(seg(tt, 0.5, 0.78))
        for i in range(n):
            ti = seg(tt, i * 0.045, i * 0.045 + 0.24)
            if ti <= 0:
                continue
            yb = lerp(-400, 800 - i * 10, spring(ti, 1.2, 7))
            rz = (i % 3 - 1) * 1.5 * (1 - ti) + (i % 2) * 0.6
            tex = SMALL_NOTE
            if i == n - 1 and band > 0:
                tex = SMALL_NOTE.copy()
                bh = int(333 * band)
                tex[:bh, 290:410] = G.YELLOW * 0.95
                if band > 0.9:
                    m = G.text_mask("PND", G.MONO, 34)
                    G.over(tex, G.hexc("#161616"), m, 350 - m.shape[1] // 2, 150)
            quad = O.project_quad(540, yb, 820, rx=30, rz=rz)
            O.place(img, tex, quad, shadow=0.35)
        img = O.camera(img, 1.0 + 0.04 * ease_io(seg(tt, 0, 1.5)))
    if post is None:
        def post(im):
            O.label(im, "05  ·  SERİ NO" if t < t_kes else ("05  ·  KESİM" if t < t_pak else "05  ·  PAKET"),
                    alpha=seg(t, 0.1, 0.5))
            return im
    return img, post


# ================================================================== 7) DARPHANE
def _coin_tex(R=220):
    s = 2 * R
    X, Y = G.grid(s, s)
    r = np.hypot(X - R, Y - R) / R
    alpha = G.smoothstep(1.0, 0.985, r)
    gold, silver = G.hexc("#C9A13B"), G.hexc("#C9CDD3")
    ring = (r > 0.7).astype(np.float32)
    color = silver * (1 - ring[..., None]) + gold * ring[..., None]
    height = G.smoothstep(0.93, 0.96, r) * 1.0 + np.exp(-((r - 0.7) / 0.012) ** 2) * 0.6
    reed = (np.sin(np.arctan2(Y - R, X - R) * 90) > 0) * (r > 0.965) * 0.3
    bub, glyph = B.emblem_mask((300, 240))
    em = np.zeros((s, s), np.float32)
    em[R - 120:R + 120, R - 150:R + 150] = G.blur(bub * (1 - glyph), 1.5)
    height = height + reed + em * 0.8
    return color.astype(np.float32), G.blur(height.astype(np.float32), 1.2), alpha


COIN_C, COIN_H, COIN_A = _coin_tex()
COIN_SMALL = [cv2.resize(G.relief(COIN_C, COIN_H, (-0.6, -0.6, 0.7), 5, 0.4), (80, 80), interpolation=cv2.INTER_AREA),
              cv2.resize(COIN_A, (80, 80), interpolation=cv2.INTER_AREA)]
RAIN = rng0.uniform(0, 1, (16, 5)).astype(np.float32)
SPARKS = rng0.uniform(0, 1, (140, 3)).astype(np.float32)


def _coin(img, cx, cy, R, theta, light):
    lit = G.relief(COIN_C, COIN_H, light=light, strength=6, spec=0.6, shininess=30)
    sq = abs(math.cos(theta))
    w = max(4, int(2 * R * sq))
    tex = cv2.resize(lit if math.cos(theta) >= 0 else lit[:, ::-1] * 0.8, (w, 2 * R), interpolation=cv2.INTER_AREA)
    a = cv2.resize(COIN_A, (w, 2 * R), interpolation=cv2.INTER_AREA)
    edge = int(22 * abs(math.sin(theta)))
    if edge > 1:
        e = np.ones((2 * R, edge, 3), np.float32) * G.hexc("#8A6A22")
        ea = cv2.resize(COIN_A, (edge * 2, 2 * R))[:, :edge]
        G.over(img, e, ea, int(cx + w / 2 - edge / 2), int(cy - R))
    G.over(img, tex, a, int(cx - w / 2), int(cy - R))
    return img


def darphane(p, t, d, wt):
    t_s = (wt[6] if len(wt) > 6 else d * 0.7) + 0.05          # "Darphane"
    img = O.WARM.copy() * 0.75
    xx, yy = G.grid(W, H)
    cone = np.clip(1 - np.abs(xx - 540) / (120 + (yy - 150) * 0.35), 0, 1) * (yy > 150) * 0.12
    img += cone[..., None] * G.hexc("#FFD99A")
    after = t > t_s
    for i, (x, y0, v, s, ph) in enumerate(RAIN):                 # arka planda yağan paralar
        if not after:
            break
        ty = (t - t_s) * (250 + 350 * v)
        y = -100 + y0 * 300 + ty
        if y > H + 100:
            continue
        sq = abs(math.cos(t * (2 + 3 * s) + ph * 6))
        cw = max(2, int(80 * sq * (0.6 + 0.8 * s)))
        ch = int(80 * (0.6 + 0.8 * s))
        c = cv2.resize(COIN_SMALL[0], (cw, ch)) * 0.55
        a = G.blur(cv2.resize(COIN_SMALL[1], (cw, ch)), 1 + 3 * (1 - s))
        G.over(img, c, a, int(x * W - cw / 2), int(y))
    anvil = np.float32([[230, 1110], [850, 1110], [920, 1290], [160, 1290]])
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [anvil.astype(np.int32)], 255, cv2.LINE_AA)
    G.over(img, G.hexc("#1B1A18"), m.astype(np.float32) / 255)
    O.rect_fill(img, 230, 1106, 620, 8, G.hexc("#5C5A55"))
    if t < t_s + 0.15:
        blank = np.zeros((H, W), np.uint8)
        cv2.ellipse(blank, (540, 1090), (150, 34), 0, 0, 360, 255, -1, cv2.LINE_AA)
        G.over(img, G.hexc("#B8A26A"), blank.astype(np.float32) / 255)
    die_b = lerp(lerp(150, 430, ease_io(seg(t, 0, t_s - 0.5))), 1052, ease_in(seg(t, t_s - 0.45, t_s)))
    die_b += math.sin(t * 60) * 2.5 * seg(t, t_s - 1.2, t_s - 0.45)
    if after:
        die_b = lerp(1052, -80, ease_io(seg(t, t_s + 0.06, t_s + 0.75)))
    X = np.arange(380, dtype=np.float32)
    prof = 0.2 + 0.8 * np.sin(X / 380 * math.pi) ** 1.3 + np.exp(-((X - 120) / 30) ** 2) * 0.4
    if die_b > 2:
        die = np.repeat(prof[None, :, None], int(die_b), 0) * np.array([0.62, 0.6, 0.57], np.float32)
        die[-10:] *= 0.55
        G.over(img, die, np.ones(die.shape[:2], np.float32), 350, 0)
    if after:
        k = t - t_s
        glow = np.zeros_like(img)
        for vx, vy, life in SPARKS:
            ang = math.pi * (1.05 + 0.9 * vx)
            sp = 500 + 900 * vy
            lt = 0.25 + 0.45 * life
            if k > lt:
                continue
            x = 540 + math.cos(ang) * sp * k
            y = 1080 + math.sin(ang) * sp * k + 900 * k * k
            x2 = x - math.cos(ang) * sp * 0.025
            y2 = y - (math.sin(ang) * sp + 1800 * k) * 0.025
            O.poly(glow, [[x, y], [x2, y2]], G.hexc("#FFD68A"), 3, 1 - k / lt)
        img = O.add_glow(img, glow, (1.0, 1.4, 1.0))
        rise = ease_out(seg(t, t_s + 0.1, t_s + 0.95))
        theta = (t - t_s) * 8.5 * (1 - 0.55 * rise) + 0.3
        la = t * 1.8
        img = _coin(img, 540, lerp(1060, 700, rise), int(lerp(150, 230, rise)), theta,
                    (math.cos(la), math.sin(la) * 0.6 - 0.4, 0.7))
        img = O.flash(img, t, t_s, 0.16, 0.85, G.hexc("#FFF0D0"))
    dx, dy = O.shake(t, t_s, 20)
    img = O.camera(img, 1.0 + 0.03 * ease_io(p), dx=dx, dy=dy)

    def post(im):
        O.label(im, "06  ·  DARPHANE", alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


SAHNELER = dict(kanca=kanca, matbaa=matbaa, pamuk=pamuk, filigran=filigran, baski=baski, seri=seri, darphane=darphane)
