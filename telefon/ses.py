"""Telefon filmi ses tasarımı (sayısal üretim). Seslendirmenin altında kalacak şekilde ölçülü.

Kullanım: python3 ses.py cikti.wav [seslendirme_kelimeleri.json]
"""
import importlib.util, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("film_ses", os.path.join(HERE, "..", "film", "ses.py"))
S = importlib.util.module_from_spec(_spec)
sys.path.insert(0, os.path.join(HERE, "..", "film"))
_spec.loader.exec_module(S)
import zamanlama as Z        # noqa: E402

SR = S.SR
N, tax, norm, filt, noise, env, fades, osc, place = S.N, S.tax, S.norm, S.filt, S.noise, S.env, S.fades, S.osc, S.place
seg = S.seg


# ================================================================== yeni sesler
def ship_horn(d=2.2, f=92.0):
    """Uzakta gemi düdüğü: kalın, titreşimli ton."""
    t = tax(d)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t)
    x = sum(osc(f * k * vib, d, "saw") / k ** 0.9 for k in (1, 2, 3))
    x = filt(filt(x, "lowpass", 900), "highpass", 60)
    e = np.clip(t / 0.25, 0, 1) * np.clip((d - t) / 0.6, 0, 1)
    return norm(x * e)


def generator(d, rate=24.0, seed=1):
    """Dizel jeneratör: düşük frekanslı patpat + mekanik tıngırtı."""
    r = np.random.default_rng(seed)
    t = tax(d)
    pulses = np.zeros(N(d), np.float32)
    k = 0.0
    while k < d:
        i = int(k * SR)
        if i < len(pulses):
            pulses[i] = r.uniform(0.6, 1.0)
        k += 1 / rate * r.uniform(0.94, 1.06)
    body = filt(pulses, "lowpass", 180) * 30 + filt(pulses, "bandpass", [300, 1400]) * 3
    rattle = filt(noise(d, seed), "bandpass", [900, 3500]) * (0.4 + 0.6 * np.abs(np.sin(np.pi * rate * t)))
    return norm(fades(body + 0.25 * rattle, 0.3, 0.4))


def buzz(d, seed=2):
    """Elektrik hattı vızıltısı + çıtırtı."""
    t = tax(d)
    x = sum(np.sin(2 * np.pi * 50 * k * t) / k for k in range(1, 12)).astype(np.float32)
    x = filt(x, "highpass", 90) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.7 * t))
    return norm(fades(x * 0.5 + S.crackle(d, 40, 10, seed) * 0.5, 0.2, 0.3))


def sewing(d, rate=3.75, seed=3):
    """Dikiş makinesi: her dikişte mekanik tık + motor vınlaması."""
    r = np.random.default_rng(seed)
    t = tax(d)
    motor = sum(osc(118 * k, d, "sin") / k for k in (1, 2, 3, 5)) * (0.6 + 0.4 * np.sin(2 * np.pi * rate * t) ** 2)
    x = filt(motor, "bandpass", [100, 2000]) * 0.35
    k = 0.0
    while k < d:
        x = place(x, k, S.tick(r.uniform(1600, 2200), int(k * 1000) + seed, 0.006, 0.05) * 0.9)
        x = place(x, k + 0.5 / rate, S.tick(r.uniform(700, 900), int(k * 1000) + seed + 7, 0.01, 0.06) * 0.5)
        k += 1 / rate
    return norm(fades(x, 0.05, 0.1))


def beep(f1=1400, f2=900, d=0.16):
    """Bankamatik hata sesi: iki tonlu bip."""
    x = np.concatenate([osc(f1, d, "sqr") * env(d, 0.003, 0.2), np.zeros(N(0.05), np.float32),
                        osc(f2, d * 1.4, "sqr") * env(d * 1.4, 0.003, 0.3)])
    return norm(filt(x, "lowpass", 5000))


def tape_stop(x, d=0.5):
    """Sesi bant durması gibi yavaşlatıp alçalt."""
    n = len(x)
    u = np.linspace(0, 1, N(d))
    speed = (1 - u) ** 1.5
    pos = np.cumsum(speed)
    pos = pos / pos[-1] * min(n - 1, N(d) * 0.55)
    return norm(np.interp(pos, np.arange(n), x).astype(np.float32) * (1 - u) ** 0.5)


def unlock():
    """Kilit açılır: metal tık + zincir şıkırtısı."""
    out = np.zeros(N(1.2), np.float32)
    place(out, 0.0, S.tick(3200, 11, 0.004, 0.05) * 1.0)
    place(out, 0.03, S.modal(0.4, [(2300, 1, 0.12), (3700, 0.6, 0.08), (5100, 0.4, 0.05)], 12) * 0.8)
    r = np.random.default_rng(13)
    for k in range(9):
        place(out, 0.12 + k * r.uniform(0.04, 0.09), S.clink(20 + k, r.uniform(2800, 4600), 0.4) * r.uniform(0.3, 0.7))
    return norm(out)


# ================================================================== olaylar
def build(tl):
    sahneler = Z.scenes(tl)
    scs = {sc["scene"]: sc for sc in sahneler}
    toplam = sahneler[-1]["end"]
    M = S.Mix(toplam)

    def W(name):
        if name not in scs:
            raise KeyError(f"ses.py: '{name}' sahnesi zaman çizelgesinde yok. Bu blok önceki filme ait: "
                           "yeni filmde bu bloğu sil ya da yeni sahneye göre yeniden yaz.")
        sc = scs[name]
        return sc["start"], sc["end"] - sc["start"], [w - sc["start"] for w in sc["t"]], \
            [x - sc["start"] for x in sc["line_t"]]

    # ======== SAHNEYE ÖZEL OLAYLAR (bu filme ait) ========
    # Her olayın zamanı, görüntüdeki olayla AYNI formülden hesaplanır (aynı wt[...] indeksi, aynı gecikme).
    def w(wt, i, dflt):
        return wt[i] if len(wt) > i else dflt

    def gr(d, dens, lo, hi, seed=None):
        """Sabit yoğunluk ve frekans aralığıyla parçacık dokusu."""
        return S.grains(d, lambda u: dens, lambda u: lo, lambda u: hi, seed)

    def rewind(d, seed=1):
        """Bant geri sarma cızırtısı: titreyen, yükselen tiz bant sesi."""
        return S.shaped(d, lambda u: 1400 + 2600 * u + 500 * np.sin(u * 60), lambda u: np.full_like(u, 0.5),
                        lambda u: np.sin(np.pi * np.clip(u, 0, 1)) ** 0.4, seed)

    def rustle(d, seed=1):
        """Kumaş hışırtısı."""
        return S.shaped(d, lambda u: 3500 + 800 * np.sin(u * 17), lambda u: np.full_like(u, 1.2),
                        lambda u: np.sin(np.pi * np.clip(u, 0, 1)) * (0.6 + 0.4 * np.abs(np.sin(u * 23))), seed)

    def power_down(d=1.4, f0=180):
        tt_ = tax(d)
        return norm(filt(osc(f0 * np.exp(-tt_ * 1.6), d, "saw") * np.exp(-tt_ * 1.3), "lowpass", 1100))

    def monitor_beep(f=1046.0, d=0.1):
        return norm(osc(f, d, "sin") * env(d, 0.004, 0.08))

    # 1) kanca: katmanlar süzülür, kilitlenir, ekran yanar
    s, d, wt, lt = W("kanca")
    tA, tT, tTk, tU = w(wt, 0, 0.3), w(wt, 2, 1.0), w(wt, 3, 1.3), w(wt, 5, 2.4)
    M.add(s, S.pad([55, 82.4, 110], d + 0.4, 0.3, 1.0), -30, 0, 0.5)
    for k, pan in enumerate((-0.6, -0.2, 0.3, 0.7)):
        M.add(s + 0.02 + k * 0.1, S.whoosh(0.7, 200, 2600, 600, 0.5, 0.9, 10 + k), -22, pan, 0.3)
    M.add(s + tA, S.chunk(20), -14, -0.3, 0.2)
    M.add(s + tA + 0.03, S.clink(21, 2600, 0.5), -20, -0.3, 0.3)
    M.add(s + tT, S.chunk(22), -15, 0.2, 0.2)
    M.add(s + tT + 0.02, S.clink(23, 3000, 0.4), -21, 0.2, 0.3)
    M.add(s + tTk - 0.05, S.blip(600, 0.35, "sin", 3.0, 0.3), -20, 0.3, 0.4)
    M.add(s + tU - 0.6, S.riser(0.6, 300, 5000, True, 24), -20, 0, 0.3)
    M.add(s + tU - 0.1, S.chunk(25), -11, 0, 0.3)
    M.add(s + tU - 0.1, S.boom(1.4, 120, 36, 0.45, 0.6, 26), -9, 0, 0.4)
    M.add(s + tU, S.whoosh(0.9, 1500, 6000, None, 0.5, 0.5, 27), -26, 0.5, 0.4)

    # 2) satış: etiket iner, yıl döner, damga
    s, d, wt, lt = W("satis")
    t_year, t_stamp = w(wt, 0, 0.3), w(wt, 1, 1.0)
    M.add(s, S.whoosh(0.5, 300, 2400, None, 0.6, 0.8, 30), -20, 0, 0.2)
    M.add(s + 0.4, S.creak(0.5, 31, 700), -30, 0.1, 0.3)
    for k in range(4):
        M.add(s + t_year - 0.55 + k * 0.18, S.flap(32 + k), -18, 0.1, 0.1)
    M.add(s + t_stamp - 0.03, S.slap(36), -12, 0, 0.3)
    M.add(s + t_stamp - 0.03, S.boom(0.8, 110, 45, 0.2, 0.5, 37), -14, 0, 0.3)

    # 3) vestel: geri sarma, 2016, çatlayan ekran
    s, d, wt, lt = W("vestel")
    t_bir, t_v, t_o = w(wt, 3, 0.9), w(wt, 6, 2.2), w(wt, 9, 3.2)
    rw = max(0.5, t_bir + 0.4)
    M.add(s - 0.4, rewind(rw, 40), -17, 0, 0.1)
    M.add(s - 0.4, S.flutter(rw, 28, 41), -24, 0, 0.1)
    M.add(s + t_bir - 0.3, tape_stop(S.whoosh(1.2, 400, 3000, None, 0.3, 0.9, 42), 0.4), -18, 0, 0.2)
    M.add(s + t_bir - 0.1, fades(filt(S.brown(d - t_bir + 0.2, 43), "lowpass", 500), 0.3, 0.3), -34, 0, 0.3)
    M.add(s + t_v, S.pop(44), -20, 0.4, 0.2)
    M.add(s + t_o - 0.02, S.crackle(0.35, 900, 0.12, 45), -12, 0.1, 0.3)
    M.add(s + t_o - 0.02, S.clink(46, 4200, 0.6), -15, 0.1, 0.4)
    M.add(s + t_o, S.boom(1.0, 100, 38, 0.3, 0.8, 47), -11, 0, 0.4)

    # 4) soru: harf tabelası
    s, d, wt, lt = W("soru")
    for k in range(22):
        settle = 0.28 + k * 0.055 * 0.4
        M.add(s + 0.02 * k + 0.05, S.flap(50 + k) * 0.7, -24, -0.4 + 0.04 * k, 0.1)
        M.add(s + settle, S.flap(80 + k), -20, -0.4 + 0.04 * k, 0.1)

    # 5) yüzde 7: telefonlar dizilir, 7'si döner
    s, d, wt, lt = W("yuzde7")
    t_sat, t_7 = w(wt, 2, 1.2), w(wt, 5, 2.6)
    for r in range(10):
        M.add(s + t_sat - 0.6 + r * 0.09, S.tick(2400 + 60 * r, 110 + r, 0.004, 0.04), -24, -0.3 + 0.06 * r, 0.1)
    for j in range(7):
        M.add(s + t_7 + j * 0.05 + 0.12, S.blip(880 * 2 ** (j / 12 * 2), 0.09, "tri", 1.0, 0.05), -21, -0.5 + j * 0.15, 0.3)
    M.add(s + t_7, S.bell(1760, 1.4, 0.7), -19, 0, 0.5)
    M.add(s + t_7 - 0.05, S.boom(0.7, 140, 60, 0.15, 0.3, 120), -16, 0, 0.3)

    # 6) satamamak: fişler akar, kelime kesilir
    s, d, wt, lt = W("satamamak")
    t_s, t_d = w(wt, 1, 0.5), w(wt, 2, 1.2)
    M.add(s, gr(d, 40, 1500, 4000, 130), -34, 0, 0.2)
    M.add(s + t_s - 0.12, S.whoosh(0.4, 400, 3000, None, 0.6, 0.7, 131), -20, 0, 0.2)
    M.add(s + t_d - 0.08, S.whoosh(0.25, 1500, 7000, None, 0.4, 0.5, 132), -13, -0.4, 0.2)
    M.add(s + t_d + 0.02, S.boom(0.9, 120, 40, 0.25, 0.7, 133), -12, 0, 0.3)

    # 7) hata: hata pencereleri, yavaşlayan yükleme, donma
    s, d, wt, lt = W("hata")
    t_y, t_v, t_c = w(wt, 1, 0.4), w(wt, 4, 2.2), w(wt, 6, 3.6)
    for i in range(6):
        ti = t_y - 0.05 + i * 0.22
        M.add(s + ti, beep(1100 - i * 60, 750 - i * 40, 0.09), -21, -0.4 + 0.16 * i, 0.2)
        M.add(s + ti, S.glitch(0.08, 140 + i), -24, 0, 0.1)
    M.add(s + t_v - 0.1, S.whoosh(0.4, 2000, 300, None, 0.4, 0.8, 150), -22, 0, 0.2)
    tt_ = tax(2.2)
    slow = osc(420 * np.exp(-tt_ * 0.6), 2.2, "tri") * (0.5 + 0.5 * np.sin(2 * np.pi * tt_ * (3 - tt_ * 1.1)) ** 2)
    M.add(s + t_v, norm(fades(filt(slow, "lowpass", 1800), 0.1, 0.4)), -24, 0, 0.3)
    k = 0.0
    while t_c + k < d:
        M.add(s + t_c + k, S.tick(900, 160 + int(k * 10), 0.01, 0.05), -22, 0, 0.1)
        k += 0.2
    M.add(s + t_c, S.pad([46, 49], d - t_c + 0.3, 0.3, 0.6), -28, 0, 0.3)
    for j in range(3):                                           # uyarı: iki tonlu alarm
        M.add(s + t_c + j * 0.5, beep(700, 520, 0.14), -20, 0, 0.2)

    # 8) çekilme: zarar çubukları, telefon toza dönüşür
    s, d, wt, lt = W("cekilme")
    t_z, t_p, t_c = w(wt, 1, 0.5), w(wt, 5, 2.8), w(wt, 6, 3.3)
    M.add(s + 0.1, S.blip(300, 0.5, "tri", 1.6, 0.4), -26, -0.3, 0.3)
    M.add(s + t_z - 0.3, S.blip(250, 0.7, "saw", 1.9, 0.6), -26, 0.3, 0.3)
    M.add(s + t_z + 0.1, S.boom(0.8, 90, 40, 0.25, 0.3, 170), -13, 0, 0.3)
    M.add(s + t_z + 0.12, filt(osc(155, 0.5, "saw") * env(0.5, 0.005, 0.3), "lowpass", 1400), -22, 0, 0.3)
    s0 = t_p - 0.1
    M.add(s + s0, gr(1.8, 900, 2500, 9000, 171), -17, 0.2, 0.3)
    M.add(s + s0, S.whoosh(1.6, 300, 2000, 500, 0.6, 1.0, 172), -19, 0.5, 0.4)
    M.add(s + t_c, S.pop(173), -22, 0, 0.2)

    # 9) strateji: taktik tahtası
    s, d, wt, lt = W("strateji")
    t_f = w(wt, 1, 0.7)
    M.add(s + 0.05, S.scratch(0.4, 180), -24, -0.3, 0.1)
    M.add(s + 0.42, S.slap(181), -18, 0.1, 0.2)
    M.add(s + t_f - 0.18, S.scratch(0.5, 182), -22, 0.3, 0.1)
    M.add(s + t_f - 0.18, S.whoosh(0.5, 400, 4000, None, 0.7, 0.7, 183), -22, 0.3, 0.2)
    M.add(s + t_f - 0.04, S.boom(1.0, 130, 42, 0.3, 0.8, 184), -10, 0, 0.35)

    # 10) garanti: mühür, 3 model, biri yükselir
    s, d, wt, lt = W("garanti")
    t_g, t_m, t_k = w(wt, 1, 0.4), (lt[1] if len(lt) > 1 else d * 0.35), w(wt, 6, 3.0)
    M.add(s + t_g - 0.05, S.whoosh(0.3, 600, 3000, None, 0.8, 0.6, 190), -20, 0, 0.2)
    M.add(s + t_g + 0.08, S.chunk(191), -11, 0, 0.3)
    M.add(s + t_g + 0.08, S.boom(1.1, 110, 40, 0.3, 0.5, 192), -12, 0, 0.4)
    for i in range(3):
        M.add(s + t_m - 0.1 + i * 0.1, S.whoosh(0.45, 300, 2500, None, 0.6, 0.8, 193 + i), -23, -0.5 + 0.5 * i, 0.2)
    M.add(s + t_k - 0.45, S.riser(0.5, 400, 4000, True, 197), -22, 0, 0.3)
    M.add(s + t_k, S.bell(1319, 1.6, 0.8), -18, 0, 0.5)
    M.add(s + t_k + 0.07, S.bell(1976, 1.6, 0.8), -20, 0.1, 0.5)

    # 11) kripto: ses dalgası şifreye dönüşür, kilit kapanır
    s, d, wt, lt = W("kripto")
    t_g = w(wt, 3, 0.9)
    r = np.random.default_rng(200)
    for k in range(int(d * 12)):
        tk = k / 12
        M.add(s + tk, S.blip(r.uniform(900, 2400), 0.03, "sqr", 1.0, 0.02), -34, r.uniform(-0.5, 0.5), 0.1)
    M.add(s + t_g - 0.1, gr(0.7, 300, 3000, 9000, 201), -21, 0, 0.2)
    M.add(s + t_g + 0.3, S.chunk(202), -14, 0, 0.2)
    M.add(s + t_g + 0.3, S.tick(3200, 203, 0.004, 0.05), -16, 0, 0.2)
    M.add(s + t_g + 0.55, S.pop(204), -20, 0, 0.2)

    # 12) devlet: tek spot, yükselen sütunlar, halka göstergeler
    s, d, wt, lt = W("devlet")
    t_oz, t_b, t_ark, t_dv = w(wt, 1, 0.4), (lt[1] if len(lt) > 1 else d * 0.4), w(wt, 6, 2.6), w(wt, 8, 3.2)
    M.add(s + 0.05, S.boom(0.9, 70, 35, 0.25, 0.2, 210), -16, 0, 0.5)
    M.add(s + 0.05, S.chunk(211), -18, 0, 0.5)
    M.add(s + t_oz, S.pop(212), -22, 0, 0.2)
    M.add(s + t_b - 0.1, S.whoosh(1.0, 200, 1200, 300, 0.5, 1.0, 213), -22, 0, 0.3)
    rumble = fades(filt(S.brown(1.3, 214), "lowpass", 180), 0.3, 0.3)
    M.add(s + t_ark - 0.15, rumble, -13, 0, 0.4)
    M.add(s + t_ark - 0.15, S.riser(1.0, 80, 900, False, 215), -24, 0, 0.3)
    M.add(s + t_ark + 0.6, S.boom(1.6, 80, 30, 0.6, 0.4, 216), -10, 0, 0.5)
    t_do = min(t_dv, t_ark + 0.55)
    for i in range(2):
        for j in range(6):
            M.add(s + t_do + j * 0.1, S.tick(1800 + 200 * j, 217 + j + 10 * i, 0.004, 0.03), -26, -0.4 + 0.8 * i, 0.1)

    # 13) telekom: harita açılır, ağ çizgileri, abone noktaları
    s, d, wt, lt = W("telekom")
    t_tt, t_m, t_g = w(wt, 5, 2.0), w(wt, 10, 4.1), w(wt, 14, 5.3)
    M.add(s, S.whoosh(1.0, 150, 1500, 300, 0.4, 1.0, 230), -22, 0, 0.4)
    q = 0.0
    while q < t_tt - 0.4:                                        # ağ başlamadan önce sonar nabzı
        M.add(s + q, S.blip(880, 0.25, "sin", 0.9, 0.22), -31, -0.2, 0.5)
        q += 0.625
    M.add(s, S.pad([65.4, 98, 130.8], d + 0.3, 1.0, 1.2), -31, 0, 0.5)
    r = np.random.default_rng(231)
    for k in range(30):
        M.add(s + t_tt - 0.25 + k * 0.045, S.blip(r.uniform(1200, 2600), 0.05, "sin", 1.0, 0.04), -28, r.uniform(-0.7, 0.7),
              0.3)
    M.add(s + t_tt - 0.25, S.whoosh(1.3, 500, 4000, None, 0.6, 0.9, 232), -24, 0, 0.3)
    M.add(s + t_m - 0.3, gr(t_g - t_m + 0.5, 500, 4000, 10000, 233), -23, 0, 0.3)
    M.add(s + t_g, S.bell(1568, 1.8, 0.6), -21, 0, 0.5)

    # 14) fatura: telefon uçar, satır kilitlenir, zincir
    s, d, wt, lt = W("fatura")
    t_tel, t_f, t_s, t_bag = w(wt, 0, 0.2), w(wt, 1, 0.7), w(wt, 4, 2.3), w(wt, 5, 2.8)
    M.add(s + t_tel - 0.05, S.whoosh(0.6, 300, 3500, None, 0.6, 0.8, 240), -19, 0.5, 0.2)
    M.add(s + t_tel + 0.55, S.pop(241), -18, -0.3, 0.2)
    M.add(s + t_f, S.tick(2000, 242, 0.01, 0.06), -18, 0, 0.2)
    M.add(s + t_f, S.blip(1320, 0.12, "tri", 1.0, 0.08), -22, 0, 0.3)
    for i in range(9):
        M.add(s + t_s - 0.2 + i * 0.07, S.clink(243 + i, 3000 + i * 150, 0.35), -21, -0.6 + 0.15 * i, 0.2)
    M.add(s + t_bag, S.chunk(253), -13, 0.2, 0.3)
    M.add(s + t_bag + 0.03, unlock(), -20, 0.2, 0.3)

    # 15) zamanlama: kronometre, 4.5G -> 5G
    s, d, wt, lt = W("zamanlama")
    t_z, t_b, t_5 = w(wt, 5, 1.8), (lt[1] if len(lt) > 1 else d * 0.6), w(wt, 8, 3.2)
    k = 0.0
    while k < t_z - 0.05:
        M.add(s + k, S.tick(3000 if int(k * 8) % 2 else 2400, 260 + int(k * 8), 0.003, 0.03), -24, 0, 0.1)
        k += 0.125
    M.add(s + t_z, S.chunk(261), -13, 0, 0.3)
    M.add(s + t_z, S.bell(2093, 1.2, 0.8), -20, 0, 0.5)
    M.add(s + t_b - 0.25, S.whoosh(0.5, 400, 3000, None, 0.5, 0.8, 262), -21, 0, 0.2)
    M.add(s + t_5 - 0.5, S.riser(0.45, 500, 6000, True, 263), -21, 0, 0.3)
    M.add(s + t_5 - 0.05, S.flap(264) * 1.5, -16, 0, 0.1)
    M.add(s + t_5, S.bell(1760, 1.6, 0.8), -18, -0.2, 0.5)
    M.add(s + t_5 + 0.06, S.bell(2637, 1.6, 0.8), -20, 0.2, 0.5)
    M.add(s + t_5, S.boom(0.8, 150, 60, 0.2, 0.3, 265), -17, 0, 0.3)

    # 16) milyonlar: tek ekran -> 95 ekranlık duvar -> altına dönen 63 ekran
    s, d, wt, lt = W("milyonlar")
    t_m, t_pz = (lt[2] if len(lt) > 2 else d * 0.4), w(wt, 11, 4.3)
    M.add(s, fades(buzz(t_m + 0.3, 270), 0.2, 0.3), -30, 0, 0.2)
    M.add(s + t_m - 0.2, S.whoosh(1.1, 3000, 300, None, 0.5, 1.0, 271), -19, 0, 0.3)
    M.add(s + t_m - 0.1, gr(1.0, 150, 1500, 6000, 272), -22, 0, 0.3)
    for j in range(10):
        M.add(s + t_pz - 0.3 + j * 0.05, S.blip(660 * 2 ** (j / 12 * 1.5), 0.08, "tri", 1.0, 0.05), -24, -0.5 + j * 0.1, 0.3)
    M.add(s + t_pz + 0.2, S.bell(1319, 2.0, 0.8), -18, 0, 0.5)

    # 17) uydu: gece, deprem, şebeke çöker, uydu bağlantısı
    s, d, wt, lt = W("uydu")
    t_dp, t_c, t_u, t_h = w(wt, 1, 0.4), w(wt, 3, 1.3), w(wt, 4, 1.9), w(wt, 7, 3.2)
    M.add(s, S.shaped(d + 0.4, lambda u: 350 + 150 * np.sin(u * 5), lambda u: np.full_like(u, 1.2),
                      lambda u: np.sin(np.pi * np.clip(u, 0, 1)) ** 0.5, 280), -30, 0, 0.3)
    q = 0.0
    while q < t_c:
        M.add(s + q, S.blip(1760, 0.06, "sin", 1.0, 0.05), -30, 0.1, 0.4)
        q += 1 / 0.9 / 3
    rum = fades(filt(S.brown(t_c - t_dp + 1.3, 281), "lowpass", 120), 0.15, 0.6)
    M.add(s + t_dp - 0.05, rum, -8, 0, 0.3)
    M.add(s + t_dp - 0.05, S.boom(2.0, 60, 25, 0.8, 0.5, 282), -9, 0, 0.4)
    M.add(s + t_c, power_down(1.4, 200), -16, 0, 0.4)
    M.add(s + t_c, S.crackle(0.4, 600, 0.1, 283), -18, 0, 0.3)
    M.add(s + t_u - 0.2, S.blip(2600, 0.5, "sin", 0.5, 0.45), -24, -0.6, 0.6)
    for k in range(10):
        M.add(s + t_u + 0.3 + k * 0.15, S.blip(1900, 0.04, "sin", 1.0, 0.03), -30, -0.3 + 0.06 * k, 0.3)
    M.add(s + t_h - 0.1, S.whoosh(0.35, 800, 5000, None, 0.6, 0.6, 284), -21, 0.4, 0.2)
    M.add(s + t_h + 0.1, S.pop(285), -19, 0.4, 0.2)
    M.add(s + t_h + 0.35, S.blip(1568, 0.08, "tri", 1.0, 0.05), -22, 0.4, 0.2)
    M.add(s + t_h + 0.45, S.blip(2093, 0.1, "tri", 1.0, 0.07), -22, 0.4, 0.2)

    # 18) ama: dev "AMA", kartlar devrilir
    s, d, wt, lt = W("ama")
    t_a = w(wt, 0, 0.1)
    M.add(s + t_a + 0.05, S.boom(1.8, 90, 28, 0.6, 1.0, 290), -7, 0, 0.5)
    M.add(s + t_a + 0.05, S.clang(1.6, 220, 291), -20, 0, 0.5)
    for i in range(4):
        M.add(s + t_a + 0.05 + i * 0.04, S.whoosh(0.5, 1200, 300, None, 0.3, 0.8, 292 + i), -22, -0.6 + 0.4 * i, 0.2)
    M.add(s + t_a + 0.3, S.pad([41.2, 43.7, 61.7], d - t_a, 0.4, 0.8), -26, 0, 0.4)

    # 19) pazar: küpler düşer, dev kuleler yükselir
    s, d, wt, lt = W("pazar")
    t_11, t_ap, t_sm = w(wt, 2, 1.0), w(wt, 6, 3.2), w(wt, 8, 3.9)
    for i in range(12):                                          # görüntüdeki gibi 0.1 sn'den itibaren düşer
        M.add(s + 0.1 + i * 0.07 + 0.12, S.chunk(300 + i) * 0.7, -22, -0.2 + 0.04 * i, 0.2)
    for key, tt, pan in (("a", t_ap, -0.5), ("s", t_sm, 0.5)):
        n = 40
        for k in range(n):
            u = (k / n) ** 1.6
            M.add(s + tt - 0.1 + u * 1.3, S.tick(1500 + 20 * k, 320 + k + (0 if key == "a" else 50), 0.004, 0.03), -27,
                  pan, 0.1)
        M.add(s + tt - 0.1, S.riser(1.3, 100, 1500, False, 330 if key == "a" else 331), -22, pan, 0.3)
        M.add(s + tt - 0.1, fades(filt(S.brown(1.3, 332), "lowpass", 160), 0.2, 0.4), -17, pan, 0.3)
    M.add(s + t_sm + 1.1, S.boom(1.4, 80, 30, 0.5, 0.4, 333), -12, 0, 0.5)

    # 20) özet: röntgen taraması, güvenlik ve abone çıkar
    s, d, wt, lt = W("ozet")
    t_scan, t_g, t_ab, t_dy = w(wt, 6, 2.6), w(wt, 7, 3.3), w(wt, 9, 4.2), w(wt, 11, 5.2)
    M.add(s, S.pad([73.4, 110, 146.8], d + 0.3, 1.0, 1.2), -32, 0, 0.5)
    scan = osc(3200, 1.2, "sin") * 0.3 + filt(noise(1.2, 340), "bandpass", [2500, 6000])
    M.add(s + t_scan - 0.1, norm(fades(scan, 0.05, 0.2)), -27, 0, 0.2)
    M.add(s + t_scan - 0.1, S.whoosh(1.1, 400, 3000, 800, 0.5, 1.0, 341), -24, 0, 0.3)
    M.add(s + t_g, S.pop(342), -19, -0.5, 0.2)
    M.add(s + t_g + 0.05, S.bell(1319, 1.4, 0.7), -20, -0.5, 0.5)
    M.add(s + t_ab, S.pop(343), -19, 0.5, 0.2)
    M.add(s + t_ab + 0.05, S.bell(1760, 1.4, 0.7), -20, 0.5, 0.5)
    M.add(s + t_dy - 0.1, S.whoosh(0.25, 1500, 6000, None, 0.4, 0.5, 344), -20, 0, 0.2)

    # 21) yaşar: EKG, kalp atışları
    s, d, wt, lt = W("yasar")
    t_k, t_d, t_c, t_y = w(wt, 3, 1.4), w(wt, 6, 3.2), (lt[2] if len(lt) > 2 else d * 0.55), w(wt, 14, 6.4)
    beats = [(t_k, True), (t_d, True)]
    tb = t_c
    while tb < d - 0.1:
        beats.append((tb, False))
        tb += 0.78
    for tb, strong in beats:
        M.add(s + tb, monitor_beep(1046.5, 0.1), -20 if strong else -25, 0.2, 0.2)
        if strong:
            M.add(s + tb - 0.02, S.heartbeat(), -12, 0, 0.3)
            M.add(s + tb, S.boom(0.7, 70, 40, 0.2, 0.1, 350 + int(tb * 10)), -16, 0, 0.3)
    M.add(s + t_y, S.bell(1319, 2.2, 0.8), -18, -0.2, 0.5)
    M.add(s + t_y + 0.08, S.bell(1661, 2.2, 0.8), -19, 0.0, 0.5)
    M.add(s + t_y + 0.16, S.bell(1976, 2.2, 0.8), -20, 0.2, 0.5)

    # 22) final: telefon cebe kayar, "SEN ALIR MISIN?", imza
    s, d, wt, lt = W("final")
    t_cb, t_b = w(wt, 2, 0.7), (lt[1] if len(lt) > 1 else d * 0.4)
    t_al = w(wt, 6, t_b + 0.3)
    t_end = (wt[-1] if wt else d * 0.6) + 0.9
    M.add(s + t_cb - 0.15, rustle(1.0, 360), -19, 0.1, 0.2)
    M.add(s + t_cb + 0.7, S.boom(0.5, 110, 60, 0.12, 0.2, 361), -20, 0, 0.3)
    M.add(s + t_b - 0.05, S.boom(1.0, 120, 40, 0.3, 0.6, 362), -12, 0, 0.3)
    M.add(s + t_al + 0.05, S.boom(1.3, 110, 34, 0.4, 0.9, 363), -9, 0, 0.4)
    M.add(s + t_end + 0.5, S.clink(364, 3300, 1.2), -17, 0, 0.6)
    for i, f in enumerate((880, 1319, 1760)):
        M.add(s + t_end + 0.52 + i * 0.13, S.bell(f, 3.0, 0.8), -15 - i, -0.3 + 0.3 * i, 0.6)

    # ======== ORTAK KISIM (her filmde kalır) ========
    # geçiş sesleri (zamanlama.GECIS tablosundan; film.py de aynı tabloyu kullanır)
    starts = {sc["scene"]: sc["start"] for sc in sahneler}
    for sc, (tur, h, ayar) in Z.GECIS.items():
        if sc not in starts:
            continue
        b = starts[sc]
        sd = sum(map(ord, sc))
        if tur == "savur":
            M.add(b - 0.3, S.whoosh(0.55, 300, 5000, 700, 0.55, 0.9, sd), -14, 0.4 if ayar == "sol" else -0.4, 0.2)
        elif tur == "zoom":
            M.add(b - 0.45, S.riser(0.45, 500, 7000, False, sd), -17, 0, 0.2)
        elif tur == "bozul":
            M.add(b - h, S.glitch(2 * h + 0.05, sd), -14, 0, 0.1)
        elif tur == "flas":
            M.add(b, S.boom(1.2, 130, 40, 0.4, 0.8, sd), -8, 0, 0.35)
        elif tur in ("karart", "erit", "isik"):
            M.add(b - h - 0.1, S.whoosh(2 * h + 0.35, 200, 1400, 400, 0.45, 1.0, sd), -24, 0, 0.4)
    room = filt(S.brown(toplam, 250), "lowpass", 400)
    M.add(0, fades(room, 1.0, 1.0), -44, 0, 0.0)
    return M


def main(out, vo=None):
    import wave
    tl = Z.build(vo_words=Z.vo_yukle(vo) if vo else None)
    mix = build(tl).render()
    y, loud = S.master(mix, lufs=-19.0)
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(out, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{out}: {len(y) / SR:.2f} sn, {loud:.1f} LUFS -> -19 LUFS")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
