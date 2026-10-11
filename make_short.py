import json, subprocess, wave, os, sys, math
from PIL import Image, ImageDraw, ImageFont

S = os.path.dirname(os.path.abspath(__file__))
VOICE = os.path.join(S, "voice", "en-us-lessac-medium.onnx")
OUT = os.path.join(S, "build"); os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
F = lambda s: ImageFont.truetype(BOLD, s)

BG1, BG2 = (10, 14, 28), (22, 30, 60)
WHITE, GOLD, RED, GREEN, GREY = (245, 247, 252), (255, 196, 0), (255, 82, 82), (60, 220, 140), (150, 160, 185)

# Each segment: spoken text, kicker (small), big (huge number), sub (caption), color, optional bars
SEG = json.load(open(sys.argv[1]))
FINAL = sys.argv[2]
VOICE = sys.argv[3] if len(sys.argv) > 3 else VOICE
COLS = {"gold": GOLD, "red": RED, "green": GREEN}
for s_ in SEG: s_["col"] = COLS.get(s_.get("col", "gold"), GOLD)

def tts(text, path):
    subprocess.run([sys.executable, "-m", "piper", "-m", VOICE, "-f", path,
                    "--length_scale", "0.92", "--sentence_silence", "0.15"],
                   input=text.encode(), check=True, capture_output=True)
    with wave.open(path) as w:
        return w.getnframes() / w.getframerate()

def bg():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(BG1[i] + (BG2[i] - BG1[i]) * t) for i in range(3)))
    return im
BASE = bg()

def center(d, y, text, font, fill):
    w = d.textlength(text, font=font)
    d.text(((W - w) / 2, y), text, font=font, fill=fill)

def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines

def ease(t): return 1 - (1 - min(max(t, 0), 1)) ** 3

def frame(seg, t, dur, idx, total_t, total_dur):
    im = BASE.copy(); d = ImageDraw.Draw(im)
    p = ease(t / 0.35)
    # kicker
    kf = F(46); kw = d.textlength(seg["kick"], font=kf)
    d.rounded_rectangle([(W - kw) / 2 - 30, 250, (W + kw) / 2 + 30, 330], 40, fill=seg["col"])
    d.text(((W - kw) / 2, 260), seg["kick"], font=kf, fill=BG1)
    if seg.get("bars"):
        bars = seg["bars"]; maxv = max(v for _, v in bars)
        bw, gap, base_y, top = 160, 50, 940, 470
        x0 = (W - (len(bars) * bw + (len(bars) - 1) * gap)) / 2
        for i, (lab, v) in enumerate(bars):
            appear = ease((t - 0.3 - i * (dur - 1.0) / len(bars)) / 0.5)
            hgt = (base_y - top) * v / maxv * appear
            x = x0 + i * (bw + gap)
            d.rounded_rectangle([x, base_y - hgt, x + bw, base_y], 18, fill=seg["col"] if i else GREY)
            if appear > 0.05:
                lf = F(44); s = f"${v}k"
                d.text((x + (bw - d.textlength(s, font=lf)) / 2, base_y - hgt - 70), s, font=lf, fill=WHITE)
            sf = F(36)
            d.text((x + (bw - d.textlength(lab, font=sf)) / 2, base_y + 20), lab, font=sf, fill=GREY)
    else:
        size = int(300 * (0.85 + 0.15 * p)) if len(seg["big"]) <= 3 else int(230 * (0.85 + 0.15 * p))
        bf = F(size)
        bw_ = d.textlength(seg["big"], font=bf)
        while bw_ > W - 120:
            size -= 10; bf = F(size); bw_ = d.textlength(seg["big"], font=bf)
        center(d, 590 - size * 0.55, seg["big"], bf, seg["col"])
        sf = F(64)
        for i, ln in enumerate(wrap(d, seg["sub"], sf, W - 300)[:2]):
            center(d, 830 + i * 76, ln, sf, WHITE)
    # spoken caption (bottom)
    # spoken caption kept inside the Shorts safe zone (above channel name/title, left of the action buttons)
    for sz in (46, 42, 38, 34):
        cf = F(sz); lines = wrap(d, seg["say"], cf, 720)
        if len(lines) <= 4: break
    y0 = 1060
    for i, ln in enumerate(lines[:4]):
        center(d, y0 + i * int(sz * 1.35), ln, cf, (225, 230, 240))
    # progress bar
    d.rectangle([0, H - 14, W * (total_t / total_dur), H], fill=GOLD)
    small = F(28); center(d, 120, "Not financial advice · educational", small, (90, 100, 125))
    return im

# 1) voice
durs = []
for i, s in enumerate(SEG):
    durs.append(tts(s["say"], os.path.join(OUT, f"a{i}.wav")) + 0.25)
total = sum(durs)

# 2) frames -> video per segment via ffmpeg pipe
elapsed = 0
parts = []
for i, s in enumerate(SEG):
    n = int(round(durs[i] * FPS))
    vp = os.path.join(OUT, f"v{i}.mp4")
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                             "-i", os.path.join(OUT, f"a{i}.wav"), "-af", "apad",
                             "-t", f"{n / FPS:.3f}", "-c:v", "libx264", "-preset", "veryfast",
                             "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", vp], stdin=subprocess.PIPE)
    for f in range(n):
        t = f / FPS
        proc.stdin.write(frame(s, t, durs[i], i, elapsed + t, total).tobytes())
    proc.stdin.close(); proc.wait()
    elapsed += durs[i]; parts.append(vp)

lst = os.path.join(OUT, "list.txt")
open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
final = FINAL
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                "-movflags", "+faststart", final], check=True)
# thumbnail-ish preview frames
frame(SEG[0], 1.0, durs[0], 0, 1.0, total).save(FINAL.replace(".mp4", "_preview.png"))
print(json.dumps({"total_seconds": round(total, 1), "file": final}))
