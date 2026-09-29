"""Seslendirme kaydı + efekt sesleri -> Instagram'a hazır miks (WAV, 48 kHz stereo).

Kullanım:
  python3 film/miks.py ses_kaydi.m4a sfx.wav miks.wav [--gecikme 0.0] [--efekt-db 0] [--kisma-db 9]
Sonra görüntüyle birleştir:
  python3 film/teslim.py master.mp4 miks.wav cikti.mp4

- Kayıt: 80 Hz altı uğultu kesilir, ses yüksekliği -16 LUFS'a getirilir.
- Efektler konuşma sırasında --kisma-db kadar kısılır (ducking), duraklamalarda tam seviyeye döner.
- Sonuç -14 LUFS (Instagram/Reels seviyesi), gerçek tepe -2 dBTP (AAC sıkıştırmasında taşmasın diye).
"""
import argparse, subprocess, wave
import numpy as np
import ses as S                       # film/ses.py: filtre ve mastering araçları

SR = S.SR


def oku(path):
    """Her türlü ses/video dosyasının sesini 48 kHz stereo float olarak oku."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


def kisma_kazanci(ses, kisma_db=9.0, pencere=0.02, atak=0.03, birakma=0.4, onden=0.05):
    """Konuşma olan yerlerde efektleri kısan kazanç eğrisi (örnek başına, doğrusal)."""
    hop = int(pencere * SR)
    m = ses.mean(1)
    n = len(m) // hop + 1
    kare = np.pad(m, (0, n * hop - len(m))).reshape(n, hop)
    db = 20 * np.log10(np.sqrt((kare ** 2).mean(1)) + 1e-9)
    esik = np.percentile(db[db > -70], 90) - 24 if (db > -70).any() else 0.0   # konuşma seviyesinin ~24 dB altı
    acik = (db > esik).astype(np.float64)
    g = np.zeros(n)
    k_up, k_dn = 1 - np.exp(-pencere / atak), 1 - np.exp(-pencere / birakma)
    for i in range(1, n):
        g[i] = g[i - 1] + (acik[i] - g[i - 1]) * (k_up if acik[i] > g[i - 1] else k_dn)
    t = (np.arange(n) + 0.5) * hop
    gs = np.interp(np.arange(len(m)) + onden * SR, t, g)        # konuşmadan biraz önce kısmaya başla
    return (10 ** (-kisma_db * gs / 20)).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kayit")
    ap.add_argument("sfx")
    ap.add_argument("cikti")
    ap.add_argument("--gecikme", type=float, default=0.0, help="kaydın filmde başlayacağı saniye")
    ap.add_argument("--efekt-db", type=float, default=0.0, help="efektlerin genel seviyesi (+/- dB)")
    ap.add_argument("--kisma-db", type=float, default=9.0, help="konuşurken efektlerin kısılma miktarı (dB)")
    a = ap.parse_args()
    import pyloudnorm as pyln
    meter = pyln.Meter(SR)
    v = oku(a.kayit)
    v = np.stack([S.filt(v[:, c], "highpass", 80) for c in range(2)], 1)
    v *= 10 ** ((-16.0 - meter.integrated_loudness(v.astype(np.float64))) / 20)
    v = np.pad(v, ((int(round(a.gecikme * SR)), 0), (0, 0)))
    fx = oku(a.sfx) * 10 ** (a.efekt_db / 20)
    n = max(len(v), len(fx))
    v = np.pad(v, ((0, n - len(v)), (0, 0)))
    fx = np.pad(fx, ((0, n - len(fx)), (0, 0)))
    mix = v + fx * kisma_kazanci(v, a.kisma_db)[:, None]
    y, loud = S.master(mix, lufs=-14.0, ceiling_db=-2.0)
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(a.cikti, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"{a.cikti}: {len(y) / SR:.2f} sn, ham {loud:.1f} LUFS -> -14 LUFS")


if __name__ == "__main__":
    main()
