"""Sahnelerin ortak araçları: zamanlama eğrileri, kamera, yazı, cam panel, ikonlar, parçacıklar."""
import math
import cv2
import numpy as np
import gfx as G
import banknot as B

W, H = G.W, G.H
ONE = np.ones(3, np.float32)


# ------------------------------------------------------------------ zamanlama eğrileri
def seg(p, a, b):
    return float(np.clip((p - a) / (b - a), 0, 1)) if b > a else float(p >= a)


def ease_out(p):
    return 1 - (1 - p) ** 3


def ease_in(p):
    return p ** 3


def ease_io(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def back(p, s=1.8):
    return 1 + (s + 1) * (p - 1) ** 3 + s * (p - 1) ** 2


def spring(p, freq=2.2, decay=6.0):
    """0'dan 1'e yaylanarak oturan hareket."""
    return 1 - math.exp(-decay * p) * math.cos(2 * math.pi * freq * p)


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------ kamera
def camera(img, zoom=1.0, cx=W / 2, cy=H / 2, rot=0.0, dx=0.0, dy=0.0):
    if abs(zoom - 1) < 1e-4 and not rot and not dx and not dy:
        return img
    M = cv2.getRotationMatrix2D((cx, cy), rot, zoom)
    M[:, 2] += (dx, dy)
    return cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def shake(t, t0, amp=14.0, dur=0.35, seed=0):
    """t0 anındaki darbeden sonra sönen sarsıntı (dx, dy)."""
    if t < t0 or t > t0 + dur:
        return 0.0, 0.0
    k = 1 - (t - t0) / dur
    rng = np.random.default_rng(int((t - t0) * 60) + seed)
    return tuple(rng.uniform(-1, 1, 2) * amp * k * k)


def flash(img, t, t0, dur=0.18, strength=0.9, color=ONE):
    if t0 <= t <= t0 + dur:
        k = (1 - (t - t0) / dur) ** 2 * strength
        img = img * (1 - k) + color * k
    return img


# ------------------------------------------------------------------ arka planlar
def radial_bg(base, glow, cx, cy, rx, ry, k=0.9):
    img = G.canvas(G.hexc(base))
    xx, yy = G.grid(W, H)
    r = np.hypot((xx - cx) / rx, (yy - cy) / ry)
    return img + (np.clip(1 - r, 0, 1) ** 2)[..., None] * G.hexc(glow) * k


WARM = radial_bg("#050403", "#3A2A12", 540, 820, 700, 900)
COOL = radial_bg("#030508", "#0C3440", 540, 800, 700, 950, 0.8)
NIGHT = radial_bg("#040405", "#15161C", 540, 800, 700, 950, 0.8)


def grid_lines(img, step=60, a=0.05, color=G.CYAN):
    out = img.copy()
    out[:, ::step] = out[:, ::step] * (1 - a) + color * a
    out[::step, :] = out[::step, :] * (1 - a) + color * a
    return out


# ------------------------------------------------------------------ yazı
def text(img, txt, x, y, px, file="Montserrat.ttf", wght=800, color=ONE, anchor="mm", alpha=1.0,
         tracking=0.0, scale=1.0, glow=0.0):
    """Keskin yazı yerleştir. anchor: 'mm' merkez, 'lm' sol-orta, 'lt' sol-üst."""
    if alpha <= 0.01:
        return img
    m = G.text_mask(txt, file, max(6, int(px * scale)), wght, tracking * scale)
    h, w = m.shape
    ox = x - w / 2 if anchor[0] == "m" else (x if anchor[0] == "l" else x - w)
    oy = y - h / 2 if anchor[1] == "m" else (y if anchor[1] == "t" else y - h)
    ox, oy = int(round(ox)), int(round(oy))
    if glow:
        g = G.blur(np.pad(m, 30), 12 * scale)
        G.add(img, (g[..., None] * np.asarray(color, np.float32) * glow * alpha).astype(np.float32), ox - 30, oy - 30)
    G.over(img, np.asarray(color, np.float32), m * alpha, ox, oy)
    return img


def label(img, txt, x=70, y=235, color=G.GOLD, alpha=1.0):
    """Bölüm etiketi: '01 · MATBAA' + ince çizgi."""
    if alpha <= 0.01:
        return img
    m = G.text_mask(txt, "Inter.ttf", 26, 700, tracking=5)
    col = np.clip(np.asarray(color) * 1.35, 0, 1)
    G.over(img, col, m * alpha, x, y)
    ln = int(90 * alpha)
    img[y + m.shape[0] + 12:y + m.shape[0] + 14, x:x + ln] = col
    return img


# ------------------------------------------------------------------ cam panel
def rounded(w, h, r):
    m = np.zeros((h, w), np.uint8)
    r = int(min(r, w // 2, h // 2))
    cv2.rectangle(m, (r, 0), (w - r, h), 255, -1)
    cv2.rectangle(m, (0, r), (w, h - r), 255, -1)
    for cx, cy in ((r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)):
        cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return m.astype(np.float32) / 255


def glass(img, x, y, w, h, r=56, frost=20, tint=0.05, refr=22, shadow=0.45, alpha=1.0):
    """Buzlu cam panel (liquid glass): bulanık + kırılan arka plan, parlak kenar, gölge."""
    if alpha <= 0.01:
        return img
    pad = int(frost * 3 + refr + 4)
    x0, y0 = max(0, x - pad), max(0, y - pad)
    x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
    crop = img[y0:y1, x0:x1]
    small = cv2.resize(crop, ((x1 - x0) // 3 + 1, (y1 - y0) // 3 + 1), interpolation=cv2.INTER_AREA)
    big = cv2.resize(cv2.GaussianBlur(small, (0, 0), frost / 3), (x1 - x0, y1 - y0), interpolation=cv2.INTER_LINEAR)
    m = rounded(w, h, r)
    d = cv2.distanceTransform((m > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    X, Y = G.grid(w, h)
    k = (1 - np.clip(d / 44, 0, 1)) ** 2
    mx = (X + (x - x0) + (w / 2 - X) / (w / 2) * k * refr).astype(np.float32)
    my = (Y + (y - y0) + (h / 2 - Y) / (h / 2) * k * refr).astype(np.float32)
    fro = cv2.remap(big, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT) * (1 + tint) + tint
    gx, gy = cv2.Sobel(m, cv2.CV_32F, 1, 0, ksize=5), cv2.Sobel(m, cv2.CV_32F, 0, 1, ksize=5)
    edge = np.exp(-((d - 1.5) / 1.6) ** 2)
    ld = np.clip((-gx - gy) / (np.hypot(gx, gy) + 1e-6), -1, 1)
    rim = edge * (0.3 + 0.45 * (0.5 + 0.5 * ld))
    spec = np.exp(-(((X + Y * 0.6) - w * 0.3) / (w * 0.09)) ** 2) * 0.045
    out = fro + (rim + spec)[..., None]
    if shadow:
        sm = np.zeros((y1 - y0, x1 - x0), np.float32)
        oy, ox = y - y0, x - x0                                   # panel kısmen ekran dışında olabilir
        a0, b0, a1, b1 = max(0, oy), max(0, ox), min(y1 - y0, oy + h), min(x1 - x0, ox + w)
        if a1 > a0 and b1 > b0:
            sm[a0:a1, b0:b1] = m[a0 - oy:a1 - oy, b0 - ox:b1 - ox]
        sh = cv2.GaussianBlur(np.roll(sm, 28, 0), (0, 0), 26) * shadow * alpha
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - sh[..., None])
    G.over(img, out, m * alpha, x, y)
    return img


# ------------------------------------------------------------------ banknot yerleştirme
def project_quad(cx, cy, width, rx=0.0, ry=0.0, rz=0.0, f=2200.0, aspect=B.BH / B.BW):
    hw, hh = width / 2, width * aspect / 2
    pts = np.array([[-hw, -hh, 0], [hw, -hh, 0], [hw, hh, 0], [-hw, hh, 0]], np.float32)
    ax, ay, az = map(math.radians, (rx, ry, rz))
    Rx = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    Ry = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    Rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    p = pts @ (Rz @ Ry @ Rx).T
    return np.float32([[cx + f * x / (f + z), cy + f * y / (f + z)] for x, y, z in p])


def place(img, tex, quad, alpha_tex=None, shadow=0.65, sdx=24, sdy=46, opacity=1.0):
    """Dokuyu (h,w,3) dörtgene perspektifle yerleştir, gölgesiyle."""
    th, tw = tex.shape[:2]
    src = np.float32([[0, 0], [tw, 0], [tw, th], [0, th]])
    M = cv2.getPerspectiveTransform(src, np.float32(quad))
    x0, y0 = np.floor(quad.min(0)).astype(int) - 80
    x1, y1 = np.ceil(quad.max(0)).astype(int) + 120
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    if x1 <= x0 or y1 <= y0:
        return img
    T = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]], np.float64) @ M
    size = (x1 - x0, y1 - y0)
    col = cv2.warpPerspective(tex, T, size, flags=cv2.INTER_LINEAR)
    a = cv2.warpPerspective(alpha_tex if alpha_tex is not None else np.ones((th, tw), np.float32), T, size,
                            flags=cv2.INTER_LINEAR) * opacity
    region = img[y0:y1, x0:x1]
    if shadow:
        s = cv2.GaussianBlur(np.roll(np.roll(a, sdy, 0), sdx, 1), (0, 0), 24) * shadow
        region *= (1 - s)[..., None]
    region[:] = region * (1 - a[..., None]) + col * a[..., None]
    return img


# ------------------------------------------------------------------ rakam parçacıkları
RAMP = "·:1732504698"
_atlas = {}


def glyph(ch, px=20):
    key = (ch, px)
    if key not in _atlas:
        _atlas[key] = G.text_mask(ch, G.MONO, px)
    return _atlas[key]


def digit_sprite(img, glow, ch, x, y, color, a=1.0, px=20):
    m = glyph(ch, px) * a
    ox, oy = int(x) - m.shape[1] // 2, int(y) - m.shape[0] // 2
    G.over(img, color, m, ox, oy)
    G.add(glow, (m[..., None] * color).astype(np.float32), ox, oy)


def add_glow(img, glow, k=(0.5, 0.8, 0.55)):
    small = cv2.resize(glow, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    g1 = cv2.resize(cv2.GaussianBlur(small, (0, 0), 3), (W, H))
    g2 = cv2.resize(cv2.GaussianBlur(small, (0, 0), 11), (W, H))
    return img + glow * k[0] + g1 * k[1] + g2 * k[2]


def mask_points(mask, n, seed=0):
    ys, xs = np.nonzero(mask > 0.5)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(xs), size=min(n, len(xs)), replace=False)
    return np.stack([xs[idx], ys[idx]], 1).astype(np.float32)


# ------------------------------------------------------------------ çizgi ikonlar (vektör, sade)
def _local(img, pts, pad):
    pts = np.asarray(pts, np.float32).reshape(-1, 2)
    x0, y0 = np.floor(pts.min(0)).astype(int) - pad
    x1, y1 = np.ceil(pts.max(0)).astype(int) + pad
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(img.shape[1], x1), min(img.shape[0], y1)
    return pts, x0, y0, x1, y1


def _stamp(img, m, x0, y0, color, alpha, glow):
    a = m.astype(np.float32) / 255 * alpha
    col = np.asarray(color, np.float32)
    if glow:
        img[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] += G.blur(a, 8)[..., None] * col * glow
    return G.over(img, col, a, x0, y0)


def poly(img, pts, color, thick=4, alpha=1.0, closed=False, glow=0.0):
    pts, x0, y0, x1, y1 = _local(img, pts, int(thick) + 4 + (26 if glow else 0))
    if x1 <= x0 or y1 <= y0:
        return img
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.polylines(m, [np.round((pts - (x0, y0)) * 4).astype(np.int32)], closed, 255, max(1, int(thick)), cv2.LINE_AA, shift=2)
    return _stamp(img, m, x0, y0, color, alpha, glow)


def circle(img, cx, cy, r, color, thick=4, alpha=1.0, fill=False, glow=0.0):
    pad = int(r + thick + 4 + (26 if glow else 0))
    x0, y0, x1, y1 = max(0, int(cx) - pad), max(0, int(cy) - pad), min(img.shape[1], int(cx) + pad), min(img.shape[0], int(cy) + pad)
    if x1 <= x0 or y1 <= y0:
        return img
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    cv2.circle(m, (int((cx - x0) * 4), int((cy - y0) * 4)), int(r * 4), 255, -1 if fill else max(1, int(thick)), cv2.LINE_AA, shift=2)
    return _stamp(img, m, x0, y0, color, alpha, glow)


def arc(img, cx, cy, r, a0, a1, color, thick=10, alpha=1.0, glow=0.0):
    angs = np.linspace(a0, a1, max(2, int(abs(a1 - a0) / 2 * 30)))
    pts = np.stack([cx + r * np.cos(angs), cy + r * np.sin(angs)], 1)
    return poly(img, pts, color, thick, alpha, glow=glow)


def rect_fill(img, x, y, w, h, color, alpha=1.0, r=0):
    m = rounded(int(w), int(h), r) if r else np.ones((int(h), int(w)), np.float32)
    return G.over(img, np.asarray(color, np.float32), m * alpha, int(x), int(y))
