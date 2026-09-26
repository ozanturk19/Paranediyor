"""Filmin ana çizimi: sahneler + geçişler + renk işlemi + altyazı + ses -> MP4 (1080x1920, 30 kare/sn).

Kullanım:
  python3 film.py tam  cikti.mp4 [--ses sfx.wav] [--vo kelimeler.json]   # tam film
  python3 film.py kontrol klasor [--adim 15]                              # her n. kareden kontrol sayfaları
"""
import argparse, json, os, subprocess, sys, time
import multiprocessing as mp
import cv2
import numpy as np
from PIL import Image
import gfx as G
import zaman as Z
import gecis as GC
import sahne1
import sahne2

R = G.R
FPS = 30
SC = {**sahne1.SAHNELER, **sahne2.SAHNELER}
CAP_TOP = 890                      # altyazı bloğunun üstü (tasarım px; x1.5 = 1335 px)
ST = {}


def setup(vo=None):
    tl = Z.build(vo_words=vo)
    R.ON_VIDEO, R.MAXW = True, 560
    cues = [R.Cue(a, b, m) for a, b, m in Z.caption_cues(tl)]
    for c in cues:
        c.layout(CAP_TOP)
    ST.update(tl=tl, cues=cues, n=int(round(tl[-1]["end"] * FPS)))


def scene_img(k, t_abs, seed):
    ln = ST["tl"][k]
    s, d = ln["start"], ln["end"] - ln["start"]
    t = t_abs - s
    img, post = SC[ln["scene"]](t / d, t, d, [w - s for w in ln["t"]])
    img = G.finish(img, seed=seed, grain_amt=0.03)
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
    tl, t = ST["tl"], i / FPS
    seed = i // 2                                            # tane 15 kare/sn değişir (film hissi, daha az veri)
    k = max(j for j, ln in enumerate(tl) if ln["start"] <= t)
    img = None
    if k > 0:                                                # bu sahneye giriş geçişi
        tur, h, ayar = GC.TABLO[tl[k]["scene"]]
        b = tl[k]["start"]
        if h > 0 and t < b + h:
            u = (t - (b - h)) / (2 * h)
            img = GC.uygula(tur, ayar, scene_img(k - 1, t, seed), scene_img(k, t, seed), u, i)
        elif tur == "flas":
            img = GC.flas(scene_img(k, t, seed), t - b)
    if img is None and k + 1 < len(tl):                      # sonraki sahneye çıkış geçişi
        tur, h, ayar = GC.TABLO[tl[k + 1]["scene"]]
        b = tl[k + 1]["start"]
        if h > 0 and t >= b - h:
            u = (t - (b - h)) / (2 * h)
            img = GC.uygula(tur, ayar, scene_img(k, t, seed), scene_img(k + 1, t, seed), u, i)
    if img is None:
        img = scene_img(k, t, seed)
    return G.to_u8(captions(img, t))


def frame_bytes(i):
    return frame(i).tobytes()


def encoder(out, fps, crf=16):
    return subprocess.Popen([
        "ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{G.W}x{G.H}", "-r", str(fps),
        "-i", "-", "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-profile:v", "high",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-movflags", "+faststart", out], stdin=subprocess.PIPE)


def run(indices, sink, workers=4):
    t0 = time.time()
    with mp.get_context("fork").Pool(workers) as pool:
        for n, buf in enumerate(pool.imap(frame_bytes, indices, chunksize=1), 1):
            sink(n, buf)
            if n % 30 == 0 or n == len(indices):
                el = time.time() - t0
                print(f"  {n}/{len(indices)} kare  {el:5.0f} sn  (kalan ~{el / n * (len(indices) - n):4.0f} sn)", flush=True)


def tam(out, sfx=None, workers=4):
    video = out if not sfx else out.replace(".mp4", "_video.mp4")
    ff = encoder(video, FPS)
    run(list(range(ST["n"])), lambda n, b: ff.stdin.write(b), workers)
    ff.stdin.close()
    ff.wait()
    if sfx:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", sfx, "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out],
                       check=True)
    print("hazır:", out)


def kontrol(folder, step=15, workers=4, cols=8):
    """Her `step`. kareyi küçültüp zaman damgalı kontrol sayfalarına diz."""
    os.makedirs(folder, exist_ok=True)
    idx = list(range(0, ST["n"], step))
    thumbs = []

    def sink(n, buf):
        im = np.frombuffer(buf, np.uint8).reshape(G.H, G.W, 3)
        th = cv2.resize(im, (216, 384), interpolation=cv2.INTER_AREA).copy()
        t = idx[n - 1] / FPS
        cv2.putText(th, f"{t:5.2f}", (6, 376), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
        cv2.putText(th, f"{t:5.2f}", (6, 376), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        thumbs.append(th)
    run(idx, sink, workers)
    per = cols * 3
    for p in range(0, len(thumbs), per):
        page = thumbs[p:p + per]
        page += [np.zeros_like(thumbs[0])] * (per - len(page))
        rows = [np.hstack(page[r * cols:(r + 1) * cols]) for r in range(3)]
        cv2.imwrite(os.path.join(folder, f"sayfa_{p // per + 1:02d}.jpg"), cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR),
                    [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f"{len(thumbs)} kare, {(len(thumbs) + per - 1) // per} sayfa -> {folder}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mod", choices=["tam", "kontrol"])
    ap.add_argument("cikti")
    ap.add_argument("--ses")
    ap.add_argument("--vo")
    ap.add_argument("--adim", type=int, default=15)
    ap.add_argument("--is", type=int, default=4, dest="workers")
    a = ap.parse_args()
    setup(Z.vo_yukle(a.vo) if a.vo else None)
    if a.mod == "tam":
        tam(a.cikti, a.ses, a.workers)
    else:
        kontrol(a.cikti, a.adim, a.workers)
