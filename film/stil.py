"""Stil kareleri: filmin görsel dilini göstermek için üç sabit kare."""
import math, os, sys
import cv2
import numpy as np
import gfx as G
import banknot as B

OUT = sys.argv[1] if len(sys.argv) > 1 else "."


# ----------------------------------------------------------------- ortak yardımcılar
def project_quad(cx, cy, width, rx=0.0, ry=0.0, rz=0.0, f=2200.0):
    """Banknot düzlemini 3B döndürüp ekrana yansıt (derece)."""
    hw, hh = width / 2, width * B.BH / B.BW / 2
    pts = np.array([[-hw, -hh, 0], [hw, -hh, 0], [hw, hh, 0], [-hw, hh, 0]], np.float32)
    ax, ay, az = map(math.radians, (rx, ry, rz))
    Rx = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    Ry = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    Rz = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    p = pts @ (Rz @ Ry @ Rx).T
    return np.float32([[cx + f * x / (f + z), cy + f * y / (f + z)] for x, y, z in p])


def place(img_local, alpha_local, quad):
    src = np.float32([[0, 0], [B.BW, 0], [B.BW, B.BH], [0, B.BH]])
    M = cv2.getPerspectiveTransform(src, quad)
    col = cv2.warpPerspective(G.blur(img_local, 0.7), M, (G.W, G.H), flags=cv2.INTER_LINEAR)
    a = cv2.warpPerspective(alpha_local, M, (G.W, G.H), flags=cv2.INTER_LINEAR)
    return col, a, M


def shadow(bg, a, dx=30, dy=50, sigma=28, k=0.7):
    s = G.blur(np.roll(np.roll(a, dy, 0), dx, 1), sigma)
    return bg * (1 - k * s)[..., None]


def label(img, text, x, y, color=G.GOLD, px=26):
    m = G.text_mask(text, "Inter.ttf", px, 700, tracking=5)
    G.over(img, np.clip(color * 1.35, 0, 1), m, x, y)
    img[y + m.shape[0] + 12:y + m.shape[0] + 14, x:x + 90] = color
    return img


def warm_bg():
    img = G.canvas(G.hexc("#050403"))
    xx, yy = G.grid(G.W, G.H)
    r = np.hypot((xx - 560) / 700, (yy - 780) / 900)
    return img + np.clip(1 - r, 0, 1)[..., None] ** 2 * G.hexc("#3A2A12") * 0.9


# ----------------------------------------------------------------- 1) KABARTMA
def frame_kabartma(note):
    bg = warm_bg()
    lit = G.relief(note["color"], note["height"], light=(-0.7, -0.6, 0.75), strength=5, spec=0.3) * 0.82
    quad = project_quad(560, 760, 980, rx=38, ry=-10, rz=-9)
    col, a, M = place(lit, note["alpha"], quad)
    img = shadow(bg, a)
    img = img * (1 - a[..., None]) + col * a[..., None]
    # ışık süpürmesi (banknot üstünde çapraz parıltı)
    xx, yy = G.grid(G.W, G.H)
    sweep = np.exp(-(((xx - 0.55 * yy) - 150) / 90) ** 2) * a * 0.18
    img += sweep[..., None] * G.hexc("#FFF2D0")
    # büyüteç: amblemi yakından, güçlü kabartma ışığıyla göster
    bub, glyph, ex, ey = note["emblem"]
    macro = G.relief(note["color"], note["height"], light=(-0.8, -0.35, 0.55), strength=11, spec=0.55, shininess=28)
    Cx, Cy, Rl, zoom = 700, 1200, 250, 1.25
    lx, ly = ex + 150, ey + 150
    X, Y = G.grid(2 * Rl, 2 * Rl)
    qx, qy = X - Rl, Y - Rl
    r = np.hypot(qx, qy) / Rl
    s = (0.72 + 0.28 * r ** 2) / zoom
    mapx, mapy = (lx + qx * s).astype(np.float32), (ly + qy * s).astype(np.float32)
    lens = cv2.remap(macro, mapx, mapy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    disk = G.smoothstep(1.0, 0.985, r)
    ring = np.exp(-((r - 0.995) / 0.018) ** 2)
    ang = np.arctan2(qy, qx)
    rim = ring[..., None] * (0.55 + 0.45 * np.cos(ang + 2.4))[..., None] * G.hexc("#FFF6E0")
    img = shadow(img, np.pad(disk, ((Cy - Rl, G.H - Cy - Rl), (Cx - Rl, G.W - Cx - Rl))), 18, 30, 22, 0.65)
    G.over(img, lens * 0.85, disk, Cx - Rl, Cy - Rl)
    G.add(img, rim * 0.9, Cx - Rl, Cy - Rl)
    hi = np.exp(-(((qx + 90) / 120) ** 2 + ((qy + 140) / 45) ** 2)) * disk * 0.22
    G.add(img, hi[..., None] * np.ones(3, np.float32), Cx - Rl, Cy - Rl)
    img = G.finish(img, seed=1, bloom_thresh=0.92, bloom_k=0.3, exposure=1.0)
    label(img, "03  ·  KABARTMA BASKI", 70, 150)
    return G.put_caption(img, "parmakla ~hissedilen / *KABARTMA baskı", 1010)


# ----------------------------------------------------------------- 2) DÖNÜŞÜM (banknot -> rakam)
RAMP = "·:1732504698"


def glyph_atlas(px=22):
    return {c: G.text_mask(c, G.MONO, px) for c in RAMP + "₺"}


def frame_donusum(note):
    rng = np.random.default_rng(4)
    img = G.canvas(G.hexc("#040608"))
    xx, yy = G.grid(G.W, G.H)
    img += (np.exp(-((xx - 790) ** 2 + (yy - 760) ** 2) / (2 * 380 ** 2)))[..., None] * G.hexc("#0E3A44") * 0.9
    lit = G.relief(note["color"], note["height"], light=(-0.5, -0.7, 0.9), strength=3, spec=0.2)
    quad = project_quad(400, 1480, 720, rx=28, ry=8, rz=-8)
    col, a, M = place(lit, note["alpha"], quad)
    # çözülme cephesi: sağdaki hücreler rakama dönüşüp telefona akar
    cw, ch = 13, 21
    atlas = glyph_atlas(20)
    x0, x1 = int(quad[:, 0].min()), int(quad[:, 0].max())
    front = x0 + 0.42 * (x1 - x0)
    keep = np.clip((front + 25 * np.sin(yy / 37) - xx) / 20, 0, 1)
    img = shadow(img, a * keep, 20, 40, 22, 0.6)
    img = img * (1 - (a * keep)[..., None]) + col * (a * keep)[..., None]
    glow = np.zeros_like(img)
    target = np.array([800.0, 700.0])
    for gy in range(0, G.H - ch, ch):
        for gx in range(0, G.W - cw, cw):
            cy_, cx_ = gy + ch // 2, gx + cw // 2
            if a[cy_, cx_] < 0.5 or keep[cy_, cx_] > 0.5:
                continue
            cell = col[gy:gy + ch, gx:gx + cw]
            lum = float(cell.mean())
            ci = int(np.clip((1 - lum) * 1.9, 0, 0.999) * len(RAMP))
            c = RAMP[ci] if rng.random() > 0.04 else "₺"
            age = np.clip((cx_ - front) / (x1 - front), 0, 1)
            t = age ** 1.3
            p0 = np.array([cx_, cy_], float)
            ctrl = p0 + np.array([60, -520])
            pos = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * ctrl + t ** 2 * (target + rng.normal(0, 60, 2))
            pos += rng.normal(0, 14 * t, 2)
            color = (1 - t) * cell.reshape(-1, 3).mean(0) * 1.2 + t * (G.CYAN * (1 - t) + G.YELLOW * t)
            m = atlas[c] * (1 - 0.65 * t)
            px_, py_ = int(pos[0]) - m.shape[1] // 2, int(pos[1]) - m.shape[0] // 2
            G.over(img, color, m, px_, py_)
            G.add(glow, (m[..., None] * color * 0.9).astype(np.float32), px_, py_)
    # akışı yoğunlaştıran serbest parçacıklar
    for _ in range(420):
        t = rng.random()
        p0 = np.array([rng.uniform(front, x1), rng.uniform(1300, 1650)])
        ctrl = p0 + np.array([60, -520])
        pos = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * ctrl + t ** 2 * (target + rng.normal(0, 90, 2)) + rng.normal(0, 25, 2)
        c = RAMP[rng.integers(2, len(RAMP))]
        m = atlas[c] * rng.uniform(0.25, 0.8)
        col_ = G.CYAN * (1 - t) + G.YELLOW * t
        G.add(glow, (m[..., None] * col_).astype(np.float32), int(pos[0]), int(pos[1]))
    img += glow * 0.55 + G.blur(glow, 6) * 0.8 + G.blur(glow, 22) * 0.6
    img = glass_phone(img, 610, 360, 380, 740)
    img = G.finish(img, seed=2, vig=0.5)
    return G.put_caption(img, "Ama asıl para / **BURADA ~doğar.", 115)


# ----------------------------------------------------------------- cam (liquid glass) öğeleri
def rounded_mask(w, h, r):
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (r, 0), (w - r, h), 255, -1)
    cv2.rectangle(m, (0, r), (w, h - r), 255, -1)
    for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(m, (cx, cy), r, 255, -1, cv2.LINE_AA)
    return m.astype(np.float32) / 255


def glass(img, x, y, w, h, r=60, frost=26, tint=0.06, refr=26):
    """Buzlu cam panel: arka planı bulanıklaştırır, kenarda kırar, parlak çerçeve ekler."""
    m = rounded_mask(w, h, r)
    d = cv2.distanceTransform((m > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    sub = img[y:y + h, x:x + w].copy()
    fro = G.blur(G.blur(img, frost)[y:y + h, x:x + w], 2)
    X, Y = G.grid(w, h)
    k = (1 - np.clip(d / 48, 0, 1)) ** 2
    dx, dy = (w / 2 - X) / (w / 2), (h / 2 - Y) / (h / 2)
    big = G.blur(img, frost)
    mx = (X + x + dx * k * refr).astype(np.float32)
    my = (Y + y + dy * k * refr).astype(np.float32)
    fro = cv2.remap(big, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    fro = fro * (1 + tint) + tint
    gx, gy = cv2.Sobel(m, cv2.CV_32F, 1, 0, ksize=5), cv2.Sobel(m, cv2.CV_32F, 0, 1, ksize=5)
    edge = np.exp(-((d - 1.5) / 1.6) ** 2)
    lightdir = np.clip((-gx - gy) / (np.hypot(gx, gy) + 1e-6), -1, 1)
    rim = edge * (0.35 + 0.45 * (0.5 + 0.5 * lightdir))
    spec = np.exp(-(((X + Y * 0.6) - w * 0.35) / (w * 0.08)) ** 2) * 0.05
    out = fro + (rim + spec)[..., None]
    shadowm = np.zeros(img.shape[:2], np.float32)
    shadowm[y:y + h, x:x + w] = m
    img = img * (1 - 0.45 * G.blur(np.roll(shadowm, 30, 0), 30))[..., None]
    G.over(img, out, m, x, y)
    return img


def glass_phone(img, x, y, w, h):
    img = glass(img, x, y, w, h, r=58, frost=18, tint=0.03)
    scr = np.zeros((h - 40, w - 40, 3), np.float32) + G.hexc("#071014")
    X, Y = G.grid(w - 40, h - 40)
    scr += np.exp(-((X - (w - 40) / 2) ** 2 + (Y - 300) ** 2) / (2 * 150 ** 2))[..., None] * G.hexc("#0F4D57") * 0.8
    G.over(img, scr, rounded_mask(w - 40, h - 40, 44) * 0.92, x + 20, y + 20)
    t1 = G.text_mask("BAKİYE", "Inter.ttf", 22, 600, tracking=4)
    G.over(img, np.ones(3, np.float32) * 0.7, t1, x + 50, y + 110)
    num = G.text_mask("₺250.000", "Montserrat.ttf", 54, 900)
    G.over(img, np.ones(3, np.float32), num, x + 48, y + 150)
    G.add(img, (G.blur(np.pad(num, 20), 10)[..., None] * G.YELLOW * 0.5).astype(np.float32), x + 28, y + 130)
    chip = rounded_mask(250, 58, 29)
    G.over(img, G.YELLOW, chip, x + 50, y + 260)
    ok = G.text_mask("✓ Kredi onaylandı", "Inter.ttf", 24, 700)
    G.over(img, G.hexc("#101010"), ok, x + 70, y + 276)
    for i in range(4):
        bar = rounded_mask(w - 120, 46, 14)
        G.over(img, np.ones(3, np.float32) * 0.1, bar * 0.8, x + 50, y + 380 + i * 66)
    return img


def aurora(seed=5):
    rng = np.random.default_rng(seed)
    img = G.canvas(G.hexc("#030406"))
    xx, yy = G.grid(G.W, G.H)
    for c, (px, py, s) in zip(["#0E5561", "#3B1F6E", "#8A5A06", "#0B2150", "#0E5561"],
                              [(250, 420, 420), (850, 700, 460), (700, 1500, 380), (200, 1250, 420), (900, 1800, 300)]):
        img += np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / (2 * s ** 2))[..., None] * G.hexc(c) * 0.7
    atlas = glyph_atlas(28)
    lay = np.zeros_like(img)
    for _ in range(160):
        c = RAMP[rng.integers(2, len(RAMP))]
        m = atlas[c]
        sc = rng.uniform(0.6, 2.4)
        m = cv2.resize(m, None, fx=sc, fy=sc)
        m = G.blur(m, rng.uniform(0, 4) * sc)
        G.add(lay, (m[..., None] * G.CYAN * rng.uniform(0.08, 0.35)).astype(np.float32),
              int(rng.uniform(0, G.W)), int(rng.uniform(0, G.H)))
    return img + lay


def frame_cam():
    img = aurora()
    img = glass(img, 80, 560, 920, 620, r=64)
    t1 = G.text_mask("HESAP BAKİYESİ", "Inter.ttf", 30, 600, tracking=5)
    G.over(img, np.ones(3, np.float32) * 0.72, t1, 150, 650)
    num = G.text_mask("₺250.000", "Montserrat.ttf", 150, 900)
    G.add(img, (G.blur(np.pad(num, 40), 26)[..., None] * G.YELLOW * 0.14).astype(np.float32), 110, 680)
    G.over(img, np.ones(3, np.float32), num, 150, 720)
    chip = rounded_mask(430, 86, 43)
    G.over(img, G.YELLOW, chip, 150, 960)
    ok = G.text_mask("✓  Kredi onaylandı", "Inter.ttf", 36, 700)
    G.over(img, G.hexc("#0C0C0C"), ok, 185, 985)
    now = G.text_mask("şimdi", "Inter.ttf", 30, 500)
    G.over(img, np.ones(3, np.float32) * 0.6, now, 820, 988)
    img = G.finish(img, seed=3, vig=0.5, bloom_thresh=0.9, bloom_k=0.25, exposure=0.9)
    label(img, "05  ·  DİJİTAL PARA", 70, 150, color=G.CYAN)
    return G.put_caption(img, "Hiçbir ~matbaaya / *UĞRAMAZ.", 880)


if __name__ == "__main__":
    note = B.banknote()
    frames = {"stil_1_kabartma": frame_kabartma(note), "stil_2_donusum": frame_donusum(note), "stil_3_cam": frame_cam()}
    for k, v in frames.items():
        cv2.imwrite(os.path.join(OUT, k + ".png"), cv2.cvtColor(G.to_u8(v), cv2.COLOR_RGB2BGR))
        print("yazıldı", k)
