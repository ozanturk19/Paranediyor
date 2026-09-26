"""Tekstil filmi: sahneler + geçişler + renk işlemi + altyazı + ses -> MP4 (1080x1920, 30 kare/sn).

Kullanım:
  python3 film.py tam  cikti.mp4 [--vo kelimeler.json]
  python3 film.py kontrol klasor [--adim 15]
  python3 film.py kare cikti.png saniye [saniye ...]
Önce 3D plakaların çizilmiş olması gerekir (b3d/ klasörü; TEKSTIL_3D_OUT ile yeri verilir).
"""
import argparse, os, subprocess, sys, time
import multiprocessing as mp
import cv2
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "film"))
import gfx as G                     # noqa: E402
import gecis as GC                  # noqa: E402
import zamanlama as Z               # noqa: E402
import sahneler as SH               # noqa: E402

R = G.R
FPS = 30
CAP_TOP = 890
TABLO = Z.GECIS
ST = {}


def setup(vo=None):
    tl = Z.build(vo_words=vo)
    R.ON_VIDEO, R.MAXW = True, 560
    last = tl[-1]
    cues = [R.Cue(a, min(b, last["end_speech"] + 0.45) if a >= last["t"][0] - 0.1 else b, m)
            for a, b, m in Z.caption_cues(tl)]                  # son altyazı kapanış kartından önce kalksın
    for c in cues:
        c.layout(CAP_TOP)
    scs = Z.scenes(tl)
    ST.update(tl=tl, scs=scs, cues=cues, n=int(round(scs[-1]["end"] * FPS)))


def scene_img(k, t_abs, seed):
    sc = ST["scs"][k]
    s, d = sc["start"], sc["end"] - sc["start"]
    t = t_abs - s
    wt = [w - s for w in sc["t"]]
    lt = [w - s for w in sc["line_t"]]
    img, post = SH.SAHNELER[sc["scene"]](t / d, t, d, wt, lt)
    img = SH.finish(img, seed, exposure=SH.EXPOSURE[sc["scene"]], bloom_k=SH.BLOOM.get(sc["scene"], 0.35))
    img = SH.shade_top(img, 0.35)                       # üstteki etiketler her zeminde okunsun
    return post(img) if post else img


def captions(img, t):
    act = [c for c in ST["cues"] if c.start <= t < c.end]
    if not act:
        return img
    layer = Image.new("RGBA", (G.W, G.H), (0, 0, 0, 0))
    for c in act:
        c.draw(layer, t)
    a = np.asarray(layer, np.float32) / 255
    return G.over(img, a[..., :3], a[..., 3])


def frame(i):
    scs, t = ST["scs"], i / FPS
    seed = i // 2
    k = max(j for j, sc in enumerate(scs) if sc["start"] <= t)
    img = None
    if k > 0:
        tur, h, ayar = TABLO[scs[k]["scene"]]
        b = scs[k]["start"]
        if h > 0 and t < b + h:
            img = GC.uygula(tur, ayar, scene_img(k - 1, t, seed), scene_img(k, t, seed), (t - (b - h)) / (2 * h), i)
    if img is None and k + 1 < len(scs):
        tur, h, ayar = TABLO[scs[k + 1]["scene"]]
        b = scs[k + 1]["start"]
        if h > 0 and t >= b - h:
            img = GC.uygula(tur, ayar, scene_img(k, t, seed), scene_img(k + 1, t, seed), (t - (b - h)) / (2 * h), i)
    if img is None:
        img = scene_img(k, t, seed)
    return G.to_u8(captions(img, t))


def frame_bytes(i):
    return frame(i).tobytes()


def run(indices, sink, workers=4):
    t0 = time.time()
    with mp.get_context("fork").Pool(workers) as pool:
        for n, buf in enumerate(pool.imap(frame_bytes, indices, chunksize=1), 1):
            sink(n, buf)
            if n % 30 == 0 or n == len(indices):
                el = time.time() - t0
                print(f"  {n}/{len(indices)} kare  {el:5.0f} sn  (kalan ~{el / n * (len(indices) - n):4.0f} sn)", flush=True)


def tam(out, workers=4):
    ff = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{G.W}x{G.H}", "-r", str(FPS),
        "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-profile:v", "high",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    run(list(range(ST["n"])), lambda n, b: ff.stdin.write(b), workers)
    ff.stdin.close()
    ff.wait()
    print("hazır:", out)


def kontrol(folder, step=15, workers=4, cols=8):
    os.makedirs(folder, exist_ok=True)
    idx = list(range(0, ST["n"], step))
    thumbs = []

    def sink(n, buf):
        im = np.frombuffer(buf, np.uint8).reshape(G.H, G.W, 3)
        th = cv2.resize(im, (216, 384), interpolation=cv2.INTER_AREA).copy()
        tt = idx[n - 1] / FPS
        cv2.putText(th, f"{tt:5.2f}", (6, 376), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
        cv2.putText(th, f"{tt:5.2f}", (6, 376), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        thumbs.append(th)
    run(idx, sink, workers)
    per = cols * 3
    for p in range(0, len(thumbs), per):
        page = thumbs[p:p + per] + [np.zeros_like(thumbs[0])] * max(0, per - len(thumbs[p:p + per]))
        rows = [np.hstack(page[r * cols:(r + 1) * cols]) for r in range(3)]
        cv2.imwrite(os.path.join(folder, f"sayfa_{p // per + 1:02d}.jpg"), cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"{len(thumbs)} kare -> {folder}")


def kare(out, times):
    ims = [cv2.resize(frame(int(round(t * FPS))), (540, 960), interpolation=cv2.INTER_AREA) for t in times]
    cv2.imwrite(out, cv2.cvtColor(np.hstack(ims), cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["tam", "kontrol", "kare"])
    ap.add_argument("cikti")
    ap.add_argument("zamanlar", nargs="*", type=float)
    ap.add_argument("--vo")
    ap.add_argument("--adim", type=int, default=15)
    ap.add_argument("--is", type=int, default=4, dest="workers")
    a = ap.parse_args()
    setup(Z.vo_yukle(a.vo) if a.vo else None)
    if a.mod == "tam":
        tam(a.cikti, a.workers)
    elif a.mod == "kontrol":
        kontrol(a.cikti, a.adim, a.workers)
    else:
        kare(a.cikti, a.zamanlar)
