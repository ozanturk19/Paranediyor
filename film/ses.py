"""Ses tasarımı: filmin bütün efekt sesleri burada sayısal olarak üretilir (hazır ses dosyası yok).

Her ses, görüntüdeki olayla aynı formülden zamanlanır (sahne başı + sahne içi an).
Kullanım: python3 ses.py cikti.wav  [seslendirme_kelimeleri.json]
"""
import json, math, sys
import numpy as np
from scipy import signal
import zaman as Z
import gecis as GC

SR = 48000
RNG = np.random.default_rng(7)


# ================================================================== temel yapı taşları
def N(d):
    return max(1, int(round(d * SR)))


def tax(d):
    return np.arange(N(d), dtype=np.float64) / SR


def norm(x, peak=1.0):
    m = np.abs(x).max()
    return (x / m * peak).astype(np.float32) if m > 0 else x.astype(np.float32)


def filt(x, kind, f, order=2):
    sos = signal.butter(order, f, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def noise(d, seed=None):
    r = np.random.default_rng(seed) if seed is not None else RNG
    return r.standard_normal(N(d)).astype(np.float32)


def brown(d, seed=None):
    return norm(filt(np.cumsum(noise(d, seed)), "highpass", 18))


def env(d, a=0.002, dec=0.2):
    t = tax(d)
    return (np.clip(t / max(a, 1e-4), 0, 1) * np.exp(-np.maximum(t - a, 0) / dec)).astype(np.float32)


def fades(x, fi=0.01, fo=0.05):
    x = x.copy()
    a, b = min(len(x), N(fi)), min(len(x), N(fo))
    x[:a] *= np.linspace(0, 1, a)
    x[len(x) - b:] *= np.linspace(1, 0, b)
    return x


def osc(freq, d, kind="sin", phase=0.0):
    n = N(d)
    f = np.full(n, float(freq)) if np.ndim(freq) == 0 else np.asarray(freq, np.float64)[:n]
    ph = phase + 2 * np.pi * np.cumsum(f) / SR
    if kind == "sin":
        return np.sin(ph).astype(np.float32)
    if kind == "saw":
        return (2 * ((ph / (2 * np.pi)) % 1) - 1).astype(np.float32)
    if kind == "tri":
        return (2 * np.abs(2 * ((ph / (2 * np.pi)) % 1) - 1) - 1).astype(np.float32)
    return np.sign(np.sin(ph)).astype(np.float32)


def shaped(d, center, width, amp, seed=None, nfft=1024):
    """Zamanla değişen bant gürültüsü (STFT içinde şekillendirilir): swoosh, rüzgâr, yükselen gerilim."""
    x = noise(d + 0.05, seed)
    f, ts, S = signal.stft(x, SR, nperseg=nfft, noverlap=nfft * 3 // 4)
    u = np.clip(ts / d, 0, 1)
    c, w, a = center(u), width(u), amp(u)
    lf = np.log2(np.maximum(f, 20))[:, None]
    gain = np.exp(-0.5 * ((lf - np.log2(np.maximum(c, 20))[None, :]) / w[None, :]) ** 2) * a[None, :]
    _, y = signal.istft(S * gain, SR, nperseg=nfft, noverlap=nfft * 3 // 4)
    return norm(y[:N(d)])


def modal(d, partials, seed=None):
    """Titreşen metal/cam: (frekans, genlik, sönüm sn) listesi."""
    r = np.random.default_rng(seed)
    t = tax(d)
    x = np.zeros(N(d), np.float64)
    for f, a, dec in partials:
        if f < SR / 2:
            x += a * np.sin(2 * np.pi * f * t + r.uniform(0, 6.28)) * np.exp(-t / dec)
    return x.astype(np.float32)


def place(buf, t, x):
    i = int(round(t * SR))
    if i < 0:
        x, i = x[-i:], 0
    j = min(len(buf), i + len(x))
    if j > i:
        buf[i:j] += x[:j - i]
    return buf


# ================================================================== ses kütüphanesi
def whoosh(d=0.5, f0=250, f1=2500, f2=None, peak=0.6, width=0.9, seed=None):
    def cen(u):
        if f2 is None:
            return f0 * (f1 / f0) ** u
        return np.where(u < peak, f0 * (f1 / f0) ** (u / peak), f1 * (f2 / f1) ** ((u - peak) / (1 - peak)))
    amp = lambda u: np.where(u < peak, (u / peak) ** 2.2, np.exp(-(u - peak) / (1 - peak) * 4.5))
    return shaped(d, cen, lambda u: np.full_like(u, width), amp, seed)


def riser(d=1.2, f0=300, f1=5000, tone=True, seed=None):
    x = shaped(d, lambda u: f0 * (f1 / f0) ** (u ** 1.5), lambda u: 0.6 + 0.4 * u, lambda u: u ** 2.5, seed)
    if tone:
        t = tax(d)
        u = t / d
        s = osc(f0 * 0.5 * (f1 / f0) ** (0.5 * u ** 2), d, "saw") * (u ** 3)
        x = x + 0.35 * filt(s, "lowpass", 3000)
    return norm(fades(x, 0.01, 0.01))


def boom(d=1.4, f0=120, f1=36, dec=0.45, crack=0.6, seed=None):
    """Derin darbe: aşağı kayan alt frekans + çatlama."""
    t = tax(d)
    f = f1 + (f0 - f1) * np.exp(-t / 0.07)
    body = osc(f, d) * np.exp(-t / dec)
    sub = osc(f * 0.5, d) * np.exp(-t / (dec * 1.3)) * 0.5
    cr = filt(noise(d, seed), "bandpass", [700, 7000]) * env(d, 0.0005, 0.018) * crack
    x = (body + sub + cr) * np.clip(t / 0.0015, 0, 1)
    return norm(x)


def clang(d=2.2, base=380, seed=None):
    """Metal darbe (para basma kalıbı)."""
    r = np.random.default_rng(seed)
    ratios = [1.0, 1.52, 2.31, 2.83, 3.47, 4.61, 5.53, 6.89, 8.2]
    parts = [(base * k * (1 + r.normal(0, 0.003)), 1 / (1 + 0.45 * i), 1.1 / (1 + 0.55 * i)) for i, k in enumerate(ratios)]
    x = modal(d, parts, seed)
    hit = filt(noise(d, seed), "bandpass", [1500, 9000]) * env(d, 0.0003, 0.01) * 2.5
    return norm(x + hit)


def clink(seed=None, base=None, d=0.7):
    """Madeni para şıngırtısı."""
    r = np.random.default_rng(seed)
    base = base or r.uniform(2400, 4200)
    parts = [(base * k, a, dec) for k, a, dec in ((1, 1, 0.3), (1.47, 0.55, 0.2), (2.09, 0.5, 0.16), (2.76, 0.35, 0.1),
                                                   (3.9, 0.25, 0.06))]
    x = modal(d, parts, seed) + filt(noise(d, seed), "highpass", 4000) * env(d, 0.0002, 0.004) * 1.5
    return norm(x)


def tick(freq=3200, seed=None, dec=0.004, d=0.03):
    x = filt(noise(d, seed), "bandpass", [freq * 0.55, min(freq * 2.2, 22000)]) * env(d, 0.0003, dec)
    x += osc(freq, d) * env(d, 0.0002, dec * 0.7) * 0.6
    return norm(x)


def flap(seed):
    """Dönen harf tabelasının plastik kart sesi: iki hızlı tık."""
    r = np.random.default_rng(seed)
    a = tick(r.uniform(1900, 2800), seed, 0.003)
    b = tick(r.uniform(1100, 1600), seed + 1, 0.004) * 0.55
    out = np.zeros(N(0.05), np.float32)
    place(out, 0, a)
    place(out, r.uniform(0.007, 0.013), b)
    return out


def blip(freq=1800, d=0.08, kind="sin", glide=1.0, dec=None):
    t = tax(d)
    x = osc(freq * glide ** (t / d), d, kind) * env(d, 0.0015, dec or d / 4)
    if kind != "sin":
        x = filt(x, "lowpass", 6000)
    return norm(x)


def pop(seed=None):
    """Altyazıdaki vurgulu kelime için yumuşak 'pop'."""
    d = 0.14
    t = tax(d)
    x = osc(420 * np.exp(-t / 0.02) + 160, d) * env(d, 0.001, 0.035)
    x += filt(noise(d, seed), "bandpass", [1500, 5000]) * env(d, 0.0003, 0.006) * 0.4
    return norm(x)


def slap(seed=None):
    """Kâğıt/banknot düşme şaplağı."""
    d = 0.16
    x = filt(noise(d, seed), "bandpass", [250, 4500]) * env(d, 0.0008, 0.022)
    x += boom(d, 170, 90, 0.03, 0.0) * 0.35
    return norm(x)


def chunk(seed=None):
    """Baskı makinesinin mekanik 'ka-çunk' sesi."""
    d = 0.5
    x = boom(d, 150, 60, 0.06, 0.25, seed) * 0.8
    x += filt(noise(d, seed), "bandpass", [900, 3600]) * env(d, 0.0004, 0.014) * 1.2
    x += modal(d, [(870, 0.35, 0.12), (1390, 0.22, 0.09), (2210, 0.14, 0.06)], seed)
    return norm(x)


def crackle(d, rate0=500, dec=0.25, seed=None):
    """Kıvılcım çıtırtısı: seyrek, sönen darbeler."""
    r = np.random.default_rng(seed)
    x = np.zeros(N(d), np.float32)
    t, T = 0.0, []
    while t < d:
        rate = rate0 * math.exp(-t / dec) + 5
        t += r.exponential(1 / rate)
        T.append(t)
    for tt_ in T:
        i = int(tt_ * SR)
        if i < len(x):
            x[i] += r.uniform(-1, 1) * math.exp(-tt_ / (dec * 1.5))
    x = filt(x, "highpass", 2500)
    return norm(filt(x, "lowpass", 14000))


def grains(d, dens, f_lo, f_hi, seed=None, gmin=0.004, gmax=0.022):
    """Dijital parçacık dokusu: çok kısa sinüs tanecikleri (yoğunluk ve frekans zamanla değişir)."""
    r = np.random.default_rng(seed)
    x = np.zeros(N(d) + N(gmax) + 2, np.float32)
    t = 0.0
    while t < d:
        u = t / d
        rate = max(1.0, float(dens(u)))
        t += r.exponential(1 / rate)
        if t >= d:
            break
        u = t / d
        f = math.exp(r.uniform(math.log(f_lo(u)), math.log(f_hi(u))))
        gd = r.uniform(gmin, gmax)
        n = N(gd)
        g = np.sin(2 * np.pi * f * np.arange(n) / SR + r.uniform(0, 6.28)) * np.hanning(n) * r.uniform(0.3, 1.0)
        i = int(t * SR)
        x[i:i + n] += g.astype(np.float32)
    return norm(x[:N(d)])


def laser(d):
    t = tax(d)
    buzz = filt(osc(118 + 7 * np.sin(2 * np.pi * 7 * t), d, "saw"), "bandpass", [500, 5000])
    fl = np.abs(filt(noise(d, 91), "lowpass", 40))
    hiss = filt(noise(d, 92), "highpass", 5000) * (0.3 + fl / (fl.max() + 1e-9))
    tone = osc(2600 + 300 * np.sin(2 * np.pi * 3 * t), d) * 0.2
    return norm(fades(buzz * 0.6 + hiss * 0.5 + tone, 0.02, 0.06))


def heartbeat():
    out = np.zeros(N(0.7), np.float32)
    place(out, 0, boom(0.35, 75, 42, 0.09, 0.0))
    place(out, 0.26, boom(0.3, 62, 38, 0.08, 0.0) * 0.65)
    return out


def bell(freq, d=2.4, bright=1.0):
    parts = [(freq * 0.5, 0.25, d * 0.45), (freq, 1.0, d * 0.35), (freq * 2.0, 0.45 * bright, d * 0.2),
             (freq * 2.41, 0.3 * bright, d * 0.12), (freq * 3.01, 0.2 * bright, d * 0.09), (freq * 4.17, 0.12 * bright, d * 0.05)]
    x = modal(d, parts, int(freq))
    x += filt(noise(d, int(freq)), "highpass", 3000) * env(d, 0.0003, 0.003) * 0.3
    return norm(x)


def scratch(d, seed=None):
    """Mürekkep/kalem çizim hışırtısı."""
    x = filt(noise(d, seed), "bandpass", [1800, 7500])
    am = np.abs(filt(noise(d, (seed or 0) + 5), "lowpass", 25))
    return norm(fades(x * (0.2 + am / (am.max() + 1e-9)), 0.03, 0.08))


def flutter(d, rate=28, seed=None):
    """Kâğıt tabakasının pırpırı."""
    t = tax(d)
    x = filt(noise(d, seed), "bandpass", [1200, 7000])
    am = 0.5 + 0.5 * np.sin(2 * np.pi * rate * t + 2 * np.sin(2 * np.pi * 3.1 * t))
    return norm(x * am ** 3)


def creak(d, seed=None, f=950):
    """Terazinin gıcırtısı: titreyen darbe dizisi + rezonans."""
    r = np.random.default_rng(seed)
    x = np.zeros(N(d), np.float32)
    t = 0.0
    while t < d:
        u = t / d
        t += 1 / (35 + 55 * math.sin(math.pi * u)) * r.uniform(0.7, 1.3)
        i = int(t * SR)
        if i < len(x):
            x[i] = r.uniform(0.5, 1.0) * math.sin(math.pi * min(1, u))
    y = filt(x, "bandpass", [f * 0.8, f * 1.25]) + 0.5 * filt(x, "bandpass", [f * 2.1, f * 2.6])
    return norm(y)


def rubber(d, f0=170, f1=430, seed=None):
    """Şişen balon: gerilen lastik gıcırtısı + hava."""
    t = tax(d)
    u = t / d
    r = np.random.default_rng(seed)
    wob = filt(r.standard_normal(len(t)), "lowpass", 7)
    wob = wob / (np.abs(wob).max() + 1e-9)
    f = f0 * (f1 / f0) ** (u ** 0.8) * (1 + 0.05 * wob) + 9 * np.sin(2 * np.pi * 5.5 * t)
    s = osc(f, d, "saw")
    y = filt(s, "bandpass", [700, 1300]) + 0.6 * filt(s, "bandpass", [1900, 2700])
    am = 0.55 + 0.45 * np.abs(wob)
    air = filt(noise(d, seed), "bandpass", [2500, 9000]) * 0.25
    return norm(fades((y * am + air) * (0.3 + 0.7 * u), 0.08, 0.15))


def glitch(d=0.32, seed=None):
    """Dijital bozulma: kesik kesik veri sesleri, bit azaltma."""
    r = np.random.default_rng(seed)
    x = np.zeros(N(d), np.float32)
    t = 0.0
    while t < d:
        L = r.uniform(0.012, 0.045)
        kind = r.integers(0, 4)
        n = N(L)
        if kind == 0:
            seg_ = osc(r.uniform(300, 3000), L, "sqr") * 0.6
        elif kind == 1:
            seg_ = noise(L, int(r.integers(1000000))) * 0.5
        elif kind == 2:
            seg_ = osc(r.uniform(60, 200), L, "saw")
        else:
            seg_ = np.zeros(n, np.float32)
        hold = int(r.integers(4, 18))
        seg_ = np.repeat(seg_[::hold], hold)[:n]
        seg_ = np.round(seg_ * 6) / 6
        i = int(t * SR)
        x[i:i + len(seg_)] += seg_[:len(x) - i]
        t += L
    return norm(fades(filt(x, "highpass", 80), 0.003, 0.02))


def hum(d, f=50, seed=None):
    t = tax(d)
    x = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.3 for k in range(1, 8))
    return norm(fades(x.astype(np.float32), 0.2, 0.3))


def pad(freqs, d, att=0.8, rel=1.2):
    """Yumuşak akor (final)."""
    t = tax(d)
    x = np.zeros(len(t))
    for i, f in enumerate(freqs):
        for det in (-0.12, 0.0, 0.12):
            x += osc(f * 2 ** (det / 12), d, "tri", phase=i * 1.3 + det) / len(freqs)
    x = filt(x.astype(np.float32), "lowpass", 2200)
    e = np.clip(t / att, 0, 1) * np.clip((d - t) / rel, 0, 1)
    return norm(x * e)


# ================================================================== miks
class Mix:
    def __init__(self, dur):
        n = N(dur + 3.0)
        self.dry = np.zeros((n, 2), np.float32)
        self.send = np.zeros((n, 2), np.float32)
        self.dur = dur

    def add(self, t, x, db=0.0, pan=0.0, rev=0.15):
        """t: saniye, x: mono ya da stereo ses, db: seviye, pan: -1 sol ... +1 sağ, rev: yankı gönderme."""
        g = 10 ** (db / 20)
        if x.ndim == 1:
            th = (np.clip(pan, -1, 1) + 1) * math.pi / 4
            x = np.stack([x * math.cos(th), x * math.sin(th)], 1) * math.sqrt(2)
        for ch in range(2):
            place(self.dry[:, ch], t, x[:, ch] * g)
            if rev > 0:
                place(self.send[:, ch], t, x[:, ch] * g * rev)

    def render(self):
        ir = reverb_ir()
        wet = np.stack([signal.fftconvolve(self.send[:, c], ir[:, c])[:len(self.send)] for c in range(2)], 1)
        out = self.dry + wet.astype(np.float32)
        out = np.stack([filt(out[:, c], "highpass", 28) for c in range(2)], 1)
        n = N(self.dur + 0.05)
        out = out[:n]
        out[-N(0.4):] *= np.linspace(1, 0, N(0.4))[:, None]
        return out


def reverb_ir(rt60=1.7, d=2.6):
    t = tax(d)
    ir = np.zeros((len(t), 2), np.float32)
    for ch in range(2):
        n = noise(d, 300 + ch)
        ir[:, ch] = (filt(n, "lowpass", 900) * np.exp(-6.9 * t / rt60)
                     + filt(n, "bandpass", [900, 4500]) * np.exp(-6.9 * t / (rt60 * 0.7))
                     + filt(n, "highpass", 4500) * np.exp(-6.9 * t / (rt60 * 0.4)))
    pre = N(0.018)
    ir[:pre] = 0
    ir[pre:pre + N(0.03)] *= np.linspace(0, 1, N(0.03))[:, None]
    return ir / np.sqrt((ir ** 2).sum(0, keepdims=True))


def master(x, lufs=-18.0, ceiling_db=-2.5):
    """Ses yüksekliğini -18 LUFS'a getir, gerçek tepe (4x örnekleme) sınırlayıcıyla taşmayı önle."""
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    loud = meter.integrated_loudness(x.astype(np.float64))
    x = x * 10 ** ((lufs - loud) / 20)
    ceil = 10 ** (ceiling_db / 20)
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    up = signal.resample_poly(x, 4, 1, axis=0)                       # örnekler arası tepeleri de yakala
    pk = np.abs(up).max(1)[:4 * len(x)].reshape(-1, 4).max(1)
    look = N(0.004)                                                  # 4 ms ileriyi gören sınırlayıcı
    req = np.minimum(1.0, ceil / np.maximum(pk, 1e-9))
    g = uniform_filter1d(minimum_filter1d(req, size=2 * look + 1), size=look + 1)
    a = math.exp(-1 / (0.08 * SR))                                   # 80 ms toparlanma
    g = np.minimum(g, signal.lfilter([1 - a], [1, -a], g))
    y = np.clip(x * g[:, None], -0.999, 0.999)
    return y.astype(np.float32), loud


# ================================================================== olaylar: sahne sahne
def scene_times(tl):
    out = {}
    for ln in tl:
        s, d = ln["start"], ln["end"] - ln["start"]
        out[ln["scene"]] = (s, d, [w - s for w in ln["t"]])
    return out


def seg(p, a, b):
    return float(np.clip((p - a) / (b - a), 0, 1))


def build(tl):
    ST = scene_times(tl)
    M = Mix(tl[-1]["end"])
    big = []                                                         # büyük darbeler (altyazı pop'u çakışmasın)

    # ---------- 1) kanca: bakiye rakamları oturur, sonra veriye dağılır
    s, d, wt = ST["kanca"]
    M.add(s + 0.0, boom(1.6, 90, 34, 0.6, 0.2, 1), -7, 0, 0.3)
    M.add(s + 0.02, riser(0.5, 2000, 9000, False, 2)[::-1].copy(), -24, 0, 0.2)
    for k in range(18):                                              # dönen rakamlar
        tk = k / 24
        M.add(s + tk, tick(RNG.uniform(2500, 4200), 100 + k, 0.003), -27 + 3 * (k / 18), RNG.uniform(-0.4, 0.4), 0.05)
    for i, ch in enumerate(" 48.250,00"):
        if ch.isdigit():
            M.add(s + 0.12 + 0.07 * i, tick(1800 + 90 * i, 200 + i, 0.006), -18, -0.5 + i / 9, 0.1)
    t_dis = (wt[4] if len(wt) > 4 else d * 0.6) - 0.05
    M.add(s + t_dis, grains(1.3, lambda u: 700 * (1 - u) ** 1.5 + 40, lambda u: 900 + 2500 * u, lambda u: 4000 + 7000 * u, 3),
          -15, 0, 0.35)
    M.add(s + t_dis - 0.05, whoosh(1.2, 400, 6000, None, 0.35, 0.8, 4), -17, 0.2, 0.3)

    # ---------- 2) matbaa: sert kesme, makine yavaşlayarak ritme oturur
    s, d, wt = ST["matbaa"]
    M.add(s, boom(1.5, 130, 40, 0.5, 0.8, 5), -5, 0, 0.35)
    M.add(s, clang(1.2, 240, 6), -16, 0, 0.3)
    big.append(s)
    off = lambda t: 2600 * (1 - math.exp(-t / 1.1)) + 150 * t
    k_prev, t = 0, 0.0
    while t < d + 0.3:
        k = int(off(t) / 273)
        if k > k_prev:
            M.add(s + t, chunk(10 + k), -12 - 3 * (t < 1.0), RNG.uniform(-0.3, 0.3), 0.2)
            k_prev = k
        t += 1 / 400
    dd = d + 0.3
    tt_ = tax(dd)
    spd = (2600 / 1.1 * np.exp(-tt_ / 1.1) + 150) / 2513
    motor = filt(brown(dd, 11), "lowpass", 220) * (0.35 + 0.65 * spd) + 0.3 * osc(46 + 30 * spd, dd, "saw") * 0.2
    M.add(s, norm(fades(motor, 0.01, 0.3)), -17, 0, 0.1)
    M.add(s, fades(flutter(dd, 30, 12) * (0.15 + 0.85 * spd).astype(np.float32), 0.01, 0.3), -21, 0.3, 0.15)
    M.add(s, whoosh(1.4, 3000, 300, None, 0.08, 1.0, 13), -14, -0.2, 0.2)

    # ---------- 3) pamuk: yumuşak rüzgâr, lifler kâğıda dönüşür
    s, d, wt = ST["pamuk"]
    M.add(s, shaped(d + 0.4, lambda u: 500 + 700 * np.sin(np.pi * u), lambda u: np.full_like(u, 0.9),
                    lambda u: np.sin(np.pi * np.clip(u, 0, 1)) ** 0.7, 14), -21, 0, 0.4)
    M.add(s + d * 0.2, whoosh(d * 0.65, 300, 1800, 600, 0.6, 1.0, 15), -18, -0.2, 0.4)
    M.add(s + d * 0.9, slap(16), -17, 0, 0.3)
    M.add(s + d * 0.9, filt(noise(0.4, 17), "bandpass", [2500, 8000]) * env(0.4, 0.002, 0.06), -26, 0.2, 0.2)

    # ---------- 4) filigran: arkadan ışık geçer, şerit gömülür
    s, d, wt = ST["filigran"]
    M.add(s, shaped(d, lambda u: 600 * 4 ** u, lambda u: np.full_like(u, 0.7), lambda u: np.sin(np.pi * u), 18), -22, 0, 0.5)
    for i, f in enumerate((1568, 2093, 2637, 3136)):
        M.add(s + d * 0.08 + i * 0.09, bell(f, 1.6, 0.5), -27 - i, -0.4 + 0.25 * i, 0.6)
    t0, t1 = s + d * 0.42, s + d * 0.78
    M.add(t0, whoosh(t1 - t0 + 0.2, 1500, 7000, None, 0.85, 0.5, 19), -19, 0.3, 0.3)
    M.add(t1, tick(5200, 20, 0.02, 0.1), -22, 0.3, 0.4)

    # ---------- 5) baskı: katmanlar çizilir, kabartma ışıkta parlar, büyüteç gelir
    s, d, wt = ST["baski"]
    M.add(s + d * 0.03, scratch(d * 0.4, 21), -22, -0.3, 0.2)
    M.add(s + d * 0.08, riser(d * 0.34, 400, 2400, True, 22), -24, 0.2, 0.3)
    for p_ in (0.3, 0.36, 0.4):
        M.add(s + d * p_, slap(int(p_ * 100)), -20, 0, 0.2)
    M.add(s + d * 0.5, whoosh(d * 0.5, 150, 700, 250, 0.5, 1.0, 23), -18, 0, 0.3)
    M.add(s + d * 0.56, whoosh(0.5, 500, 4000, None, 0.7, 0.8, 24), -18, 0.5, 0.2)
    M.add(s + d * 0.77, bell(4186, 0.8, 0.3), -27, 0.2, 0.4)

    # ---------- 6) seri no, lazer kesim, paketleme
    s, d, wt = ST["seri"]
    t_kes = (wt[3] if len(wt) > 3 else d * 0.5) - 0.05
    t_pak = (wt[4] if len(wt) > 4 else d * 0.75) - 0.05
    settle = [t_kes * (0.35 + 0.1 * i) for i in range(6)]
    t = 0.0
    while t < max(settle):
        rolling = sum(st > t for st in settle)
        if rolling:
            M.add(s + t, tick(RNG.uniform(2200, 3400), int(t * 1000), 0.0025), -30 + rolling, RNG.uniform(-0.3, 0.3), 0.05)
        t += 1 / 22
    for i, st in enumerate(settle):
        M.add(s + st, tick(1500, 300 + i, 0.008), -19, -0.4 + 0.16 * i, 0.1)
    M.add(s + max(settle), chunk(31), -9, 0, 0.3)
    M.add(s + max(settle), boom(0.8, 120, 50, 0.15, 0.6, 32), -11, 0, 0.3)
    cut = (t_pak - t_kes)
    M.add(s + t_kes, laser(cut * 0.72), -18, 0, 0.2)
    M.add(s + t_kes + cut * 0.65, whoosh(0.35, 800, 3500, None, 0.5, 0.7, 33), -22, 0, 0.2)
    for i in range(8):
        M.add(s + t_pak + i * 0.045 + 0.09, slap(40 + i), -15 - i * 0.3, RNG.uniform(-0.2, 0.2), 0.15)
    M.add(s + t_pak + 0.78, pop(48), -16, 0, 0.2)
    M.add(s + t_pak + 0.78, tick(900, 49, 0.02, 0.1), -18, 0, 0.2)

    # ---------- 7) darphane: kalıp iner, titrer, çarpar; para döner, para yağmuru
    s, d, wt = ST["darphane"]
    t_s = (wt[6] if len(wt) > 6 else d * 0.7) + 0.05
    M.add(s, fades(filt(brown(d + 1.5, 50), "lowpass", 160), 0.3, 0.6), -24, 0, 0.1)
    M.add(s, whoosh(max(0.4, t_s - 0.5), 180, 420, None, 0.9, 0.6, 51), -21, 0, 0.2)
    tv = 0.75
    rattle = filt(noise(tv, 52), "bandpass", [300, 1600]) * (0.5 + 0.5 * np.sin(2 * np.pi * 9.5 * tax(tv))) ** 2
    M.add(s + t_s - 1.2, norm(rattle * np.linspace(0.2, 1, len(rattle))), -20, 0, 0.1)
    M.add(s + t_s - 1.2, riser(1.2, 200, 3000, True, 53), -19, 0, 0.2)
    M.add(s + t_s - 0.45, whoosh(0.45, 300, 1500, None, 0.95, 0.8, 54), -15, 0, 0.1)
    M.add(s + t_s, boom(2.2, 140, 32, 0.6, 1.0, 55), -3, 0, 0.45)
    M.add(s + t_s, clang(2.6, 330, 56), -8, 0, 0.5)
    big.append(s + t_s)
    M.add(s + t_s + 0.01, crackle(0.75, 900, 0.18, 57), -13, 0.2, 0.25)
    M.add(s + t_s + 0.06, whoosh(0.7, 900, 250, None, 0.25, 0.8, 58), -20, 0, 0.2)
    ring_d = d - t_s + 0.8
    tr = tax(ring_d)
    rise = np.clip((tr - 0.1) / 0.85, 0, 1)
    spin = 8.5 * (1 - 0.55 * (1 - (1 - rise) ** 3)) / math.pi
    ring = modal(ring_d, [(2410, 1, 0.9), (3890, 0.6, 0.7), (6120, 0.3, 0.4), (1520, 0.4, 1.1)], 59)
    am = 0.6 + 0.4 * np.abs(np.sin(np.pi * np.cumsum(spin) / SR))
    M.add(s + t_s + 0.05, norm(ring * am), -17, 0, 0.5)
    for i in range(14):
        M.add(s + t_s + 0.25 + i * RNG.uniform(0.08, 0.22), clink(60 + i), -27 + RNG.uniform(-4, 2), RNG.uniform(-0.9, 0.9), 0.4)

    # ---------- 8) soru: dönen harf tabelası
    s, d, wt = ST["soru"]
    rows = ["KİM KARAR", "VERİYOR?"]
    k = 0
    last_settle = 0
    for row in rows:
        for ch in row:
            k += 1
            M.add(s + 0.03 * k, tick(1200, 400 + k, 0.004), -26, -0.6 + k * 0.07, 0.1)
            if ch == " ":
                continue
            st = d * 0.38 + k * 0.055
            last_settle = max(last_settle, st)
            n0 = math.ceil((0.03 * k / 0.075) + k * 0.37)
            n = n0
            while True:
                tf = (n - k * 0.37) * 0.075
                if tf >= st:
                    break
                if tf >= 0.03 * k:
                    M.add(s + tf, flap(1000 * k + n), -25 + RNG.uniform(-3, 2), -0.6 + k * 0.07, 0.08)
                n += 1
            M.add(s + st, flap(5000 + k) * 1.6, -17, -0.6 + k * 0.07, 0.12)
    M.add(s + last_settle + 0.05, boom(1.2, 80, 38, 0.35, 0.1, 61), -12, 0, 0.3)
    M.add(s + d - 1.25, riser(1.25, 250, 6000, True, 62), -14, 0, 0.3)

    # ---------- 9) sen: kalp atışı, parmak izi, dev yazı
    s, d, wt = ST["sen"]
    t_sen = wt[1] if len(wt) > 1 else d * 0.45
    M.add(s, boom(0.9, 70, 34, 0.25, 0.0, 63), -8, 0, 0.2)
    M.add(s + 0.05, heartbeat(), -8, 0, 0.1)
    M.add(s, shaped(t_sen, lambda u: 900 + 900 * u, lambda u: np.full_like(u, 0.25), lambda u: u, 64), -30, 0, 0.2)
    M.add(s + t_sen - 0.35, riser(0.35, 800, 9000, False, 65), -16, 0, 0.1)
    M.add(s + t_sen, boom(2.0, 150, 30, 0.7, 1.0, 66), -3, 0, 0.5)
    M.add(s + t_sen, clang(1.4, 180, 67), -16, 0, 0.5)
    big.append(s + t_sen)

    # ---------- 10) dolaşım: talepler ve nakit akışı
    s, d, wt = ST["dolasim"]
    M.add(s, whoosh(0.8, 300, 3000, 800, 0.4, 0.8, 70), -20, 0, 0.3)
    xs_people = [(b + 50 + (j % 3) * 90) for b in (90, 400, 710) for j in range(6)]
    for j in range(18):
        for rep in range(2):
            M.add(s + d * (0.16 + 0.012 * j + rep * 0.12), blip(2400 + 40 * j, 0.05), -31, xs_people[j] / 540 - 1, 0.2)
    for i in range(3):
        for rep in range(3):
            M.add(s + d * (0.36 + 0.03 * i + rep * 0.05), blip(1600, 0.06, "sin", 1.3), -27, (i - 1) * 0.6, 0.2)
    for i in range(3):
        for rep in range(4):
            M.add(s + d * (0.66 + 0.025 * i + rep * 0.06), clink(80 + i * 4 + rep, 1900, 0.4), -28, (i - 1) * 0.6, 0.3)
    for j in range(18):
        M.add(s + d * (0.86 + 0.01 * j), blip(900 + 30 * j, 0.07, "tri", 0.8), -30, xs_people[j] / 540 - 1, 0.2)

    # ---------- 11) dönüşüm: banknot rakamlara ayrışıp telefona akar
    s, d, wt = ST["donusum"]
    M.add(s + d * 0.03, grains(d * 0.72, lambda u: 900 * math.sin(math.pi * min(1, u * 1.1)) + 50,
                               lambda u: 500 + 1500 * u, lambda u: 3000 + 6000 * u, 71), -16, 0.2, 0.35)
    M.add(s + d * 0.03, whoosh(d * 0.72, 300, 4000, 1500, 0.6, 0.9, 72), -21, 0.3, 0.3)
    M.add(s + d * 0.7, boom(0.6, 200, 70, 0.1, 0.0, 73), -17, 0.4, 0.3)
    M.add(s + d * 0.7, blip(1319, 0.25, "sin", 1.0, 0.08), -20, 0.4, 0.4)
    M.add(s + d * 0.7 + 0.09, blip(1976, 0.3, "sin", 1.0, 0.1), -21, 0.4, 0.4)

    # ---------- 12) kredi: yükleniyor, onay, bakiye sayar, patlama
    s, d, wt = ST["kredi"]
    a, b = s + d * 0.04, s + d * 0.34
    tl_ = tax(b - a)
    load = osc(320 * 2 ** (1.2 * tl_ / (b - a)), b - a) * (0.6 + 0.4 * np.sin(2 * np.pi * 14 * tl_))
    M.add(a, norm(fades(load, 0.05, 0.05)), -28, 0, 0.2)
    for pc in range(1, 10):
        q = pc / 10
        u = (q / 4) ** (1 / 3) if q < 0.5 else 1 - ((2 - 2 * q) ** (1 / 3)) / 2   # ease_io tersi
        M.add(a + u * (b - a), tick(2600, 500 + pc, 0.003), -26, 0, 0.05)
    M.add(s + d * 0.36, bell(1319, 1.4), -15, -0.1, 0.35)
    M.add(s + d * 0.36 + 0.09, bell(1976, 1.6), -15, 0.1, 0.35)
    M.add(s + d * 0.4, pop(81), -18, 0, 0.2)
    c0, c1 = s + d * 0.46, s + d * 0.84
    for n in range(1, 26):
        q = n / 25
        u = 1 - (1 - q) ** (1 / 3)                                      # ease_out tersi
        M.add(c0 + u * (c1 - c0), tick(3000 + 40 * n, 600 + n, 0.003), -24, 0, 0.05)
    M.add(c1, clink(90, 2800), -16, 0, 0.4)
    M.add(c1, bell(2637, 1.2, 0.8), -21, 0, 0.4)
    M.add(s + d * 0.84, grains(0.8, lambda u: 900 * (1 - u) ** 2 + 30, lambda u: 2000 + 0 * u, lambda u: 9000 + 0 * u, 91),
          -18, 0, 0.4)
    M.add(s + d * 0.84, whoosh(0.6, 600, 5000, None, 0.15, 0.9, 92), -20, 0, 0.3)

    # ---------- 13) uğramaz: matbaanın üstü çizilir
    s, d, wt = ST["ugramaz"]
    t_x = (wt[2] if len(wt) > 2 else d * 0.5) - 0.05
    M.add(s, whoosh(0.45, 400, 2500, None, 0.5, 0.8, 100), -22, 0, 0.2)
    M.add(s + t_x - 0.05, whoosh(0.3, 1200, 8000, None, 0.75, 0.6, 101), -13, -0.3, 0.2)
    M.add(s + t_x + 0.18, boom(0.9, 110, 40, 0.2, 0.7, 102), -9, 0, 0.3)
    M.add(s + t_x + 0.18, filt(noise(0.25, 103), "bandpass", [1500, 6000]) * env(0.25, 0.001, 0.04), -17, -0.3, 0.3)

    # ---------- 14) 100 liranın 3-4'ü: ızgara, çözülme, dijital duvar
    s, d, wt = ST["grid"]
    t_d = (wt[4] if len(wt) > 4 else d * 0.35) - 0.1
    t_g = (wt[8] if len(wt) > 8 else d * 0.7) - 0.1
    for k in range(19):
        M.add(s + 0.05 + 0.025 * k, tick(1500 + 110 * k, 700 + k, 0.004), -24, -0.7 + k * 0.075, 0.1)
    M.add(s + t_d, grains(1.2, lambda u: 700 * (1 - u) + 50, lambda u: 600 + 1200 * u, lambda u: 3000 + 5000 * u, 110),
          -17, 0, 0.35)
    M.add(s + t_d, whoosh(1.0, 400, 5000, None, 0.3, 0.9, 111), -22, 0, 0.3)
    M.add(s + t_d + 0.35, pop(112), -12, 0, 0.3)
    M.add(s + t_d + 0.35, bell(2093, 1.2, 0.6), -20, 0, 0.4)
    M.add(s + t_g, grains(0.6, lambda u: 1500 * (1 - u) + 100, lambda u: 2000 + 0 * u, lambda u: 8000 + 0 * u, 113),
          -18, 0, 0.3)
    M.add(s + t_g, whoosh(0.5, 800, 6000, None, 0.2, 0.7, 114), -19, 0, 0.3)
    hd = d - t_g + 0.3
    fl = hum(hd, 60) * (0.85 + 0.15 * np.sin(23 * tax(hd))).astype(np.float32)
    M.add(s + t_g, filt(fl, "highpass", 100), -32, 0, 0.1)

    # ---------- 15) grafik: para eğrisi üretimden hızlı büyür (sesle de)
    s, d, wt = ST["grafik"]
    a, b = s + d * 0.06, s + d * 0.8
    dd = b - a + 0.4
    tg = tax(dd)
    xm = np.clip(tg / (b - a), 0, 1)
    xm = np.where(xm < 0.5, 4 * xm ** 3, 1 - (-2 * xm + 2) ** 3 / 2)
    fpara = 0.06 + 0.9 * (np.exp(3.2 * xm) - 1) / (math.exp(3.2) - 1)
    furet = 0.06 + 0.28 * xm
    tone_p = filt(osc(180 * 2 ** (3.2 * fpara), dd, "saw"), "lowpass", 3500) * (0.3 + 0.7 * fpara)
    tone_u = osc(180 * 2 ** (3.2 * furet), dd, "tri") * 0.5
    M.add(a, norm(fades(tone_p + tone_u, 0.1, 0.35)), -29, 0, 0.3)
    M.add(s + d * 0.5, shaped(d * 0.35, lambda u: 800 + 2000 * u, lambda u: np.full_like(u, 0.8), lambda u: u ** 2, 120),
          -24, 0, 0.3)
    M.add(s + d * 0.62, pop(121), -18, 0.3, 0.3)

    # ---------- 16) terazi: para kefesi dolar, mal kefesi yükselir, fiyat artar
    s, d, wt = ST["terazi"]
    t_f = (wt[6] if len(wt) > 6 else d * 0.6) - 0.1
    last_n = 2
    for i in range(200):
        p_ = i / 200
        e = seg(p_, 0.1, 0.8)
        e = 4 * e ** 3 if e < 0.5 else 1 - (-2 * e + 2) ** 3 / 2
        n = int(2 + 15 * e)
        if n > last_n:
            M.add(s + d * p_, slap(130 + n), -21, -0.5, 0.15)
            last_n = n
    M.add(s + d * 0.15, creak(d * 0.45, 131), -21, 0, 0.25)
    M.add(s + d * 0.33, boom(0.5, 140, 70, 0.08, 0.2, 132), -18, 0, 0.3)
    for i, f in enumerate((659, 831, 988)):
        M.add(s + t_f + i * 0.08, blip(f * 2, 0.12, "tri", 1.0, 0.05), -21, 0.4, 0.3)
    M.add(s + t_f + 0.26, bell(2637, 1.0, 0.7), -20, 0.4, 0.4)

    # ---------- 17) enflasyon: kelime balon gibi şişer
    s, d, wt = ST["enflasyon"]
    M.add(s + d * 0.08, rubber(d * 0.85, 160, 420, 140), -17, 0, 0.3)
    M.add(s + d * 0.08, shaped(d * 0.85, lambda u: 3000 + 2000 * u, lambda u: np.full_like(u, 0.6), lambda u: 0.3 + 0.7 * u, 141),
          -26, 0, 0.3)
    M.add(s + d * 0.33, boom(0.4, 180, 80, 0.07, 0.0, 142), -20, 0, 0.3)

    # ---------- 18) simit ve kira: fiyatlar döner
    s, d, wt = ST["simit"]
    t_k = (wt[1] if len(wt) > 1 else d * 0.3) - 0.1
    M.add(s, whoosh(0.5, 300, 2400, None, 0.55, 0.8, 150), -20, -0.4, 0.2)
    M.add(s + t_k, whoosh(0.5, 300, 2400, None, 0.55, 0.8, 151), -20, 0.5, 0.2)
    t = 0.2
    while t < d:
        M.add(s + t, tick(2000, 1500 + int(t * 100), 0.003), -30, -0.4, 0.05)
        if t > t_k + 0.2:
            M.add(s + t + 0.05, tick(2300, 1600 + int(t * 100), 0.003), -30, 0.5, 0.05)
        t += 0.11

    # ---------- 19) final: amblem yükselir, imza sesi
    s, d, wt = ST["final"]
    M.add(s + d * 0.05, riser(d * 0.35, 400, 5000, False, 160), -20, 0, 0.5)
    M.add(s + d * 0.05, pad([110, 164.8, 246.9, 277.2, 415.3], d + 0.2, 1.5, 1.4), -24, 0, 0.5)
    if len(wt) > 5:
        M.add(s + wt[5] - 0.02, boom(1.4, 110, 38, 0.45, 0.2, 161), -11, 0, 0.5)
    end_t = (wt[-1] if wt else d * 0.5) + 0.7
    M.add(s + end_t, clink(162, 3300, 1.2), -16, 0, 0.6)
    for i, f in enumerate((880, 1319, 1760)):
        M.add(s + end_t + 0.02 + i * 0.13, bell(f, 3.0, 0.8), -14 - i, -0.3 + 0.3 * i, 0.6)

    # ---------- geçiş sesleri (gecis.py tablosuyla aynı anlarda)
    starts = {ln["scene"]: ln["start"] for ln in tl}
    for sc, (tur, yarim, ayar) in GC.TABLO.items():
        b = starts[sc]
        sd = sum(map(ord, sc))                                     # sabit tohum (her çalıştırmada aynı ses)
        if tur == "savur":
            w = whoosh(0.55, 300, 5000, 700, 0.55, 0.9, sd)
            yon = {"sol": -1.0, "sag": 1.0}.get(ayar, 0.0)            # ses de görüntüyle aynı yöne kayar
            th = (np.linspace(-0.8, 0.8, len(w)) * yon + 1) * math.pi / 4
            M.add(b - 0.3, np.stack([w * np.cos(th), w * np.sin(th)], 1).astype(np.float32) * 1.41, -11, 0, 0.2)
        elif tur == "zoom":
            M.add(b - 0.45, riser(0.45, 500, 7000, False, sd), -15, 0, 0.2)
            M.add(b, boom(0.7, 180, 60, 0.12, 0.3, sd + 1), -15, 0, 0.3)
        elif tur == "bozul":
            M.add(b - yarim, glitch(2 * yarim + 0.05, sd), -14, 0, 0.1)
        elif tur in ("karart", "isik", "erit"):
            M.add(b - yarim - 0.1, whoosh(2 * yarim + 0.35, 200, 1400, 400, 0.45, 1.0, sd), -22, 0, 0.4)
    # ---------- altyazıdaki vurgulu (**) kelimeler için 'pop'
    for st, en, markup in Z.caption_cues(tl):
        for tok in markup.split():
            if tok.startswith("**") and "@" in tok:
                tw = float(tok.rsplit("@", 1)[1]) - 0.06
                if all(abs(tw - bt) > 0.35 for bt in big):
                    M.add(tw, pop(int(tw * 100)), -19, 0, 0.2)
    # ---------- hafif oda sesi (tamamen sessiz boşluk olmasın)
    dur = tl[-1]["end"]
    room = filt(brown(dur, 170), "lowpass", 400)
    M.add(0, fades(room, 1.0, 1.0), -42, 0, 0.0)
    return M


def main(out, vo=None):
    tl = Z.build(vo_words=Z.vo_yukle(vo) if vo else None)
    M = build(tl)
    mix = M.render()
    y, loud = master(mix)
    import wave
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{out}: {len(y) / SR:.2f} sn, ham ses yüksekliği {loud:.1f} LUFS -> -18 LUFS")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
