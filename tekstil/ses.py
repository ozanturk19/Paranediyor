"""Tekstil filmi ses tasarımı (sayısal üretim). Seslendirmenin altında kalacak şekilde ölçülü.

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
    scs = {sc["scene"]: sc for sc in Z.scenes(tl)}
    M = S.Mix(scs["final"]["end"])

    def W(name):
        sc = scs[name]
        return sc["start"], sc["end"] - sc["start"], [w - sc["start"] for w in sc["t"]], \
            [x - sc["start"] for x in sc["line_t"]]

    # 1) fabrika: floresan vızıltısı, uzak makineler, 350.000 sayacı
    s, d, wt, lt = W("fabrika")
    M.add(s, S.boom(1.4, 80, 32, 0.5, 0.15, 1), -12, 0, 0.3)
    M.add(s, fades(filt(buzz(d + 0.4, 3), "bandpass", [80, 3000]), 0.4, 0.4), -34, 0, 0.3)
    M.add(s, fades(filt(S.brown(d + 0.4, 4), "lowpass", 300), 0.3, 0.4), -30, 0, 0.2)
    for k in range(3):
        M.add(s + 0.4 + k * 1.3, sewing(0.7, 11 + k * 2, 30 + k), -32, -0.6 + 0.6 * k, 0.8)
    t_num = wt[9] if len(wt) > 9 else d * 0.7
    M.add(s + t_num - 0.15, S.boom(1.6, 110, 30, 0.5, 0.8, 5), -6, 0, 0.4)
    for k in range(22):
        u = 1 - (1 - k / 22) ** (1 / 3)
        M.add(s + t_num - 0.15 + u * 1.05, S.tick(2600 + 30 * k, 50 + k, 0.003), -24, 0, 0.05)

    # 2) söylenti: harita açılır, oklar akar, konuşma balonları
    s, d, wt, lt = W("soylenti")
    M.add(s - 0.25, S.whoosh(0.7, 200, 2500, 600, 0.45, 0.9, 60), -18, 0, 0.3)
    for k in range(10):
        M.add(s + d * 0.15 + k * 0.08, S.whoosh(0.5, 600, 4000, None, 0.7, 0.6, 61 + k), -30, -0.5 + k * 0.1, 0.2)
    for i in range(3):
        M.add(s + 0.3 + i * 0.35, S.pop(70 + i), -18, (-0.5, 0.5, -0.3)[i], 0.2)

    # 3) ilk fabrika: yakınlaşma, pin, 150 -> 350.000 kıyası
    s, d, wt, lt = W("ilk")
    M.add(s, S.whoosh(1.2, 300, 3000, 500, 0.6, 1.0, 80), -20, 0, 0.3)
    t_ilk = wt[3] if len(wt) > 3 else d * 0.3
    M.add(s + t_ilk - 0.1, S.bell(1760, 1.2, 0.6), -19, 0.3, 0.5)
    t_150 = wt[9] if len(wt) > 9 else d * 0.7
    M.add(s + t_150, S.pop(81), -16, 0, 0.2)
    M.add(s + t_150 + 1.1, S.riser(max(0.4, d - t_150 - 1.1), 200, 3000, True, 82), -20, 0, 0.4)
    M.add(s + d - 0.05, S.boom(1.5, 90, 30, 0.5, 0.3, 83), -12, 0, 0.5)

    # 4-5) neden / işçilik: dikiş makinesi yakın çekim, kartlar
    s, d, wt, lt = W("neden")
    s2, d2, _, _ = W("iscilik")
    M.add(s, sewing(d + d2 + 0.2, 3.75, 90), -17, 0.1, 0.15)
    t_n = wt[2] if len(wt) > 2 else d * 0.4
    for i in range(3):
        M.add(s + t_n + i * 0.22, S.whoosh(0.35, 800, 5000, None, 0.6, 0.6, 91 + i), -24, -0.4, 0.2)
        M.add(s + t_n + i * 0.22 + 0.2, S.tick(1800, 95 + i, 0.01, 0.08), -22, -0.4, 0.2)
    M.add(s2 + 0.05, S.pop(96), -18, 0, 0.2)
    for j in range(6):
        M.add(s2 + 0.2 + j * 0.1, S.blip(500 + 90 * j, 0.08, "tri", 1.0, 0.03), -24, -0.3 + 0.12 * j, 0.2)

    # 6) faiz: yükselen eğri
    s, d, wt, lt = W("faiz")
    t_f = wt[4] if len(wt) > 4 else d * 0.55
    M.add(s + 0.05, S.whoosh(0.5, 400, 3000, None, 0.5, 0.8, 100), -22, 0, 0.3)
    a, b = t_f - 0.4, t_f + 0.8
    tt_ = tax(b - a + 0.3)
    tone = S.osc(160 * 2 ** (2.2 * np.clip(tt_ / (b - a), 0, 1) ** 2), b - a + 0.3, "saw")
    M.add(s + a, norm(fades(filt(tone, "lowpass", 2500), 0.1, 0.25)), -28, 0, 0.3)
    M.add(s + b - 0.1, S.boom(0.8, 140, 55, 0.18, 0.4, 101), -14, 0, 0.3)

    # 7) ihracat: liman rüzgârı, uzak gemi düdüğü, çubuklar, -%16
    s, d, wt, lt = W("ihracat")
    M.add(s, S.shaped(d + 0.4, lambda u: 400 + 300 * np.sin(np.pi * u), lambda u: np.full_like(u, 1.0),
                      lambda u: np.sin(np.pi * np.clip(u, 0, 1)) ** 0.5, 110), -27, 0, 0.3)
    M.add(s + 0.3, ship_horn(2.4), -24, 0.4, 0.9)
    t_ab = wt[1] if len(wt) > 1 else d * 0.15
    M.add(s + t_ab, S.whoosh(0.4, 500, 3000, None, 0.5, 0.8, 111), -22, 0, 0.2)
    t_16 = wt[11] if len(wt) > 11 else d * 0.75
    M.add(s + t_16 - 0.9, S.shaped(0.8, lambda u: 900 - 500 * u, lambda u: np.full_like(u, 0.5), lambda u: u, 112),
          -26, 0.2, 0.2)
    M.add(s + t_16 - 0.05, S.boom(1.2, 160, 40, 0.35, 0.5, 113), -9, 0, 0.4)

    # 8) suriye: sıcak rüzgâr, soru
    s, d, wt, lt = W("suriye")
    M.add(s, S.shaped(d + 0.5, lambda u: 300 + 200 * u, lambda u: np.full_like(u, 1.1),
                      lambda u: np.sin(np.pi * np.clip(u, 0, 1)), 120), -25, 0, 0.4)
    M.add(s + 0.35, S.boom(1.0, 120, 45, 0.3, 0.2, 121), -13, 0, 0.4)

    # 9) ücret: iki çubuk
    s, d, wt, lt = W("ucret")
    M.add(s + 0.1, S.whoosh(0.5, 300, 2500, None, 0.5, 0.8, 130), -22, 0, 0.3)
    for tt, val, pan in ((wt[10] if len(wt) > 10 else d * 0.5, 575, -0.5), (wt[14] if len(wt) > 14 else d * 0.85, 100, 0.5)):
        n = 18 if val > 300 else 6
        for k in range(n):
            M.add(s + tt - 0.5 + k * (1.0 / n), S.tick(2200 + 40 * k, 131 + k, 0.003), -26, pan, 0.05)
        M.add(s + tt + 0.5, S.clink(140 + val, 2600 if val > 300 else 3400, 0.6), -18, pan, 0.4)

    # 10) yaptırım: kilit açılır
    s, d, wt, lt = W("yaptirim")
    t_k = wt[3] if len(wt) > 3 else d * 0.6
    M.add(s + t_k - 0.12, unlock(), -10, 0, 0.35)
    M.add(s + t_k, S.boom(0.9, 130, 50, 0.2, 0.3, 150), -13, 0, 0.3)
    M.add(s + t_k + 0.1, S.pop(151), -18, 0, 0.2)

    # 11) taşınma: oklar yola çıkar, "HAYIR"da bant durur
    s, d, wt, lt = W("tasinma")
    t_h = lt[1] if len(lt) > 1 else d * 0.55
    sw = np.zeros(N(t_h + 0.1), np.float32)
    for k in range(8):
        place(sw, 0.2 + k * 0.12, S.whoosh(0.6, 500, 3500, None, 0.7, 0.7, 160 + k) * 0.6)
    M.add(s, norm(sw), -22, 0, 0.2)
    M.add(s + t_h - 0.05, tape_stop(S.whoosh(1.2, 300, 3000, None, 0.3, 0.9, 170), 0.5), -16, 0, 0.2)
    M.add(s + t_h, S.boom(1.1, 120, 38, 0.3, 0.9, 171), -7, 0, 0.35)

    # 12) altyapı: jeneratör, kablo vızıltısı, titreyen lamba
    s, d, wt, lt = W("altyapi")
    M.add(s - 0.2, generator(d + 0.6), -20, 0.3, 0.3)
    M.add(s, buzz(d + 0.3, 180), -27, -0.2, 0.2)
    for k in range(6):
        M.add(s + 0.3 + k * 0.4, S.crackle(0.12, 400, 0.05, 181 + k), -26, -0.4, 0.2)

    # 13) elektrik: bölge bölge sönen ışıklar
    s, d, wt, lt = W("elektrik")
    t_y = wt[4] if len(wt) > 4 else d * 0.5
    M.add(s, fades(filt(buzz(d, 190), "bandpass", [60, 1500]), 0.3, 0.4), -30, 0, 0.3)
    r = np.random.default_rng(191)
    for k in range(9):
        tk = t_y - 1.2 + k * 0.17 + r.uniform(-0.05, 0.05)
        M.add(s + tk, S.tick(r.uniform(500, 900), 192 + k, 0.02, 0.1), -20, r.uniform(-0.7, 0.7), 0.4)
    tt_ = tax(1.6)
    down = osc(120 * np.exp(-tt_ * 1.5), 1.6, "saw") * np.exp(-tt_ * 1.2)
    M.add(s + t_y - 0.4, norm(filt(down, "lowpass", 900)), -17, 0, 0.4)

    # 14) banka: bankamatik hata sesi
    s, d, wt, lt = W("banka")
    M.add(s + 0.25, beep(), -18, 0.2, 0.2)
    M.add(s + 1.1, beep(1200, 800, 0.12), -22, 0.2, 0.2)
    for i in range(3):
        M.add(s + 0.3 + i * 0.25, S.pop(200 + i), -22, -0.5, 0.2)

    # 15) vergi: liman, bariyer ışığı, dönen oran göstergesi
    s, d, wt, lt = W("vergi")
    M.add(s, S.shaped(d + 0.4, lambda u: 500 + 0 * u, lambda u: np.full_like(u, 1.0), lambda u: 0.6 + 0 * u, 210),
          -30, 0, 0.3)
    t_v = wt[3] if len(wt) > 3 else d * 0.3
    k = 0
    while t_v + k / 2.2 < d:
        M.add(s + t_v + k / 2.2, S.flap(211 + k) * 1.6, -18, 0.1, 0.1)
        k += 1

    # 16) başlangıç: olumlu / olumsuz
    s, d, wt, lt = W("baslangic")
    t_b = wt[3] if len(wt) > 3 else 0.5
    t_g = wt[6] if len(wt) > 6 else d * 0.7
    M.add(s + t_b, S.bell(1319, 1.2, 0.6), -17, -0.2, 0.4)
    M.add(s + t_b + 0.08, S.bell(1976, 1.2, 0.6), -18, 0.2, 0.4)
    M.add(s + t_g, S.boom(0.7, 90, 45, 0.15, 0.3, 220), -14, 0, 0.3)
    M.add(s + t_g, filt(osc(140, 0.4, "saw") * env(0.4, 0.005, 0.15), "lowpass", 1200), -20, 0, 0.2)

    # 17) final: yeni pinler, oklar kıpırdar, imza sesi
    s, d, wt, lt = W("final")
    for i, idx in enumerate((2, 4)):
        tt = wt[idx] if len(wt) > idx else d * (0.2 + 0.1 * i)
        M.add(s + tt, S.bell(2093 + i * 300, 1.0, 0.4), -21, 0.3 - 0.6 * i, 0.5)
    t_h = wt[-1] if wt else d * 0.6
    for k in range(4):
        M.add(s + t_h - 0.2 + k * 0.12, S.whoosh(0.6, 500, 4000, None, 0.7, 0.7, 230 + k), -24, -0.3 + 0.2 * k, 0.3)
    end_t = t_h + 0.9
    M.add(s + end_t, S.clink(240, 3300, 1.2), -17, 0, 0.6)
    for i, f in enumerate((880, 1319, 1760)):
        M.add(s + end_t + 0.02 + i * 0.13, S.bell(f, 3.0, 0.8), -15 - i, -0.3 + 0.3 * i, 0.6)

    # geçiş sesleri
    starts = {sc["scene"]: sc["start"] for sc in Z.scenes(tl)}
    for sc, (tur, h, ayar) in Z.GECIS.items():
        b = starts[sc]
        sd = sum(map(ord, sc))
        if tur == "savur":
            M.add(b - 0.3, S.whoosh(0.55, 300, 5000, 700, 0.55, 0.9, sd), -14, 0.4 if ayar == "sol" else -0.4, 0.2)
        elif tur == "zoom":
            M.add(b - 0.45, S.riser(0.45, 500, 7000, False, sd), -17, 0, 0.2)
        elif tur in ("karart", "erit"):
            M.add(b - h - 0.1, S.whoosh(2 * h + 0.35, 200, 1400, 400, 0.45, 1.0, sd), -24, 0, 0.4)
    room = filt(S.brown(scs["final"]["end"], 250), "lowpass", 400)
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
