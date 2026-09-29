"""Telefon filmi sahnelerinin ortak araçları: plakalar, katmanlı telefon, harita, ikonlar, parçacıklar.

Renk kuralı: gerçekçi (3D) sahnelerde `img` doğrusal renktir, `post` katmanı renk işleminden sonra (ekran
renginde) çizilir. Animasyon sahneleri (ANIMASYON) film/ tarzı gibi doğrudan ekran renkleriyle çizilir.
"""
import json, math, os, sys
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
GOLD = G.GOLD
DARK = G.hexc("#111111")
_XX, _YY = G.grid(W, H)
SERIF = "InstrumentSerif-Italic.ttf"


# ================================================================== plakalar
_PL, _META = {}, {}


def plate(name):
    if name not in _PL:
        e = exr.oku(os.path.join(PLAKA, name + ".exr"))
        if "alpha" in e:
            e["alpha"] = np.clip(e["alpha"], 0, 1)
        _PL[name] = e
    return _PL[name]


def meta(name):
    if name not in _META:
        with open(os.path.join(PLAKA, name + ".json")) as f:
            _META[name] = json.load(f)
    return _META[name]


def push(rgb, depth, u, z0=1.0, z1=1.07, k=0.0, c=(540, 960), dx=0.0, dy=0.0, dref=6.0):
    """2.5D kamera: yavaş yaklaşma; k>0 ise yakın nesneler daha çok büyür (derinlik paralaksı)."""
    s = (z0 + (z1 - z0) * u) * 1.012
    sx = (c[0] + (_XX - c[0]) / s - dx).astype(np.float32)
    sy = (c[1] + (_YY - c[1]) / s - dy).astype(np.float32)
    if k and depth is not None:
        d = cv2.remap(depth, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        f = 1 + k * u * (1 / np.maximum(d, 1.5) - 1 / dref)
        sx = (c[0] + (sx - c[0]) / f).astype(np.float32)
        sy = (c[1] + (sy - c[1]) / f).astype(np.float32)
    out = cv2.remap(rgb, sx, sy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    dep = cv2.remap(depth, sx, sy, cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE) if depth is not None else None
    return out, dep


def zoom_pt(p, s, c=(540, 960), dx=0.0, dy=0.0):
    """push() ile aynı dönüşüm, tek nokta için (plakadaki nokta -> ekrandaki yeri)."""
    s = s * 1.012
    return (c[0] + (p[0] - c[0]) * s + dx * s, c[1] + (p[1] - c[1]) * s + dy * s)


def hand(t, amp=3.0, seed=0.0):
    dx = amp * (math.sin(t * 0.83 + seed) + 0.6 * math.sin(t * 1.71 + 2 * seed) + 0.3 * math.sin(t * 3.1 + seed))
    dy = amp * (math.sin(t * 0.67 + 1.3 + seed) + 0.5 * math.sin(t * 1.43 + seed) + 0.25 * math.sin(t * 2.9 + 3 * seed))
    return dx, dy


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


_TOPG = np.clip(1 - _YY / 820, 0, 1)[..., None] ** 1.6


def shade_top(im, k=0.45):
    im *= 1 - k * _TOPG
    return im


# ================================================================== katmanlar ve dönüşümler
def affine(s=1.0, c=(540, 960), dx=0.0, dy=0.0, rot=0.0):
    M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), rot, s)
    M[:, 2] += (dx, dy)
    return M


def compose(M2, M1):
    """Önce M1, sonra M2 (2x3 matrisler)."""
    A = np.vstack([M1, [0, 0, 1]])
    B = np.vstack([M2, [0, 0, 1]])
    return (B @ A)[:2]


def warp(x, M, interp=cv2.INTER_LINEAR):
    return cv2.warpAffine(x, M, (W, H), flags=interp, borderMode=cv2.BORDER_CONSTANT)


def over_pm(img, rgb, a):
    """Önceden çarpılmış renkli katmanı bindir."""
    return img * (1 - a[..., None]) + rgb


def app(pt, M):
    return (M[0, 0] * pt[0] + M[0, 1] * pt[1] + M[0, 2], M[1, 0] * pt[0] + M[1, 1] * pt[1] + M[1, 2])


HERO_ORDER = ["arka", "kart", "govde", "ekran"]
HERO_OFF = {"ekran": 0.11, "govde": 0.04, "kart": -0.04, "arka": -0.11}


def hero_layers(ex=None, ui=1.0, M=None, fly=None, only=None, tint=None):
    """Katmanlı telefon: ex[k] 0 = yerinde, 1 = patlatılmış (normal ekseni boyunca ayrık).
    M: bütün telefona uygulanacak ekran dönüşümü. fly[k] = (dx, dy, rot) ek savrulma. Döndürür: [(k, rgb, a)]."""
    hm = meta("hero")
    cx, cy = hm["center"][:2]
    nx, ny = hm["normal_px_per_m"]
    ks = hm["depth_scale_per_m"]
    out = []
    for k in HERO_ORDER:
        if only and k not in only:
            continue
        pl = plate("hero_" + k)
        rgb, a = pl["rgb"], pl["alpha"]
        if k == "ekran" and ui < 1:
            rgb = rgb * (0.05 + 0.95 * ui)
        if tint is not None and k in tint:
            rgb = rgb * np.asarray(tint[k], np.float32)
        e = (ex or {}).get(k, 0.0)
        off = HERO_OFF[k] * e
        fdx, fdy, frot = (fly or {}).get(k, (0.0, 0.0, 0.0))
        L = affine(1 + off * ks, (cx, cy), off * nx + fdx, off * ny + fdy, frot)
        T_ = compose(M, L) if M is not None else L
        out.append((k, warp(rgb, T_), warp(a, T_)))
    return out


def hero_over(img, layers):
    for _, rgb, a in layers:
        img = over_pm(img, rgb, a)
    return img


_HERO_FULL = None


def hero_sprite():
    """Birleşik telefon (renk önceden çarpılmış, alfa) — küçük kopyalar için."""
    global _HERO_FULL
    if _HERO_FULL is None:
        img = np.zeros((H, W, 3), np.float32)
        a = np.zeros((H, W), np.float32)
        for k in HERO_ORDER:
            pl = plate("hero_" + k)
            img = over_pm(img, pl["rgb"], pl["alpha"])
            a = a + pl["alpha"] * (1 - a)
        ys, xs = np.nonzero(a > 0.01)
        y0, y1, x0, x1 = ys.min() - 4, ys.max() + 5, xs.min() - 4, xs.max() + 5
        _HERO_FULL = (img[y0:y1, x0:x1].copy(), a[y0:y1, x0:x1].copy(), (x0, y0))
    return _HERO_FULL


def paste_pm(img, rgb, a, x, y, s=1.0, alpha=1.0, rot=0.0):
    """Küçük önceden çarpılmış sprite'ı (x,y merkezli) ölçekleyip bindir."""
    if alpha <= 0.01 or s <= 0.01:
        return img
    h, w = a.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), rot, s)
    M[:, 2] += (x - w / 2, y - h / 2)
    r2 = warp(rgb, M) * alpha
    a2 = warp(a, M) * alpha
    return over_pm(img, r2, a2)


# ================================================================== yazı/etiket/ikon
def chip(im, txt, x, y, color=YELLOW, a=1.0, px=30, dark=True, anchor="lm", icon=None):
    if a <= 0.01:
        return im
    m = G.text_mask(txt, "Montserrat.ttf", px, 800)
    ic = int(px * 1.1) if icon else 0
    w, h = m.shape[1] + 34 + ic, m.shape[0] + 18
    x0 = int(x if anchor[0] == "l" else x - w / 2 if anchor[0] == "m" else x - w)
    O.rect_fill(im, x0, int(y - h / 2), w, h, color, a, r=h // 2)
    fg = DARK if dark else ONE
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


def counter_text(v, fmt="{:,.0f}"):
    return fmt.format(v).replace(",", "X").replace(".", ",").replace("X", ".")


def text_w(txt, px, file="Montserrat.ttf", wght=800, tracking=0.0):
    return G.text_mask(txt, file, px, wght, tracking).shape[1]


def lock_icon(im, x, y, s, color, a=1.0, open_=0.0, thick=None, glow=0.0):
    """Çizgi asma kilit: open_ 0 kapalı, 1 açık (dil yukarı kalkar)."""
    if a <= 0.01:
        return im
    th = thick or max(3, int(s * 0.09))
    bw, bh = s * 0.9, s * 0.68
    top = y - bh * 0.1
    O.rect_fill(im, x - bw / 2, top, bw, bh, color, a * 0.18, r=int(s * 0.12))
    O.poly(im, [[x - bw / 2, top], [x + bw / 2, top], [x + bw / 2, top + bh], [x - bw / 2, top + bh]], color, th, a,
           closed=True, glow=glow)
    r = s * 0.27
    lift = s * 0.24 * open_
    cyc = top - s * 0.14 - lift
    ang = np.linspace(math.pi, 2 * math.pi, 24)
    arc = np.stack([x + r * np.cos(ang), cyc + r * np.sin(ang)], 1)
    pts = np.vstack([[[x - r, top - lift]], arc, [[x + r, top - lift]]])
    O.poly(im, pts, color, th, a, glow=glow)
    O.circle(im, x, top + bh * 0.45, s * 0.07, color, fill=True, alpha=a)
    return im


def person_icon(im, x, y, s, color, a=1.0):
    O.circle(im, x, y - s * 0.28, s * 0.2, color, fill=True, alpha=a)
    O.arc(im, x, y + s * 0.42, s * 0.36, math.pi, 2 * math.pi, color, thick=max(3, int(s * 0.14)), alpha=a)
    return im


def signal_bars(im, x, y, s, n_on, color, a=1.0, off_color=None):
    for i in range(4):
        h = s * (0.3 + 0.23 * i)
        col = color if i < n_on else (off_color if off_color is not None else ONE * 0.25)
        O.rect_fill(im, x + i * s * 0.28, y - h, s * 0.18, h, col, a, r=int(s * 0.04))
    return im


def phone_icon(im, x, y, w, h, color, a=1.0, fill=None, thick=3):
    if fill is not None:
        O.rect_fill(im, x - w / 2, y - h / 2, w, h, fill, a, r=int(w * 0.18))
    O.poly(im, [[x - w / 2 + w * 0.18, y - h / 2], [x + w / 2 - w * 0.18, y - h / 2], [x + w / 2, y - h / 2 + w * 0.18],
                [x + w / 2, y + h / 2 - w * 0.18], [x + w / 2 - w * 0.18, y + h / 2], [x - w / 2 + w * 0.18, y + h / 2],
                [x - w / 2, y + h / 2 - w * 0.18], [x - w / 2, y - h / 2 + w * 0.18]], color, thick, a, closed=True)
    return im


def ring_text(im, txt, cx, cy, r, px, color, a=1.0, rot=0.0, file="Montserrat.ttf", wght=800):
    """Yazıyı çemberin üzerine diz (mühür)."""
    if a <= 0.01:
        return im
    n = len(txt)
    for i, ch in enumerate(txt):
        if ch == " ":
            continue
        ang = rot + 2 * math.pi * i / n
        m = G.text_mask(ch, file, px, wght)
        mh, mw = m.shape
        pad = max(mh, mw)
        big = np.zeros((pad * 2, pad * 2), np.float32)
        big[pad - mh // 2:pad - mh // 2 + mh, pad - mw // 2:pad - mw // 2 + mw] = m
        R_ = cv2.getRotationMatrix2D((pad, pad), -math.degrees(ang), 1.0)
        big = cv2.warpAffine(big, R_, (pad * 2, pad * 2))
        x = cx + r * math.sin(ang)
        y = cy - r * math.cos(ang)
        G.over(im, np.asarray(color, np.float32), big * a, int(x - pad), int(y - pad))
    return im


def rot_layer(im, draw, rot, c, alpha=1.0, pad_box=None):
    """draw(layer) ile tam boy RGBA katmanına çiz, c etrafında döndürüp bindir."""
    if alpha <= 0.01:
        return im
    col = np.zeros((H, W, 3), np.float32)
    a = np.zeros((H, W), np.float32)
    draw(col, a)
    M = cv2.getRotationMatrix2D((float(c[0]), float(c[1])), rot, 1.0)
    col = warp(col, M)
    a = warp(a, M) * alpha
    return im * (1 - a[..., None]) + col * a[..., None]


# ================================================================== harita (eğik)
def tilt_matrix(strength=0.2):
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    inset = W * strength
    dst = np.float32([[inset, 160], [W - inset, 160], [W + 60, H + 40], [-60, H + 40]])
    return cv2.getPerspectiveTransform(src, dst)


TILT = tilt_matrix()
_MASK = None


def map_mask():
    global _MASK
    if _MASK is None:
        m = cv2.warpPerspective(np.ones((H, W), np.float32), TILT, (W, H), flags=cv2.INTER_LINEAR)
        m = cv2.erode(m, np.ones((61, 61), np.uint8))
        _MASK = G.blur(m, 40)[..., None]
    return _MASK


def warp_pt(M, xy):
    v = M @ np.array([xy[0], xy[1], 1.0])
    return v[:2] / v[2]


def tilt_img(img):
    img = cv2.warpPerspective(img, TILT, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    mask = map_mask()
    bg = np.array([0.008, 0.012, 0.02], np.float32)
    img = img * mask + bg * (1 - mask)
    fog = np.clip(1 - (_YY - 120) / 700, 0, 1)[..., None] ** 1.5
    return img * (1 - 0.75 * fog) + bg * 0.75 * fog


# ================================================================== harf tabelası
TILE_W, TILE_H, GAP = 70, 104, 8


def _tile():
    m = O.rounded(TILE_W, TILE_H, 10)
    y = np.linspace(0, 1, TILE_H, dtype=np.float32)[:, None, None]
    col = np.ones((TILE_H, TILE_W, 3), np.float32) * (0.10 + 0.05 * (1 - y))
    col[TILE_H // 2 - 1:TILE_H // 2 + 1] *= 0.35
    return col, m


TILE, TILE_M = _tile()
ALPH = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ0123456789?"


def flap_board(img, rows, t, t_settle, y0=620, colors=None, speed=0.055, px=78):
    k = 0
    for r, row in enumerate(rows):
        n = len(row)
        x0 = 540 - (n * TILE_W + (n - 1) * GAP) / 2
        yy = y0 + r * (TILE_H + 20)
        for i, ch in enumerate(row):
            k += 1
            appear = ease_out(seg(t, 0.02 * k, 0.02 * k + 0.18))
            if appear <= 0:
                continue
            x = int(x0 + i * (TILE_W + GAP))
            G.over(img, TILE, TILE_M * appear, x, int(yy))
            if ch == " ":
                continue
            settle = t_settle + k * speed * 0.4
            if t < settle:
                cyc = t / 0.05 + k * 0.37
                cur = ALPH[int(cyc * 7 + k * 5) % len(ALPH)]
                frac = cyc % 1
                sy = 0.25 + 0.75 * abs(math.cos(math.pi * frac))
                col = ONE * 0.75
            else:
                cur = ch
                col = (colors[r][i] if colors else YELLOW)
                sy = 1.0 - 0.6 * math.exp(-(t - settle) * 18) * abs(math.cos((t - settle) * 40))
            m = G.text_mask(cur, "Montserrat.ttf", px, 900)
            mh = max(2, int(m.shape[0] * sy))
            m = cv2.resize(m, (m.shape[1], mh))
            G.over(img, np.asarray(col, np.float32), m * appear, int(x + TILE_W / 2 - m.shape[1] / 2),
                   int(yy + TILE_H / 2 - mh / 2))
    return img


# ================================================================== parçacıklar
def splat(img, pts, cols, size=2, alpha=None):
    """Noktaları (x,y) renkleriyle görüntüye ekle (ışık gibi toplanır)."""
    if len(pts) == 0:
        return img
    x = np.round(pts[:, 0]).astype(int)
    y = np.round(pts[:, 1]).astype(int)
    ok = (x >= 0) & (x < W - 1) & (y >= 0) & (y < H - 1)
    x, y, c = x[ok], y[ok], cols[ok]
    if alpha is not None:
        c = c * alpha[ok][:, None]
    acc = np.zeros((H, W, 3), np.float32)
    np.add.at(acc, (y, x), c)
    if size > 1:
        acc = cv2.dilate(acc, np.ones((size, size), np.uint8))
    return img + acc


def dust(t, n=160, seed=3, area=(0, 200, W, 1500)):
    """Havada süzülen toz parçacıkları (x, y, parlaklık)."""
    rng = np.random.default_rng(seed)
    x0, y0, x1, y1 = area
    base = rng.uniform(0, 1, (n, 2)) * [x1 - x0, y1 - y0] + [x0, y0]
    vel = rng.normal(0, 1, (n, 2)) * [6, 4] + [4, -10]
    ph = rng.uniform(0, 6.28, n)
    p = base + vel * t + np.stack([np.sin(t * 0.7 + ph) * 8, np.cos(t * 0.5 + ph) * 6], 1)
    p[:, 0] = x0 + (p[:, 0] - x0) % (x1 - x0)
    p[:, 1] = y0 + (p[:, 1] - y0) % (y1 - y0)
    b = 0.5 + 0.5 * np.sin(t * 1.3 + ph * 3)
    return p, b


def draw_dust(img, t, color, k=1.0, n=160, seed=3, area=(0, 200, W, 1500)):
    p, b = dust(t, n, seed, area)
    glow = np.zeros_like(img)
    glow = splat(glow, p, np.outer(b, color).astype(np.float32) * k, 3)
    return img + G.blur(glow, 2.5) * 0.9 + G.blur(glow, 8) * 0.6
