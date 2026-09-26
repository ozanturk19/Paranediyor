"""Blender'ın çok katmanlı EXR çıktısını oku: renk (doğrusal), derinlik, nesne numarası.

Komut satırı: python3 exr.py girdi.exr cikti.png  -> hızlı önizleme (ton eşleme + sRGB)
"""
import sys
import numpy as np
import OpenEXR


def oku(path):
    """Çok parçalı (Blender 5) ya da tek parçalı çok katmanlı EXR."""
    ch = {}
    with OpenEXR.File(path, separate_channels=True) as f:
        for p in f.parts:
            for n, c in p.channels.items():
                ch[n] = np.asarray(c.pixels, np.float32)

    def get(suffix):
        for n in ch:
            if n.endswith(suffix):
                return ch[n]
        return None
    out = {"rgb": np.dstack([get(f"Combined.{c}") for c in "RGB"])}
    d = get("Depth.Z")
    if d is not None:
        out["depth"] = d
    ix = get("Object Index.X")
    if ix is None:
        ix = get("IndexOB.X")
    if ix is not None:
        out["index"] = ix
    return out


def onizleme(rgb, exposure=1.0):
    x = np.maximum(rgb * exposure, 0)
    x = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    x = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0, 1), 1 / 2.4) - 0.055)
    return (np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    import cv2
    e = oku(sys.argv[1])
    print({k: (v.shape, float(np.percentile(v, 50)), float(v.max())) for k, v in e.items()})
    cv2.imwrite(sys.argv[2], cv2.cvtColor(onizleme(e["rgb"], float(sys.argv[3]) if len(sys.argv) > 3 else 1.0),
                                          cv2.COLOR_RGB2BGR))
