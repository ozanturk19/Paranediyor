"""Videodaki konuşmayı kelime kelime zamanlarıyla yazıya döker (Whisper-small, ONNX, CPU).

Kullanım:
    bash altyazi/model_indir.sh                           # bir kez: modeli indirir (~250 MB)
    python3 altyazi/yaziya_dok.py girdi/video.mp4 [dil]   # dil: tr (varsayılan), en, ...

Çıktı: bölümler, kelime zamanları ve make.py'ye yapıştırılabilecek taslak altyazı satırları.
Yöntem: zaman damgası kurallarıyla açgözlü çözümleme (30 sn'lik pencereler), ardından
hizalama kafalarının çapraz dikkatleri üzerinde DTW (openai-whisper'daki find_alignment).
"""
import json, os, string, subprocess, sys
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from transformers import WhisperFeatureExtractor

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "models", "whisper-small")
SR, WIN, TP = 16000, 30.0, 0.02          # sample rate, window (s), timestamp precision (s)
SOT, EOT, TRANSCRIBE, NOTS, TS0 = 50258, 50257, 50359, 50363, 50364


def load_audio(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768.0


def median_filter(x, w=7):
    pad = w // 2
    xp = np.pad(x, [(0, 0)] * (x.ndim - 1) + [(pad, pad)], mode="reflect")
    return np.median(np.lib.stride_tricks.sliding_window_view(xp, w, axis=-1), axis=-1)


def dtw(x):
    N, M = x.shape
    cost = np.full((N + 1, M + 1), np.inf)
    trace = -np.ones((N + 1, M + 1))
    cost[0, 0] = 0
    for j in range(1, M + 1):
        for i in range(1, N + 1):
            c0, c1, c2 = cost[i - 1, j - 1], cost[i - 1, j], cost[i, j - 1]
            if c0 < c1 and c0 < c2:
                c, t = c0, 0
            elif c1 < c0 and c1 < c2:
                c, t = c1, 1
            else:
                c, t = c2, 2
            cost[i, j] = x[i - 1, j - 1] + c
            trace[i, j] = t
    i, j = N, M
    trace[0, :] = 2
    trace[:, 0] = 1
    path = []
    while i > 0 or j > 0:
        path.append((i - 1, j - 1))
        if trace[i, j] == 0:
            i, j = i - 1, j - 1
        elif trace[i, j] == 1:
            i -= 1
        else:
            j -= 1
    return np.array(path[::-1]).T


class Whisper:
    def __init__(self, lang):
        self.lang_id = json.load(open(f"{MD}/added_tokens.json"))[f"<|{lang}|>"]
        cfg = json.load(open(f"{MD}/generation_config.json"))
        self.suppress = cfg.get("suppress_tokens", [])
        self.heads = cfg["alignment_heads"]
        self.tok = Tokenizer.from_file(f"{MD}/tokenizer.json")
        self.fe = WhisperFeatureExtractor.from_pretrained(MD)
        so = ort.SessionOptions()
        so.intra_op_num_threads = os.cpu_count() or 4
        prov = ["CPUExecutionProvider"]
        self.enc = ort.InferenceSession(f"{MD}/onnx/encoder_model_quantized.onnx", so, providers=prov)
        self.dec = ort.InferenceSession(f"{MD}/onnx/decoder_model_merged_quantized.onnx", so, providers=prov)
        self.out_names = [o.name for o in self.dec.get_outputs()]
        self.past_names = [i.name for i in self.dec.get_inputs() if i.name.startswith("past_key_values")]
        shape = next(i.shape for i in self.dec.get_inputs() if i.name.startswith("past_key_values"))
        self.n_heads, self.head_dim = shape[1], shape[3]

    # ------------------------------------------------------------ decoder plumbing
    def _empty(self):
        return {n: np.zeros((1, self.n_heads, 0, self.head_dim), np.float32) for n in self.past_names}

    def _run(self, hs, ids, past, use_cache):
        feed = {"input_ids": np.array([ids], np.int64), "encoder_hidden_states": hs,
                "use_cache_branch": np.array([use_cache]), **past}
        return dict(zip(self.out_names, self.dec.run(None, feed)))

    def _next_past(self, res, old):
        new = {}
        for n in self.past_names:
            present = res[n.replace("past_key_values", "present")]
            new[n] = present if (".decoder." in n or old[n].shape[2] == 0) else old[n]
        return new

    # ------------------------------------------------------------ greedy decoding with timestamp rules
    def greedy(self, hs):
        seq = []
        res = self._run(hs, [SOT, self.lang_id, TRANSCRIBE], self._empty(), False)
        past = self._next_past(res, self._empty())
        logits = res["logits"][0, -1].astype(np.float64)
        for step in range(224):
            lg = logits.copy()
            lg[NOTS] = -np.inf
            lg[self.suppress] = -np.inf
            if step == 0:
                lg[220] = lg[EOT] = -np.inf
                lg[:TS0] = -np.inf                  # must start with a timestamp
                lg[TS0 + 51:] = -np.inf             # ... within the first second
            else:
                last_ts = seq[-1] >= TS0
                pen_ts = len(seq) < 2 or seq[-2] >= TS0
                if last_ts:
                    if pen_ts:
                        lg[TS0:] = -np.inf
                    else:
                        lg[:EOT] = -np.inf
                tss = [t for t in seq if t >= TS0]
                if tss:
                    floor = tss[-1] if (last_ts and not pen_ts) else tss[-1] + 1
                    lg[TS0:floor] = -np.inf
                m = lg.max()
                lp = lg - m - np.log(np.exp(lg - m).sum())
                if np.logaddexp.reduce(lp[TS0:]) > lp[:TS0].max():
                    lg[:TS0] = -np.inf
            nxt = int(np.argmax(lg))
            seq.append(nxt)
            if nxt == EOT:
                break
            res = self._run(hs, [nxt], past, True)
            past = self._next_past(res, past)
            logits = res["logits"][0, -1].astype(np.float64)
        return [t for t in seq if t != EOT]

    @staticmethod
    def segments(tokens, offset, win_dur):
        """Split sampled tokens into segments; return (segments, seconds to advance)."""
        is_ts = [t >= TS0 for t in tokens]
        single_end = len(tokens) >= 2 and not is_ts[-2] and is_ts[-1]
        consecutive = [i + 1 for i in range(len(tokens) - 1) if is_ts[i] and is_ts[i + 1]]
        segs = []
        if consecutive:
            slices = consecutive + ([len(tokens)] if single_end else [])
            last = 0
            for cur in slices:
                sl = tokens[last:cur]
                text = [t for t in sl if t < EOT]
                if text:
                    segs.append((offset + (sl[0] - TS0) * TP, offset + (sl[-1] - TS0) * TP, text))
                last = cur
            advance = win_dur if single_end else (tokens[last - 1] - TS0) * TP
        else:
            tss = [t for t in tokens if t >= TS0]
            dur = (tss[-1] - TS0) * TP if tss and tss[-1] != TS0 else win_dur
            text = [t for t in tokens if t < EOT]
            if text:
                segs.append((offset, offset + dur, text))
            advance = win_dur
        return segs, (advance if advance > 0 else win_dur)

    # ------------------------------------------------------------ word timing (cross-attention DTW)
    def _split_words(self, tokens):
        dec = lambda ids: self.tok.decode(ids, skip_special_tokens=False)
        full = dec(tokens)
        subs, subt, cur, off = [], [], [], 0
        for t in tokens:                      # keep multi-byte characters (ç, ğ, ş...) together
            cur.append(t)
            d = dec(cur)
            if "�" not in d or full[off + d.index("�")] == "�":
                subs.append(d); subt.append(cur); cur = []; off += len(d)
        words, wtoks = [], []
        for s, st in zip(subs, subt):
            if st[0] >= EOT or s.startswith(" ") or s.strip() in string.punctuation or not words:
                words.append(s); wtoks.append(list(st))
            else:
                words[-1] += s; wtoks[-1].extend(st)
        return words, wtoks

    def align(self, hs, text, n_frames):
        res = self._run(hs, [SOT, self.lang_id, TRANSCRIBE, NOTS] + text + [EOT], self._empty(), False)
        att = np.stack([res[f"cross_attentions.{l}"][0, h] for l, h in self.heads])[:, :, :n_frames]
        att = (att - att.mean(axis=-2, keepdims=True)) / (att.std(axis=-2, keepdims=True) + 1e-8)
        matrix = median_filter(att, 7).mean(axis=0)[3:-1]     # rows: <|notimestamps|>, text tokens
        text_idx, time_idx = dtw(-matrix)
        words, wtoks = self._split_words(text + [EOT])
        bounds = np.pad(np.cumsum([len(t) for t in wtoks[:-1]]), (1, 0))
        jumps = np.pad(np.diff(text_idx), (1, 0), constant_values=1).astype(bool)
        jt = time_idx[jumps] * TP
        return list(zip(words[:-1], jt[bounds[:-1]], jt[bounds[1:]]))


def transcribe(path, lang="tr"):
    audio = load_audio(path)
    total = len(audio) / SR
    w = Whisper(lang)
    seek, segs_out, words = 0.0, [], []
    while seek < total - 0.2:
        chunk = audio[int(seek * SR):int((seek + WIN) * SR)]
        win_dur = len(chunk) / SR
        feats = w.fe(chunk, sampling_rate=SR, return_tensors="np").input_features.astype(np.float32)
        hs = w.enc.run(["last_hidden_state"], {"input_features": feats})[0]
        segs, advance = w.segments(w.greedy(hs), seek, win_dur)
        text = [t for s in segs for t in s[2]]
        if text:
            for word, s, e in w.align(hs, text, int(round(win_dur / TP))):
                word = word.strip()
                if word in string.punctuation and words:
                    words[-1]["w"] += word
                elif word:
                    words.append({"w": word, "s": round(seek + float(s), 2), "e": round(seek + float(e), 2)})
        segs_out += [(round(a, 2), round(b, 2), w.tok.decode(ids).strip()) for a, b, ids in segs]
        seek += advance
    return segs_out, words, total


def draft_cues(words, total, max_words=6, pause=0.35):
    """Group words into caption pages (make.py format), two lines each."""
    groups, cur = [], []
    for i, wd in enumerate(words):
        if cur and (len(cur) >= max_words or wd["s"] - cur[-1]["e"] > pause
                    or (cur[-1]["w"][-1] in ".!?" and len(cur) >= 2)
                    or (cur[-1]["w"][-1] in ",;:" and len(cur) >= 3)):
            groups.append(cur); cur = []
        cur.append(wd)
    if cur:
        groups.append(cur)
    lines = []
    for gi, g in enumerate(groups):
        start = g[0]["s"]
        end = groups[gi + 1][0]["s"] - 0.02 if gi + 1 < len(groups) else min(total, g[-1]["e"] + 2.0)
        toks = [f'{x["w"]}@{x["s"]:.2f}' for x in g]
        if len(g) >= 3:                        # break the page into two lines of similar length
            lens = np.cumsum([len(x["w"]) for x in g])
            k = int(np.argmin(np.abs(lens[:-1] - lens[-1] / 2))) + 1
            toks.insert(k, "/")
        lines.append(f"{start:.2f} {end:.2f}   " + " ".join(toks))
    return lines


if __name__ == "__main__":
    path, lang = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "tr")
    segs, words, total = transcribe(path, lang)
    print("BÖLÜMLER:")
    for a, b, t in segs:
        print(f"  {a:6.2f}-{b:6.2f}  {t}")
    print("KELİMELER:")
    for x in words:
        print(f'  {x["s"]:6.2f}-{x["e"]:6.2f}  {x["w"]}')
    print("TASLAK ALTYAZI (make.py):")
    for ln in draft_cues(words, total):
        print("  " + ln)
    out = os.path.splitext(path)[0] + "_kelimeler.json"
    json.dump({"bolumler": segs, "kelimeler": words}, open(out, "w"), ensure_ascii=False, indent=1)
    print("kaydedildi:", out)
