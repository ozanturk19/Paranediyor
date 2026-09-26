"""Sahne geçişleri. Her geçiş, bitmiş (renk işlemi + yazılar yapılmış) iki kareyi birleştirir.

TABLO: gelen sahne -> (tür, yarım süre sn, ayar). Geçiş penceresi [sınır - yarım, sınır + yarım].
Ses tasarımı (ses.py) aynı tabloyu kullanır, böylece her geçişin sesi görüntüsüyle aynı anda olur.
"""
import math
import cv2
import numpy as np
import gfx as G
from ortak import W, H, ease_in, ease_out, ease_io

TABLO = {
    "matbaa":    ("flas", 0.0, None),          # kanca -> matbaa: sert kesme + beyaz parlama + itme
    "pamuk":     ("zoom", 0.22, (540, 800)),   # kâğıdın içine dal
    "filigran":  ("karart", 0.25, None),
    "baski":     ("isik", 0.28, None),          # sıcak ışık sızıntısıyla geçiş
    "seri":      ("savur", 0.18, "sol"),
    "darphane":  ("savur", 0.18, "asagi"),
    "soru":      ("karart", 0.3, None),
    "sen":       ("kes", 0.0, None),            # sen sahnesinin kendi parlaması var
    "dolasim":   ("bozul", 0.16, None),         # dijital dünyaya geçiş: glitch
    "donusum":   ("erit", 0.22, None),
    "kredi":     ("zoom", 0.22, (800, 620)),    # telefonun içine dal
    "ugramaz":   ("savur", 0.18, "sol"),
    "grid":      ("bozul", 0.16, None),
    "grafik":    ("erit", 0.22, None),
    "terazi":    ("savur", 0.18, "yukari"),
    "enflasyon": ("zoom", 0.22, (540, 800)),
    "simit":     ("savur", 0.18, "sag"),
    "final":     ("karart", 0.35, None),
}
FLAS_SURE = 0.22


def _shift_blur(img, dx, dy, k, axis):
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    out = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    if k > 2:
        out = cv2.blur(out, (k, 1) if axis == 0 else (1, k))
    return out


def savur(A, B, u, yon):
    """Hızlı kamera savurma (whip pan): hareket bulanıklığıyla kayar."""
    e = ease_io(u)
    vel = (12 * u * u if u < 0.5 else 12 * (1 - u) ** 2)       # ease_io türevi (0..3)
    axis = 0 if yon in ("sol", "sag") else 1
    L = W if axis == 0 else H
    sgn = -1 if yon in ("sol", "yukari") else 1
    k = int(vel * L / 11 * 0.9)
    a_off, b_off = sgn * e * L, sgn * (e - 1) * L
    if axis == 0:
        a, b = _shift_blur(A, a_off, 0, k, 0), _shift_blur(B, b_off, 0, k, 0)
    else:
        a, b = _shift_blur(A, 0, a_off, k, 1), _shift_blur(B, 0, b_off, k, 1)
    return a + b


def _radial(img, s, cx, cy, streak):
    """Merkeze doğru ışınsal (zoom) bulanıklık: birkaç büyütülmüş kopyanın ortalaması."""
    n = 7 if streak > 0.01 else 1
    acc = np.zeros_like(img)
    for j in range(n):
        sj = s * (1 + streak * j / max(1, n - 1))
        M = np.float32([[sj, 0, (1 - sj) * cx], [0, sj, (1 - sj) * cy]])
        acc += cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return acc / n


def zoom(A, B, u, merkez):
    """İçine dalma: eski sahne hızla büyür, yeni sahne büyükten yerine oturur."""
    cx, cy = merkez
    if u < 0.5:
        q = ease_in(u * 2)
        img = _radial(A, 1 + 1.4 * q, cx, cy, 0.18 * q)
        mix = max(0.0, (u - 0.38) / 0.12)
        if mix > 0:
            img = img * (1 - 0.5 * mix) + _radial(B, 2.4, 540, 800, 0.18) * 0.5 * mix
    else:
        q = ease_out((u - 0.5) * 2)
        img = _radial(B, 2.4 - 1.4 * q, 540, 800, 0.18 * (1 - q))
        mix = max(0.0, (0.62 - u) / 0.12)
        if mix > 0:
            img = img * (1 - 0.5 * mix) + _radial(A, 2.4, cx, cy, 0.18) * 0.5 * mix
    return img


def karart(A, B, u):
    """Kısa karartma (siyaha inip çıkma)."""
    if u < 0.5:
        return A * (1 - ease_in(u * 2))
    return B * ease_out((u - 0.5) * 2)


def erit(A, B, u):
    e = ease_io(u)
    return A * (1 - e) + B * e


_QG = None


def isik(A, B, u):
    """Sıcak ışık sızıntısı (light leak) ile çapraz geçiş: ekranın üstünden yumuşak bir ışık geçer."""
    global _QG
    if _QG is None:
        _QG = G.grid(W // 4, H // 4)
    xx, yy = _QG
    cx = (u * 1.6 - 0.3) * W / 4
    blob = np.exp(-(((xx - cx) / (W / 4 * 0.3)) ** 2 + ((yy - H / 4 * 0.45) / (H / 4 * 0.4)) ** 2))
    blob2 = np.exp(-(((xx - cx * 0.8 - W / 40) / (W / 4 * 0.15)) ** 2 + ((yy - H / 4 * 0.62) / (H / 4 * 0.18)) ** 2))
    leak = cv2.resize(blob.astype(np.float32), (W, H))[..., None] * G.hexc("#FFB45A") \
        + cv2.resize(blob2.astype(np.float32), (W, H))[..., None] * G.hexc("#FF6A3A") * 0.6
    e = G.smoothstep(0.3, 0.7, np.float32(u))
    return A * (1 - e) + B * e + leak * math.sin(math.pi * u) * 0.7


def bozul(A, B, u, seed):
    """Dijital bozulma (glitch): renk kanalları ayrılır, şeritler kayar, iki sahne birbirine girer."""
    r = np.random.default_rng(seed)
    k = math.sin(math.pi * u)
    base, other = (A, B) if u < 0.5 else (B, A)
    out = base.copy()
    for _ in range(int(4 + 12 * k)):                               # kayan yatay şeritler
        y0, h = int(r.integers(0, H - 20)), int(r.integers(6, 140))
        dx = int(r.integers(-160, 160) * k)
        src = other if r.random() < 0.35 * k else base
        out[y0:y0 + h] = np.roll(src[y0:y0 + h], dx, axis=1)
    for _ in range(int(3 * k)):                                     # iri piksel blokları
        y0, h = int(r.integers(0, H - 200)), int(r.integers(40, 200))
        band = out[y0:y0 + h]
        small = cv2.resize(band, (W // 24, max(1, h // 24)), interpolation=cv2.INTER_AREA)
        out[y0:y0 + h] = cv2.resize(small, (W, h), interpolation=cv2.INTER_NEAREST)
    sh = int(26 * k)                                                # RGB ayrışması
    if sh:
        out[..., 0] = np.roll(out[..., 0], sh, axis=1)
        out[..., 2] = np.roll(out[..., 2], -sh, axis=1)
    out[::3] *= 1 - 0.25 * k                                        # tarama çizgileri
    return out


def uygula(tur, ayar, A, B, u, seed=0):
    if tur == "savur":
        return savur(A, B, u, ayar)
    if tur == "zoom":
        return zoom(A, B, u, ayar)
    if tur == "karart":
        return karart(A, B, u)
    if tur == "isik":
        return isik(A, B, u)
    if tur == "bozul":
        return bozul(A, B, u, seed)
    return erit(A, B, u)


def flas(img, dt):
    """Sert kesmeden sonra: beyaz parlama + hafif itme (dt: kesmeden beri geçen sn)."""
    if dt < 0 or dt > FLAS_SURE:
        return img
    k = (1 - dt / FLAS_SURE) ** 2
    s = 1 + 0.06 * k
    M = np.float32([[s, 0, (1 - s) * W / 2], [0, s, (1 - s) * H / 2]])
    img = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return img * (1 - 0.85 * k) + G.hexc("#FFF4E0") * 0.85 * k
