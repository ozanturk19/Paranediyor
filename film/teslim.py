"""Teslim kodlaması: ana kopya (master) + ses efektleri -> boyut sınırına sığan son MP4 (iki geçişli H.264).

Kullanım: python3 teslim.py master.mp4 sfx.wav cikti.mp4 [sınır_MiB=29]
"""
import json, os, subprocess, sys, tempfile

COLOR = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def encode(master, sfx, out, limit_mib=29.0, audio_kbps=160):
    dur = duration(master)
    total_kbit = limit_mib * 1024 * 1024 * 8 / 1000 * 0.985            # kapsayıcı payı
    vk = int(total_kbit / dur - audio_kbps)
    log = os.path.join(tempfile.mkdtemp(), "x264")
    base = ["-c:v", "libx264", "-preset", "slower", "-b:v", f"{vk}k", "-maxrate", f"{int(vk * 2.2)}k",
            "-bufsize", f"{vk * 4}k", "-profile:v", "high", "-pix_fmt", "yuv420p", "-passlogfile", log] + COLOR
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master] + base + ["-pass", "1", "-an", "-f", "null", "/dev/null"],
                   check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", master, "-i", sfx, "-map", "0:v", "-map", "1:a"] + base +
                   ["-pass", "2", "-c:a", "aac", "-b:a", f"{audio_kbps}k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    mib = os.path.getsize(out) / 1024 / 1024
    print(f"{out}: {dur:.2f} sn, video {vk} kbit/sn, {mib:.2f} MiB")
    return mib


if __name__ == "__main__":
    encode(sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]) if len(sys.argv) > 4 else 29.0)
