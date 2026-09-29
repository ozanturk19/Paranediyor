"""Telefon filmi sahneleri 1-11: kanca → kripto.  İmza: f(p, t, d, wt, lt) -> (görüntü, post)."""
import math
import cv2
import numpy as np
from yardim import *                                          # noqa: F401,F403
from yardim import G, O, HM, _XX, _YY


def _w(wt, i, default):
    return wt[i] if len(wt) > i else default


def _bg_dark(glow=0.0, warm=(0.09, 0.055, 0.02), cool=(0.01, 0.03, 0.05), cy=820):
    """Doğrusal koyu stüdyo zemini: telefonun arkasında sıcak ışık, sağda soğuk ton."""
    r = np.hypot((_XX - 540) / 520, (_YY - cy) / 760)
    img = np.zeros((H, W, 3), np.float32) + np.array([0.0035, 0.004, 0.006], np.float32)
    img += (np.clip(1 - r, 0, 1) ** 2)[..., None] * np.asarray(warm, np.float32) * (0.35 + glow)
    r2 = np.hypot((_XX - 900) / 500, (_YY - 500) / 700)
    img += (np.clip(1 - r2, 0, 1) ** 2)[..., None] * np.asarray(cool, np.float32) * 0.6
    return img


_BGD = {}


def bg_dark(glow):
    key = round(glow, 2)
    if key not in _BGD:
        if len(_BGD) > 60:
            _BGD.clear()
        _BGD[key] = _bg_dark(glow)
    return _BGD[key].copy()


def _union_alpha(layers):
    a = np.zeros((H, W), np.float32)
    for _, _, la in layers:
        a = a + la * (1 - a)
    return a


def _sweep(img, a, t, t0, dur=0.9, k=0.55):
    """Telefonun üstünden çapraz bir ışık bandı geçer."""
    u = seg(t, t0, t0 + dur)
    if 0 < u < 1:
        x = lerp(150, 950, ease_io(u))
        band = np.exp(-(((_XX - x) + (_YY - 900) * 0.45) / 45) ** 2)
        img += (band * a)[..., None] * np.array([1.0, 0.92, 0.78], np.float32) * k * math.sin(math.pi * u)
    return img


def _leader(im, x0, y0, x1, y1, a, color=ONE):
    if a <= 0.01:
        return im
    O.poly(im, [[x0, y0], [x1, y1]], color * 0.8, 2, a)
    O.circle(im, x1, y1, 6, color, fill=True, alpha=a)
    return im


# ================================================================== 1) KANCA: telefon katmanları birleşir
FLY = {"arka": (-120.0, -160.0, -9.0), "kart": (-60.0, 110.0, 7.0), "govde": (90.0, -130.0, -6.0), "ekran": (170.0, 160.0, 8.0)}


def kanca_state(t, wt):
    tA, tT, tTk, tU = _w(wt, 0, 0.3), _w(wt, 2, 1.0), _w(wt, 3, 1.3), _w(wt, 5, 2.4)
    enter = ease_out(seg(t, -0.6, 1.0))
    lockA = ease_out(seg(t, tA - 0.05, tA + 0.5))
    lockG = ease_out(seg(t, tT - 0.05, tT + 0.45))
    lockE = spring(seg(t, tU - 0.14, tU + 0.55), 1.3, 6)
    drift = 0.06 * math.sin(t * 1.7)
    ex = {"arka": (1 - lockA) * (1 + drift), "kart": (1 - lockA) * (1 - drift), "govde": (1 - lockG) * (1 + drift),
          "ekran": (1 - lockE) * (1 - drift)}
    fly = {k: (v[0] * (1 - enter), v[1] * (1 - enter), v[2] * (1 - enter) * (1 - lockE)) for k, v in FLY.items()}
    flick = 1.0 if (t - tTk) > 0.25 else (0.6 if int(t * 40) % 3 else 0.15)
    ui = seg(t, tTk - 0.1, tTk + 0.3) * flick if t > tTk - 0.1 else 0.0
    return ex, fly, ui, (tA, tT, tTk, tU), lockE


def kanca(p, t, d, wt, lt):
    ex, fly, ui, (tA, tT, tTk, tU), lockE = kanca_state(t, wt)
    hm = meta("hero")
    cx, cy = hm["center"][:2]
    hx, hy = hand(t, 3, 1)
    sdx, sdy = O.shake(t, tU, 14)
    M = affine(0.9 + 0.08 * ease_io(p), (cx, cy), hx + sdx, hy + sdy)
    layers = hero_layers(ex, ui, M, fly)
    img = bg_dark(0.25 + 0.75 * max(0.0, min(1.0, lockE)))
    img = draw_dust(img, t, np.array([0.05, 0.035, 0.02], np.float32), 1.0, 140, 3)
    img = hero_over(img, layers)
    img = _sweep(img, _union_alpha(layers), t, tU + 0.05)
    if tU - 0.05 <= t <= tU + 0.5:
        kb = math.exp(-max(0.0, t - tU) * 7) * seg(t, tU - 0.05, tU)
        burst = np.exp(-(((_XX - cx) / 330) ** 2 + ((_YY - cy) / 520) ** 2))
        img = img + burst[..., None] * np.array([0.5, 0.33, 0.14], np.float32) * kb

    def post(im):
        O.label(im, "ASELSAN  ·  TÜRK TELEKOM", color=GOLD, alpha=seg(t, 0.1, 0.5))
        k1 = ease_out(seg(t, tA, tA + 0.35))
        if k1 > 0:
            chip(im, "DONANIM · ÜRETİM", 70, 340, YELLOW, k1, 26)
            O.text(im, "ASELSAN", 70, 395, 30, "Montserrat.ttf", 900, ONE, "lm", alpha=k1, tracking=4)
            kx, ky = app((cx - 40, cy - 250), M)
            _leader(im, 250, 420, kx, ky, k1 * (1 - seg(t, tU, tU + 0.3)))
        k2 = ease_out(seg(t, tTk, tTk + 0.35))
        if k2 > 0:
            chip(im, "YAZILIM · PAZARLAMA", 1010, 340, CYAN, k2, 26, anchor="rm")
            O.text(im, "TÜRK TELEKOM", 1010, 395, 30, "Montserrat.ttf", 900, ONE, "rm", alpha=k2, tracking=4)
            sx, sy = app((cx + 120, cy - 300), M)
            _leader(im, 850, 420, sx, sy, k2 * (1 - seg(t, tU, tU + 0.3)))
        return im
    return img, post


# ================================================================== 2) SATIŞ: fiyat etiketi 2027
def _tag_draw(t, t_year, t_stamp):
    tw, th = 330, 470

    def draw(col, a):
        x0, y0 = 540 - tw // 2, 190
        m = O.rounded(tw, th, 26)
        ys = np.linspace(0, 1, th, dtype=np.float32)[:, None, None]
        paper = np.ones((th, tw, 3), np.float32) * np.array([0.93, 0.9, 0.84], np.float32) * (1 - 0.08 * ys)
        G.over(col, paper, m, x0, y0)
        a[y0:y0 + th, x0:x0 + tw] = np.maximum(a[y0:y0 + th, x0:x0 + tw], m)
        O.circle(col, 540, y0 + 38, 14, np.array([0.12, 0.12, 0.12], np.float32), fill=True)
        O.circle(col, 540, y0 + 38, 20, np.array([0.7, 0.62, 0.35], np.float32), thick=4)
        O.text(col, "SATIŞA ÇIKIŞ", 540, y0 + 100, 26, "Inter.ttf", 700, DARK * 1.2, tracking=5)
        # yıl: son hane kayarak 2024 -> 2027
        u = ease_out(seg(t, t_year - 0.55, t_year + 0.15))
        v = 4 + 3 * u
        wf = text_w("2027", 118, wght=900)
        w202 = text_w("202", 118, wght=900)
        wd = text_w("7", 118, wght=900)
        xl = 540 - wf / 2
        O.text(col, "202", xl, y0 + 205, 118, "Montserrat.ttf", 900, DARK, "lm")
        dx = xl + w202 + wd / 2 - 8
        top_d, frac = int(v), v - int(v)
        for dd, off in ((top_d, -frac), (min(9, top_d + 1), 1 - frac)):
            yy = y0 + 205 + off * 120
            if abs(off) < 1:
                m2 = G.text_mask(str(dd), "Montserrat.ttf", 118, 900)
                clip = np.zeros_like(m2)
                hh = m2.shape[0]
                oy = int(yy - hh / 2)
                for r in range(hh):
                    if y0 + 140 <= oy + r <= y0 + 270:
                        clip[r] = m2[r]
                G.over(col, DARK, clip, int(dx - m2.shape[1] / 2), oy)
        O.text(col, "İLK YARI", 540, y0 + 300, 34, "Montserrat.ttf", 800, np.array([0.55, 0.42, 0.12], np.float32),
               tracking=8)
        return col, a
    return draw, tw, th


def satis(p, t, d, wt, lt):
    t_year = _w(wt, 0, 0.3)
    t_stamp = _w(wt, 1, 1.0)
    hm = meta("hero")
    cx, cy = hm["center"][:2]
    hx, hy = hand(t + 4.1, 3, 1)
    M = affine(0.98 + 0.04 * ease_io(p), (cx, cy), hx, hy + 40 * ease_io(p))
    img = bg_dark(1.0)
    img = draw_dust(img, t + 4.1, np.array([0.05, 0.035, 0.02], np.float32), 1.0, 140, 3)
    img = hero_over(img, hero_layers(None, 1.0, M))
    img = G.blur(img, 4.0 * ease_out(seg(t, 0.0, 0.5)))                   # odak etikete kayar

    def post(im):
        O.label(im, "TAKVİM", color=GOLD, alpha=seg(t, 0.05, 0.3))
        drop = ease_out(seg(t, 0.0, 0.45))
        ang = 16 * math.exp(-3.2 * t) * math.cos(7.5 * t) * drop
        draw, tw, th = _tag_draw(t, t_year, t_stamp)
        yoff = -520 * (1 - drop)
        col = np.zeros((H, W, 3), np.float32)
        a = np.zeros((H, W), np.float32)
        draw(col, a)
        M2 = cv2.getRotationMatrix2D((540.0, 120.0), ang, 1.0)
        M2[1, 2] += yoff
        colw, aw = warp(col, M2), warp(a, M2)
        sh = G.blur(np.roll(np.roll(aw, 30, 0), 18, 1), 22) * 0.6
        im *= (1 - sh[..., None])
        im[:] = im * (1 - aw[..., None]) + colw * aw[..., None]
        hole = app((540, 228), M2)
        O.poly(im, [[540, 0], [hole[0], hole[1]]], np.array([0.75, 0.68, 0.5], np.float32), 3, drop)
        ks = seg(t, t_stamp - 0.04, t_stamp + 0.12)
        if ks > 0:
            sc = lerp(1.9, 1.0, ease_out(ks))
            sx, sy = app((540, 590), M2)
            stamp = np.zeros((H, W, 3), np.float32)
            wv = int(360 * sc)
            hv = int(110 * sc)
            b_ = max(2, int(7 * sc))
            ring = O.rounded(wv, hv, int(18 * sc)) - np.pad(O.rounded(wv - 2 * b_, hv - 2 * b_, int(12 * sc)), b_)
            G.over(stamp, RED, np.clip(ring, 0, 1), int(sx - wv / 2), int(sy - hv / 2))
            O.text(stamp, "SATIŞTA", sx, sy + 2, int(72 * sc), "Montserrat.ttf", 900, RED, tracking=8 * sc)
            m = (stamp.max(2) > 0.02).astype(np.float32)
            rng = np.random.default_rng(3)
            grit = (G.blur(rng.random((H, W)).astype(np.float32), 1.2) > 0.36).astype(np.float32)
            m *= grit * min(1, ks * 3)
            R_ = cv2.getRotationMatrix2D((float(sx), float(sy)), 9, 1.0)
            m = warp(m, R_) * 0.92
            im[:] = im * (1 - m[..., None]) + RED * m[..., None]
        return im
    return img, post


# ================================================================== 3) VESTEL: geri sarma, 2016, çatlayan ekran
def vhs(im, k, t, seed=0):
    """VHS geri sarma görünümü (k: 0..1 yoğunluk)."""
    if k <= 0.01:
        return im
    rng = np.random.default_rng(seed)
    out = im.copy()
    for _ in range(int(3 + 10 * k)):
        y0, h = int(rng.integers(0, H - 30)), int(rng.integers(4, 60))
        out[y0:y0 + h] = np.roll(out[y0:y0 + h], int(rng.integers(-40, 40) * k), axis=1)
    sh = int(10 * k)
    if sh:
        out[..., 0] = np.roll(out[..., 0], sh, axis=1)
        out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    ty = int((t * 900) % (H + 200)) - 100
    band = np.exp(-((_YY - ty) / 26) ** 2)[..., None]
    noise = rng.random((H // 4, W // 4)).astype(np.float32)
    noise = cv2.resize(noise, (W, H), interpolation=cv2.INTER_NEAREST)[..., None]
    out = out * (1 - 0.6 * band * k) + noise * band * 0.9 * k
    out[::2] *= 1 - 0.18 * k
    lum = out.mean(2, keepdims=True)
    out = lum + (out - lum) * (1 - 0.45 * k)
    return out


def _tri(im, x, y, s, color, a, left=True):
    d = -1 if left else 1
    pts = np.array([[x, y - s], [x, y + s], [x + d * s * 1.3, y]], np.float32)
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [np.round(pts * 4).astype(np.int32)], 255, cv2.LINE_AA, shift=2)
    G.over(im, np.asarray(color, np.float32), m.astype(np.float32) / 255 * a)


def osd_rewind(im, year, a):
    """VHS ekran yazısı: ◀◀ ve yıl."""
    if a <= 0.01:
        return im
    _tri(im, 110, 340, 20, ONE, a, True)
    _tri(im, 140, 340, 20, ONE, a, True)
    O.text(im, "GERİ", 160, 340, 34, G.MONO, None, ONE, "lm", alpha=a)
    O.text(im, str(year), 540, 560, 190, G.MONO, None, ONE, alpha=a, glow=0.2)
    return im


_CRACK = None


def crack_lines():
    global _CRACK
    if _CRACK is None:
        rng = np.random.default_rng(11)
        lines = []
        c = np.array([0.62, 0.33])
        for k in range(14):
            ang = rng.uniform(0, 2 * math.pi)
            p = c.copy()
            pts = [p.copy()]
            L = rng.uniform(0.35, 0.9)
            n = 9
            for i in range(n):
                ang += rng.normal(0, 0.35)
                p = p + np.array([math.cos(ang), math.sin(ang) * 0.56]) * L / n
                pts.append(p.copy())
            lines.append(np.array(pts))
        for r in (0.05, 0.1):                                  # darbe noktası çevresinde kırık halkalar
            th = np.linspace(0, 2 * math.pi, 30)
            ring = c + np.stack([np.cos(th) * r, np.sin(th) * r * 0.56], 1) * (1 + 0.15 * rng.random(30)[:, None])
            for i in range(0, 30, 3):
                lines.append(ring[i:i + 3])
        _CRACK = lines
    return _CRACK


def quad_map(q, uv):
    """(u,v) ∈ [0,1]² -> dörtgen içindeki nokta (bilinear); q: TL, TR, BR, BL."""
    q = np.asarray(q, np.float32)[:, :2]
    u, v = uv[..., 0:1], uv[..., 1:2]
    top = q[0] + (q[1] - q[0]) * u
    bot = q[3] + (q[2] - q[3]) * u
    return top + (bot - top) * v


def eski_view(t, p, z0, z1, c=(533, 958), amp=2.5, seed=2):
    pl = plate("eski")
    hx, hy = hand(t, amp, seed)
    s = z0 + (z1 - z0) * ease_io(p)
    img, _ = push(pl["rgb"], pl["depth"], 1.0, s, s, c=c, dx=hx, dy=hy)
    q = [zoom_pt(pt[:2], s, c, hx, hy) for pt in meta("eski")["screen_corners"]]
    return img, q


def vestel(p, t, d, wt, lt):
    t_bir = _w(wt, 3, 0.9)
    t_v = _w(wt, 6, 2.2)
    t_o = _w(wt, 9, 3.2)
    img, q = eski_view(t, p, 1.0, 1.14)
    rew = 1 - seg(t, t_bir - 0.35, t_bir)
    grade = np.array([1.08, 0.98, 0.84], np.float32)
    img = img * grade
    k_c = seg(t, t_o - 0.02, t_o + 0.1)
    if k_c > 0:
        img = img * (1 - 0.1 * k_c)
    sdx, sdy = O.shake(t, t_o, 16)
    if sdx or sdy:
        img = O.camera(img, 1.0, dx=sdx, dy=sdy)
        q = [(x + sdx, y + sdy) for x, y in q]
    if t_o <= t <= t_o + 0.14:
        img = img + 0.35 * (1 - (t - t_o) / 0.14)

    def post(im):
        im = vhs(im, rew, t, int(abs(t) * 30))
        yr = int(round(lerp(2027, 2016, ease_io(seg(t, 0.0, t_bir - 0.2)))))
        osd_rewind(im, yr, rew)
        O.label(im, "2016", color=WARM, alpha=seg(t, t_bir - 0.3, t_bir) )
        k = ease_out(seg(t, t_v - 0.1, t_v + 0.3))
        if k > 0:
            chip(im, "VESTEL VENÜS", 1010, 360, ONE * 0.92, k, 30, anchor="rm")
            O.text(im, "2014'te piyasaya çıktı", 1010, 425, 34, SERIF, None, ONE, "rm", alpha=k)
        if k_c > 0:
            glow = np.zeros_like(im)
            for ln in crack_lines():
                pts = quad_map(q, ln)
                n = max(2, int(len(pts) * min(1, k_c * 1.3)))
                O.poly(im, pts[:n], ONE * 0.92, 2, 0.85)
                O.poly(glow, pts[:n], ONE, 5, 0.5)
            im += G.blur(glow, 3) * 0.35
        return im
    return img, post


# ================================================================== 4) SORU: harf tabelası
def soru(p, t, d, wt, lt):
    img = O.NIGHT.copy()
    rows = ["BU SEFER", "FARKLI", "OLAN NE?"]
    colors = [[ONE] * 8, [YELLOW] * 6, [ONE] * 8]
    img = flap_board(img, rows, t, 0.28, y0=600, colors=colors)
    img = O.camera(img, 1.0 + 0.05 * ease_io(p))
    return img, None


# ================================================================== 5) YÜZDE 7: 100 telefonun 7'si
HL7 = [13, 26, 38, 47, 61, 74, 88]
_Q7 = None


def _grid_M():
    global _Q7
    if _Q7 is None:
        src = np.float32([[120, 380], [960, 380], [960, 1300], [120, 1300]])
        dst = np.float32([[250, 545], [830, 545], [1010, 1290], [70, 1290]])
        _Q7 = cv2.getPerspectiveTransform(src, dst)
    return _Q7


def yuzde7(p, t, d, wt, lt):
    t_sat = _w(wt, 2, 1.2)
    t_100 = _w(wt, 3, 1.6)
    t_7 = _w(wt, 5, 2.6)
    img = O.COOL.copy() * 0.7
    layer = np.zeros((H, W, 3), np.float32)
    la = np.zeros((H, W), np.float32)
    cw, ch = 84, 92
    dim = seg(t, t_7, t_7 + 0.3)
    for i in range(100):
        r, c = divmod(i, 10)
        k = ease_out(seg(t, 0.05 + r * 0.1 + c * 0.012, 0.3 + r * 0.1 + c * 0.012))
        if k <= 0:
            continue
        x = 120 + c * cw + cw / 2
        y = 380 + r * ch + ch / 2 - 30 * (1 - k)
        hl = i in HL7
        fl = seg(t, t_7 + HL7.index(i) * 0.05, t_7 + 0.25 + HL7.index(i) * 0.05) if hl else 0.0
        wscale = abs(math.cos(math.pi * fl)) if 0 < fl < 1 else 1.0
        on = hl and fl >= 0.5
        pw, ph = 46 * wscale, 76
        if pw < 2:
            continue
        col = YELLOW if on else ONE * (0.8 - 0.45 * dim)
        fillc = YELLOW * 0.9 if on else ONE * 0.08
        O.rect_fill(layer, x - pw / 2, y - ph / 2, pw, ph, fillc, k, r=int(min(pw, 46) * 0.2))
        phone_icon(layer, x, y, pw, ph, col, k, thick=3)
        O.rect_fill(layer, x - 5, y + ph / 2 - 9, 10, 3, col * 0.8, k)
        m = O.rounded(int(pw) + 8, ph + 8, 12) * k
        x0_, y0_ = int(x - pw / 2 - 4), int(y - ph / 2 - 4)
        la[y0_:y0_ + m.shape[0], x0_:x0_ + m.shape[1]] = np.maximum(la[y0_:y0_ + m.shape[0], x0_:x0_ + m.shape[1]], m)
    Mq = _grid_M()
    lw = cv2.warpPerspective(layer, Mq, (W, H), flags=cv2.INTER_LINEAR)
    aw = cv2.warpPerspective(la, Mq, (W, H), flags=cv2.INTER_LINEAR)
    if dim > 0:
        glow = G.blur(lw * (lw[..., 0:1] > lw[..., 2:3] + 0.2), 14)
        lw = lw + glow * 0.8 * dim
    img = img * (1 - 0.6 * aw[..., None]) + lw
    img = O.camera(img, 1.0 + 0.05 * ease_io(p), cy=900)

    def post(im):
        O.label(im, "2016  ·  TÜRKİYE PAZARI", color=GOLD, alpha=seg(t, 0.1, 0.4))
        k0 = ease_out(seg(t, t_100 - 0.2, t_100 + 0.2))
        O.text(im, "HER 100 TELEFONDAN", 540, 310, 36, "Montserrat.ttf", 800, ONE * 0.9, alpha=k0 * (1 - dim * 0.3),
               tracking=6)
        k7 = seg(t, t_7 - 0.05, t_7 + 0.45)
        if k7 > 0:
            v = int(round(7 * ease_out(k7)))
            sc = lerp(1.35, 1.0, ease_out(seg(t, t_7 - 0.05, t_7 + 0.25)))
            O.text(im, f"%{v}", 540, 405, 120, "Montserrat.ttf", 900, YELLOW, alpha=min(1, k7 * 3), scale=sc, glow=0.35)
            O.text(im, "VESTEL VENÜS", 540, 490, 30, "Inter.ttf", 700, ONE, alpha=seg(t, t_7 + 0.3, t_7 + 0.6),
                   tracking=6)
        return im
    return img, post


# ================================================================== 6) SATAMAMAK: üstü çizilen kelime
def _receipts(t):
    img = np.zeros((H, W, 3), np.float32)
    rng = np.random.default_rng(21)
    for i in range(7):
        x = 60 + i * 150 + rng.uniform(-20, 20)
        sp = rng.uniform(60, 120)
        off = (t * sp + rng.uniform(0, 400)) % 140
        O.rect_fill(img, x, 0, 110, H, ONE * 0.9, 0.06)
        for j in range(-1, 15):
            y = j * 140 + off
            for k in range(4):
                O.rect_fill(img, x + 12, y + k * 22, rng.uniform(40, 86), 7, ONE, 0.10)
    return G.blur(img, 6)


def satamamak(p, t, d, wt, lt):
    t_s = _w(wt, 1, 0.5)
    t_d = _w(wt, 2, 1.2)
    img = O.NIGHT.copy() + _receipts(t)
    img = O.camera(img, 1.0 + 0.04 * ease_io(p))

    def post(im):
        k0 = ease_out(seg(t, 0.0, 0.3))
        O.text(im, "SORUN", 540, 640, 42, "Inter.ttf", 700, ONE * 0.85, alpha=k0, tracking=14)
        k1 = ease_out(seg(t, t_s - 0.12, t_s + 0.2))
        sl = ease_out(seg(t, t_d - 0.08, t_d + 0.12))
        sc = lerp(1.12, 1.0, k1)
        dx, dy = O.shake(t, t_d + 0.05, 12)
        O.text(im, "SATAMAMAK", 540 + dx, 790 + dy, 128, "Montserrat.ttf", 900, ONE * (1 - 0.55 * sl), alpha=k1, scale=sc)
        if sl > 0:
            x1 = lerp(80, 1000, sl)
            y1 = lerp(812, 768, sl)
            O.poly(im, [[80 + dx, 812 + dy], [x1 + dx, y1 + dy]], RED, 14, 1.0, glow=0.9)
        k2 = ease_out(seg(t, t_d + 0.05, t_d + 0.35))
        O.text(im, "değildi.", 540, 945, 96, SERIF, None, YELLOW, alpha=k2)
        return im
    return img, post


# ================================================================== 7) HATA: hata pencereleri, yavaşlık
_HOME = None


def home_tex():
    global _HOME
    if _HOME is None:
        im = cv2.cvtColor(cv2.imread(os.path.join(PLAKA, "eski_ekran.png")), cv2.COLOR_BGR2RGB)
        _HOME = im.astype(np.float32) / 255
    return _HOME


DIALOGS = ["Uygulama yanıt vermiyor", "Sistem hatası", "Beklenmeyen bir hata", "İşlem durduruldu",
           "Uygulama yanıt vermiyor", "Bellek yetersiz"]


def _dialog(tex, x, y, title, a):
    w, h = 470, 230
    O.rect_fill(tex, x + 8, y + 12, w, h, np.zeros(3, np.float32), 0.45 * a, r=14)
    O.rect_fill(tex, x, y, w, h, np.array([0.93, 0.93, 0.94], np.float32), a, r=14)
    O.circle(tex, x + 44, y + 58, 20, RED, fill=True, alpha=a)
    O.text(tex, "!", x + 44, y + 58, 30, "Montserrat.ttf", 900, ONE, alpha=a)
    O.text(tex, title, x + 80, y + 58, 27, "Inter.ttf", 700, DARK, "lm", alpha=a)
    O.text(tex, "Kapatılsın mı?", x + 80, y + 100, 24, "Inter.ttf", 500, DARK * 3, "lm", alpha=a)
    O.text(tex, "BEKLE", x + w - 210, y + h - 45, 26, "Inter.ttf", 700, np.array([0.1, 0.45, 0.8], np.float32), alpha=a)
    O.text(tex, "KAPAT", x + w - 80, y + h - 45, 26, "Inter.ttf", 700, np.array([0.1, 0.45, 0.8], np.float32), alpha=a)


def hata_ui(t, wt):
    t_y = _w(wt, 1, 0.4)
    t_v = _w(wt, 4, 2.2)
    t_c = _w(wt, 6, 3.6)
    tex = home_tex().copy()
    th, tw = tex.shape[:2]
    # hata pencereleri çağlayanı
    fade = 1 - seg(t, t_v - 0.1, t_v + 0.15)
    for i, title in enumerate(DIALOGS):
        ti = t_y - 0.05 + i * 0.22
        k = ease_out(seg(t, ti, ti + 0.1)) * fade
        if k > 0:
            _dialog(tex, 40 + i * 14, 180 + i * 90, title, k)
    last = max([t_y - 0.05 + i * 0.22 for i in range(len(DIALOGS))])
    glitch = any(0 <= t - (t_y - 0.05 + i * 0.22) < 0.07 for i in range(len(DIALOGS)))
    # yavaşlık: ağır dönen halka + takılı ilerleme çubuğu
    kv = seg(t, t_v - 0.1, t_v + 0.2)
    if kv > 0:
        tex = tex * (1 - 0.72 * kv)
        tt = max(0.0, t - t_v)
        step = int(tt * 5) / 5 if t > t_c else tt                  # donunca kare kare takılır
        ang = 2 * math.pi * (step ** 0.55) * 0.9
        cx, cy = tw / 2, th * 0.42
        O.arc(tex, cx, cy, 90, 0, 2 * math.pi, ONE * 0.25, 12, kv)
        O.arc(tex, cx, cy, 90, ang, ang + 1.6, ONE, 12, kv)
        O.text(tex, "Yükleniyor…", cx, cy + 170, 36, "Inter.ttf", 600, ONE * 0.9, alpha=kv)
        O.rect_fill(tex, 90, cy + 230, tw - 180, 16, ONE * 0.2, kv, r=8)
        O.rect_fill(tex, 90, cy + 230, (tw - 180) * 0.12, 16, CYAN, kv, r=8)
        O.text(tex, "%12", tw - 90, cy + 275, 30, "Inter.ttf", 700, ONE * 0.8, "rm", alpha=kv)
    kw = seg(t, t_c - 0.05, t_c + 0.25)
    if kw > 0:                                                   # ciddi sıkıntı: ekran donar, uyarı belirir
        tex = tex * (1 - 0.55 * kw)
        cx, cy = tw / 2, th * 0.42
        pulse = 0.75 + 0.25 * math.sin((t - t_c) * 9)
        tri = np.array([[cx, cy - 150], [cx - 170, cy + 140], [cx + 170, cy + 140]], np.float32)
        mm = np.zeros(tex.shape[:2], np.uint8)
        cv2.fillPoly(mm, [np.round(tri * 4).astype(np.int32)], 255, cv2.LINE_AA, shift=2)
        G.over(tex, RED * pulse, mm.astype(np.float32) / 255 * kw)
        O.text(tex, "!", cx, cy + 40, 190, "Montserrat.ttf", 900, ONE, alpha=kw)
        O.text(tex, "Telefon yanıt vermiyor", cx, cy + 250, 40, "Inter.ttf", 700, ONE, alpha=kw)
    if t > t_c and int(t * 7) % 3 == 0:                           # donma: ekran titrer
        tex = np.roll(tex, 6, axis=1)
    return tex, glitch


def hata(p, t, d, wt, lt):
    t_c = _w(wt, 6, 3.6)
    img, q = eski_view(t, p, 2.0, 2.45, amp=2.0, seed=4)
    kz_ = ease_out(seg(t, t_c - 0.05, t_c + 0.5))
    if kz_ > 0:                                                  # uyarıyla birlikte ekrana ek itme
        s_ = 1 + 0.14 * kz_
        img = O.camera(img, s_, 533, 958)
        q = [(533 + (x - 533) * s_, 958 + (y - 958) * s_) for x, y in q]
    tex, glitch = hata_ui(t, wt)
    lin = np.power(np.clip(tex, 0, 1), 2.2) * 0.9
    O.place(img, lin, np.float32([pt for pt in q]), shadow=0)
    if t > t_c:
        img = img * (1 - 0.15 * seg(t, t_c, t_c + 0.8))

    def post(im):
        O.label(im, "VESTEL VENÜS", color=WARM, alpha=seg(t, 0.1, 0.4))
        k = ease_out(seg(t, _w(wt, 1, 0.4) - 0.1, _w(wt, 1, 0.4) + 0.25))
        chip(im, "KULLANICI ŞİKAYETLERİ", 70, 330, RED, k, 28, dark=False)
        if glitch:
            im[..., 0] = np.roll(im[..., 0], 8, axis=1)
            im[..., 2] = np.roll(im[..., 2], -8, axis=1)
        return im
    return img, post


# ================================================================== 8) ÇEKİLME: zarar, telefon toza dönüşür
_OLD = None


def old_sprite():
    """Eski telefonu plakadan kes (nesne no > 0), dik çevir. (renk, alfa, parçacıklar)"""
    global _OLD
    if _OLD is None:
        pl = plate("eski")
        m = (pl["index"] > 0.5).astype(np.float32)
        m = cv2.erode(m, np.ones((3, 3), np.uint8))
        m = G.blur(m, 1.0)
        R_ = cv2.getRotationMatrix2D((533.0, 958.0), -14, 1.25)
        R_[:, 2] += (540 - 533, 930 - 958)
        rgb = warp(pl["rgb"] * m[..., None], R_)
        a = warp(m, R_)
        ys, xs = np.nonzero(a > 0.5)
        rng = np.random.default_rng(5)
        idx = rng.choice(len(xs), 9000, replace=False)
        pts = np.stack([xs[idx], ys[idx]], 1).astype(np.float32)
        cols = rgb[ys[idx], xs[idx]] / np.maximum(a[ys[idx], xs[idx]], 0.05)[:, None]
        _OLD = (rgb, a, pts, cols, xs.min(), xs.max(), rng.random((9000, 4)).astype(np.float32))
    return _OLD


def cekilme(p, t, d, wt, lt):
    t_z = _w(wt, 1, 0.5)
    t_p = _w(wt, 5, 2.8)
    t_c = _w(wt, 6, 3.3)
    rgb, a, pts, cols, xmin, xmax, rnd = old_sprite()
    img = _bg_dark(0.4, warm=(0.07, 0.04, 0.02))
    img = draw_dust(img, t, np.array([0.04, 0.03, 0.02], np.float32), 0.8, 120, 8)
    hx, hy = hand(t, 3, 5)
    s0 = t_p - 0.1
    sweep = lerp(xmin - 30, xmax + 60, ease_in(seg(t, s0, s0 + 1.1)))
    keep = np.clip((_XX - sweep) / 20, 0, 1)
    M = affine(1.0 + 0.1 * ease_io(p), (540, 930), hx, hy + 20, 3.0 * math.sin(t * 0.9))
    r2, a2 = warp(rgb, M) * keep[..., None], warp(a, M) * keep
    img = over_pm(img, r2, a2)
    edge = np.exp(-((_XX - sweep) / 10) ** 2) * warp(a, M)
    img += edge[..., None] * np.array([1.0, 0.55, 0.2], np.float32) * 0.8
    if t > s0:
        px = (pts @ M[:, :2].T + M[:, 2]).astype(np.float32)
        ti = s0 + (px[:, 0] - xmin) / max(1, xmax - xmin) * 1.1 * 0.95 + rnd[:, 0] * 0.08
        dt = np.maximum(0, t - ti)
        live = (dt > 0) & (dt < 2.2)
        v = np.stack([160 + rnd[:, 1] * 260, -40 - rnd[:, 2] * 160], 1)
        turb = np.stack([np.sin(dt * 3 + rnd[:, 3] * 6) * 18, np.cos(dt * 2.3 + rnd[:, 0] * 6) * 14], 1)
        pos = px + v * dt[:, None] + np.array([90, -30]) * (dt ** 2)[:, None] + turb * dt[:, None]
        fadek = np.clip(1 - dt / 2.2, 0, 1) ** 1.5
        c_ = (cols * 1.3 + np.array([0.25, 0.12, 0.04])) * (fadek * live)[:, None]
        glow = splat(np.zeros_like(img), pos[live], c_[live].astype(np.float32), 2)
        img = img + glow * 0.8 + G.blur(glow, 3) * 0.8

    def post(im):
        O.label(im, "VESTEL  ·  ZARAR", color=WARM, alpha=seg(t, 0.1, 0.4))
        kp = ease_out(seg(t, 0.0, 0.35)) * (1 - seg(t, t_c, t_c + 0.4))
        if kp > 0.01:
            O.glass(im, 110, 280, 860, 300, r=40, frost=16, tint=0.05, alpha=kp)
            O.rect_fill(im, 110, 280, 860, 300, np.zeros(3, np.float32), 0.35 * kp, r=40)
            base_x, full = 330, 580
            u1 = ease_out(seg(t, 0.1, 0.6))
            u2 = ease_out(seg(t, t_z - 0.3, t_z + 0.4))
            O.text(im, "FİYAT", 160, 375, 30, "Montserrat.ttf", 800, ONE, "lm", alpha=kp, tracking=3)
            O.rect_fill(im, base_x, 358, full * 0.62 * u1, 36, ONE * 0.85, kp, r=18)
            O.text(im, "MALİYET", 160, 475, 30, "Montserrat.ttf", 800, ONE, "lm", alpha=kp, tracking=3)
            O.rect_fill(im, base_x, 458, full * 0.88 * u2, 36, RED, kp, r=18)
            kz = seg(t, t_z + 0.1, t_z + 0.35)
            if kz > 0:
                x0, x1 = base_x + full * 0.62, base_x + full * 0.88
                O.poly(im, [[x0, 350], [x0, 505]], ONE * 0.9, 3, kz * kp)
                O.poly(im, [[x1, 440], [x1, 505]], ONE * 0.9, 3, kz * kp)
                pz = 0.5 + 0.5 * math.sin((t - t_z) * 7)
                O.rect_fill(im, x0, 458, x1 - x0, 36, ONE, 0.25 * pz * kz * kp, r=10)
                chip(im, "ZARAR", (x0 + x1) / 2, 540, RED, kz * kp, 28, dark=False, anchor="mm")
        kc = ease_out(seg(t, t_c, t_c + 0.3))
        chip(im, "SON MODELLER · 2019", 540, 1230, ONE * 0.9, kc, 28, anchor="mm")
        return im
    return img, post


# ================================================================== 9) STRATEJİ: taktik tahtası
def _dashed(im, pts, color, th, a, dash=18, gap=12):
    seglen = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seglen)])
    L = cum[-1]
    s = 0.0
    while s < L:
        e = min(L, s + dash)
        idx = (cum >= s) & (cum <= e)
        sub = pts[idx]
        if len(sub) >= 2:
            O.poly(im, sub, color, th, a)
        s += dash + gap


def strateji(p, t, d, wt, lt):
    t_f = _w(wt, 1, 0.7)
    img = np.zeros((H, W, 3), np.float32) + G.hexc("#0A0D10")
    img = O.grid_lines(img, 60, 0.035, ONE)
    img = O.camera(img, 1.0 + 0.03 * ease_io(p))
    start = np.array([210.0, 1060.0])
    wall_x = 640

    def post(im):
        O.label(im, "PLAN", color=GOLD, alpha=seg(t, 0.05, 0.3))
        O.circle(im, *start, 22, ONE * 0.8, 4, 1.0)
        O.rect_fill(im, wall_x - 9, 600, 18, 360, ONE * 0.75, ease_out(seg(t, 0.0, 0.2)), r=6)
        u = ease_out(seg(t, 0.05, 0.45))
        old = np.stack([np.linspace(start[0], wall_x - 30, 40), np.linspace(start[1], 800, 40)], 1)
        n = max(2, int(40 * u))
        _dashed(im, old[:n], ONE * 0.5, 5, 1.0)
        kx = seg(t, 0.42, 0.55)
        if kx > 0:
            c = old[-1]
            s = 26 * spring(kx, 1.5, 6)
            O.poly(im, [[c[0] - s, c[1] - s], [c[0] + s, c[1] + s]], RED, 8, 1.0, glow=0.6)
            O.poly(im, [[c[0] + s, c[1] - s], [c[0] - s, c[1] + s]], RED, 8, 1.0, glow=0.6)
        un = ease_io(seg(t, t_f - 0.18, t_f + 0.35))
        if un > 0:
            tt = np.linspace(0, 1, 70)[:, None]
            p0, p1, p2, p3 = start, np.array([520.0, 1180.0]), np.array([900.0, 1080.0]), np.array([860.0, 560.0])
            bez = (1 - tt) ** 3 * p0 + 3 * (1 - tt) ** 2 * tt * p1 + 3 * (1 - tt) * tt ** 2 * p2 + tt ** 3 * p3
            n = max(2, int(70 * un))
            O.poly(im, bez[:n], YELLOW, 8, 1.0, glow=0.8)
            h = bez[n - 1]
            O.circle(im, h[0], h[1], 10, YELLOW, fill=True, alpha=1.0)
            kt = seg(un, 0.85, 1.0)
            pulse = (t * 2) % 1
            O.circle(im, *p3, 30, YELLOW, 4, kt)
            O.circle(im, *p3, 30 + 40 * pulse, YELLOW, 3, kt * (1 - pulse))
        O.text(im, "STRATEJİ", 540, 350, 86, "Montserrat.ttf", 900, ONE, alpha=ease_out(seg(t, 0.0, 0.25)), tracking=8)
        kf = seg(t, t_f - 0.05, t_f + 0.2)
        if kf > 0:
            dx, dy = O.shake(t, t_f + 0.05, 10)
            O.text(im, "FARKLI.", 540 + dx, 470 + dy, 120, "Montserrat.ttf", 900, YELLOW, alpha=min(1, kf * 3),
                   scale=lerp(1.4, 1.0, ease_out(kf)), glow=0.3)
        return im
    return img, post


# ================================================================== 10) GARANTİ: mühür + 3 model, biri kamuya özel
def seal(im, cx, cy, s, a, rot):
    if a <= 0.01:
        return im
    O.circle(im, cx, cy, 230 * s, YELLOW, max(2, int(6 * s)), a, glow=0.4)
    O.circle(im, cx, cy, 170 * s, YELLOW, max(2, int(3 * s)), a)
    ring_text(im, "GARANTİ MÜŞTERİ • GARANTİ MÜŞTERİ • ", cx, cy, 200 * s, max(8, int(30 * s)), YELLOW, a, rot)
    k = s * 70
    O.poly(im, [[cx - k, cy], [cx - k * 0.25, cy + k * 0.7], [cx + k, cy - k * 0.75]], YELLOW, max(3, int(16 * s)), a,
           glow=0.5)
    return im


def garanti(p, t, d, wt, lt):
    t_g = _w(wt, 1, 0.4)
    t_m = lt[1] if len(lt) > 1 else d * 0.35
    t_k = _w(wt, 6, 3.0)
    img = _bg_dark(0.5, warm=(0.06, 0.045, 0.02), cy=900)
    img = draw_dust(img, t, np.array([0.04, 0.03, 0.015], np.float32), 0.8, 100, 12)
    spr, sa, _ = hero_sprite()
    ks = ease_out(seg(t, t_m - 0.1, t_m + 0.5))
    rise = ease_out(seg(t, t_k - 0.1, t_k + 0.45))
    for i, x in enumerate((250, 540, 830)):
        kk = ease_out(seg(t, t_m - 0.1 + i * 0.1, t_m + 0.4 + i * 0.1))
        if kk <= 0:
            continue
        y = 880 + 500 * (1 - kk)
        sc = 0.42
        al = 1.0
        if i == 1:
            y -= 60 * rise
            sc += 0.08 * rise
        else:
            al = 1 - 0.6 * rise
        img = paste_pm(img, spr, sa, x, y, sc, al * kk)
    if rise > 0:
        ring = np.exp(-((np.hypot((_XX - 540) / 150, (_YY - 820) / 290) - 1.0) / 0.05) ** 2)
        img += ring[..., None] * np.array([0.25, 0.8, 1.0], np.float32) * 0.25 * rise

    def post(im):
        O.label(im, "01  ·  GARANTİ MÜŞTERİ", color=GOLD, alpha=seg(t, 0.1, 0.4))
        kst = seg(t, t_g - 0.05, t_g + 0.15)
        up = ease_io(seg(t, t_m - 0.2, t_m + 0.4))
        if kst > 0:
            s = lerp(1.6, 1.0, ease_out(kst)) * lerp(1.0, 0.42, up)
            cy = lerp(780, 380, up)
            dx, dy = O.shake(t, t_g + 0.1, 12)
            seal(im, 540 + dx, cy + dy, s, min(1, kst * 3), t * 0.35)
        kc = ease_out(seg(t, t_k, t_k + 0.35))
        if kc > 0:
            chip(im, "KAMUYA ÖZEL", 540, 1175, CYAN, kc, 32, anchor="mm")
            O.text(im, "kriptolu", 540, 1235, 34, SERIF, None, ONE, alpha=kc)
            for x in (250, 830):
                chip(im, "TÜKETİCİ", x, 1175, ONE * 0.8, kc * 0.9, 24, anchor="mm")
        km = ease_out(seg(t, t_m + 0.3, t_m + 0.6)) * (1 - kc)
        O.text(im, "3 MODEL", 540, 1175, 34, "Montserrat.ttf", 800, ONE * 0.85, alpha=km, tracking=8)
        return im
    return img, post


# ================================================================== 11) KRİPTO: ses dalgası şifreye dönüşür
HEX = "0123456789ABCDEF"


def kripto(p, t, d, wt, lt):
    t_g = _w(wt, 3, 0.9)
    img = O.COOL.copy()
    img = O.grid_lines(img, 54, 0.04, CYAN)
    img = O.camera(img, 1.04 - 0.04 * ease_io(p))

    def post(im):
        O.poly(im, [[60, 220], [60, 1580], [1020, 1580], [1020, 220], [60, 220]], ONE * 0.18, 3, 1.0)
        lock_icon(im, 300, 322, 44, ONE * 0.9, 1.0, 1 - ease_out(seg(t, t_g + 0.15, t_g + 0.4)))
        O.text(im, "KRİPTOLU HABERLEŞME", 350, 330, 32, "Inter.ttf", 700, ONE * 0.9, "lm", tracking=3)
        n = 36
        conv = seg(t, t_g - 0.1, t_g + 0.6)
        rng = np.random.default_rng(int(abs(t) * 12))
        glow = np.zeros_like(im)
        for i in range(n):
            x = 150 + i * (780 / (n - 1))
            u = i / (n - 1)
            if u < conv * 1.1:
                ch = HEX[rng.integers(0, 16)]
                yy = 700 + math.sin(t * 6 + i) * 30
                O.text(im, ch, x, yy, 40, G.MONO, None, CYAN, alpha=0.95)
                O.text(glow, ch, x, yy, 40, G.MONO, None, CYAN, alpha=0.8)
            else:
                amp = (0.3 + 0.7 * abs(math.sin(t * 7 + i * 0.7) * math.sin(t * 3.1 + i * 0.33))) * 150
                O.rect_fill(im, x - 6, 700 - amp / 2, 12, amp, ONE * 0.92, 1.0, r=6)
        im += G.blur(glow, 8) * 0.8
        kl = seg(t, t_g + 0.15, t_g + 0.45)
        big = lerp(1.25, 1.0, ease_out(kl)) if kl > 0 else 1.0
        lock_icon(im, 540, 1000, 170 * big, YELLOW if kl > 0.5 else ONE * 0.85, 1.0,
                  1 - ease_out(kl), thick=10, glow=0.6 * kl)
        kc = ease_out(seg(t, t_g + 0.4, t_g + 0.7))
        chip(im, "ŞİFRELENDİ", 540, 1225, GREEN, kc, 32, anchor="mm", icon="check")
        return im
    return img, post
