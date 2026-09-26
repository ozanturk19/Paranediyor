"""Dijital dünya ve ekonomi sahneleri: soru, sen, dolaşım, dönüşüm, kredi, uğramaz,
100'lük ızgara, grafik, terazi, enflasyon, simit, final.  (İmza: f(p, t, d, wt) -> (görüntü, post))"""
import math
import cv2
import numpy as np
import gfx as G
import banknot as B
import ortak as O
import sahne1 as S1
from ortak import W, H, ONE, seg, ease_out, ease_in, ease_io, back, spring, lerp

rng0 = np.random.default_rng(23)
GOLDB = G.hexc("#E8B93A")


def fmt_tl(v):
    return "₺" + f"{int(v):,}".replace(",", ".")


# ================================================================== 8) SORU: dönen harf tabelası
ROWS = ["KİM KARAR", "VERİYOR?"]
ALPH = "ABCDEFGHIKLMNOPRSTUVYZÇĞİÖŞÜ?"
TILE_W, TILE_H, GAP = 94, 132, 9


def _tile_bg():
    t = np.zeros((TILE_H, TILE_W, 3), np.float32) + G.hexc("#24262E")
    t += np.linspace(0.07, -0.04, TILE_H, dtype=np.float32)[:, None, None]
    t[:2] += 0.12
    t[TILE_H // 2 - 1:TILE_H // 2 + 1] = G.hexc("#050506")
    return t, O.rounded(TILE_W, TILE_H, 10)


TILE, TILE_M = _tile_bg()


def soru(p, t, d, wt):
    img = O.NIGHT.copy()
    k = 0
    for r, row in enumerate(ROWS):
        n = len(row)
        x0 = 540 - (n * TILE_W + (n - 1) * GAP) / 2
        y0 = 600 + r * (TILE_H + 22)
        for i, ch in enumerate(row):
            k += 1
            appear = ease_out(seg(t, 0.03 * k, 0.03 * k + 0.25))
            if appear <= 0:
                continue
            x = int(x0 + i * (TILE_W + GAP))
            G.over(img, TILE, TILE_M * appear, x, int(y0))
            if ch == " ":
                continue
            settle = d * 0.38 + k * 0.055
            if t < settle:
                cyc = t / 0.075 + k * 0.37
                cur = ALPH[int(cyc * 7 + k * 5) % len(ALPH)]
                frac = cyc % 1
                sy = 0.25 + 0.75 * abs(math.cos(math.pi * frac))
                col = ONE * 0.8
            else:
                cur, sy, col = ch, 1.0, G.YELLOW
                sy = 1.0 - 0.6 * math.exp(-(t - settle) * 18) * abs(math.cos((t - settle) * 40))
            m = G.text_mask(cur, "Montserrat.ttf", 92, 900)
            mh = max(2, int(m.shape[0] * sy))
            m = cv2.resize(m, (m.shape[1], mh))
            G.over(img, col, m * appear, int(x + TILE_W / 2 - m.shape[1] / 2), int(y0 + TILE_H / 2 - mh / 2))
    img = O.camera(img, 1.0 + 0.04 * ease_io(p))
    return img, None


# ================================================================== 9) SEN: parmak izi + dev yazı
def _fingerprint():
    ridges = []
    for k in range(1, 30):
        th = np.linspace(0, 2 * math.pi, 400)
        r = 9.5 * k * (1 + 0.07 * np.sin(3 * th + k * 0.35) + 0.04 * np.sin(5 * th - k * 0.2))
        x = 540 + r * np.cos(th) * 0.8
        y = 760 + r * np.sin(th) * 1.05 - 18 * np.exp(-((th - 4.7) ** 2) / 0.3) * (k < 14)
        pts = np.stack([x, y], 1)
        cuts = sorted(rng0.integers(0, 400, 3))
        for a, b in zip([0] + cuts, cuts + [400]):
            if b - a > 12:
                ridges.append(pts[a + 3:b - 3])
    return ridges


FP = _fingerprint()


def sen(p, t, d, wt):
    t_sen = wt[1] if len(wt) > 1 else d * 0.45
    img = G.canvas(G.hexc("#030303"))
    q = ease_out(seg(t, 0.0, max(0.4, t_sen + 0.2)))
    m = np.zeros((H, W), np.uint8)
    for i, rd in enumerate(FP):
        n = int(len(rd) * np.clip(q * 1.4 - (i % 7) * 0.06, 0, 1))
        if n > 1:
            cv2.polylines(m, [np.round(rd[:n] * 4).astype(np.int32)], False, 255, 3, cv2.LINE_AA, shift=2)
    a = m.astype(np.float32) / 255
    fade = 1 - 0.55 * seg(t, t_sen, t_sen + 0.3)
    img += (a * 0.9 + G.blur(a, 6) * 0.8)[..., None] * G.GOLD * 1.3 * fade
    dx, dy = O.shake(t, t_sen, 22)
    img = O.camera(img, 1.0 + 0.06 * ease_out(p), dx=dx, dy=dy)
    img = O.flash(img, t, 0.0, 0.14, 0.8)

    def post(im):
        O.text(im, "Aslında", 540, 600, 74, "InstrumentSerif-Italic.ttf", None, ONE, alpha=seg(t, wt[0] - 0.05, wt[0] + 0.2))
        if t >= t_sen - 0.02:
            k = ease_out(seg(t, t_sen, t_sen + 0.2))
            for ghost, al in ((0.35, 0.25), (0.18, 0.4), (0.0, 1.0)):
                sc = lerp(2.4, 1.0, k) + ghost * (1 - k)
                O.text(im, "SEN.", 540 + dx, 790 + dy, 330, "Montserrat.ttf", 900, G.YELLOW, alpha=al * min(1, k * 3),
                       scale=sc, glow=0.35 if ghost == 0 else 0)
        return im
    return img, post


# ================================================================== 10) DOLAŞIM
CB = (290, 330, 500, 140)
BANKS = [(90, 640, 280, 110), (400, 640, 280, 110), (710, 640, 280, 110)]
PEOPLE = [(b[0] + 50 + (j % 3) * 90, 920 + (j // 3) * 70) for b in BANKS for j in range(6)]


def _bank_icon(img, x, y, c, a=1.0):
    O.poly(img, [[x - 34, y - 8], [x, y - 32], [x + 34, y - 8]], c, 4, a, closed=True)
    for i in range(4):
        O.poly(img, [[x - 24 + i * 16, y - 4], [x - 24 + i * 16, y + 22]], c, 5, a)
    O.poly(img, [[x - 36, y + 28], [x + 36, y + 28]], c, 5, a)


def _vault_icon(img, x, y, c, a=1.0):
    O.circle(img, x, y, 38, c, 5, a)
    O.circle(img, x, y, 10, c, 5, a)
    for k in range(6):
        an = k * math.pi / 3
        O.poly(img, [[x + 14 * math.cos(an), y + 14 * math.sin(an)], [x + 30 * math.cos(an), y + 30 * math.sin(an)]], c, 4, a)


def _person(img, x, y, c, a=1.0):
    O.circle(img, x, y - 16, 11, c, fill=True, alpha=a)
    O.arc(img, x, y + 18, 22, math.pi, 2 * math.pi, c, 7, a)


def _dolasim_bg():
    img = O.grid_lines(O.COOL.copy(), 60, 0.035)
    for bx, by, bw, bh in BANKS:
        O.poly(img, [[CB[0] + CB[2] / 2, CB[1] + CB[3]], [bx + bw / 2, by]], G.CYAN, 2, 0.18)
    for (px, py), bi in zip(PEOPLE, np.repeat(range(3), 6)):
        bx, by, bw, bh = BANKS[bi]
        O.poly(img, [[bx + bw / 2, by + bh], [px, py - 30]], G.CYAN, 1, 0.12)
    O.glass(img, *CB, r=36)
    for b in BANKS:
        O.glass(img, *b, r=30)
    _vault_icon(img, CB[0] + 80, CB[1] + CB[3] / 2, G.GOLD * 1.3)
    for bx, by, bw, bh in BANKS:
        _bank_icon(img, bx + 62, by + bh / 2, ONE * 0.85)
    for px, py in PEOPLE:
        _person(img, px, py, ONE * 0.8)
    return img


DOL_BG = _dolasim_bg()
DOL_BASE = O.grid_lines(O.COOL.copy(), 60, 0.035)


def _travel(img, glow, a, b, u, kind):
    x, y = lerp(a[0], b[0], u), lerp(a[1], b[1], u)
    if kind == "req":
        O.circle(img, x, y, 6, G.CYAN, fill=True)
        O.circle(glow, x, y, 9, G.CYAN, fill=True)
    else:
        O.rect_fill(img, x - 15, y - 8, 30, 16, GOLDB, 1.0, r=3)
        O.rect_fill(glow, x - 15, y - 8, 30, 16, GOLDB, 0.8, r=3)


def dolasim(p, t, d, wt):
    appear = ease_out(seg(p, 0.0, 0.18))
    img = DOL_BASE * (1 - appear) + DOL_BG * appear
    glow = np.zeros_like(img)
    cbp = (CB[0] + CB[2] / 2, CB[1] + CB[3])
    for j, (px, py) in enumerate(PEOPLE):                       # talepler: insan -> banka -> MB
        bx, by, bw, bh = BANKS[j // 6]
        for rep in range(2):
            u = seg(p, 0.16 + 0.012 * j + rep * 0.12, 0.3 + 0.012 * j + rep * 0.12)
            if 0 < u < 1:
                _travel(img, glow, (px, py - 30), (bx + bw / 2, by + bh), ease_io(u), "req")
    for i, (bx, by, bw, bh) in enumerate(BANKS):
        for rep in range(3):
            u = seg(p, 0.36 + 0.03 * i + rep * 0.05, 0.5 + 0.03 * i + rep * 0.05)
            if 0 < u < 1:
                _travel(img, glow, (bx + bw / 2, by), cbp, ease_io(u), "req")
    for i, (bx, by, bw, bh) in enumerate(BANKS):                # nakit: MB -> banka -> insan
        for rep in range(4):
            u = seg(p, 0.52 + 0.025 * i + rep * 0.06, 0.66 + 0.025 * i + rep * 0.06)
            if 0 < u < 1:
                _travel(img, glow, cbp, (bx + bw / 2, by), ease_io(u), "cash")
    for j, (px, py) in enumerate(PEOPLE):
        bx, by, bw, bh = BANKS[j // 6]
        u = seg(p, 0.72 + 0.01 * j, 0.86 + 0.01 * j)
        if 0 < u < 1:
            _travel(img, glow, (bx + bw / 2, by + bh), (px, py - 30), ease_io(u), "cash")
    img = O.add_glow(img, glow, (0.3, 0.7, 0.5))
    img = O.camera(img, 1.0 + 0.03 * ease_io(p))

    def post(im):
        a = appear
        O.text(im, "MERKEZ BANKASI", CB[0] + 150, CB[1] + CB[3] / 2, 34, "Inter.ttf", 700, ONE, "lm", a, tracking=2)
        for bx, by, bw, bh in BANKS:
            O.text(im, "BANKA", bx + 120, by + bh / 2, 28, "Inter.ttf", 700, ONE * 0.9, "lm", a, tracking=3)
        O.text(im, "İHTİYAÇ", 250, 830, 26, "Inter.ttf", 700, G.CYAN, alpha=seg(p, 0.2, 0.3) * (1 - seg(p, 0.55, 0.62)), tracking=4)
        O.text(im, "NAKİT", 830, 830, 26, "Inter.ttf", 700, GOLDB, alpha=seg(p, 0.55, 0.65), tracking=4)
        O.label(im, "07  ·  DOLAŞIM", color=G.CYAN, alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 11) DÖNÜŞÜM: banknot -> rakam -> telefon
PHONE = (620, 330, 360, 700)


def _phone_screen(img, x, y, w, h, alpha=0.92):
    O.glass(img, x, y, w, h, r=56, frost=16, tint=0.03)
    scr = np.zeros((h - 36, w - 36, 3), np.float32) + G.hexc("#061014")
    X, Y = G.grid(w - 36, h - 36)
    scr += np.exp(-((X - (w - 36) / 2) ** 2 + (Y - 240) ** 2) / (2 * 150 ** 2))[..., None] * G.hexc("#0F4D57") * 0.7
    G.over(img, scr, O.rounded(w - 36, h - 36, 42) * alpha, x + 18, y + 18)
    return img


def _dn_setup():
    bg = O.COOL.copy()
    _phone_screen(bg, *PHONE)
    x, y, w, h = PHONE
    O.text(bg, "BAKİYE", x + 50, y + 120, 22, "Inter.ttf", 600, ONE * 0.7, "lm", tracking=4)
    O.text(bg, "₺0,00", x + 48, y + 175, 54, "Montserrat.ttf", 900, ONE * 0.5, "lm")
    for i in range(4):
        O.rect_fill(bg, x + 48, y + 300 + i * 66, w - 96, 44, ONE * 0.08, 0.9, r=12)
    quad = O.project_quad(360, 1420, 700, rx=28, ry=8, rz=-8)
    note_layer = np.zeros_like(bg)
    O.place(note_layer, S1.NOTE_LIT, quad, shadow=0)
    alpha = np.zeros((H, W, 3), np.float32)
    O.place(alpha, np.ones((B.BH, B.BW, 3), np.float32), quad, shadow=0)
    alpha = alpha[..., 0]
    cells = []
    cw, ch = 13, 21
    xs = quad[:, 0]
    for gy in range(0, H - ch, ch):
        for gx in range(0, W - cw, cw):
            cy, cx = gy + ch // 2, gx + cw // 2
            if alpha[cy, cx] < 0.5:
                continue
            c = note_layer[gy:gy + ch, gx:gx + cw].reshape(-1, 3).mean(0)
            lum = float(c.mean())
            chh = O.RAMP[int(np.clip((1 - lum) * 1.9, 0, 0.999) * len(O.RAMP))]
            cells.append((cx, cy, c, chh if rng0.random() > 0.04 else "₺", rng0.normal(0, 60, 2), rng0.random()))
    return bg, note_layer, alpha, cells, float(xs.min()), float(xs.max())


DN_BG, DN_NOTE, DN_A, DN_CELLS, DN_X0, DN_X1 = _dn_setup()
DN_TARGET = np.array([PHONE[0] + 170, PHONE[1] + 180], float)


def donusum(p, t, d, wt):
    img = DN_BG.copy()
    xx = np.arange(W, dtype=np.float32)[None, :]
    yy = np.arange(H, dtype=np.float32)[:, None]
    fq = ease_io(seg(p, 0.04, 0.72))
    front = DN_X1 + 40 - fq * (DN_X1 - DN_X0 + 80)             # sağdan sola çözülür
    keep = np.clip((xx - (front + 22 * np.sin(yy / 37))) / 18, 0, 1) * DN_A
    img *= (1 - 0.6 * G.blur(np.roll(np.roll(keep, 40, 0), 20, 1), 22))[..., None]
    img = img * (1 - keep[..., None]) + DN_NOTE * keep[..., None]
    glow = np.zeros_like(img)
    arrived = 0
    for cx, cy, c, chh, jit, r in DN_CELLS:
        if cx < front:
            continue
        born = (DN_X1 + 40 - cx) / (DN_X1 - DN_X0 + 80)
        age = (fq - born) * d / 0.72
        u = np.clip(age / 1.1, 0, 1)
        if u >= 1:
            arrived += 1
            continue
        uu = u ** 1.2
        p0 = np.array([cx, cy], float)
        ctrl = p0 + np.array([80, -560])
        pos = (1 - uu) ** 2 * p0 + 2 * (1 - uu) * uu * ctrl + uu ** 2 * (DN_TARGET + jit)
        col = (1 - uu) * c * 1.2 + uu * (G.CYAN * (1 - uu) + G.YELLOW * uu)
        O.digit_sprite(img, glow, chh, pos[0], pos[1], col, 1 - 0.6 * uu, 20)
    img = O.add_glow(img, glow)
    halo = min(1.0, arrived / 500)
    x, y, w, h = PHONE
    ph = np.zeros((H, W), np.float32)
    ph[y:y + h, x:x + w] = O.rounded(w, h, 56)
    img += G.blur(ph, 40)[..., None] * G.CYAN * 0.35 * halo
    img = O.camera(img, 1.0 + 0.07 * ease_io(p), 760, 700)

    def post(im):
        O.label(im, "08  ·  YENİ PARA", color=G.CYAN, alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 12) KREDİ ekranı
KP = (220, 300, 640, 960)


def _kredi_bg():
    bg = O.grid_lines(O.COOL.copy(), 60, 0.03)
    _phone_screen(bg, *KP)
    x, y, w, h = KP
    O.text(bg, "Kredi başvurusu", x + w / 2, y + 110, 34, "Inter.ttf", 700, ONE * 0.85)
    O.circle(bg, 540, 620, 130, ONE * 0.08, 14)
    return bg


KR_BG = _kredi_bg()
BURST = rng0.uniform(0, 1, (260, 4)).astype(np.float32)


def kredi(p, t, d, wt):
    img = KR_BG.copy()
    glow = np.zeros_like(img)
    q1 = ease_io(seg(p, 0.04, 0.34))
    done = seg(p, 0.34, 0.4)
    col = G.CYAN * (1 - done) + G.YELLOW * done
    if q1 > 0:
        O.arc(img, 540, 620, 130, -math.pi / 2, -math.pi / 2 + 2 * math.pi * q1, col, 14)
        O.arc(glow, 540, 620, 130, -math.pi / 2, -math.pi / 2 + 2 * math.pi * q1, col, 14)
    if done <= 0:
        O.text(img, f"%{int(q1 * 100)}", 540, 620, 64, "Montserrat.ttf", 800, ONE * 0.9)
    else:
        ck = ease_out(seg(p, 0.35, 0.44))
        pts = np.array([[480, 622], [528, 668], [612, 572]], float)
        seglen = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
        L = seglen[-1] * ck
        k = np.searchsorted(seglen, L)
        path = list(pts[:k])
        if k < len(pts):
            f = (L - seglen[k - 1]) / (seglen[k] - seglen[k - 1])
            path.append(pts[k - 1] + (pts[k] - pts[k - 1]) * f)
        if len(path) > 1:
            O.poly(img, path, G.YELLOW, 16)
            O.poly(glow, path, G.YELLOW, 16)
    chip = spring(seg(p, 0.38, 0.5), 1.6, 6)
    if chip > 0:
        w_ = int(300 * min(1.15, chip))
        O.rect_fill(img, 540 - w_ / 2, 800, w_, 70, G.YELLOW, min(1, chip * 2), r=35)
    v = ease_out(seg(p, 0.46, 0.84)) * 250000
    speed = seg(p, 0.46, 0.5) * (1 - seg(p, 0.78, 0.84))
    for off, al in ((-26, 0.25 * speed), (26, 0.25 * speed), (0, 1.0)):
        O.text(img, fmt_tl(v), 540, 1020 + off, 104, "Montserrat.ttf", 900, ONE, alpha=al * seg(p, 0.44, 0.5),
               glow=0.3 if off == 0 else 0)
    bq = seg(p, 0.84, 1.0)
    if bq > 0:
        for bx, by, bs, bc in BURST:
            ang = bx * 2 * math.pi
            r = (80 + 520 * by) * ease_out(bq)
            x, y = 540 + math.cos(ang) * r * 1.2, 1020 + math.sin(ang) * r * 0.8
            c = G.YELLOW if bc > 0.5 else G.CYAN
            O.digit_sprite(img, glow, O.RAMP[int(bs * 11.99)], x, y, c, 1 - bq, 24)
    img = O.add_glow(img, glow)
    img = O.camera(img, 1.0 + 0.05 * ease_io(p), 540, 800)

    def post(im):
        if done > 0.5:
            O.text(im, "✓ Onaylandı", 540, 835, 36, "Inter.ttf", 700, G.hexc("#111111"), alpha=min(1, chip * 2))
        O.text(im, "BAKİYE", 540, 930, 26, "Inter.ttf", 600, ONE * 0.7, alpha=seg(p, 0.44, 0.5), tracking=5)
        O.label(im, "09  ·  KREDİ", color=G.CYAN, alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 13) HİÇBİR MATBAAYA UĞRAMAZ
def _press_icon(img, cx, cy, c, a):
    O.rect_fill(img, cx - 150, cy - 150, 300, 300, ONE * 0.04, a, r=24)
    O.poly(img, [[cx - 150, cy - 150], [cx + 150, cy - 150], [cx + 150, cy + 150], [cx - 150, cy + 150]], c, 5, a, True)
    O.circle(img, cx - 55, cy - 20, 62, c, 6, a)
    O.circle(img, cx + 55, cy - 20, 62, c, 6, a)
    O.poly(img, [[cx - 130, cy + 44], [cx + 130, cy + 44]], c, 6, a)
    O.poly(img, [[cx - 100, cy + 44], [cx - 100, cy + 110], [cx + 100, cy + 110], [cx + 100, cy + 44]], c, 4, a)


def ugramaz(p, t, d, wt):
    t_x = (wt[2] if len(wt) > 2 else d * 0.5) - 0.05
    img = O.NIGHT.copy()
    ap = ease_out(seg(t, 0, 0.35))
    xk = seg(t, t_x, t_x + 0.22)
    press_c = ONE * lerp(0.75, 0.35, xk)
    _press_icon(img, 320, 760, press_c, ap)
    glow = np.zeros_like(img)
    O.rect_fill(img, 700, 580, 200, 360, ONE * 0.05, ap, r=30)
    O.poly(img, [[700, 610], [700, 910]], G.CYAN, 5, ap)
    O.poly(img, [[900, 610], [900, 910]], G.CYAN, 5, ap)
    O.arc(img, 730, 610, 30, math.pi, 1.5 * math.pi, G.CYAN, 5, ap)
    O.arc(img, 870, 610, 30, 1.5 * math.pi, 2 * math.pi, G.CYAN, 5, ap)
    O.poly(img, [[730, 580], [870, 580]], G.CYAN, 5, ap)
    O.poly(img, [[730, 940], [870, 940]], G.CYAN, 5, ap)
    O.arc(img, 730, 910, 30, 0.5 * math.pi, math.pi, G.CYAN, 5, ap)
    O.arc(img, 870, 910, 30, 0, 0.5 * math.pi, G.CYAN, 5, ap)
    O.rect_fill(glow, 700, 580, 200, 360, G.CYAN, 0.25 * ap, r=30)
    if xk > 0:
        a0, a1 = np.array([150, 590]), np.array([490, 930])
        e = a0 + (a1 - a0) * ease_out(xk)
        O.poly(img, [a0, e], G.YELLOW, 22)
        O.poly(glow, [a0, e], G.YELLOW, 22)
    img = O.add_glow(img, glow)
    dx, dy = O.shake(t, t_x + 0.2, 9)
    img = O.camera(img, 1.0 + 0.04 * ease_io(p), dx=dx, dy=dy)

    def post(im):
        O.text(im, "₺", 800, 760, 120, "Montserrat.ttf", 900, G.CYAN, alpha=ap, glow=0.4)
        O.text(im, "MATBAA", 320, 960, 28, "Inter.ttf", 700, press_c * 1.2, alpha=ap, tracking=5)
        O.text(im, "EKRAN", 800, 990, 28, "Inter.ttf", 700, G.CYAN, alpha=ap, tracking=5)
        return im
    return img, post


# ================================================================== 14) 100 LİRANIN 3-4'Ü
MINI = cv2.resize(S1.NOTE_LIT, (84, 40), interpolation=cv2.INTER_AREA)
GX0, GY0, GDX, GDY = 84, 430, 92, 50
KEEP = {(4, 4): 1.0, (5, 4): 1.0, (4, 5): 1.0, (5, 5): 0.45}
TILE_SEEDS = rng0.uniform(0, 1, (10, 10, 6)).astype(np.float32)
_wall = np.zeros((H, W, 1), np.float32)
for _j in range(0, 520, 24):
    for _i in range(0, 900, 15):
        if rng0.random() < 0.7:
            m = O.glyph(O.RAMP[rng0.integers(2, len(O.RAMP))], 18)
            G.over(_wall, np.ones(1, np.float32), m * rng0.uniform(0.2, 0.7), 90 + _i, 420 + _j)
WALL = _wall[..., 0]


def grid(p, t, d, wt):
    t_d = (wt[4] if len(wt) > 4 else d * 0.35) - 0.1           # "sadece"
    t_g = (wt[8] if len(wt) > 8 else d * 0.7) - 0.1            # "Gerisi"
    img = O.COOL.copy() * 0.8
    glow = np.zeros_like(img)
    wall = seg(t, t_g, t_g + 0.5)
    if wall > 0:
        flick = 0.85 + 0.15 * math.sin(t * 23)
        img += (WALL * wall * flick * 0.55)[..., None] * G.CYAN
        glow += (WALL * wall * 0.3)[..., None] * G.CYAN
    for j in range(10):
        for i in range(10):
            s = TILE_SEEDS[j, i]
            ap = ease_out(seg(t, 0.05 + 0.025 * (i + j), 0.25 + 0.025 * (i + j)))
            if ap <= 0:
                continue
            x, y = GX0 + i * GDX, GY0 + j * GDY
            kv = KEEP.get((i, j))
            if kv is None:
                dq = seg(t, t_d + s[0] * 0.45, t_d + s[0] * 0.45 + 0.7)
                if dq >= 1:
                    continue
                if dq > 0:
                    for k in range(3):
                        px_ = x + 42 + (s[k + 1] - 0.5) * 80 * dq
                        py_ = y + 20 - (60 + 260 * s[k + 3 if k < 3 else 5]) * dq ** 1.2
                        O.digit_sprite(img, glow, O.RAMP[int(s[k + 1] * 11.99)], px_, py_, G.CYAN, 1 - dq, 18)
                G.over(img, MINI, np.ones(MINI.shape[:2], np.float32) * ap * (1 - dq) ** 2, x, y)
            else:
                hl = ease_out(seg(t, t_d + 0.3, t_d + 0.7))
                sc = 1 + 0.12 * hl
                tile = cv2.resize(MINI, (int(84 * sc), int(40 * sc)))
                G.over(img, tile * (1 + 0.25 * hl), np.ones(tile.shape[:2], np.float32) * ap * kv,
                       int(x + 42 - tile.shape[1] / 2), int(y + 20 - tile.shape[0] / 2))
                if hl > 0:
                    O.rect_fill(glow, x - 4, y - 4, 92, 48, GOLDB, 0.6 * hl * kv, r=6)
    img = O.add_glow(img, glow, (0.3, 0.8, 0.6))
    img = O.camera(img, 1.0 + 0.05 * ease_io(p), 540, 700)

    def post(im):
        O.text(im, "100 ₺", 540, 350, 64, "Montserrat.ttf", 900, ONE, alpha=seg(t, 0.2, 0.5) * (1 - seg(t, t_d, t_d + 0.4)))
        k = seg(t, t_d + 0.35, t_d + 0.6)
        O.text(im, "3-4 ₺", 540, 1030, 120, "Montserrat.ttf", 900, G.YELLOW, alpha=k, scale=lerp(1.3, 1, ease_out(k)), glow=0.3)
        O.text(im, "NAKİT", 540, 1130, 32, "Inter.ttf", 700, GOLDB, alpha=k, tracking=8)
        O.text(im, "GERİSİ: EKRANDA", 540, 350, 40, "Inter.ttf", 800, G.CYAN, alpha=wall, tracking=6)
        O.label(im, "10  ·  NAKİT", color=G.CYAN, alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 15) GRAFİK: para vs üretim
CX0, CY0, CX1, CY1 = 130, 430, 950, 1070


def _curve(fn, xmax, n=120):
    xs = np.linspace(0, xmax, max(2, int(n * xmax)))
    return np.stack([CX0 + xs * (CX1 - CX0), CY1 - fn(xs) * (CY1 - CY0)], 1)


F_PARA = lambda x: 0.06 + 0.9 * (np.exp(3.2 * x) - 1) / (math.exp(3.2) - 1)
F_URET = lambda x: 0.06 + 0.28 * x


def grafik(p, t, d, wt):
    img = O.grid_lines(O.NIGHT.copy(), 60, 0.025, ONE)
    O.poly(img, [[CX0, CY0 - 20], [CX0, CY1], [CX1 + 20, CY1]], ONE * 0.5, 3, 0.8)
    xm = ease_io(seg(p, 0.06, 0.8))
    glow = np.zeros_like(img)
    if xm > 0.01:
        cp, cu = _curve(F_PARA, xm), _curve(F_URET, xm)
        gap = seg(p, 0.5, 0.8)
        if gap > 0:
            poly_ = np.vstack([cp, cu[::-1]]).astype(np.int32)
            m = np.zeros((H, W), np.uint8)
            cv2.fillPoly(m, [poly_], 255, cv2.LINE_AA)
            yy = np.arange(H, dtype=np.float32)[:, None]
            grad = np.clip((CY1 - yy) / (CY1 - CY0), 0, 1)
            G.over(img, G.YELLOW, m.astype(np.float32) / 255 * grad * 0.22 * gap)
        for c, col in ((cu, G.CYAN), (cp, G.YELLOW)):
            O.poly(img, c, col, 8)
            O.poly(glow, c, col, 8)
            O.circle(img, c[-1][0], c[-1][1], 12, col, fill=True)
            O.circle(glow, c[-1][0], c[-1][1], 22, col, fill=True, alpha=0.6)
        heads = (cp[-1], cu[-1])
    else:
        heads = None
    img = O.add_glow(img, glow)
    img = O.camera(img, 1.0 + 0.04 * ease_io(p))

    def post(im):
        O.text(im, "zaman →", CX1 - 60, CY1 + 40, 26, "Inter.ttf", 500, ONE * 0.55)
        if heads is not None and xm > 0.3:
            (px_, py_), (ux, uy) = heads
            a = seg(xm, 0.3, 0.45)
            O.text(im, "PARA", px_ - 24, py_ - 42, 36, "Montserrat.ttf", 900, G.YELLOW, "rm", alpha=a)
            O.text(im, "ÜRETİM", ux - 10, uy + 44, 32, "Montserrat.ttf", 900, G.CYAN, "rm", alpha=a)
            gp = seg(p, 0.62, 0.85)
            fx = 0.86 * xm
            gx = CX0 + fx * (CX1 - CX0)
            gy = (CY1 - F_PARA(fx) * (CY1 - CY0) + CY1 - F_URET(fx) * (CY1 - CY0)) / 2
            O.text(im, "FARK", gx, gy + 6, 30, "Inter.ttf", 800, G.YELLOW, alpha=gp, tracking=6)
        O.label(im, "11  ·  PARA ARZI", color=G.YELLOW, alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 16) TERAZİ
PIV = np.array([540.0, 470.0])


def terazi(p, t, d, wt):
    t_f = (wt[6] if len(wt) > 6 else d * 0.6) - 0.1           # "fiyatlar"
    img = O.WARM.copy() * 0.9
    th = math.radians(12) * spring(seg(p, 0.15, 0.85), 1.1, 4.5)
    Lp = PIV + np.array([-330 * math.cos(th), 330 * math.sin(th)])
    Rp = PIV + np.array([330 * math.cos(th), -330 * math.sin(th)])
    gold = G.hexc("#C9A13B")
    O.poly(img, [[540, 470], [540, 1130]], gold * 0.8, 12)
    base = np.float32([[430, 1130], [650, 1130], [690, 1175], [390, 1175]])
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [base.astype(np.int32)], 255, cv2.LINE_AA)
    G.over(img, gold * 0.6, m.astype(np.float32) / 255)
    O.poly(img, [Lp, Rp], gold, 12)
    O.circle(img, 540, 470, 16, gold * 1.1, fill=True)
    pans = []
    for e in (Lp, Rp):
        pan = e + np.array([0, 300])
        O.poly(img, [e, pan + (-95, 0)], ONE * 0.6, 2)
        O.poly(img, [e, pan + (95, 0)], ONE * 0.6, 2)
        em = np.zeros((H, W), np.uint8)
        cv2.ellipse(em, (int(pan[0]), int(pan[1])), (110, 20), 0, 0, 180, 255, -1, cv2.LINE_AA)
        G.over(img, gold * 0.75, em.astype(np.float32) / 255)
        pans.append(pan)
    n = int(2 + 15 * ease_io(seg(p, 0.1, 0.8)))
    for i in range(n):
        y = pans[0][1] - 12 - i * 11
        O.rect_fill(img, pans[0][0] - 75, y, 150, 10, G.hexc("#E9DDB8") * (0.85 + 0.15 * (i % 2)), 1.0, r=2)
        O.rect_fill(img, pans[0][0] - 75, y + 8, 150, 2, TEALISH, 1.0)
    rx, ry = pans[1]
    O.circle(img, rx - 50, ry - 34, 30, G.hexc("#C8843A"), 13)
    O.rect_fill(img, rx - 5, ry - 62, 58, 44, G.hexc("#D9A45A"), 1.0, r=16)
    O.rect_fill(img, rx + 60, ry - 78, 34, 60, ONE * 0.9, 1.0, r=4)
    rise = seg(t, t_f, t_f + 1.2)
    img = O.camera(img, 1.0 + 0.04 * ease_io(p))

    def post(im):
        O.text(im, "PARA", pans[0][0], pans[0][1] + 60, 30, "Inter.ttf", 800, G.YELLOW, tracking=5)
        O.text(im, "MAL", pans[1][0], pans[1][1] + 60, 30, "Inter.ttf", 800, ONE, tracking=5)
        if rise > 0:
            v = 10 + 30 * ease_out(rise)
            ty = pans[1][1] - 190 - 20 * ease_out(rise)
            O.rect_fill(im, pans[1][0] - 90, ty - 40, 180, 80, G.YELLOW, min(1, rise * 3), r=16)
            O.text(im, f"₺{int(v)} ↑", pans[1][0], ty, 44, "Montserrat.ttf", 900, G.hexc("#111111"), alpha=min(1, rise * 3))
        O.label(im, "12  ·  FİYATLAR", alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


TEALISH = G.hexc("#1E5E63")


# ================================================================== 17) ENFLASYON: şişen balon yazı
WORD = "ENFLASYON"
LET = [G.text_mask(c, "Montserrat.ttf", 170, 900) for c in WORD]


def enflasyon(p, t, d, wt):
    img = O.NIGHT.copy()
    grow = spring(seg(p, 0.08, 0.95), 1.3, 3.8)
    fit = 930 / (sum(m.shape[1] for m in LET) * 0.93 * 1.12)
    sc = lerp(0.5, 1.12, grow) * fit
    widths = [m.shape[1] * sc * 0.93 for m in LET]
    x = 540 - sum(widths) / 2
    M3 = np.zeros((H, W, 1), np.float32)
    for i, m in enumerate(LET):
        wob = 1 + 0.06 * math.sin(t * 6 + i * 1.3) * grow
        mm = cv2.resize(m, (max(2, int(m.shape[1] * sc * wob)), max(2, int(m.shape[0] * sc / wob ** 0.5))))
        yy = 800 - mm.shape[0] / 2 + math.sin(t * 4 + i) * 10 * grow
        G.over(M3, np.ones(1, np.float32), mm, int(x + widths[i] / 2 - mm.shape[1] / 2), int(yy))
        x += widths[i]
    M = M3[..., 0]
    x0 = int(max(0, 540 - sum(widths) / 2 - 60))
    x1 = int(min(W, 540 + sum(widths) / 2 + 60))
    sub = M[560:1040, x0:x1]
    h = G.blur(sub, 10 * sc) ** 0.7 * sub
    col = np.zeros(sub.shape + (3,), np.float32) + G.hexc("#FFB21E")
    lit = G.relief(col, G.blur(h, 3) * 7, light=(-0.5, -0.8, 0.55), strength=3, spec=0.9, shininess=46)
    region = img[560:1040, x0:x1]
    region *= (1 - 0.6 * G.blur(np.roll(sub, 24, 0), 16))[..., None]
    region[:] = region * (1 - sub[..., None]) + lit * sub[..., None]
    img = O.camera(img, 1.0 + 0.05 * ease_io(p))

    def post(im):
        O.text(im, "İşte buna", 540, 560, 70, "InstrumentSerif-Italic.ttf", None, ONE, alpha=seg(t, wt[0] - 0.05, wt[0] + 0.2))
        O.text(im, "diyoruz.", 540, 1070, 70, "InstrumentSerif-Italic.ttf", None, ONE,
               alpha=seg(t, wt[3] - 0.05, wt[3] + 0.2) if len(wt) > 3 else seg(p, 0.7, 0.8))
        O.label(im, "13  ·  ENFLASYON", alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 18) SİMİT ve KİRA
def _simit_tex(s=300):
    X, Y = G.grid(s, s)
    r = np.hypot(X - s / 2, Y - s / 2)
    prof = np.clip(1 - ((r - 100) / 45) ** 2, 0, 1)
    a = G.smoothstep(0.0, 0.08, prof)
    height = np.sqrt(prof) * 1.0
    col = np.zeros((s, s, 3), np.float32) + G.hexc("#B8702C")
    col *= (0.75 + 0.35 * np.clip(1 - (Y - s / 2) / 150, 0, 1))[..., None]
    for _ in range(90):
        ang, rr = rng0.uniform(math.pi * 1.05, math.pi * 1.95), rng0.uniform(70, 135)
        cx, cy = s / 2 + rr * math.cos(ang), s / 2 + rr * math.sin(ang) * 0.95
        m = np.zeros((s, s), np.uint8)
        cv2.ellipse(m, (int(cx), int(cy)), (5, 3), rng0.uniform(0, 180), 0, 360, 255, -1, cv2.LINE_AA)
        mm = m.astype(np.float32) / 255 * a
        col = col * (1 - mm[..., None]) + G.hexc("#F4E4C0") * mm[..., None]
        height = height + mm * 0.25
    return G.relief(col, G.blur(height, 1.5) * 18, light=(-0.5, -0.7, 0.8), strength=1.2, spec=0.3), a


SIMIT, SIMIT_A = _simit_tex()
SL_CARD, SR_CARD = (80, 440, 440, 600), (560, 440, 440, 600)


def _house(img, cx, cy, c, a):
    O.poly(img, [[cx - 110, cy - 10], [cx, cy - 110], [cx + 110, cy - 10]], c, 9, a)
    O.poly(img, [[cx - 85, cy - 25], [cx - 85, cy + 100], [cx + 85, cy + 100], [cx + 85, cy - 25]], c, 9, a)
    O.poly(img, [[cx - 22, cy + 100], [cx - 22, cy + 30], [cx + 22, cy + 30], [cx + 22, cy + 100]], c, 7, a)


def _roll(im, x, y, t, seed, alpha):
    v = 10 + (t * 37 + seed) % 90
    for off, al in ((-22, 0.25), (22, 0.25), (0, 1.0)):
        O.text(im, f"₺{int((v + off) % 100):02d}", x, y + off, 64, "Montserrat.ttf", 900, ONE, alpha=al * alpha)
    O.text(im, "↑", x + 120, y - 10 * abs(math.sin(t * 6)), 60, "Montserrat.ttf", 900, G.YELLOW, alpha=alpha, glow=0.3)


def simit(p, t, d, wt):
    t_k = (wt[1] if len(wt) > 1 else d * 0.3) - 0.1
    img = O.WARM.copy() * 0.8
    la = ease_out(seg(t, 0, 0.35))
    ra = ease_out(seg(t, t_k, t_k + 0.35))
    O.glass(img, SL_CARD[0], SL_CARD[1] + int(40 * (1 - la)), SL_CARD[2], SL_CARD[3], r=40, alpha=la)
    if ra > 0:
        O.glass(img, SR_CARD[0] + int(120 * (1 - ra)), SR_CARD[1], SR_CARD[2], SR_CARD[3], r=40, alpha=ra)
    sx, sy = SL_CARD[0] + SL_CARD[2] // 2 - 150, SL_CARD[1] + 70 + int(40 * (1 - la))
    G.over(img, SIMIT, SIMIT_A * la, sx, sy)
    if ra > 0:
        _house(img, SR_CARD[0] + SR_CARD[2] / 2 + 120 * (1 - ra), SR_CARD[1] + 230, ONE * 0.9, ra)
    img = O.camera(img, 1.0 + 0.04 * ease_io(p))

    def post(im):
        O.text(im, "SİMİT", SL_CARD[0] + SL_CARD[2] / 2, SL_CARD[1] + 420, 34, "Inter.ttf", 800, ONE, alpha=la, tracking=6)
        _roll(im, SL_CARD[0] + SL_CARD[2] / 2 - 40, SL_CARD[1] + 510, t, 3, la)
        if ra > 0:
            cx = SR_CARD[0] + SR_CARD[2] / 2 + 120 * (1 - ra)
            O.text(im, "KİRA", cx, SR_CARD[1] + 420, 34, "Inter.ttf", 800, ONE, alpha=ra, tracking=6)
            _roll(im, cx - 40, SR_CARD[1] + 510, t * 1.3, 7, ra)
        O.label(im, "14  ·  HAYAT", alpha=seg(t, 0.1, 0.5))
        return im
    return img, post


# ================================================================== 19) FİNAL
_bub, _gly, EX, EY = S1.NOTE["emblem"]
EW, EH = _bub.shape[1], _bub.shape[0]


def final(p, t, d, wt):
    img = O.WARM.copy()
    la = t * 0.9 - 2.2
    lit = G.relief(S1.NOTE["color"], S1.NOTE["height"], light=(math.cos(la), math.sin(la), 0.7), strength=5,
                   spec=0.45) * 0.86
    lift = ease_io(seg(p, 0.05, 0.4))
    fy = 1330 + math.sin(t * 1.2) * 8
    quad = O.project_quad(540, fy, 900, rx=38, rz=-4)
    dim = 0.75 - 0.3 * lift
    O.place(img, lit * dim, quad, shadow=0.55)
    if lift > 0:
        em = lit[EY - 20:EY + EH + 20, EX - 20:EX + EW + 20]
        ea = np.pad(_bub, 20)
        sc = lerp(0.56, 1.35, ease_out(lift))
        ew, eh = int(em.shape[1] * sc), int(em.shape[0] * sc)
        tex = cv2.resize(em, (ew, eh))
        ta = cv2.resize(ea, (ew, eh))
        cx, cy = lerp(700, 540, ease_out(lift)), lerp(1250, 480, ease_out(lift))
        sh = np.zeros((H, W), np.float32)
        G.over(sh[..., None], np.ones(1, np.float32), ta, int(cx - ew / 2 + 20), int(cy - eh / 2 + 40))
        img *= (1 - 0.6 * G.blur(sh, 20))[..., None]
        G.over(img, tex * 1.05, ta, int(cx - ew / 2), int(cy - eh / 2))
    img = O.camera(img, 1.0 + 0.04 * ease_io(p))
    end_t = (wt[-1] if wt else d * 0.5) + 0.7

    def post(im):
        words = ["Para", "her", "zaman", "bir", "şey", "söyler."]
        line1, line2 = " ".join(words[:3]), " ".join(words[3:])
        a1 = seg(t, wt[0] - 0.05, wt[0] + 0.2) if wt else 1
        a2 = seg(t, wt[3] - 0.05, wt[3] + 0.2) if len(wt) > 3 else seg(p, 0.5, 0.6)
        O.text(im, line1, 540, 770, 78, "Montserrat.ttf", 800, ONE, alpha=a1)
        O.text(im, "bir şey", 430, 870, 78, "Montserrat.ttf", 800, ONE, alpha=a2)
        O.text(im, "söyler.", 700, 875, 96, "InstrumentSerif-Italic.ttf", None, G.YELLOW, alpha=a2, glow=0.25)
        e = seg(t, end_t, end_t + 0.4)
        O.text(im, "PARA NE DİYOR?", 540, 1020, 46, "Montserrat.ttf", 900, G.YELLOW, alpha=e, tracking=10)
        if e > 0:
            im[1062:1065, int(540 - 150 * e):int(540 + 150 * e)] = G.YELLOW * 0.8
        return im
    return img, post


SAHNELER = dict(soru=soru, sen=sen, dolasim=dolasim, donusum=donusum, kredi=kredi, ugramaz=ugramaz, grid=grid,
                grafik=grafik, terazi=terazi, enflasyon=enflasyon, simit=simit, final=final)
