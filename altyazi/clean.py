import cv2, numpy as np
def text_mask(band, p=12):
    mn = band.min(axis=2)
    core = (mn > 215) & ((band.max(axis=2).astype(int) - mn) < 40)
    core[:p, :] = core[-p:, :] = False
    core[:, :p] = core[:, -p:] = False
    return core
def fill_normconv(band, m, sig=(4, 10, 24)):
    img = band.astype(np.float32)
    valid = (1 - m).astype(np.float32)
    out = img.copy(); todo = m.astype(bool).copy()
    for s in sig:
        num = cv2.GaussianBlur(img * valid[..., None], (0, 0), s)
        den = cv2.GaussianBlur(valid, (0, 0), s)[..., None]
        est = num / np.maximum(den, 1e-4)
        ok = todo & (den[..., 0] > 0.15)
        out[ok] = est[ok]; todo &= ~ok
    out[todo] = est[todo]
    return out
def clean(fr, method="norm", rad=6):
    fr = fr.copy()
    y0, y1, x0, x1, p = 584, 640, 150, 630, 30
    band = fr[y0 - p:y1 + p, x0 - p:x1 + p]
    core = text_mask(band, p)
    if core.sum() < 30:
        return fr
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rad + 1, 2 * rad + 1))
    m = cv2.dilate(core.astype(np.uint8), k)
    if method == "telea":
        f = cv2.inpaint(band, m * 255, 7, cv2.INPAINT_TELEA).astype(np.float32)
        f = cv2.GaussianBlur(f, (0, 0), 2.0)
    else:
        f = fill_normconv(band, m)
    # subtle grain so the patch doesn't look plastic
    f += np.random.normal(0, 2.2, f.shape).astype(np.float32)
    feather = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 2.5)
    feather = np.clip(feather * 1.6, 0, 1)[..., None]
    band[:] = np.clip(band * (1 - feather) + f * feather, 0, 255).astype(np.uint8)
    return fr
