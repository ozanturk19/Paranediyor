"""Para Ne Diyor? film grafik araçları: tuval, yazı, ışık, doku (numpy + OpenCV + Pillow)."""
import math, os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "altyazi"))
import render as R                                   # fontlar ve altyazı motoru

W, H = 1080, 1920
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def hexc(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255


YELLOW, CYAN, TEAL = hexc("#FFD21A"), hexc("#3CF0FF"), hexc("#14505A")
GOLD, PAPER, RED = hexc("#B8902B"), hexc("#ECE2C6"), hexc("#C8452B")
NIGHT, WHITE = hexc("#060708"), np.ones(3, np.float32)


def canvas(color=NIGHT, w=W, h=H):
    return np.ones((h, w, 3), np.float32) * np.asarray(color, np.float32)


def grid(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx, yy


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def normalize(v):
    v = np.asarray(v, np.float32)
    return v / np.linalg.norm(v)


def over(dst, rgb, a, x=0, y=0):
    """Alfa ile üst üste bindir (rgb: h,w,3 ya da renk; a: h,w)."""
    h, w = a.shape
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return dst
    sa = a[y0 - y:y1 - y, x0 - x:x1 - x][..., None]
    src = rgb if np.ndim(rgb) == 1 else rgb[y0 - y:y1 - y, x0 - x:x1 - x]
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - sa) + src * sa
    return dst


def add(dst, rgb, x=0, y=0):
    """Işık ekle (glow, parıltı)."""
    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(dst.shape[1], x + w), min(dst.shape[0], y + h)
    if x1 > x0 and y1 > y0:
        dst[y0:y1, x0:x1] += rgb[y0 - y:y1 - y, x0 - x:x1 - x]
    return dst


_fonts = {}
def get_font(file, px, wght=None):
    """Değişken (ağırlık ekseni olan) ve sabit fontları birlikte destekler."""
    key = (file, px, wght)
    if key not in _fonts:
        from PIL import ImageFont
        path = file if os.path.isabs(file) else R.FD + file
        f = ImageFont.truetype(path, px, layout_engine=ImageFont.Layout.RAQM)
        try:
            axes = f.get_variation_axes()
        except OSError:
            axes = []
        if axes and wght:
            f.set_variation_by_axes([wght if (a["name"] in (b"Weight", "Weight")) else a["default"] for a in axes])
        _fonts[key] = f
    return _fonts[key]


def text_mask(txt, file, px, wght=None, tracking=0.0):
    """Metni alfa maskesi olarak çiz (tracking: harf arası, px cinsinden)."""
    f = get_font(file, int(px), wght)
    x0, y0, x1, y1 = f.getbbox(txt, anchor="ls")
    extra = int(abs(tracking) * max(0, len(txt) - 1)) + 4
    img = Image.new("L", (x1 - x0 + extra + 8, y1 - y0 + 8), 0)
    d = ImageDraw.Draw(img)
    if tracking:
        cx = 4 - x0
        for ch in txt:
            d.text((cx, 4 - y0), ch, font=f, fill=255, anchor="ls")
            cx += f.getlength(ch) + tracking
    else:
        d.text((4 - x0, 4 - y0), txt, font=f, fill=255, anchor="ls")
    return np.asarray(img, np.float32) / 255


def blur(x, sigma):
    return cv2.GaussianBlur(x, (0, 0), sigma) if sigma > 0 else x


def bloom(img, thresh=0.72, sigma=22, strength=0.55):
    """Parlak alanlardan ışık taşması (dörtte bir çözünürlükte hesaplanır, hızlı)."""
    h, w = img.shape[:2]
    m = smoothstep(thresh, 1.0, img.max(axis=2))[..., None]
    small = cv2.resize(img * m, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    b = cv2.GaussianBlur(small, (0, 0), sigma / 4) + 0.5 * cv2.GaussianBlur(small, (0, 0), sigma * 3 / 4)
    return img + cv2.resize(b, (w, h), interpolation=cv2.INTER_LINEAR) * strength


_vig = {}
def vignette(img, strength=0.45):
    key = img.shape[:2]
    if key not in _vig:
        xx, yy = grid(img.shape[1], img.shape[0])
        r = np.hypot((xx - img.shape[1] / 2) / (img.shape[1] / 2), (yy - img.shape[0] / 2) / (img.shape[0] / 2))
        _vig[key] = (np.clip(r / 1.3, 0, 1) ** 2)[..., None]
    return img * (1 - strength * _vig[key])


def chroma(img, px=2.5):
    """Kenarlara doğru hafif renk kayması (lens hissi)."""
    h, w = img.shape[:2]
    out = img.copy()
    for ch, s in ((0, px), (2, -px)):
        k = 1 + s / (w / 2)
        M = np.float32([[k, 0, (1 - k) * w / 2], [0, k, (1 - k) * h / 2]])
        out[..., ch] = cv2.warpAffine(img[..., ch], M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    return out


def grain(img, amt=0.035, seed=0):
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (img.shape[0] // 2 + 1, img.shape[1] // 2 + 1)).astype(np.float32)
    n = cv2.resize(n, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
    lum = img.mean(axis=2, keepdims=True)
    return img + n[..., None] * amt * (0.35 + 0.65 * (1 - np.abs(lum * 2 - 1)))


def filmic(x, exposure=1.0):
    """ACES benzeri ton eğrisi: parlak alanları patlatmadan sıkıştırır."""
    x = np.maximum(x * exposure, 0)
    return (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)


def finish(img, seed=0, vig=0.45, grain_amt=0.035, bloom_on=True, bloom_thresh=0.8, bloom_k=0.45, exposure=1.15):
    if bloom_on:
        img = bloom(img, bloom_thresh, strength=bloom_k)
    img = filmic(chroma(vignette(img, vig)), exposure)
    return grain(img, grain_amt, seed)


def to_u8(img):
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def relief(color, height, light=(-0.55, -0.75, 0.8), strength=5.0, spec=0.35, shininess=36):
    """Yükseklik haritasından ışıklandırma: kabartma baskı (intaglio) hissi."""
    gx = cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3)
    n = np.dstack([-gx * strength, -gy * strength, np.ones_like(height)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    L = normalize(light)
    shade = 1 + 0.9 * (n @ L - L[2])
    Hv = normalize(L + np.array([0, 0, 1], np.float32))
    sp = np.clip(n @ Hv, 0, 1) ** shininess * spec
    return color * shade[..., None] + sp[..., None]


def put_caption(img, markup, top_design, t=99.0, on_video=False, center_x=360):
    """Altyazı motoruyla (render.py) tek bir sayfayı tuvale çiz."""
    R.ON_VIDEO = on_video
    cue = R.Cue(0.0, 100.0, markup)
    cue.layout(top_design, center_x)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cue.draw(layer, t)
    a = np.asarray(layer, np.float32) / 255
    return over(img, a[..., :3], a[..., 3])
