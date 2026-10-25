"""Long-form (16:9) video generator for Money Rules in 60s.

Usage:
  sh setup_voice.sh   (once)
  python3 make_long.py script.json output.mp4 kokoro:af_heart
  (a Piper .onnx path still works as the 3rd argument)

script.json:
{
  "title": "Video title (used on the intro card and thumbnail)",
  "thumb": "SHORT THUMB TEXT",          # 2-5 words, shown huge on the thumbnail
  "thumb_big": "$1M",                   # optional big number on the thumbnail
  "sections": [
    {
      "chapter": "Chapter name",        # used for YouTube chapters
      "say": "Narration for this section (English, numbers in words, <= 140 words)",
      "col": "gold" | "green" | "red",
      "visual": one of
        {"type": "big",   "big": "72", "sub": "short caption"}
        {"type": "bars",  "bars": [["Today", 10], ["9 yrs", 20]], "prefix": "$", "suffix": "k"}
        {"type": "line",  "points": [[0, 10], [10, 21.6], [20, 46.6]], "xlabel": "years", "prefix": "$", "suffix": "k"}
        {"type": "list",  "items": ["Point one", "Point two", "Point three"]}
        {"type": "compare", "left": ["Label A", "$120k"], "right": ["Label B", "$310k"]}
    }
  ]
}

Outputs: output.mp4, output_thumb.png (1280x720), output_chapters.txt (YouTube chapter lines).
"""
import json, os, subprocess, sys, wave

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 25
BOLD = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
F = lambda s: ImageFont.truetype(BOLD, s)

BG1, BG2 = (10, 14, 28), (22, 30, 60)
WHITE, GOLD, RED, GREEN, GREY = (245, 247, 252), (255, 196, 0), (255, 82, 82), (60, 220, 140), (150, 160, 185)
COLS = {"gold": GOLD, "red": RED, "green": GREEN}

SCRIPT = json.load(open(sys.argv[1]))
FINAL = sys.argv[2]
VOICE = sys.argv[3] if len(sys.argv) > 3 else "kokoro:af_heart"  # or a Piper .onnx path
OUT = os.path.join(os.path.dirname(os.path.abspath(FINAL)) or ".", "build_long")
os.makedirs(OUT, exist_ok=True)


def gradient(w, h):
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(BG1[i] + (BG2[i] - BG1[i]) * t) for i in range(3)))
    return im


BASE = gradient(W, H)


def center(d, cx, y, text, font, fill):
    d.text((cx - d.textlength(text, font=font) / 2, y), text, font=font, fill=fill)


def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, maxw, start, minimum=40):
    size = start
    while size > minimum and d.textlength(text, font=F(size)) > maxw:
        size -= 6
    return F(size)


def fmt(v, prefix, suffix):
    v = int(v) if float(v).is_integer() else round(v, 1)
    return f"{prefix}{v:,}{suffix}"


def chrome(d, chapter, col, idx, total):
    d.text((90, 70), "MONEY RULES IN 60s", font=F(30), fill=(110, 120, 150))
    tag = chapter.upper()
    tf = F(40)
    tw = d.textlength(tag, font=tf)
    d.rounded_rectangle([90, 130, 90 + tw + 50, 200], 35, fill=col)
    d.text((115, 138), tag, font=tf, fill=BG1)
    disc, dfont = "Educational · not financial advice", F(24)
    d.text((W - 90 - d.textlength(disc, font=dfont), 74), disc, font=dfont, fill=(90, 100, 125))
    # section progress dots
    for i in range(total):
        x = W - 90 - (total - 1 - i) * 34
        d.ellipse([x - 9, H - 70, x + 9, H - 52], fill=col if i <= idx else (50, 58, 85))


def draw_visual(d, v, col):
    t = v.get("type", "big")
    area = (160, 250, W - 160, H - 130)  # x0, y0, x1, y1
    cx = W / 2
    if t == "big":
        bf = fit(d, v["big"], W - 400, 340, 120)
        center(d, cx, 300, v["big"], bf, col)
        sf = F(64)
        for i, ln in enumerate(wrap(d, v.get("sub", ""), sf, W - 500)[:2]):
            center(d, cx, 730 + i * 80, ln, sf, WHITE)
    elif t == "bars":
        bars = v["bars"]
        pre, suf = v.get("prefix", ""), v.get("suffix", "")
        maxv = max(b[1] for b in bars)
        n = len(bars)
        gap = 70
        bw = min(260, (area[2] - area[0] - gap * (n - 1)) / n)
        x0 = cx - (n * bw + (n - 1) * gap) / 2
        base, top = 880, 330
        for i, (lab, val) in enumerate(bars):
            x = x0 + i * (bw + gap)
            h = (base - top) * val / maxv
            d.rounded_rectangle([x, base - h, x + bw, base], 20, fill=col if i else GREY)
            s = fmt(val, pre, suf)
            lf = fit(d, s, bw + 40, 56, 30)
            center(d, x + bw / 2, base - h - 75, s, lf, WHITE)
            center(d, x + bw / 2, base + 22, lab, fit(d, lab, bw + 40, 40, 24), GREY)
    elif t == "line":
        pts = v["points"]
        pre, suf = v.get("prefix", ""), v.get("suffix", "")
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        gx0, gy0, gx1, gy1 = 260, 300, W - 300, 860
        xmin, xmax, ymax = min(xs), max(xs), max(ys) * 1.1
        px = lambda x: gx0 + (x - xmin) / ((xmax - xmin) or 1) * (gx1 - gx0)
        py = lambda y: gy1 - y / (ymax or 1) * (gy1 - gy0)
        for k in range(5):
            yy = gy1 - k * (gy1 - gy0) / 4
            d.line([(gx0, yy), (gx1, yy)], fill=(45, 54, 82), width=2)
            lab = fmt(round(ymax * k / 4), pre, suf)
            d.text((gx0 - 30 - d.textlength(lab, font=F(30)), yy - 20), lab, font=F(30), fill=GREY)
        d.line([(px(x), py(y)) for x, y in pts], fill=col, width=10, joint="curve")
        for x, y in (pts[0], pts[-1]):
            d.ellipse([px(x) - 14, py(y) - 14, px(x) + 14, py(y) + 14], fill=col)
        last = fmt(pts[-1][1], pre, suf)
        lf = F(64)
        d.text((min(px(xs[-1]) - d.textlength(last, font=lf) / 2, W - 120 - d.textlength(last, font=lf)), py(ys[-1]) - 100), last, font=lf, fill=WHITE)
        for x in (xs[0], xs[len(xs) // 2], xs[-1]):
            center(d, px(x), gy1 + 20, f"{int(x)}", F(32), GREY)
        center(d, cx, gy1 + 70, v.get("xlabel", ""), F(32), GREY)
    elif t == "list":
        items = v["items"][:5]
        lf = F(60)
        y = 320
        for i, it in enumerate(items):
            d.ellipse([300, y + 22, 340, y + 62], fill=col)
            center(d, 320, y + 18, str(i + 1), F(30), BG1)
            for j, ln in enumerate(wrap(d, it, lf, W - 760)[:2]):
                d.text((380, y + j * 72), ln, font=lf, fill=WHITE)
            y += 120 if len(wrap(d, it, lf, W - 760)) == 1 else 180
    elif t == "compare":
        for side, (lab, val), c in (("l", v["left"], RED), ("r", v["right"], GREEN)):
            x = W / 4 if side == "l" else 3 * W / 4
            d.rounded_rectangle([x - 360, 320, x + 360, 860], 40, outline=c, width=6)
            center(d, x, 380, lab, fit(d, lab, 640, 56, 30), GREY)
            center(d, x, 520, val, fit(d, val, 640, 170, 60), c)
        center(d, W / 2, 540, "vs", F(70), WHITE)


def section_frame(sec, idx, total):
    im = BASE.copy()
    d = ImageDraw.Draw(im)
    col = COLS.get(sec.get("col", "gold"), GOLD)
    chrome(d, sec["chapter"], col, idx, total)
    draw_visual(d, sec["visual"], col)
    return im


def title_frame():
    im = BASE.copy()
    d = ImageDraw.Draw(im)
    d.text((90, 70), "MONEY RULES IN 60s", font=F(30), fill=(110, 120, 150))
    tf = F(96)
    lines = wrap(d, SCRIPT["title"], tf, W - 300)
    y = H / 2 - len(lines) * 60
    for ln in lines:
        center(d, W / 2, y, ln, tf, WHITE)
        y += 120
    d.rectangle([W / 2 - 120, y + 30, W / 2 + 120, y + 42], fill=GOLD)
    return im


def thumbnail():
    im = gradient(1280, 720)
    d = ImageDraw.Draw(im)
    big = SCRIPT.get("thumb_big", "")
    text = SCRIPT.get("thumb", SCRIPT["title"]).upper()
    if big:
        bf = F(260)
        while d.textlength(big, font=bf) > 1180:
            bf = F(bf.size - 10)
        d.text(((1280 - d.textlength(big, font=bf)) / 2, 40), big, font=bf, fill=GOLD)
        y = 380
    else:
        y = 160
    tf = F(110)
    lines = wrap(d, text, tf, 1180)
    while len(lines) > 2 and tf.size > 60:
        tf = F(tf.size - 10)
        lines = wrap(d, text, tf, 1180)
    for ln in lines[:3]:
        d.text(((1280 - d.textlength(ln, font=tf)) / 2, y), ln, font=tf, fill=WHITE, stroke_width=4, stroke_fill=BG1)
        y += tf.size + 20
    return im


sys.path.insert(0, HERE)
import voice_tts


def tts(text, path):
    return voice_tts.tts(text, path, VOICE, speed=1.0,
                         piper_args=("--length_scale", "0.97", "--sentence_silence", "0.25"))


def clip(png, wav, dur, out):
    """Still image + narration with a slow push-in so the frame is never frozen."""
    frames = int(round(dur * FPS))
    zoom = f"zoompan=z='1+0.04*on/{max(frames, 1)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png]
    if wav:
        cmd += ["-i", wav, "-af", "apad"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono"]
    cmd += ["-vf", f"scale={W * 2}:{H * 2},{zoom},format=yuv420p", "-t", f"{dur:.3f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-tune", "stillimage",
            "-c:a", "aac", "-ar", "44100", "-ac", "1", out]
    subprocess.run(cmd, check=True)


secs = SCRIPT["sections"]
parts, chapters, t = [], [], 0.0

# intro title card (3 s, silent) — chapter 0:00 must exist for YouTube chapters
title_png = os.path.join(OUT, "title.png")
title_frame().save(title_png)
intro = os.path.join(OUT, "p_intro.mp4")
clip(title_png, None, 3.0, intro)
parts.append(intro)
# YouTube needs every chapter >= 10 s, so the 3 s intro is folded into the first chapter
chapters.append((0.0, secs[0]["chapter"]))
t += 3.0

for i, sec in enumerate(secs):
    png = os.path.join(OUT, f"s{i}.png")
    section_frame(sec, i, len(secs)).save(png)
    wav = os.path.join(OUT, f"s{i}.wav")
    dur = tts(sec["say"], wav) + 0.6
    out = os.path.join(OUT, f"p{i}.mp4")
    clip(png, wav, dur, out)
    parts.append(out)
    if i > 0:
        chapters.append((t, sec["chapter"]))
    t += dur

lst = os.path.join(OUT, "list.txt")
open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                "-c", "copy", "-movflags", "+faststart", FINAL], check=True)

thumbnail().save(FINAL.replace(".mp4", "_thumb.png"))
stamp = lambda s: f"{int(s // 60)}:{int(s % 60):02d}"
open(FINAL.replace(".mp4", "_chapters.txt"), "w").write("\n".join(f"{stamp(s)} {name}" for s, name in chapters) + "\n")
print(json.dumps({"seconds": round(t, 1), "file": FINAL, "size_mb": round(os.path.getsize(FINAL) / 1e6, 1)}))
