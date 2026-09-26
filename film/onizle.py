"""Sahne önizleme: python3 onizle.py çıktı.png sahne1,sahne2,... [p1,p2,p3]"""
import sys, time
import cv2
import numpy as np
import gfx as G
import zaman as Z

SC = {}
try:
    import sahne1
    SC.update(sahne1.SAHNELER)
except Exception as e:                           # geliştirme sırasında diğer dosya eksik olabilir
    print("sahne1 yüklenemedi:", e)
try:
    import sahne2
    SC.update(sahne2.SAHNELER)
except Exception as e:
    print("sahne2 yüklenemedi:", e)


def render_scene(ln, p):
    d = ln["end"] - ln["start"]
    t = p * d
    wt = [w - ln["start"] for w in ln["t"]]
    img, post = SC[ln["scene"]](p, t, d, wt)
    img = G.finish(img, seed=int(t * 30))
    if post:
        img = post(img)
    return img


if __name__ == "__main__":
    out, names = sys.argv[1], sys.argv[2].split(",")
    ps = [float(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3 else ["0.15", "0.5", "0.85"])]
    tl = {ln["scene"]: ln for ln in Z.build()}
    rows = []
    for n in names:
        tiles = []
        for p in ps:
            t0 = time.time()
            im = render_scene(tl[n], p)
            print(f"{n} p={p:.2f} {time.time() - t0:.2f}s", flush=True)
            tiles.append(cv2.resize(G.to_u8(im), (270, 480), interpolation=cv2.INTER_AREA))
        rows.append(np.hstack(tiles))
    cv2.imwrite(out, cv2.cvtColor(np.vstack(rows), cv2.COLOR_RGB2BGR))
