"""Para Ne Diyor? - kinetic Turkish caption renderer.

Markup per cue text:
  *WORD   -> key word   (big, bold caps, brand yellow)
  **WORD  -> hero word  (biggest, black on yellow pill, slight tilt)
  ~word   -> accent     (italic serif, editorial)
  word    -> normal     (small, white)
  /       -> line break
  _       -> non-breaking space inside one token
  tok@12.3 -> explicit appear time for that token
"""
import json, math, os, re, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts") + "/"
S = 1.5                       # 720x1280 design space -> 1080x1920 output
W, H = int(720 * S), int(1280 * S)
FPS = 30
YELLOW = (255, 210, 26)
LEAD = 0.06                   # words appear slightly before they are spoken
MAXW = 600                    # max caption line width (design px)
ON_VIDEO = False              # captions drawn over the picture: add outline + shadow

# iPhone HDR (HLG / Dolby Vision) -> SDR BT.709, ending in 8-bit RGB.
# npl sets the exposure: dim indoor footage needs ~35, bright daylight ~150 (see auto_npl).
def hdr_to_sdr(npl=35):
    return (f"zscale=t=linear:npl={npl:g},format=gbrpf32le,zscale=p=bt709,"
            "tonemap=tonemap=mobius:desat=0,zscale=t=bt709:d=error_diffusion,format=gbrp")

HDR_TO_SDR = hdr_to_sdr(35)

STYLES = {
    "n": dict(file="Montserrat.ttf", size=34, wght=650, color=(255, 255, 255), upper=False),
    "s": dict(file="InstrumentSerif-Italic.ttf", size=46, wght=None, color=(250, 244, 228), upper=False),
    "k": dict(file="Montserrat.ttf", size=54, wght=900, color=YELLOW, upper=True),
    "h": dict(file="Montserrat.ttf", size=58, wght=900, color=(14, 14, 14), upper=True, pill=YELLOW),
}

_font_cache = {}
def get_font(file, px, wght=None, opsz=None):
    key = (file, px, wght, opsz)
    if key not in _font_cache:
        f = ImageFont.truetype(FD + file, px, layout_engine=ImageFont.Layout.RAQM)
        axes = f.get_variation_axes() if file != "InstrumentSerif-Italic.ttf" else []
        if axes:
            vals = []
            for a in axes:
                n = a["name"].decode() if isinstance(a["name"], bytes) else a["name"]
                vals.append(wght if n == "Weight" else (opsz or a["default"]))
            f.set_variation_by_axes(vals)
        _font_cache[key] = f
    return _font_cache[key]

def tr_upper(s):
    return s.replace("i", "İ").replace("ı", "I").upper()

def ease_out_back(p, c1=1.9):
    c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2

def ease_out_cubic(p):
    return 1 - (1 - p) ** 3

# --------------------------------------------------------------------------- words
class Word:
    G = int(26 * S)  # margin around glyphs for glow / overshoot

    def __init__(self, raw, t=None):
        style = "n"
        if raw.startswith("**"):
            style, raw = "h", raw[2:]
        elif raw.startswith("*"):
            style, raw = "k", raw[1:]
        elif raw.startswith("~"):
            style, raw = "s", raw[1:]
        self.style, self.t = style, t
        st = STYLES[style]
        txt = raw.replace("_", " ")
        self.text = tr_upper(txt) if st["upper"] else txt
        self.fit = 1.0
        self.render()

    def render(self):
        st = STYLES[self.style]
        px = int(round(st["size"] * S * self.fit))
        f = get_font(st["file"], px, st["wght"])
        x0, y0, x1, y1 = f.getbbox(self.text, anchor="ls")
        self.size_px = px
        asc, desc = -y0, max(y1, int(px * 0.10))
        if self.style == "s":
            desc = max(desc, int(px * 0.14))
        padx = pady = 0
        if self.style == "h":
            padx, pady = int(14 * S * self.fit), int(7 * S * self.fit)
        self.asc, self.desc = asc + pady, desc + pady
        self.w = (x1 - x0) + 2 * padx
        G = self.G
        img = Image.new("RGBA", (self.w + 2 * G, self.asc + self.desc + 2 * G), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        ox, oy = G + padx - x0, G + self.asc
        if self.style == "h":
            r = int(12 * S * self.fit)
            # soft drop shadow under the pill
            sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle(
                [G, G + int(5 * S), G + self.w, G + self.asc + self.desc + int(5 * S)], r, fill=(0, 0, 0, 150))
            img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(6 * S)))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([G, G, G + self.w, G + self.asc + self.desc], r, fill=st["pill"] + (255,))
        if ON_VIDEO and self.style != "h":
            sw = max(2, int(round((1.5 if self.style == "s" else 2.2) * S * self.fit)))
            sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((ox, oy + int(3 * S)), self.text, font=f, fill=(0, 0, 0, 190),
                                    anchor="ls", stroke_width=sw, stroke_fill=(0, 0, 0, 190))
            img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(5 * S)))
            d = ImageDraw.Draw(img)
            d.text((ox, oy), self.text, font=f, fill=st["color"] + (255,), anchor="ls",
                   stroke_width=sw, stroke_fill=(0, 0, 0, 255))
        else:
            d.text((ox, oy), self.text, font=f, fill=st["color"] + (255,), anchor="ls")
        if self.style == "h":
            img = img.rotate(2.5, resample=Image.BICUBIC, expand=False)
        self.img = img
        # glow for key words: blurred yellow copy of the glyphs
        self.glow = None
        if self.style == "k":
            a = img.getchannel("A").filter(ImageFilter.GaussianBlur(9 * S))
            g = Image.new("RGBA", img.size, YELLOW + (0,))
            g.putalpha(a.point(lambda v: min(255, int(v * 1.6))))
            self.glow = g

    def frame_sprite(self, dt):
        """Return (image, dx, dy) for time since appearance dt (>=0)."""
        dur = {"n": 0.16, "s": 0.2, "k": 0.24, "h": 0.28}[self.style]
        s0 = {"n": 0.72, "s": 0.8, "k": 0.35, "h": 0.25}[self.style]
        p = min(1.0, dt / dur)
        sc = s0 + (1 - s0) * ease_out_back(p) if p < 1 else 1.0
        alpha = min(1.0, dt / 0.07)
        rise = (1 - ease_out_cubic(p)) * 16 * S
        base = self.img
        if self.glow is not None:
            ga = 0.85 * math.exp(-dt / 0.45) + 0.18
            if ON_VIDEO:
                ga *= 0.55
            glow = self.glow.copy()
            glow.putalpha(glow.getchannel("A").point(lambda v: int(v * ga)))
            base = Image.alpha_composite(glow, base)
        if abs(sc - 1) > 1e-3:
            w, h = base.size
            nw, nh = max(1, int(w * sc)), max(1, int(h * sc))
            spr = base.resize((nw, nh), Image.BICUBIC)
            dx, dy = (w - nw) / 2, (h - nh) / 2
        else:
            spr, dx, dy = base, 0, 0
        return spr, dx, dy + rise, alpha

# --------------------------------------------------------------------------- cues
class Cue:
    def __init__(self, start, end, markup):
        self.start, self.end = start, end
        lines = []
        for ln in markup.split("/"):
            toks = []
            for tok in ln.split():
                t = None
                m = re.match(r"^(.*)@([\d.]+)$", tok)
                if m:
                    tok, t = m.group(1), float(m.group(2))
                toks.append((tok, t))
            if toks:
                lines.append(toks)
        self.lines = [[Word(tok, t) for tok, t in ln] for ln in lines]
        self.words = [w for ln in self.lines for w in ln]
        self._assign_times()

    def _assign_times(self):
        # spread un-timed words over the first ~65% of the cue, weighted by length
        span = max(0.25, min(1.6, (self.end - self.start) * 0.65))
        lens = [max(2, len(w.text)) for w in self.words]
        total, acc = sum(lens), 0
        for w, L in zip(self.words, lens):
            if w.t is None:
                w.t = self.start + span * acc / total
            acc += L
        for w in self.words:
            w.t = max(self.start, w.t - LEAD)

    def layout(self, top_y, center_x=360):
        """Compute absolute positions (output px). Returns block height."""
        gapl = int(6 * S)
        y = top_y * S
        for ln in self.lines:
            def measure():
                tot = 0
                for i, w in enumerate(ln):
                    tot += w.w
                    if i:
                        tot += self._space(ln[i - 1], w)
                return tot
            width = measure()
            if width > MAXW * S:
                f = (MAXW * S) / width
                for w in ln:
                    w.fit = f
                    w.render()
                width = measure()
            asc = max(w.asc for w in ln)
            desc = max(w.desc for w in ln)
            x = center_x * S - width / 2
            base = y + asc
            for i, w in enumerate(ln):
                if i:
                    x += self._space(ln[i - 1], w)
                w.x = x - Word.G
                w.y = base - w.asc - Word.G
                x += w.w
            y += asc + desc + gapl
        return y - top_y * S

    @staticmethod
    def _space(a, b):
        big = max(a.size_px, b.size_px)
        return int(big * 0.24)

    def draw(self, layer, t):
        exit_d = 0.12
        fade = 1.0
        if t > self.end - exit_d:
            fade = max(0.0, (self.end - t) / exit_d)
        for w in self.words:
            dt = t - w.t
            if dt < 0:
                continue
            spr, dx, dy, a = w.frame_sprite(dt)
            a *= fade
            if a <= 0.01:
                continue
            if a < 0.999:
                spr = spr.copy()
                spr.putalpha(spr.getchannel("A").point(lambda v: int(v * a)))
            lift = (1 - fade) * 8 * S
            layer.alpha_composite(spr, (int(round(w.x + dx)), int(round(w.y + dy - lift))))


def parse_cues(text):
    cues = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        a, b, markup = line.split(None, 2)
        cues.append(Cue(float(a), float(b), markup.strip().strip("|").strip()))
    return cues

def place_cues(cues, track, bottom_limit=0.833, upper_limits=((0, 1e9, 0.15),), margin=0.012, center_x=360):
    """Put each cue right under the face; if the face is too low, move it above the face.

    track: [(t, (score, x0, y0, x1, y1) or None)] with fractions of the frame (see yuz_takip.py).
    upper_limits: [(t0, t1, frac)] - highest allowed caption top (e.g. below burned-in titles).
    Sets cue.top (design px) and cue.where ("alt", "üst" or "alt*" when nothing fits).
    """
    boxes = [b for _, b in track if b]
    chin_of = lambda b: b[4] + 0.10 * (b[4] - b[2])        # beard below the detector box
    head_of = lambda b: b[2] - 0.45 * (b[4] - b[2])        # hair above the detector box
    base = float(np.percentile([chin_of(b) for b in boxes], 90)) + margin if boxes else 0.72
    for c in cues:
        near = [b for t, b in track if b and c.start - 0.1 <= t <= c.end + 0.1]
        chin = max((chin_of(b) for b in near), default=base - margin)
        head = min((head_of(b) for b in near), default=0.0)
        upper = max((u for t0, t1, u in upper_limits if t0 <= c.start < t1), default=0.15)
        h = c.layout(base * 1280, center_x) / H
        top = min(max(base, chin + margin), bottom_limit - h)
        if top >= chin + margin:
            c.where = "alt"
        elif head - margin - h >= upper:
            top, c.where = head - margin - h, "üst"
        else:
            top, c.where = bottom_limit - h, "alt*"
        c.top = top * 1280
        c.layout(c.top, center_x)
    return base

# --------------------------------------------------------------------------- title
def draw_title(lines, x, y, size, maxw):
    """lines: list of list of (text, color). Returns RGBA layer at output res."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    px = int(size * S)
    while True:
        f = get_font("Inter.ttf", px, 750, 32)
        widths = [sum(d.textlength(t, font=f) for t, _ in ln) for ln in lines]
        if max(widths) <= maxw * S or px < 20:
            break
        px -= 1
    lh = int(px * 1.18)
    for i, ln in enumerate(lines):
        cx = x * S
        by = y * S + px + i * lh
        for t, col in ln:
            d.text((cx, by), t, font=f, fill=col + (255,), anchor="ls")
            cx += d.textlength(t, font=f)
    return layer

# --------------------------------------------------------------------------- video
def probe_size(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation", "-of", "json", src],
                         capture_output=True, text=True, check=True).stdout
    st = json.loads(out)["streams"][0]
    w, h = st["width"], st["height"]
    rot = next((int(sd["rotation"]) for sd in st.get("side_data_list", []) if "rotation" in sd), 0)
    return (h, w) if rot % 180 else (w, h)

def probe_duration(src):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())

def auto_npl(src, target=155, samples=5, candidates=(25, 35, 50, 70, 100, 120, 150, 200, 300)):
    """Pick the HDR exposure whose median luma is closest to `target` with <=5% clipped pixels."""
    w, h = probe_size(src)
    dur = probe_duration(src)
    stats = {}
    for npl in candidates:
        p50, clip = [], []
        for k in range(samples):
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{dur * (k + 0.5) / samples:.2f}", "-i", src,
                                  "-frames:v", "1", "-vf", hdr_to_sdr(npl) + ",format=rgb24",
                                  "-f", "rawvideo", "-"], capture_output=True).stdout
            x = np.frombuffer(raw[:w * h * 3], np.uint8).reshape(h, w, 3)
            p50.append(np.percentile(x @ np.array([0.2126, 0.7152, 0.0722]), 50))
            clip.append((x.max(axis=2) >= 250).mean())
        stats[npl] = (float(np.mean(p50)), float(np.mean(clip)))
    pool = [n for n in candidates if stats[n][1] <= 0.05] or list(candidates)
    return min(pool, key=lambda n: abs(stats[n][0] - target)), stats

def read_frames(src, vf_in=None):
    """Yield RGB frames at constant FPS, decoded (and optionally tone-mapped) by ffmpeg."""
    w, h = probe_size(src)
    vf = (vf_in + "," if vf_in else "") + "format=rgb24"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-map", "0:v:0", "-vf", vf,
                          "-fps_mode", "cfr", "-r", str(FPS), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    size = w * h * 3
    try:
        while True:
            buf = p.stdout.read(size)
            if len(buf) < size:
                break
            yield np.frombuffer(buf, np.uint8).reshape(h, w, 3).copy()
    finally:
        if p.poll() is None:
            p.kill()
        p.wait()

def run(src, out, cues, frame_fn, cap_top, overlay=None, vf_in=None, center_x=360, crf=18):
    for c in cues:
        c.layout(getattr(c, "top", cap_top), center_x)
    ff = subprocess.Popen([
        "ffmpeg", "-v", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", src, "-map", "0:v", "-map", "1:a?",
        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-profile:v", "high",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-c:a", "copy", "-movflags", "+faststart", "-shortest", out,
    ], stdin=subprocess.PIPE)
    for i, fr in enumerate(read_frames(src, vf_in)):
        t = i / FPS
        base = frame_fn(fr)                                     # RGB, source resolution
        if base.shape[1] != W or base.shape[0] != H:
            base = cv2.resize(base, (W, H), interpolation=cv2.INTER_LANCZOS4)
        img = Image.fromarray(base).convert("RGBA")
        if overlay is not None:
            img.alpha_composite(overlay)
        for c in cues:
            if c.start - 0.5 <= t <= c.end:
                c.draw(img, t)
        ff.stdin.write(img.convert("RGB").tobytes())
        if (i + 1) % 150 == 0:
            print(f"  {out}: {i + 1} frames", flush=True)
    ff.stdin.close()
    ff.wait()
    print("done", out, ff.returncode)
