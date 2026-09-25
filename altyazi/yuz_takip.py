"""Videodaki yüzün konumunu kare kare ölçer (MediaPipe BlazeFace, ONNX).

Model: npm'deki "jp.keijiro.mediapipe.blazeface" paketi (Apache-2.0), model_indir.sh indirir.
Tam ekran videolarda altyazının yüzü kapatmaması için kullanılır.
"""
import os, sys
import numpy as np
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "models", "blazeface", "face_detection_back_256x256_barracuda.onnx")
N = 256


def _anchors():
    a16 = [((x + 0.5) / 16, (y + 0.5) / 16) for y in range(16) for x in range(16) for _ in range(2)]
    a8 = [((x + 0.5) / 8, (y + 0.5) / 8) for y in range(8) for x in range(8) for _ in range(6)]
    return np.array(a16 + a8, np.float32)


class FaceDetector:
    def __init__(self, model=MODEL):
        so = ort.SessionOptions()
        so.log_severity_level = 3
        self.sess = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
        self.anchors = _anchors()

    def detect(self, rgb):
        """rgb: HxWx3 uint8. Returns (score, x0, y0, x1, y1) in frame fractions, or None."""
        h, w = rgb.shape[:2]
        side = max(h, w)
        sq = np.zeros((side, side, 3), np.uint8)             # letterbox to a square
        ox, oy = (side - w) // 2, (side - h) // 2
        sq[oy:oy + h, ox:ox + w] = rgb
        import cv2
        inp = cv2.resize(sq, (N, N), interpolation=cv2.INTER_AREA).astype(np.float32) / 127.5 - 1.0
        s16, s8, r16, r8 = self.sess.run(None, {"input:0": inp[None]})
        raw = np.concatenate([s16[0, :, 0], s8[0, :, 0]]).astype(np.float64)
        scores = 1 / (1 + np.exp(-np.clip(raw, -100, 100)))
        reg = np.concatenate([r16[0], r8[0]])
        i = int(np.argmax(scores))
        if scores[i] < 0.5:
            return None
        # weighted average of overlapping confident boxes (MediaPipe-style blending)
        cx = reg[:, 0] / N + self.anchors[:, 0]
        cy = reg[:, 1] / N + self.anchors[:, 1]
        bw, bh = reg[:, 2] / N, reg[:, 3] / N
        near = (scores > 0.5) & (np.abs(cx - cx[i]) < bw[i] / 2) & (np.abs(cy - cy[i]) < bh[i] / 2)
        wts = scores[near]
        box = [float(np.average(v[near], weights=wts)) for v in (cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2)]
        x0, y0, x1, y1 = [(b * side - o) for b, o in zip(box, (ox, oy, ox, oy))]
        return float(scores[i]), x0 / w, y0 / h, x1 / w, y1 / h


def track(frames, step=3, fps=30):
    """frames: iterable of RGB frames. Returns list of (t, box or None) every `step` frames."""
    det, out = FaceDetector(), []
    for i, fr in enumerate(frames):
        if i % step == 0:
            out.append((i / fps, det.detect(fr)))
    return out


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    import render as R
    src = sys.argv[1]
    npl = float(sys.argv[2]) if len(sys.argv) > 2 else None
    vf = R.hdr_to_sdr(npl) if npl else None
    res = track(R.read_frames(src, vf), step=5)
    bottoms = [b[4] * 100 for _, b in res if b]
    print(f"yüz bulunan kare: {len(bottoms)}/{len(res)}")
    if bottoms:
        print("çene (%): p10={:.1f} p50={:.1f} p90={:.1f} max={:.1f}".format(*np.percentile(bottoms, [10, 50, 90]), max(bottoms)))
    for t, b in res[::2]:
        print(f"  t={t:5.1f}  " + (f"skor={b[0]:.2f} üst={b[2]*100:5.1f}% alt={b[4]*100:5.1f}% x={b[1]*100:4.0f}-{b[3]*100:3.0f}%" if b else "yüz yok"))
