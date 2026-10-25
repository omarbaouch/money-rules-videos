"""Vertical Short generator for Money Rules in 60s.

Usage:
  sh setup_voice.sh   (once)
  python3 make_short.py segments.json short.mp4 [kokoro:af_heart | /path/piper.onnx]

segments.json = list of segments:
  {"say": spoken text, "kick": SMALL LABEL, "col": "gold"|"red"|"green",
   and ONE visual:
     "big": "$820/mo", "sub": "short caption"        -> huge number (numbers count up)
     "bars": [["Today", 10], ["30 yrs", 76]]          -> 2-4 bars, values in thousands
     "rows": [["Doctor", "$239K"], ["Nurse", "$94K"]] -> ranked list, up to 10 rows,
                                                        revealed one by one while spoken
  }

Retention design: nothing stays frozen. Words light up as they are spoken,
numbers count up, rows/bars build up, a soft light drifts in the background.
Text stays inside the Shorts safe zone (above y=1400, never x>905 below y=1050).
"""
import json, subprocess, os, sys, math, re
from PIL import Image, ImageDraw, ImageFont, ImageFilter

S = os.path.dirname(os.path.abspath(__file__))
VOICE = "kokoro:af_heart"  # or a Piper .onnx path; see voice_tts.py
OUT = os.path.join(S, "build"); os.makedirs(OUT, exist_ok=True)
W, H, FPS = 1080, 1920, 30
BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
_fc = {}
def F(s):
    s = int(s)
    if s not in _fc: _fc[s] = ImageFont.truetype(BOLD, s)
    return _fc[s]

BG1, BG2 = (10, 14, 28), (22, 30, 60)
WHITE, GOLD, RED, GREEN, GREY = (245, 247, 252), (255, 196, 0), (255, 82, 82), (60, 220, 140), (150, 160, 185)
DIM = (120, 130, 155)

SEG = json.load(open(sys.argv[1]))
FINAL = sys.argv[2]
VOICE = sys.argv[3] if len(sys.argv) > 3 else VOICE
COLS = {"gold": GOLD, "red": RED, "green": GREEN}
for s_ in SEG: s_["col"] = COLS.get(s_.get("col", "gold"), GOLD)

sys.path.insert(0, S)
import voice_tts
PAD = 0.25  # silence added after each segment

def tts(text, path):
    return voice_tts.tts(text, path, VOICE)

# ---------- background ----------
def bg():
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(BG1[i] + (BG2[i] - BG1[i]) * t) for i in range(3)))
    return im.convert("RGBA")
BASE = bg()

def make_glow(col, r=420):
    g = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([r * 0.35, r * 0.35, r * 1.65, r * 1.65], fill=col + (70,))
    return g.filter(ImageFilter.GaussianBlur(r * 0.3))
GLOWS = {c: make_glow(c) for c in (GOLD, RED, GREEN)}

def ease(t): return 1 - (1 - min(max(t, 0), 1)) ** 3
def back(t):  # overshoot pop
    t = min(max(t, 0), 1); c = 1.7
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

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

# ---------- animated numbers ----------
NUM = re.compile(r"^([^\d]*?)(\d[\d,]*\.?\d*)(.*)$")
def count_up(text, p):
    m = NUM.match(text or "")
    if not m or p >= 1: return text
    pre, num, post = m.groups()
    dec = len(num.split(".")[1]) if "." in num else 0
    v = float(num.replace(",", "")) * p
    s = f"{v:,.{dec}f}" if "," in num else f"{v:.{dec}f}"
    return pre + s + post

# ---------- karaoke captions ----------
def word_times(say, dur):
    words = say.split()
    wts = [len(w) + 2 + (4 if w[-1] in ".,?!" else 0) for w in words]
    speak = max(dur - PAD - 0.15, 0.5)
    tot, acc, out = sum(wts), 0, []
    for w, k in zip(words, wts):
        out.append((w, acc / tot * speak)); acc += k
    return out

def chunks(wt):
    out, cur = [], []
    for w, t in wt:
        cur.append((w, t))
        if len(cur) == 4 or w[-1] in ".,?!:;":
            out.append(cur); cur = []
    if cur: out.append(cur)
    return out

def caption(d, seg, t):
    ch = seg["_chunks"]
    idx = 0
    for i, c in enumerate(ch):
        if t >= c[0][1]: idx = i
    c = ch[idx]
    cur = max(j for j, (_, wt) in enumerate(c) if t >= wt or j == 0)
    sz = 66
    while sz > 40:
        f = F(sz)
        lines = wrap(d, " ".join(w for w, _ in c), f, 700)
        if len(lines) <= 2: break
        sz -= 4
    f = F(sz); y = 1110
    k = 0
    for ln in lines:
        lw = d.textlength(ln, font=f); x = (W - lw) / 2
        for w in ln.split():
            col = seg["col"] if k == cur else (WHITE if k < cur else (175, 182, 200))
            d.text((x, y), w, font=f, fill=col, stroke_width=3, stroke_fill=BG1)
            x += d.textlength(w + " ", font=f); k += 1
        y += int(sz * 1.25)

# ---------- frame ----------
def frame(seg, t, dur, idx, total_t, total_dur, last):
    im = BASE.copy()
    gx = int(W / 2 - 420 + 260 * math.sin(total_t * 0.6 + idx))
    gy = int(620 - 420 + 160 * math.cos(total_t * 0.45))
    im.alpha_composite(GLOWS[seg["col"]], (gx, gy))
    d = ImageDraw.Draw(im)
    p = ease(t / 0.3)
    # kicker slides down
    kf = F(46); kw = d.textlength(seg["kick"], font=kf); ky = 250 - 60 * (1 - p)
    d.rounded_rectangle([(W - kw) / 2 - 30, ky, (W + kw) / 2 + 30, ky + 80], 40, fill=seg["col"])
    d.text(((W - kw) / 2, ky + 10), seg["kick"], font=kf, fill=BG1)

    if seg.get("rows"):
        rows = seg["rows"][:10]; n = len(rows)
        top, bot = 380, 1020; rh = (bot - top) / n
        fs = min(56, int(rh * 0.5)); f = F(fs)
        span = max(dur - PAD - 0.6, 0.5)
        shown = [i for i in range(n) if t >= 0.25 + i * span / n]
        for i in shown:
            a = ease((t - 0.25 - i * span / n) / 0.25)
            y = top + i * rh; x0 = 90 + 60 * (1 - a)
            hot = i == shown[-1]
            d.rounded_rectangle([x0, y + 6, x0 + 900, y + rh - 6], 22,
                                fill=seg["col"] if hot else (30, 40, 72))
            tc = BG1 if hot else WHITE
            lab, val = str(rows[i][0]), str(rows[i][1])
            ty = y + (rh - fs * 1.25) / 2
            d.text((x0 + 30, ty), lab, font=f, fill=tc)
            d.text((x0 + 870 - d.textlength(val, font=f), ty), val, font=f, fill=tc)
    elif seg.get("bars"):
        bars = seg["bars"]; maxv = max(v for _, v in bars)
        bw, gap, base_y, top = 160, 50, 940, 470
        x0 = (W - (len(bars) * bw + (len(bars) - 1) * gap)) / 2
        for i, (lab, v) in enumerate(bars):
            appear = ease((t - 0.3 - i * (dur - 1.0) / len(bars)) / 0.5)
            hgt = (base_y - top) * v / maxv * appear
            x = x0 + i * (bw + gap)
            d.rounded_rectangle([x, base_y - hgt, x + bw, base_y], 18, fill=seg["col"] if i else GREY)
            if appear > 0.05:
                lf = F(44); s = count_up(f"${v}k", appear)
                d.text((x + (bw - d.textlength(s, font=lf)) / 2, base_y - hgt - 70), s, font=lf, fill=WHITE)
            sf = F(36)
            d.text((x + (bw - d.textlength(lab, font=sf)) / 2, base_y + 20), lab, font=sf, fill=GREY)
    else:
        big = count_up(seg.get("big", ""), ease(t / 0.8))
        pop = back(t / 0.35)
        size = int((300 if len(seg.get("big", "")) <= 3 else 230) * (0.6 + 0.4 * pop))
        bf = F(max(size, 10)); bw_ = d.textlength(big, font=bf)
        while bw_ > W - 120 and size > 40:
            size -= 10; bf = F(size); bw_ = d.textlength(big, font=bf)
        center(d, 590 - size * 0.55, big, bf, seg["col"])
        sf = F(64)
        sp = ease((t - 0.35) / 0.3)
        if sp > 0:
            for i, ln in enumerate(wrap(d, seg.get("sub", ""), sf, W - 300)[:2]):
                center(d, 830 + i * 76 + 30 * (1 - sp), ln, sf, WHITE)

    caption(d, seg, t)
    d.rectangle([0, H - 14, W * (total_t / total_dur), H], fill=GOLD)
    if last:
        center(d, 140, "Educational, not financial advice", F(28), (90, 100, 125))
    return im.convert("RGB")

# 1) voice
durs = []
for i, s in enumerate(SEG):
    durs.append(tts(s["say"], os.path.join(OUT, f"a{i}.wav")) + PAD)
    s["_chunks"] = chunks(word_times(s["say"], durs[-1]))
total = sum(durs)

# 2) frames -> video per segment via ffmpeg pipe
elapsed, parts = 0, []
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
        proc.stdin.write(frame(s, t, durs[i], i, elapsed + t, total, i == len(SEG) - 1).tobytes())
    proc.stdin.close(); proc.wait()
    elapsed += durs[i]; parts.append(vp)

lst = os.path.join(OUT, "list.txt")
open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                "-movflags", "+faststart", FINAL], check=True)
frame(SEG[0], 1.0, durs[0], 0, 1.0, total, len(SEG) == 1).save(FINAL.replace(".mp4", "_preview.png"))
print(json.dumps({"total_seconds": round(total, 1), "file": FINAL}))
