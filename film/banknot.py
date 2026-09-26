"""Hayali "Para Ne Diyor?" banknotu: güvenlik baskısı estetiğiyle, tamamen prosedürel.

Gerçek bir banknotun tasarımını taklit etmez (portre, kurum adı, resmi ibare yok).
Katmanlar ayrı döner; film sahneleri onları tek tek canlandırabilir.
"""
import math
import cv2
import numpy as np
from gfx import (GOLD, MONO, PAPER, RED, TEAL, blur, grid, smoothstep, text_mask)

BW, BH = 1600, 760


def _poly(mask, pts, thick=1, frac=1.0):
    n = max(2, int(len(pts) * frac))
    cv2.polylines(mask, [np.round(pts[:n] * 4).astype(np.int32)], False, 255, thick, cv2.LINE_AA, shift=2)


def rosette_curves(cx, cy, R0, n=36, samples=2400):
    """İç içe geçmiş spirograf eğrileri (guilloche rozeti)."""
    t = np.linspace(0, 6 * math.pi, samples)
    curves = []
    Rr, r = 11.0, 3.0
    for i in range(n):
        d = 1.2 + 1.6 * i / n
        rot = i * (2 * math.pi / n) * 0.5
        x = (Rr - r) * np.cos(t) + d * np.cos((Rr - r) / r * t)
        y = (Rr - r) * np.sin(t) - d * np.sin((Rr - r) / r * t)
        s = R0 / (Rr - r + d)
        xr, yr = x * math.cos(rot) - y * math.sin(rot), x * math.sin(rot) + y * math.cos(rot)
        curves.append(np.stack([cx + xr * s, cy + yr * s], 1))
    return curves


def wave_band(x0, x1, yc, amp, n=16, spread=46, samples=1800):
    x = np.linspace(x0, x1, samples)
    out = []
    for i in range(n):
        ph = i * 0.42
        y = yc + (i - n / 2) * spread / n + amp * np.sin(x / 38 + ph) * np.cos(x / 97 - ph * 0.5)
        out.append(np.stack([x, y], 1))
    return out


def engraving(mask, spacing=7.0, angle=0.0, shade=None, wobble=5.0, period=42.0):
    """Gravür çizgileri: gölgeye göre kalınlaşan dalgalı paralel çizgiler."""
    h, w = mask.shape
    xx, yy = grid(w, h)
    ca, sa = math.cos(angle), math.sin(angle)
    u = -xx * sa + yy * ca
    v = xx * ca + yy * sa
    wave = 0.5 + 0.5 * np.sin(2 * math.pi * (u + wobble * np.sin(v / period)) / spacing)
    if shade is None:
        shade = np.full_like(mask, 0.5)
    th = 1 - np.clip(shade, 0.02, 0.98)
    return smoothstep(th - 0.09, th + 0.09, wave) * mask


def emblem_mask(size=(390, 310)):
    """Konuşma balonu içinde ₺: 'para konuşur' amblemi."""
    w, h = size
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (30, 20), (w - 30, h - 80), 255, -1, cv2.LINE_AA)
    m = cv2.GaussianBlur(m, (0, 0), 1)
    rr = np.zeros_like(m)
    cv2.rectangle(rr, (0, 0), (w, h), 0, -1)
    # yuvarlatılmış köşe: kapat-aç ile
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (81, 81))
    m = cv2.morphologyEx(cv2.erode(m, k), cv2.MORPH_DILATE, k)
    tail = np.array([[w * 0.30, h - 90], [w * 0.22, h - 8], [w * 0.47, h - 90]], np.int32)
    cv2.fillPoly(m, [tail], 255, cv2.LINE_AA)
    glyph = text_mask("₺", "Montserrat.ttf", int((h - 100) * 1.1), 900)
    gh, gw = glyph.shape
    gy, gx = (h - 80) // 2 - gh // 2 + int(h * 0.045), w // 2 - gw // 2
    g = np.zeros((h, w), np.float32)
    ys, xs = max(0, gy), max(0, gx)
    ye, xe = min(h, gy + gh), min(w, gx + gw)
    g[ys:ye, xs:xe] = glyph[ys - gy:ye - gy, xs - gx:xe - gx]
    return m.astype(np.float32) / 255, g


def banknote(draw=1.0, seed=7):
    """Banknotu katmanlarıyla üret. draw: desenlerin çizilme oranı (0-1)."""
    rng = np.random.default_rng(seed)
    xx, yy = grid(BW, BH)
    # --- kâğıt: pamuk lifleri + düşük frekanslı dalgalanma
    base = np.ones((BH, BW, 3), np.float32) * PAPER
    lowf = blur(rng.normal(0, 1, (BH, BW)).astype(np.float32), 40) * 6
    base *= (1 + 0.035 * lowf)[..., None]
    fib = np.zeros((BH, BW), np.uint8)
    for _ in range(420):
        x0, y0 = rng.uniform(0, BW), rng.uniform(0, BH)
        ang, ln = rng.uniform(0, math.pi), rng.uniform(8, 26)
        pts = np.array([[x0 + math.cos(ang) * s + 3 * math.sin(s / 5), y0 + math.sin(ang) * s] for s in np.linspace(0, ln, 8)])
        cv2.polylines(fib, [pts.astype(np.int32)], False, int(rng.uniform(30, 75)), 1, cv2.LINE_AA)
    fibers = fib.astype(np.float32) / 255
    base *= (1 - 0.07 * fibers)[..., None]
    # hafif renk geçişi (sol teal, sağ altın)
    tint = np.clip(xx / BW, 0, 1)[..., None]
    base = base * (1 - 0.08 * (1 - tint) * (1 - TEAL)) * (1 - 0.06 * tint * (1 - GOLD))

    iris = np.exp(-((yy - BH * 0.52) / 170) ** 2)[..., None] * 0.07
    base = base * (1 - iris) + iris * (np.dstack([0.9 + 0.1 * np.sin(xx / 260), 0.85 + 0.1 * np.sin(xx / 260 + 2), 0.55 + 0.2 * np.sin(xx / 260 + 4)]))
    mesh = smoothstep(0.93, 0.99, 0.5 + 0.5 * np.sin((yy + 9 * np.sin(xx / 55)) / 2.2)) * 0.10
    layers = [("mesh", TEAL * 0.9, mesh, 0.05)]    # (ad, renk, alfa, yükseklik ağırlığı)
    # --- güvenlik rozeti (sol)
    ros = np.zeros((BH, BW), np.uint8)
    for c in rosette_curves(330, 380, 250, n=22):
        _poly(ros, c, 1, draw)
    for c in rosette_curves(330, 380, 118, n=14):
        _poly(ros, c, 1, draw)
    layers.append(("rosette", TEAL * 0.9, ros.astype(np.float32) / 255 * 0.75, 0.6))
    # --- kenar dalga bantları
    wav = np.zeros((BH, BW), np.uint8)
    for band in (wave_band(40, BW - 40, 70, 16), wave_band(40, BW - 40, BH - 70, 16)):
        for c in band:
            _poly(wav, c, 1, draw)
    layers.append(("waves", GOLD * 0.85, wav.astype(np.float32) / 255 * 0.9, 0.5))
    # --- filigran penceresi (açık oval) + soluk amblem
    wm = np.exp(-(((xx - 330) / 125) ** 2 + ((yy - 380) / 175) ** 2) ** 2)
    base = base * (1 + 0.07 * wm[..., None])
    # --- gravür amblem (sağ)
    bub, glyph = emblem_mask()
    eh, ew = bub.shape
    ex, ey = 1170, 130
    dist = cv2.distanceTransform((bub > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
    ex_x, ex_y = grid(ew, eh)
    bulge = np.clip(dist / 70, 0, 1)
    light = 0.5 + 0.5 * np.clip(((ex_x - ew * 0.3) + (ex_y - eh * 0.3)) / (ew + eh) * 2, -1, 1)
    shade = np.clip(0.95 - 0.55 * bulge - 0.25 * light, 0, 1)
    emb = engraving(bub * (1 - glyph), spacing=6.5, angle=0.35, shade=shade)
    edge = np.clip(cv2.dilate(glyph, np.ones((5, 5), np.uint8)) - glyph, 0, 1)
    emb = np.maximum(emb, edge * 0.95)
    E = np.zeros((BH, BW), np.float32)
    E[ey:ey + eh, ex:ex + ew] = emb
    layers.append(("emblem", TEAL * 0.55, E * (0.3 + 0.7 * min(1, draw * 1.4)), 1.0))
    # --- "100" (çizgi dokulu dev rakam)
    num = text_mask("100", "Montserrat.ttf", 210, 900)
    nh, nw = num.shape
    N = np.zeros((BH, BW), np.float32)
    nx, ny = BW - nw - 70, BH - nh - 70
    N[ny:ny + nh, nx:nx + nw] = num
    fill = engraving(N, spacing=5.0, angle=-0.6, shade=np.full_like(N, 0.55), wobble=0)
    outline = np.clip(cv2.dilate(N, np.ones((3, 3), np.uint8)) - cv2.erode(N, np.ones((3, 3), np.uint8)), 0, 1)
    layers.append(("num100", TEAL * 0.7, np.maximum(fill, outline), 0.9))
    small = text_mask("100", "Montserrat.ttf", 70, 900)
    S = np.zeros((BH, BW), np.float32)
    S[70:70 + small.shape[0], 700:700 + small.shape[1]] = small
    layers.append(("small100", GOLD * 0.8, S * 0.9, 0.8))
    # --- yazılar: marka, mikro yazı, seri no
    wmk = text_mask("PARA NE DİYOR?", "Montserrat.ttf", 40, 800, tracking=5)
    T = np.zeros((BH, BW), np.float32)
    T[160:160 + wmk.shape[0], 640:640 + wmk.shape[1]] = wmk
    micro = text_mask("PARANEDİYOR · " * 12, "Inter.ttf", 11, 600)
    T[218:218 + micro.shape[0], 640:640 + min(micro.shape[1], 470)] = micro[:, :470] * 0.8
    yuz = text_mask("YÜZ", "Montserrat.ttf", 34, 700, tracking=10)
    T[260:260 + yuz.shape[0], 640:640 + yuz.shape[1]] = yuz
    layers.append(("texts", TEAL * 0.8, T, 0.7))
    ser = text_mask("PND 004721", MONO, 34)
    Sr = np.zeros((BH, BW), np.float32)
    Sr[70:70 + ser.shape[0], 80:80 + ser.shape[1]] = ser
    Sr[BH - 120:BH - 120 + ser.shape[0], 700:700 + ser.shape[1]] = ser
    layers.append(("serial", RED, Sr, 0.4))
    # --- güvenlik şeridi (pencereli metalik bant)
    thread = ((xx > 596) & (xx < 622)).astype(np.float32)
    window = (np.sin(yy / 22) > -0.2).astype(np.float32)
    metal = 0.55 + 0.3 * np.sin(yy / 3.1) * np.cos(yy / 17)
    tcol = np.dstack([metal * 0.86, metal * 0.84, metal * 0.78]) + 0.08

    color, height = base.copy(), 0.06 * fibers
    for _, col, a, hw in layers:
        color = color * (1 - a[..., None]) + np.asarray(col, np.float32) * a[..., None]
        height = height + hw * a
    ta = thread * window * min(1, draw * 1.5)
    color = color * (1 - ta[..., None]) + tcol * ta[..., None]
    height = height + 0.5 * ta
    return {"color": color, "height": blur(height, 0.8), "alpha": np.ones((BH, BW), np.float32),
            "wm": wm, "emblem": (bub, glyph, ex, ey), "base": base, "fibers": fibers, "layers": layers,
            "thread": (tcol, thread * window)}
