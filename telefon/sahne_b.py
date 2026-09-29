"""Telefon filmi sahneleri 12-22: devlet → final.  İmza: f(p, t, d, wt, lt) -> (görüntü, post)."""
import math
import cv2
import numpy as np
from yardim import *                                          # noqa: F401,F403
from yardim import G, O, HM, _XX, _YY
from sahne_a import _w, _bg_dark, bg_dark, _union_alpha, _sweep


# ================================================================== 12) DEVLET: yalnız telefon, arkada yükselen sütunlar
_COLBASE = None


def _col_base():
    global _COLBASE
    if _COLBASE is None:
        a = plate("devlet_sutun")["alpha"]
        rows = np.nonzero(a.max(1) > 0.5)[0]
        _COLBASE = int(rows.max()) if len(rows) else H
    return _COLBASE


def donut(im, cx, cy, r, frac, color, a, th=16):
    O.arc(im, cx, cy, r, 0, 2 * math.pi, ONE * 0.18, th, a)
    if frac > 0.002:
        O.arc(im, cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * frac, color, th, a, glow=0.5)


def devlet(p, t, d, wt, lt):
    t_oz = _w(wt, 1, 0.4)
    t_b = lt[1] if len(lt) > 1 else d * 0.4
    t_dv = _w(wt, 8, 3.2)
    t_var = _w(wt, 9, 3.6)
    sc_ = plate("devlet_sahne")
    col = plate("devlet_sutun")
    t_ark = _w(wt, 6, 2.6)
    rise = ease_out(seg(t, t_ark - 0.15, t_ark + 0.9))
    base_y = _col_base()
    off = (base_y + 40) * (1 - rise)
    M = np.float32([[1, 0, 0], [0, 1, off]])
    crgb, ca = warp(col["rgb"], M), warp(col["alpha"], M)
    cut = (_YY < base_y + 2).astype(np.float32)
    far = (sc_["depth"] > 1.6).astype(np.float32)
    ca = ca * cut * far
    floor_dim = 1 - 0.85 * G.smoothstep(1120, 1700, _YY)[..., None]          # zemindeki sert parlamayı bastır
    img = sc_["rgb"] * floor_dim * (1 - ca[..., None]) + crgb * (cut * far)[..., None]
    if 0 < rise < 1:                                            # yükselirken toz
        dustk = math.sin(math.pi * rise)
        img = draw_dust(img, t, np.array([0.06, 0.05, 0.04], np.float32), 1.6 * dustk, 220, 30,
                        area=(0, base_y - 160, W, base_y + 40))
    pc = meta("devlet")["phone_center"]
    z = lerp(1.75, 1.0, ease_io(seg(t, t_b - 0.1, t_b + 1.0)))
    c = (pc[0], pc[1] - 40)
    hx, hy = hand(t, 2.5, 9)
    sdx, sdy = O.shake(t, t_ark + 0.6, 12, dur=0.6)
    img, _ = push(img, None, 1.0, z, z, c=c, dx=hx + sdx, dy=hy + sdy)
    img = shade_top(img, 0.75)

    def post(im):
        O.label(im, "VESTEL" if t < t_b else "02  ·  DEVLET DESTEĞİ", color=GOLD, alpha=seg(t, 0.1, 0.4))
        k = ease_out(seg(t, t_oz - 0.1, t_oz + 0.25)) * (1 - seg(t, t_b - 0.1, t_b + 0.2))
        chip(im, "ÖZEL ŞİRKET", 540, 740, ONE * 0.9, k, 32, anchor="mm")
        O.text(im, "tek başına", 540, 805, 40, SERIF, None, ONE, alpha=k)
        t_do = min(t_dv, t_ark + 0.55)
        kd = ease_out(seg(t, t_do - 0.2, t_do + 0.2))
        if kd > 0:
            for i, (name, sub, frac, colr) in enumerate((("TÜRK TELEKOM", "Varlık Fonu + Hazine", 0.867, YELLOW),
                                                         ("ASELSAN", "TSK Güçlendirme Vakfı", 0.742, CYAN))):
                x0 = 70 + i * 480
                O.glass(im, x0, 290, 460, 230, r=36, frost=14, tint=0.05, alpha=kd)
                O.rect_fill(im, x0, 290, 460, 230, np.zeros(3, np.float32), 0.35 * kd, r=36)
                fr = frac * ease_out(seg(t, t_do - 0.05, t_do + 0.6))
                donut(im, x0 + 105, 405, 68, fr, colr, kd)
                O.text(im, f"%{int(round(fr * 100))}", x0 + 105, 405, 38, "Montserrat.ttf", 900, ONE, alpha=kd)
                O.text(im, name, x0 + 195, 385, 27, "Montserrat.ttf", 900, ONE, "lm", alpha=kd, tracking=1)
                O.text(im, sub, x0 + 195, 428, 22, "Inter.ttf", 600, ONE * 0.8, "lm", alpha=kd)
        return im
    return img, post


# ================================================================== 13) TELEKOM: gece Türkiye haritası, abone ağı
CAM_T = (35.2, 38.7, 80.0)
_MAPC = {}


def _map_cache():
    if not _MAPC:
        img, masks = HM.base(CAM_T, {"TUR": ((0.035, 0.035, 0.04), 1.0)})
        _MAPC["base"] = img
        tur = masks["TUR"] > 128
        rng = np.random.default_rng(9)
        pts, cols = [], []
        tot = sum(HM.POP.values())
        for name, pop in HM.POP.items():
            n = int(7000 * pop / tot) + 30
            cx, cy = HM.city_xy(name, CAM_T)
            sig = 10 + 7 * math.sqrt(pop)
            q = rng.normal(0, 1, (n, 2)) * sig + [cx, cy]
            pts.append(q)
        pts = np.vstack(pts)
        xi = np.clip(pts[:, 0].astype(int), 0, W - 1)
        yi = np.clip(pts[:, 1].astype(int), 0, H - 1)
        pts = pts[tur[yi, xi]]
        hub = np.array(HM.city_xy("Ankara", CAM_T))
        dist = np.hypot(*(pts - hub).T)
        order = (dist / dist.max()) * 0.75 + rng.random(len(pts)) * 0.25
        _MAPC["pts"] = pts.astype(np.float32)
        _MAPC["order"] = order.astype(np.float32)
        _MAPC["bright"] = rng.uniform(0.5, 1.0, len(pts)).astype(np.float32)
    return _MAPC


def _arc_pts(a, b, bend=0.18, n=32):
    a, b = np.asarray(a, float), np.asarray(b, float)
    mid = (a + b) / 2
    nrm = np.array([-(b - a)[1], (b - a)[0]])
    ctrl = mid + nrm * bend
    u = np.linspace(0, 1, n)[:, None]
    return (1 - u) ** 2 * a + 2 * (1 - u) * u * ctrl + u ** 2 * b


def telekom(p, t, d, wt, lt):
    t_tt = _w(wt, 5, 2.0)
    t_m = _w(wt, 10, 4.1)
    t_g = _w(wt, 14, 5.3)
    mc = _map_cache()
    img = mc["base"].copy()
    glow = np.zeros_like(img)
    net = seg(t, t_tt - 0.25, t_tt + 1.3)
    hubs = ["Ankara", "İstanbul"]
    others = [c for c in HM.POP if c not in hubs]
    if net > 0:
        for i, cname in enumerate(others):
            hname = "İstanbul" if HM.CITIES[cname][1] < 31 else "Ankara"
            u = np.clip(net * 1.4 - i * 0.012, 0, 1)
            if u <= 0:
                continue
            path = _arc_pts(HM.city_xy(hname, CAM_T), HM.city_xy(cname, CAM_T), 0.15 + 0.05 * (i % 3))
            n = max(2, int(len(path) * u))
            O.poly(img, path[:n], np.array([0.25, 0.6, 0.8], np.float32) * 0.5, 2, 0.8)
            O.poly(glow, path[:n], np.array([0.2, 0.7, 1.0], np.float32), 5, 0.5)
            if u >= 1:
                q = ((t * 0.9 + i * 0.137) % 1)
                pp = path[int(q * (len(path) - 1))]
                O.circle(glow, pp[0], pp[1], 4, np.array([0.6, 0.9, 1.0], np.float32), fill=True, alpha=0.9)
        O.poly(img, _arc_pts(HM.city_xy("İstanbul", CAM_T), HM.city_xy("Ankara", CAM_T), 0.1),
               np.array([0.3, 0.7, 0.9], np.float32), 3, min(1, net * 3))
    idle = 1 - seg(t, t_tt - 0.4, t_tt)
    if idle > 0:
        for j, hname in enumerate(hubs):
            x, y = HM.city_xy(hname, CAM_T)
            for q_ in range(2):
                ph = ((t * 0.8 + j * 0.3 + q_ * 0.5) % 1)
                O.circle(glow, x, y, 10 + 160 * ph, np.array([0.2, 0.7, 1.0], np.float32), 2, idle * (1 - ph) * 0.8)
    for cname in HM.POP:
        x, y = HM.city_xy(cname, CAM_T)
        r = 6 if cname in hubs else 3.5
        O.circle(img, x, y, r, np.array([0.8, 0.85, 0.9], np.float32) * 0.6, fill=True, alpha=0.9)
    kd = seg(t, t_m - 0.3, t_g + 0.2)
    if kd > 0:
        live = mc["order"] < kd
        cols = np.outer(mc["bright"][live], np.array([1.0, 0.72, 0.25], np.float32)) * 0.55
        glow = splat(glow, mc["pts"][live], cols.astype(np.float32), 2)
    img = img + glow * 0.9 + G.blur(glow, 3) * 0.7 + G.blur(glow, 10) * 0.5
    img = tilt_img(img)
    z = 1.0 + 0.07 * ease_io(p) + 0.03 * ease_out(seg(t, t_g - 0.2, t_g + 0.6))
    hx, hy = hand(t, 2, 13)
    img, _ = push(img, None, 1.0, z, z, c=(560, 900), dx=hx, dy=hy)
    fade = ease_out(seg(t, 0.0, 0.5))
    img = img * (0.25 + 0.75 * fade)

    def post(im):
        O.label(im, "03  ·  ABONE AĞI", color=CYAN, alpha=seg(t, 0.1, 0.4))
        kt = ease_out(seg(t, t_tt - 0.1, t_tt + 0.3))
        chip(im, "TÜRK TELEKOM", 540, 470, CYAN, kt * (1 - seg(t, t_m - 0.4, t_m)), 30, anchor="mm")
        kc = ease_out(seg(t, t_m - 0.2, t_m + 0.2))
        if kc > 0:
            O.glass(im, 170, 290, 740, 220, r=40, frost=14, tint=0.05, alpha=kc)
            O.rect_fill(im, 170, 290, 740, 220, np.zeros(3, np.float32), 0.35 * kc, r=40)
            v = 32.7 * ease_out(seg(t, t_m - 0.1, t_g + 0.1))
            O.text(im, f"{v:.1f}".replace(".", ",") + " MİLYON", 540, 375, 72, "Montserrat.ttf", 900, YELLOW, alpha=kc,
                   glow=0.3)
            O.text(im, "MOBİL ABONE  ·  2026", 540, 455, 28, "Inter.ttf", 700, ONE * 0.85, alpha=kc, tracking=5)
        return im
    return img, post


# ================================================================== 14) FATURA: telefon faturada bir satıra dönüşür, zincir
def _chain(im, x0, x1, y, n, k, tight=0.0, color=None):
    color = YELLOW if color is None else color
    L = (x1 - x0)
    step = L / n * (1 - 0.06 * tight)
    start = x0 + (L - step * n) / 2
    for i in range(n):
        ki = seg(k, i / n, (i + 1) / n)
        if ki <= 0:
            continue
        cx = start + step * (i + 0.5)
        if i % 2 == 0:
            ang = np.linspace(0, 2 * math.pi, 40)
            pts = np.stack([cx + step * 0.62 * np.cos(ang), y + step * 0.32 * np.sin(ang)], 1)
            O.poly(im, pts, color, 8, ki, closed=True, glow=0.35)
        else:
            O.rect_fill(im, cx - step * 0.55, y - 5, step * 1.1, 10, color * 0.9, ki, r=5)


def fatura(p, t, d, wt, lt):
    t_tel = _w(wt, 0, 0.2)
    t_f = _w(wt, 1, 0.7)
    t_b = lt[1] if len(lt) > 1 else d * 0.5
    t_s = _w(wt, 4, 2.3)
    t_bag = _w(wt, 5, 2.8)
    img = O.WARM.copy() * 0.8
    img = O.camera(img, 1.0 + 0.04 * ease_io(p))
    spr, sa, _ = hero_sprite()

    def post(im):
        O.label(im, "OPERATÖR AVANTAJI", color=GOLD, alpha=seg(t, 0.05, 0.3))
        up = ease_io(seg(t, t_b - 0.1, t_b + 0.5))
        y0 = 300
        kp = ease_out(seg(t, 0.0, 0.3))
        pw, ph = 780, 640
        x0 = 150
        O.glass(im, x0, y0, pw, ph, r=44, frost=16, tint=0.06, alpha=kp)
        O.rect_fill(im, x0, y0, pw, ph, np.zeros(3, np.float32), 0.3 * kp, r=44)
        O.text(im, "AYLIK FATURA", x0 + 50, y0 + 70, 38, "Montserrat.ttf", 900, ONE, "lm", alpha=kp, tracking=4)
        O.rect_fill(im, x0 + 50, y0 + 115, pw - 100, 2, ONE * 0.4, kp)
        rows = [("Mobil hat", 0.0), ("İnternet paketi", 0.0), ("Cihaz taksiti", 1.0)]
        for i, (name, new) in enumerate(rows):
            yy = y0 + 180 + i * 95
            if new:
                kn = ease_out(seg(t, t_tel + 0.45, t_tel + 0.7))
                hl = ease_out(seg(t, t_f - 0.05, t_f + 0.25))
                if hl > 0:
                    O.rect_fill(im, x0 + 30, yy - 38, pw - 60, 76, YELLOW, 0.2 * hl * kp, r=20)
                phone_icon(im, x0 + 78, yy, 26, 44, YELLOW, kn * kp, thick=3)
                O.text(im, name, x0 + 120, yy, 34, "Montserrat.ttf", 800, YELLOW if hl > 0.5 else ONE, "lm",
                       alpha=kn * kp)
                O.text(im, "+ •••,•• TL", x0 + pw - 50, yy, 32, "Montserrat.ttf", 800, YELLOW, "rm", alpha=kn * kp)
            else:
                O.text(im, name, x0 + 60, yy, 32, "Inter.ttf", 600, ONE * 0.9, "lm", alpha=kp)
                O.text(im, "•••,•• TL", x0 + pw - 50, yy, 30, "Inter.ttf", 600, ONE * 0.8, "rm", alpha=kp)
        O.rect_fill(im, x0 + 50, y0 + 470, pw - 100, 2, ONE * 0.4, kp)
        O.text(im, "TOPLAM", x0 + 60, y0 + 540, 34, "Montserrat.ttf", 900, ONE, "lm", alpha=kp)
        O.text(im, "•.•••,•• TL", x0 + pw - 50, y0 + 540, 34, "Montserrat.ttf", 900, ONE, "rm", alpha=kp)
        # telefon uçarak satıra dönüşür
        u = seg(t, t_tel - 0.05, t_tel + 0.6)
        if 0 < u < 1:
            e = ease_io(u)
            tx, ty = lerp(1150, x0 + 78, e), lerp(760, y0 + 180 + 2 * 95, e) - 160 * math.sin(math.pi * e)
            s = lerp(0.42, 0.05, e)
            rot = lerp(-25, 0, e)
            h_, w_ = sa.shape
            Mw = cv2.getRotationMatrix2D((w_ / 2, h_ / 2), rot, s)
            Mw[:, 2] += (tx - w_ / 2, ty - h_ / 2)
            r2, a2 = warp(spr, Mw), warp(sa, Mw)
            disp = srgb(G.filmic(r2 / np.maximum(a2, 1e-3)[..., None] * 1.4))
            im[:] = im * (1 - a2[..., None]) + disp * a2[..., None]
        # zincir: seni sisteme bağlar
        kc = seg(t, t_s - 0.2, t_s + 0.45)
        if kc > 0:
            yc = 1110
            person_icon(im, 150, yc, 90, ONE, ease_out(seg(kc, 0, 0.3)))
            O.text(im, "SEN", 150, yc + 85, 28, "Montserrat.ttf", 900, ONE, alpha=ease_out(seg(kc, 0, 0.3)), tracking=4)
            tight = ease_out(seg(t, t_bag - 0.05, t_bag + 0.2))
            dx = O.shake(t, t_bag, 8, 0.3)[0]
            _chain(im, 230 + dx, 820 + dx, yc, 9, kc, tight)
            kh = seg(kc, 0.8, 1.0)
            O.circle(im, 915, yc, 58, CYAN, 5, kh, glow=0.4)
            for j in range(6):
                a_ = j * math.pi / 3 + t
                O.circle(im, 915 + 32 * math.cos(a_), yc + 32 * math.sin(a_), 7, CYAN, fill=True, alpha=kh)
            O.circle(im, 915, yc, 10, CYAN, fill=True, alpha=kh)
            O.text(im, "ŞEBEKE", 915, yc + 90, 26, "Montserrat.ttf", 900, CYAN, alpha=kh, tracking=4)
        return im
    return img, post


# ================================================================== 15) ZAMANLAMA: kronometre, 4.5G -> 5G
def _chrono(im, cx, cy, R, ang, a, flash=0.0):
    if a <= 0.01:
        return im
    O.circle(im, cx, cy, R, ONE * 0.85, 4, a)
    O.circle(im, cx, cy, R * 0.97, ONE * 0.2, 2, a)
    for i in range(60):
        th = i / 60 * 2 * math.pi
        l = 26 if i % 5 == 0 else 12
        w = 4 if i % 5 == 0 else 2
        c, s_ = math.sin(th), -math.cos(th)
        O.poly(im, [[cx + c * (R - 14), cy + s_ * (R - 14)], [cx + c * (R - 14 - l), cy + s_ * (R - 14 - l)]],
               ONE * (0.9 if i % 5 == 0 else 0.55), w, a)
        if i % 5 == 0:
            n = 60 if i == 0 else i
            O.text(im, str(n), cx + c * (R - 70), cy + s_ * (R - 70), 30, "Inter.ttf", 600, ONE * 0.8, alpha=a)
    O.circle(im, cx, cy + R * 0.38, R * 0.2, ONE * 0.35, 2, a)
    sub = ang * 0.2
    O.poly(im, [[cx, cy + R * 0.38], [cx + math.sin(sub) * R * 0.16, cy + R * 0.38 - math.cos(sub) * R * 0.16]],
           ONE * 0.7, 3, a)
    hx, hy = cx + math.sin(ang) * (R - 30), cy - math.cos(ang) * (R - 30)
    tx, ty = cx - math.sin(ang) * 50, cy + math.cos(ang) * 50
    O.poly(im, [[tx, ty], [hx, hy]], RED, 5, a, glow=0.4 + flash)
    O.circle(im, cx, cy, 14, RED, fill=True, alpha=a)
    O.circle(im, cx, cy, 5, ONE, fill=True, alpha=a)
    O.rect_fill(im, cx - 28, cy - R - 58, 56, 38, ONE * 0.8, a, r=8)
    O.rect_fill(im, cx - 12, cy - R - 26, 24, 28, ONE * 0.6, a, r=4)
    if flash > 0:
        O.circle(im, cx, cy, R + 30 * flash, YELLOW, 6, flash * a, glow=0.8)
    return im


def zamanlama(p, t, d, wt, lt):
    t_z = _w(wt, 5, 1.8)
    t_b = lt[1] if len(lt) > 1 else d * 0.6
    t_5 = _w(wt, 8, 3.2)
    img = O.NIGHT.copy()
    img = O.camera(img, 1.0 + 0.04 * ease_io(p))

    def post(im):
        O.label(im, "04  ·  ZAMANLAMA", color=GOLD, alpha=seg(t, 0.1, 0.4))
        out = ease_io(seg(t, t_b - 0.3, t_b + 0.1))
        if out < 1:
            if t < t_z - 0.05:
                ang = t * 5.5
            else:
                ang = 2 * math.pi * math.ceil((t_z - 0.05) * 5.5 / (2 * math.pi))
                ang += 0.12 * math.exp(-(t - t_z) * 14) * math.sin((t - t_z) * 50)
            fl = max(0.0, 1 - (t - t_z) / 0.3) if t >= t_z else 0.0
            s = 1 - 0.4 * out
            _chrono(im, 540, 780 - 200 * out, 330 * s, ang, (1 - out) * ease_out(seg(t, 0.0, 0.25)), fl)
        kb = ease_out(seg(t, t_b - 0.2, t_b + 0.25))
        if kb > 0:
            y = lerp(420, 680, kb)
            O.glass(im, 120, int(y - 90), 840, 180, r=90, frost=16, tint=0.06, alpha=kb)
            O.rect_fill(im, 120, int(y - 90), 840, 180, np.zeros(3, np.float32), 0.35 * kb, r=90)
            on5 = seg(t, t_5 - 0.05, t_5 + 0.1)
            bars = 2 + int(2 * on5)
            signal_bars(im, 210, y + 38, 90, bars, ONE, kb)
            fl = seg(t, t_5 - 0.08, t_5 + 0.12)
            txt = "5G" if fl >= 0.5 else "4.5G"
            sy = abs(math.cos(math.pi * fl)) if 0 < fl < 1 else 1.0
            m = G.text_mask(txt, "Montserrat.ttf", 120, 900)
            mh = max(2, int(m.shape[0] * sy))
            m = cv2.resize(m, (m.shape[1], mh))
            colr = CYAN if fl >= 0.5 else ONE * 0.85
            G.over(im, colr, m * kb, int(560 - m.shape[1] / 2 + 60), int(y - mh / 2))
            O.rect_fill(im, 830, y - 26, 80, 52, ONE * 0.85, kb, r=10)
            O.rect_fill(im, 910, y - 10, 8, 20, ONE * 0.85, kb, r=3)
            O.rect_fill(im, 836, y - 20, 68 * (0.5 + 0.5 * on5), 40, GREEN if on5 else ONE * 0.6, kb, r=7)
            if t > t_5:
                for j in range(3):
                    q = ((t - t_5) * 1.2 + j / 3) % 1
                    O.circle(im, 560, y, 150 + 380 * q, CYAN, 3, kb * (1 - q) * 0.7)
            kc = ease_out(seg(t, t_5 + 0.1, t_5 + 0.4))
            chip(im, "1 NİSAN 2026", 540, 900, CYAN, kc, 32, anchor="mm")
            O.text(im, "5G başladı", 540, 965, 40, SERIF, None, ONE, alpha=kc)
        return im
    return img, post


# ================================================================== 16) MİLYONLAR: 95 ekranlık video duvarı
NCOL, NROW, CELL = 10, 10, 84
WALL_X0, WALL_Y0 = 540 - NCOL * CELL / 2, 392
_CYAN_SET = set(np.random.default_rng(12).choice(95, 32, replace=False).tolist())
FOCUS = 44


def _tile(im, x, y, s, kind, a, gold=0.0):
    w, h = CELL * 0.82 * s, CELL * 0.86 * s
    if w < 3:
        return
    if kind == "5g":
        fill, col, txt = CYAN * 0.25, CYAN, "5G"
    else:
        fill, col, txt = ONE * 0.1, ONE * 0.55, "4.5G"
    if gold > 0 and kind != "5g":
        fill = fill * (1 - gold) + YELLOW * 0.35 * gold
        col = col * (1 - gold) + YELLOW * gold
    O.rect_fill(im, x - w / 2, y - h / 2, w, h, fill, a, r=max(2, int(w * 0.12)))
    if w > 16:
        O.poly(im, [[x - w / 2, y - h / 2], [x + w / 2, y - h / 2], [x + w / 2, y + h / 2], [x - w / 2, y + h / 2]],
               col, max(1, int(w / 40)), a * 0.8, closed=True)
        O.text(im, txt, x, y - h * 0.08, max(6, int(w * 0.3)), "Montserrat.ttf", 900, col, alpha=a)
        if kind != "5g" and w > 200:
            O.text(im, "5G UYUMSUZ", x, y + h * 0.2, int(w * 0.075), "Montserrat.ttf", 800, RED * (1 - gold) + YELLOW * gold,
                   alpha=a, tracking=w * 0.005)


def milyonlar(p, t, d, wt, lt):
    t_uy = _w(wt, 2, 0.9)
    t_m = lt[2] if len(lt) > 2 else d * 0.4
    t_pz = _w(wt, 11, 4.3)
    img = O.NIGHT.copy()
    fx, fy = divmod(FOCUS, NCOL)[::-1]
    fcx = WALL_X0 + (fx + 0.5) * CELL
    fcy = WALL_Y0 + (fy + 0.5) * CELL
    zu = ease_io(seg(t, t_m - 0.15, t_m + 0.95))
    S0 = 8.0 + 1.2 * ease_io(seg(t, 0.0, t_m))
    S = math.exp(math.log(S0) * (1 - zu))
    cx, cy = lerp(fcx, 540, zu), lerp(fcy, WALL_Y0 + NROW * CELL / 2, zu)
    for i in range(95):
        r, c = divmod(i, NCOL)
        x = 540 + ((WALL_X0 + (c + 0.5) * CELL) - cx) * S
        y = lerp(820, WALL_Y0 + NROW * CELL / 2, zu) + ((WALL_Y0 + (r + 0.5) * CELL) - cy) * S
        if x < -CELL * S or x > W + CELL * S or y < -CELL * S or y > H + CELL * S:
            continue
        kind = "5g" if i in _CYAN_SET else "old"
        on = 1.0
        if i != FOCUS:
            on = ease_out(seg(t, t_m - 0.2 + (abs(r - fy) + abs(c - fx)) * 0.03, t_m + 0.1 + (abs(r - fy) + abs(c - fx)) * 0.03))
        gold = ease_out(seg(t, t_pz - 0.3 + (r + c) * 0.025, t_pz - 0.05 + (r + c) * 0.025))
        flick = 0.85 + 0.15 * math.sin(t * 9 + i * 1.7)
        _tile(img, x, y, S, kind, on * flick, gold)
    img = O.camera(img, 1.0 + 0.02 * ease_io(p))

    def post(im):
        O.label(im, "5G GEÇİŞİ", color=CYAN, alpha=seg(t, 0.1, 0.4))
        ks = ease_out(seg(t, t_m + 0.5, t_m + 0.9))
        if ks > 0:
            gold = ease_out(seg(t, t_pz - 0.1, t_pz + 0.3))
            O.text(im, "95 MİLYON TELEFONUN", 540, 282, 34, "Montserrat.ttf", 900, ONE * 0.9, alpha=ks * (1 - gold), tracking=4)
            chip(im, "5G · 32 MİLYON", 300, 334, CYAN, ks * (1 - gold * 0.5), 26, anchor="mm")
            chip(im, "UYUMSUZ · 63 MİLYON", 750, 334, ONE * 0.75, ks * (1 - gold), 26, anchor="mm")
            if gold > 0:
                O.text(im, "YENİ PAZAR", 540, 280, 40, "Montserrat.ttf", 900, YELLOW, alpha=gold, tracking=8)
                chip(im, "63 MİLYON TELEFON", 750, 334, YELLOW, gold, 26, anchor="mm")
            O.text(im, "1 kare = 1 milyon telefon", 540, 1272, 30, SERIF, None, ONE * 0.8, alpha=ks)
        return im
    return img, post


# ================================================================== 17) UYDU: deprem, şebeke çöker, uydu bağlantısı
_STARS = None


def stars():
    global _STARS
    if _STARS is None:
        rng = np.random.default_rng(17)
        s = np.zeros((H, W), np.float32)
        n = 1400
        x = rng.integers(0, W, n)
        y = rng.integers(0, int(H * 0.75), n)
        b = rng.uniform(0.2, 1.0, n) ** 3
        s[y, x] = b
        s = G.blur(s, 0.7) * 3 + G.blur(s, 2.0) * 1.2
        sky = (plate("kule_acik")["depth"] > 1e4).astype(np.float32)
        _STARS = (s * G.blur(sky, 2))[..., None] * np.array([0.8, 0.85, 1.0], np.float32) * 0.08
    return _STARS


def _satellite(im, x, y, s, a, t):
    if a <= 0.01:
        return
    O.rect_fill(im, x - 10 * s, y - 8 * s, 20 * s, 16 * s, np.array([0.85, 0.7, 0.35], np.float32), a, r=2)
    for sgn in (-1, 1):
        x0 = x + sgn * 14 * s
        O.poly(im, [[x + sgn * 10 * s, y], [x0, y]], ONE * 0.7, 2, a)
        xx = x0 if sgn > 0 else x0 - 44 * s
        O.rect_fill(im, xx, y - 9 * s, 44 * s, 18 * s, np.array([0.15, 0.3, 0.6], np.float32), a)
        for k in range(1, 4):
            O.poly(im, [[xx + k * 11 * s, y - 9 * s], [xx + k * 11 * s, y + 9 * s]], ONE * 0.5, 1, a)
    gl = 0.5 + 0.5 * math.sin(t * 8)
    O.circle(im, x + 6 * s, y - 4 * s, 3 * s, ONE, fill=True, alpha=a * gl, glow=0.8 * gl)


def _msg_phone(im, x, y, w, h, a, t, t_sent, t_link):
    if a <= 0.01:
        return
    O.glass(im, int(x), int(y), int(w), int(h), r=44, frost=14, tint=0.06, alpha=a)
    O.rect_fill(im, x, y, w, h, np.zeros(3, np.float32), 0.45 * a, r=44)
    link = seg(t, t_link - 0.1, t_link + 0.2)
    O.text(im, "UYDU" if link > 0.5 else "SERVİS YOK", x + 30, y + 50, 24, "Montserrat.ttf", 900,
           CYAN if link > 0.5 else RED, "lm", alpha=a, tracking=3)
    signal_bars(im, x + w - 90, y + 62, 40, 4 if link > 0.5 else 0, CYAN, a)
    ks = ease_out(seg(t, t_sent - 0.1, t_sent + 0.25))
    if ks > 0:
        bw = w - 70
        by = y + h - 140 - 20 * (1 - ks)
        O.rect_fill(im, x + 40, by, bw, 90, np.array([0.2, 0.55, 0.35], np.float32), a * ks, r=30)
        O.text(im, "Güvendeyim.", x + 70, by + 45, 34, "Inter.ttf", 700, ONE, "lm", alpha=a * ks)
        tick = seg(t, t_sent + 0.35, t_sent + 0.5)
        for j in range(2):
            xx = x + 40 + bw - 70 + j * 16
            O.poly(im, [[xx, by + 55], [xx + 7, by + 63], [xx + 20, by + 45]], CYAN, 3, a * tick)


def uydu(p, t, d, wt, lt):
    t_dp = _w(wt, 1, 0.4)
    t_c = _w(wt, 3, 1.3)
    t_u = _w(wt, 4, 1.9)
    t_h = _w(wt, 7, 3.2)
    on = plate("kule_acik")
    off = plate("kule_kapali")
    k = seg(t, t_c - 0.05, t_c + 0.35)
    flick = 1.0 if k <= 0 or k >= 1 else (1.0 if (int(t * 24) % 3) else 0.0)
    mix = k if flick else 1.0
    if 0 < k < 1 and not flick:
        mix = 1.0
    img = on["rgb"] * (1 - mix) + off["rgb"] * mix + stars()
    hx, hy = hand(t, 2.5, 17)
    quake = seg(t, t_dp - 0.05, t_dp + 0.1) * (1 - seg(t, t_c + 0.4, t_c + 1.2))
    rng = np.random.default_rng(int(abs(t) * 60))
    qx, qy = (rng.uniform(-1, 1, 2) * 16 * quake) if quake > 0 else (0.0, 0.0)
    img, _ = push(img, on["depth"], 1.0, 1.0 + 0.06 * ease_io(p), 1.0 + 0.06 * ease_io(p), c=(560, 900),
                  dx=hx + qx, dy=hy + qy)
    top = meta("kule")["top"]

    def post(im):
        O.label(im, "AFET  ·  UYDU BAĞLANTISI", color=CYAN, alpha=seg(t, 0.1, 0.4))
        s_ = (1.0 + 0.06 * ease_io(p)) * 1.012
        tx, ty = 560 + (top[0] - 560) * s_ + (hx + qx) * s_, 900 + (top[1] - 900) * s_ + (hy + qy) * s_
        if t < t_c:
            for j in range(3):
                q = ((t * 0.9 + j / 3) % 1)
                O.circle(im, tx, ty, 30 + 330 * q, CYAN, 3, (1 - q) * 0.7)
        kx = ease_out(seg(t, t_c + 0.1, t_c + 0.4)) * (1 - seg(t, t_u + 0.6, t_u + 1.0))
        if kx > 0:
            chip(im, "ŞEBEKE ÇÖKTÜ", 70, 330, RED, kx, 28, dark=False, icon="cross")
        su = seg(t, t_u - 0.4, t_u + 3.2)
        if su > 0:
            sx = lerp(-80, 1160, su)
            sy = 470 - 90 * math.sin(math.pi * su)
            _satellite(im, sx, sy, 1.3, min(1, su * 8), t)
            px, py = 800, 1010
            kb = seg(t, t_u + 0.25, t_u + 0.6)
            if kb > 0:
                n = 26
                for j in range(n):
                    q = (j / n + t * 1.5) % 1
                    bx, by = lerp(sx, px, q), lerp(sy + 12, py, q)
                    O.circle(im, bx, by, 3, CYAN, fill=True, alpha=kb * (0.35 + 0.65 * (1 - abs(q - 0.5) * 2)))
                O.poly(im, [[sx, sy + 12], [px, py]], CYAN, 1, kb * 0.35)
            _msg_phone(im, 610, 880, 380, 380, ease_out(seg(t, t_u, t_u + 0.4)), t, t_h, t_u + 0.4)
        return im
    return img, post


# ================================================================== 18) AMA: avantaj kartları devrilir
CARDS = ["GARANTİ MÜŞTERİ", "DEVLET DESTEĞİ", "ABONE AĞI", "5G ZAMANLAMASI"]


def ama(p, t, d, wt, lt):
    t_a = _w(wt, 0, 0.1)
    t_d = _w(wt, 1, 0.5)
    t_o = _w(wt, 2, 1.0)
    red = seg(t, t_a, t_a + 0.2)
    img = O.NIGHT.copy() * (1 - 0.3 * red) + (O.radial_bg("#000000", "#3A0806", 540, 760, 700, 900) * red)
    img = O.camera(img, 1.0 + 0.04 * ease_io(p))

    def post(im):
        for i, txt in enumerate(CARDS):
            y = 520 + i * 125
            fall = seg(t, t_a + 0.02 + i * 0.04, t_a + 0.5 + i * 0.04)
            k0 = ease_out(seg(t, 0.0 + i * 0.04, 0.2 + i * 0.04))
            if fall >= 1 or k0 <= 0:
                continue
            dy = 1400 * fall ** 2
            rot = (-1) ** i * 38 * fall
            dx = (-1) ** i * 180 * fall

            def draw(col, a, y=y, txt=txt, dx=dx, dy=dy):
                O.rect_fill(col, 170 + dx, y + dy, 740, 100, np.array([0.14, 0.16, 0.15], np.float32), 1.0, r=30)
                m = O.rounded(740, 100, 30)
                yy, xx = int(y + dy), int(170 + dx)
                if 0 <= yy < H - 100 and -740 < xx < W:
                    x0c, x1c = max(0, xx), min(W, xx + 740)
                    a[yy:yy + 100, x0c:x1c] = np.maximum(a[yy:yy + 100, x0c:x1c], m[:, x0c - xx:x1c - xx])
                O.circle(col, 230 + dx, y + 50 + dy, 22, GREEN, fill=True)
                O.poly(col, [[219 + dx, y + 50 + dy], [227 + dx, y + 59 + dy], [243 + dx, y + 41 + dy]], DARK, 5)
                O.text(col, txt, 275 + dx, y + 50 + dy, 36, "Montserrat.ttf", 800, ONE, "lm")
            im[:] = rot_layer(im, draw, rot, (540 + dx, y + 50 + dy), k0 * (1 - fall ** 2))
        ks = seg(t, t_a - 0.02, t_a + 0.14)
        if ks > 0:
            dx, dy = O.shake(t, t_a + 0.1, 18, 0.45)
            O.text(im, "AMA", 540 + dx, 720 + dy, 260, "Montserrat.ttf", 900, RED, alpha=min(1, ks * 3),
                   scale=lerp(2.0, 1.0, ease_out(ks)), glow=0.4)
        t_d2 = max(t_d, t_a + 0.55)
        O.text(im, "DEĞİŞMEYEN", 540, 920, 60, "Montserrat.ttf", 900, ONE, alpha=ease_out(seg(t, t_d2 - 0.1, t_d2 + 0.2)),
               tracking=8)
        O.text(im, "olumsuz şartlar", 540, 1010, 84, SERIF, None, RED * 1.2,
               alpha=ease_out(seg(t, max(t_o, t_d2 + 0.2) - 0.1, max(t_o, t_d2 + 0.2) + 0.25)))
        return im
    return img, post


# ================================================================== 19) PAZAR: izometrik küpler, ölçek şoku
def _cube_sprite(u, color, hf=1.0):
    """İzometrik küp (hf: yükseklik kesri; kısmi küp için)."""
    w = int(u * 1.732) + 4
    h = int(u * 2) + 4
    col = np.zeros((h, w, 3), np.float32)
    a = np.zeros((h, w), np.float32)
    cx = w / 2
    d_ = (1 - hf) * u
    top = np.array([[cx, 2 + d_], [cx + u * 0.866, 2 + u * 0.5 + d_], [cx, 2 + u + d_], [cx - u * 0.866, 2 + u * 0.5 + d_]])
    left = np.array([[cx - u * 0.866, 2 + u * 0.5 + d_], [cx, 2 + u + d_], [cx, 2 + 2 * u], [cx - u * 0.866, 2 + u * 1.5]])
    right = np.array([[cx + u * 0.866, 2 + u * 0.5 + d_], [cx, 2 + u + d_], [cx, 2 + 2 * u], [cx + u * 0.866, 2 + u * 1.5]])
    color = np.asarray(color, np.float32)
    for poly_, shade in ((top, 1.0), (left, 0.62), (right, 0.42)):
        m = np.zeros((h, w), np.uint8)
        cv2.fillPoly(m, [np.round(poly_ * 4).astype(np.int32)], 255, cv2.LINE_AA, shift=2)
        mf = m.astype(np.float32) / 255
        col = col * (1 - mf[..., None]) + color * shade * mf[..., None]
        a = np.maximum(a, mf)
    for poly_ in (top, left, right):
        cv2.polylines(col, [np.round(poly_ * 4).astype(np.int32)], True, (0.02, 0.02, 0.02), 1, cv2.LINE_AA, shift=2)
    return col, a


def _stack(n_total, fw=4, fd=4):
    """Küp konumları (gx, gy, gz) ve son küpün kesri."""
    pos = []
    per = fw * fd
    full = int(n_total)
    for i in range(full):
        z, r = divmod(i, per)
        gy, gx = divmod(r, fw)
        pos.append((gx, gy, z, 1.0))
    frac = n_total - full
    if frac > 0.01:
        z, r = divmod(full, per)
        gy, gx = divmod(r, fw)
        pos.append((gx, gy, z, frac))
    return pos


STACKS = {"tr": (11.6, 4, 3, YELLOW), "apple": (247.8, 4, 4, ONE * 0.82), "samsung": (241.2, 4, 4, ONE * 0.55)}


def _draw_stack(img, key, ox, oy, u, grow, t_drop=None, t=0.0):
    n, fw, fd, colr = STACKS[key]
    pos = _stack(n, fw, fd)
    spr, sa = _cube_sprite(u, colr)
    sh, sw = sa.shape
    order = sorted(range(len(pos)), key=lambda i: (pos[i][2], pos[i][0] + pos[i][1]))
    shown = grow * len(pos)
    for rank, i in enumerate(order):
        gx, gy, gz, fr = pos[i]
        if i >= shown:
            continue
        drop = 0.0
        if t_drop is not None:
            k = seg(t, t_drop + i * 0.07, t_drop + i * 0.07 + 0.25)
            if k <= 0:
                continue
            drop = (1 - spring(k, 1.2, 7)) * 120
        x = ox + (gx - gy) * u * 0.866
        y = oy + (gx + gy) * u * 0.5 - gz * u - drop
        if fr < 1:
            s2, a2 = _cube_sprite(u, colr, fr)
            G.over(img, s2, a2 * 0.9, int(x - sw / 2), int(y - u - 2))
        else:
            G.over(img, spr, sa, int(x - sw / 2), int(y - u - 2))


def pazar(p, t, d, wt, lt):
    t_11 = _w(wt, 2, 1.0)
    t_ap = _w(wt, 6, 3.2)
    t_sm = _w(wt, 8, 3.9)
    img = O.NIGHT.copy()
    zo = ease_io(seg(t, t_ap - 0.2, t_ap + 1.0))
    S = lerp(2.6, 1.0, zo)
    u = 40 * S
    base_y = 1150
    cxw = 540
    ox_tr = cxw + (540 - cxw) * S
    oy_tr = lerp(820, base_y - 60, zo)
    _draw_stack(img, "tr", ox_tr - (4 - 3) * u * 0.433, oy_tr, u, 1.0, 0.1, t)
    ga = ease_out(seg(t, t_ap - 0.1, t_ap + 1.2))
    gs = ease_out(seg(t, t_sm - 0.1, t_sm + 1.2))
    if ga > 0:
        _draw_stack(img, "apple", ox_tr - 330 * S, oy_tr - 20 * S, u, ga)
    if gs > 0:
        _draw_stack(img, "samsung", ox_tr + 330 * S, oy_tr - 20 * S, u, gs)
    sdx, sdy = O.shake(t, t_ap + 0.4, 6, 0.8)
    hx, hy = hand(t, 3, 19)
    img = O.camera(img, 1.0 + 0.06 * ease_io(seg(t, t_sm, d)), dx=sdx + hx, dy=sdy + hy)

    def post(im):
        O.label(im, "PAZAR BÜYÜKLÜĞÜ  ·  2025", color=GOLD, alpha=seg(t, 0.1, 0.4))
        k1 = ease_out(seg(t, 0.1, 0.4))
        if k1 > 0:
            v = 11.6 * ease_out(seg(t, 0.15, 1.2))
            ytr = lerp(470, 1235, zo)
            px = lerp(84, 44, zo)
            O.text(im, f"{v:.1f}".replace(".", ",") + " MİLYON", 540, ytr, int(px), "Montserrat.ttf", 900, YELLOW, alpha=k1,
                   glow=0.3)
            O.text(im, "TÜRKİYE · yıllık satış", 540, ytr + lerp(60, 36, zo), int(lerp(30, 22, zo)), "Inter.ttf", 700,
                   ONE * 0.85, alpha=k1 * (1 - 0.3 * zo), tracking=3)
        for key, tt, x, val in (("apple", t_ap, 540 - 330, 247.8), ("samsung", t_sm, 540 + 330, 241.2)):
            kk = ease_out(seg(t, tt + 0.3, tt + 1.2))
            if kk > 0:
                v = val * kk
                O.text(im, f"{v:.1f}".replace(".", ","), x, 318, 60, "Montserrat.ttf", 900, ONE, alpha=kk)
                O.text(im, "MİLYON", x, 366, 24, "Montserrat.ttf", 800, ONE * 0.8, alpha=kk, tracking=6)
                O.text(im, "APPLE" if key == "apple" else "SAMSUNG", x, 402, 28, "Montserrat.ttf", 900,
                       ONE * 0.9, alpha=kk, tracking=5)
        return im
    return img, post


# ================================================================== 20) ÖZET: röntgen taraması, içeride güvenlik + abone
def _xray(layers_rgb, a):
    lum = layers_rgb.mean(2)
    lum = lum / max(1e-4, float(np.percentile(lum[a > 0.5], 98)) if (a > 0.5).any() else 1.0)
    e = np.abs(cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)) + np.abs(cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3))
    ea = np.abs(cv2.Sobel(a, cv2.CV_32F, 1, 0, ksize=3)) + np.abs(cv2.Sobel(a, cv2.CV_32F, 0, 1, ksize=3))
    v = np.clip(0.25 * a + lum * 0.5 + e * 1.2 + ea * 0.8, 0, 2)
    return v[..., None] * np.array([0.1, 0.5, 0.85], np.float32)




def ozet(p, t, d, wt, lt):
    t_tel = _w(wt, 4, 1.4)
    t_scan = _w(wt, 6, 2.6)
    t_g = _w(wt, 7, 3.3)
    t_ab = _w(wt, 9, 4.2)
    t_dy = _w(wt, 11, 5.2)
    hm = meta("hero")
    cx, cy = hm["center"][:2]
    hx, hy = hand(t, 3, 21)
    M = affine(0.8 + 0.1 * ease_io(p), (cx, cy), hx + (540 - cx) * 0.6, hy - 40, 2 * math.sin(t * 0.6))
    layers = hero_layers(None, 1.0, M)
    img = bg_dark(0.5)
    solid = hero_over(img.copy(), layers)
    kart = hero_layers(None, 1.0, M, only=["kart"])
    xr_src = np.zeros((H, W, 3), np.float32)
    ka_ = np.zeros((H, W), np.float32)
    for _, r_, a_ in kart:
        xr_src = over_pm(xr_src, r_, a_)
        ka_ = np.maximum(ka_, a_)
    ua = _union_alpha(layers)
    xr = (_xray(xr_src, ka_) + np.array([0.01, 0.04, 0.07], np.float32)) * ua[..., None] + img * (1 - ua[..., None])
    edge = np.abs(cv2.Sobel(ua, cv2.CV_32F, 1, 0, ksize=5)) + np.abs(cv2.Sobel(ua, cv2.CV_32F, 0, 1, ksize=5))
    xr += np.clip(edge * 0.05, 0, 1)[..., None] * np.array([0.3, 0.8, 1.0], np.float32)
    sc = ease_io(seg(t, t_scan - 0.1, t_scan + 1.0))
    ys, _ = np.nonzero(ua > 0.3)
    y0p, y1p = (ys.min(), ys.max()) if len(ys) else (300, 1300)
    ly = lerp(y0p - 20, y1p + 20, sc)
    m = np.clip((ly - _YY) / 12, 0, 1)[..., None] if sc > 0 else np.zeros((H, W, 1), np.float32)
    img = solid * (1 - m) + xr * m
    if 0 < sc < 1:
        band = np.exp(-((_YY - ly) / 6) ** 2) * (0.3 + ua)
        img += band[..., None] * np.array([0.3, 0.9, 1.2], np.float32) * 0.9

    def post(im):
        O.label(im, "KISACASI", color=GOLD, alpha=seg(t, 0.1, 0.4))
        kt = ease_out(seg(t, t_tel - 0.1, t_tel + 0.25))
        strike = ease_out(seg(t, t_dy - 0.1, t_dy + 0.2))
        if kt > 0:
            chip(im, "TELEFON PROJESİ?", 540, 330, ONE * (0.9 - 0.4 * strike), kt, 32, anchor="mm")
            if strike > 0:
                O.poly(im, [[330, 332], [lerp(330, 750, strike), 328]], RED, 6, 1.0, glow=0.5)
        kg = ease_out(seg(t, t_g - 0.1, t_g + 0.4))
        if kg > 0:
            x, y = lerp(540, 250, kg), lerp(760, 700, kg)
            s = lerp(0.3, 1.0, kg)
            lock_icon(im, x, y, 150 * s, YELLOW, kg, 0.0, thick=9, glow=0.5)
            chip(im, "GÜVENLİK", x, y + 150 * s, YELLOW, kg, 30, anchor="mm")
        ka = ease_out(seg(t, t_ab - 0.1, t_ab + 0.4))
        if ka > 0:
            x, y = lerp(540, 830, ka), lerp(900, 700, ka)
            s = lerp(0.3, 1.0, ka)
            nodes = [(0, 0)] + [(math.cos(j * 1.047 + 0.5) * 90, math.sin(j * 1.047 + 0.5) * 90) for j in range(6)]
            for (a_, b_) in nodes[1:]:
                O.poly(im, [[x, y], [x + a_ * s, y + b_ * s]], CYAN, 3, ka * 0.8)
            for (a_, b_) in nodes:
                person_icon(im, x + a_ * s, y + b_ * s, 40 * s, CYAN, ka)
            chip(im, "ABONE", x, y + 150 * s, CYAN, ka, 30, anchor="mm")
        return im
    return img, post


# ================================================================== 21) YAŞAR: EKG monitörü
def _ecg(tau, beats):
    """tau anındaki sinyal (0 civarı taban, kalp atışlarında sivri tepe)."""
    v = 0.03 * np.sin(tau * 37) + 0.02 * np.sin(tau * 13.3)
    for tb, amp in beats:
        x = tau - tb
        v = v + amp * (np.exp(-((x) / 0.018) ** 2) * 1.0 - 0.35 * np.exp(-((x - 0.045) / 0.02) ** 2)
                       - 0.2 * np.exp(-((x + 0.04) / 0.02) ** 2)) + 0.18 * amp * np.exp(-((x - 0.22) / 0.06) ** 2)
    return v


def yasar(p, t, d, wt, lt):
    t_k = _w(wt, 3, 1.4)
    t_d = _w(wt, 6, 3.2)
    t_c = lt[2] if len(lt) > 2 else d * 0.55
    t_y = _w(wt, 14, 6.4)
    img = O.COOL.copy() * 0.9
    img = O.camera(img, 1.06 - 0.06 * ease_io(p))
    beats = [(t_k, 1.0), (t_d, 1.1)]
    tb = t_c
    while tb < d + 3:
        beats.append((tb, 0.85))
        tb += 0.78

    def post(im):
        O.label(im, "SONUÇ", color=GOLD, alpha=seg(t, 0.1, 0.4))
        kp = ease_out(seg(t, 0.0, 0.3))
        x0, y0, pw, ph = 80, 330, 920, 620
        O.glass(im, x0, y0, pw, ph, r=40, frost=14, tint=0.05, alpha=kp)
        O.rect_fill(im, x0, y0, pw, ph, np.zeros(3, np.float32), 0.45 * kp, r=40)
        for gx in range(x0 + 40, x0 + pw - 20, 60):
            O.rect_fill(im, gx, y0 + 30, 1, ph - 60, GREEN, 0.08 * kp)
        for gy in range(y0 + 50, y0 + ph - 20, 60):
            O.rect_fill(im, x0 + 30, gy, pw - 60, 1, GREEN, 0.08 * kp)
        span = 2.4
        xs = np.linspace(x0 + 40, x0 + pw - 60, 360)
        taus = t - span + (xs - xs[0]) / (xs[-1] - xs[0]) * span
        vals = _ecg(taus, beats)
        ys = y0 + ph / 2 + 40 - vals * 230
        vis = taus > 0
        pts = np.stack([xs[vis], ys[vis]], 1)
        if len(pts) > 2:
            O.poly(im, pts, GREEN, 5, kp, glow=0.9)
            O.circle(im, pts[-1][0], pts[-1][1], 9, ONE, fill=True, alpha=kp, glow=0.8)
        for tb_, name in ((t_k, "KAMU"), (t_d, "DEVLET")):
            if t > tb_:
                xx = xs[-1] - (t - tb_) / span * (xs[-1] - xs[0])
                if xx > x0 + 60:
                    ka = seg(t, tb_, tb_ + 0.2)
                    chip(im, name, xx, y0 + 160, YELLOW, ka, 26, anchor="mm")
                    O.poly(im, [[xx, y0 + 185], [xx, y0 + ph / 2 - 180]], YELLOW, 2, ka * 0.6)
        hb = max([math.exp(-((t - b) / 0.08) ** 2) for b, _ in beats if b <= t + 0.2] + [0.0])
        s = 1 + 0.18 * hb
        hx, hy = x0 + pw - 90, y0 + 80
        O.circle(im, hx - 13 * s, hy - 6 * s, 16 * s, RED, fill=True, alpha=kp)
        O.circle(im, hx + 13 * s, hy - 6 * s, 16 * s, RED, fill=True, alpha=kp)
        tri = np.array([[hx - 29 * s, hy], [hx + 29 * s, hy], [hx, hy + 32 * s]], np.float32)
        mm = np.zeros((H, W), np.uint8)
        cv2.fillPoly(mm, [np.round(tri * 4).astype(np.int32)], 255, cv2.LINE_AA, shift=2)
        G.over(im, RED, mm.astype(np.float32) / 255 * kp)
        O.text(im, "NABIZ", x0 + 50, y0 + 60, 26, "Inter.ttf", 700, GREEN, "lm", alpha=kp, tracking=5)
        ky = ease_out(seg(t, t_y - 0.1, t_y + 0.3))
        if ky > 0:
            chip(im, "YAŞAYACAK", 540, 1120, GREEN, ky, 44, anchor="mm", icon="check")
        return im
    return img, post


# ================================================================== 22) FİNAL: cebine girer mi? + kapanış kartı
def final(p, t, d, wt, lt):
    t_cb = _w(wt, 2, 0.7)
    t_b = lt[1] if len(lt) > 1 else d * 0.4
    t_end = (wt[-1] if wt else d * 0.6) + 0.9
    base = plate("cep_zemin")
    tel = plate("cep_tel")
    yama = plate("cep_yama")
    cm = meta("cep")
    ux, uy = cm["up_px_per_5cm"][:2]
    slide = ease_io(seg(t, t_cb - 0.15, t_cb + 0.85))
    off = 2.8 * (1 - slide)
    wob = 3 * math.sin(t * 5) * (1 - slide)
    pc = cm["phone_center"][:2]
    Mt = affine(1.0, pc, ux * off, uy * off, wob)
    trgb, ta = warp(tel["rgb"], Mt), warp(tel["alpha"], Mt)
    img = base["rgb"].copy()
    sh = G.blur(np.roll(np.roll(ta, 22, 0), 14, 1), 16) * 0.55
    img = img * (1 - sh[..., None])
    img = over_pm(img, trgb, ta)
    img = over_pm(img, yama["rgb"], yama["alpha"])
    hx, hy = hand(t, 2.5, 22)
    z = 1.2 + 0.1 * ease_io(p)
    img, _ = push(img, base["depth"], 1.0, z, z, c=(560, 900), dx=hx, dy=hy)
    kb = ease_out(seg(t, t_b - 0.15, t_b + 0.35))
    if kb > 0:
        img = G.blur(img, 14 * kb) * (1 - 0.84 * kb)
    ke = seg(t, t_end, t_end + 0.5)
    if ke > 0:
        img = img * (1 - 0.8 * ke)

    def post(im):
        O.label(im, "SON SÖZ", color=GOLD, alpha=seg(t, 0.1, 0.4) * (1 - kb))
        if kb > 0:
            a = min(1, kb * 1.5) * (1 - seg(t, t_end, t_end + 0.35))
            k1 = ease_out(seg(t, t_b - 0.05, t_b + 0.2))
            k2 = seg(t, _w(wt, 6, t_b + 0.3) - 0.05, _w(wt, 6, t_b + 0.3) + 0.15)
            O.text(im, "SEN", 540, 680, 150, "Montserrat.ttf", 900, ONE, alpha=a * k1, scale=lerp(1.3, 1.0, k1))
            if k2 > 0:
                dx, dy = O.shake(t, _w(wt, 6, t_b + 0.3) + 0.08, 10)
                O.text(im, "ALIR MISIN?", 540 + dx, 830 + dy, 118, "Montserrat.ttf", 900, YELLOW, alpha=a * min(1, k2 * 3),
                       scale=lerp(1.4, 1.0, ease_out(k2)), glow=0.3)
            O.text(im, "Yorumlara yaz.", 540, 960, 56, SERIF, None, ONE * 0.9,
                   alpha=a * ease_out(seg(t, t_b + 0.8, t_b + 1.2)))
        if ke > 0:
            O.text(im, "Takipte kal.", 540, 760, 92, SERIF, None, ONE, alpha=seg(t, t_end + 0.35, t_end + 0.75))
            O.text(im, "PARA NE DİYOR?", 540, 890, 64, "Montserrat.ttf", 900, YELLOW, alpha=seg(t, t_end + 0.5, t_end + 0.9),
                   tracking=10, glow=0.25)
            ln = seg(t, t_end + 0.6, t_end + 1.1)
            if ln > 0:
                im[948:952, int(540 - 210 * ln):int(540 + 210 * ln)] = YELLOW * 0.85
        return im
    return img, post
