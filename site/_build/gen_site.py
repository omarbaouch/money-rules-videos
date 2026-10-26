"""Build the static store site of The Digital Shelf.

Usage (from the repo root):
  gumroad products list --json > /tmp/products.json
  python3 site/_build/gen_site.py /tmp/products.json [https://base-url]

To add a product: add one entry to site/_build/catalog.json (slug, gumroad id, category, title,
pitch, key, pin_hook, pin_sub), then rerun. Missing images (laptop mockup, Pinterest pin, cover
previews) are generated automatically from the Gumroad covers.
"""
import json, os, re, sys, html, urllib.request
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)  # site/
BASE = (sys.argv[2] if len(sys.argv) > 2 else "https://the-digital-shelf.vercel.app").rstrip("/")
for d in ["img", "products", "tools"]:
    os.makedirs(f"{OUT}/{d}", exist_ok=True)

prods = {p["id"]: p for p in json.load(open(sys.argv[1]))["products"]}
CAT = json.load(open(f"{HERE}/catalog.json"))
P = [(c["slug"], c["id"], c["category"], c["title"], c["pitch"], c["key"]) for c in CAT if c["id"] in prods and prods[c["id"]].get("published")]
CATS = {"finance": "Personal finance spreadsheets", "printables": "Printables", "engineering": "Engineering calculators"}

# ---------- images (generated only when missing) ----------
FONT = "/usr/share/fonts/opentype/inter/"
def F(w, s): return ImageFont.truetype(FONT + f"Inter-{w}.otf", s)
QUAD = [(667, 67), (1193, 67), (1191, 288), (671, 288)]  # laptop screen in _build/desk-base.jpg

def coeffs(dst, src):
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()

def laptop_mockup(cover, dst):
    base = Image.open(f"{HERE}/desk-base.jpg").convert("RGB")
    W, H = cover.size
    warped = cover.transform(base.size, Image.PERSPECTIVE, coeffs(QUAD, [(0, 0), (W, 0), (W, H), (0, H)]), Image.BICUBIC)
    mask = Image.new("L", base.size, 0); ImageDraw.Draw(mask).polygon(QUAD, fill=255)
    base.paste(warped, (0, 0), mask)
    base.crop((300, 0, 1600, 867)).resize((1200, 800), Image.LANCZOS).save(dst, quality=82, optimize=True, progressive=True)

def wrap(d, text, font, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w
    return lines + [cur]

def pin(photo, hook, title, sub, dst):
    pinim = Image.new("RGB", (1000, 1500), (15, 32, 58))
    ph = Image.open(photo).convert("RGB"); tw, th = 1000, 860; r = max(tw / ph.width, th / ph.height)
    ph = ph.resize((int(ph.width * r) + 1, int(ph.height * r) + 1), Image.LANCZOS)
    x, y = (ph.width - tw) // 2, (ph.height - th) // 2
    pinim.paste(ph.crop((x, y, x + tw, y + th)), (0, 0)); d = ImageDraw.Draw(pinim)
    d.text((60, 900), hook.upper(), font=F("Bold", 34), fill=(246, 190, 59)); yy = 955
    for line in wrap(d, title, F("Black", 84), 880):
        d.text((60, yy), line, font=F("Black", 84), fill="white"); yy += 96
    d.text((60, yy + 14), sub, font=F("SemiBold", 38), fill=(160, 178, 204))
    d.rounded_rectangle([60, 1380, 560, 1450], radius=35, fill=(246, 190, 59))
    d.text((92, 1394), "Instant download \u2192", font=F("Bold", 34), fill=(15, 32, 58))
    d.text((640, 1398), "The Digital Shelf", font=F("Bold", 32), fill="white")
    pinim.save(dst, quality=85, optimize=True)

for c in CAT:
    if c["id"] not in prods: continue
    key, p = c["key"], prods[c["id"]]
    if not os.path.exists(f"{OUT}/img/{key}-cover-0.jpg"):
        for i, cv in enumerate(p.get("covers") or []):
            u = cv["url"] if isinstance(cv, dict) else cv
            im = Image.open(urllib.request.urlopen(u, timeout=60)).convert("RGB"); im.thumbnail((1280, 720))
            im.save(f"{OUT}/img/{key}-cover-{i}.jpg", quality=82, optimize=True, progressive=True)
    if not os.path.exists(f"{OUT}/img/{key}-laptop.jpg"):
        laptop_mockup(Image.open(f"{OUT}/img/{key}-cover-0.jpg").convert("RGB"), f"{OUT}/img/{key}-laptop.jpg")
    if not os.path.exists(f"{OUT}/img/{key}-pin.jpg"):
        photo = f"{OUT}/img/{c['pin_photo']}" if c.get("pin_photo") else f"{OUT}/img/{key}-laptop.jpg"
        pin(photo, c["pin_hook"], c["title"], c["pin_sub"], f"{OUT}/img/{key}-pin.jpg")

def card_img(key):
    return f"/img/{key}-laptop.jpg"

def esc(s):
    return html.escape(s, quote=True)

CSS = """
:root{--navy:#0f203a;--navy2:#1c3458;--gold:#f6be3b;--ink:#1a2233;--muted:#5b6678;--bg:#f7f5f0;--card:#fff;--line:#e6e1d6;--green:#1f9d55}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:var(--ink);background:var(--bg);line-height:1.6}
a{color:inherit}img{max-width:100%;height:auto;display:block}
.wrap{max-width:1120px;margin:0 auto;padding:0 16px}
header.site{background:var(--navy);color:#fff;position:sticky;top:0;z-index:10}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:60px;flex-wrap:wrap}
.logo{font-weight:800;text-decoration:none;font-size:1.15rem;letter-spacing:-.01em}.logo span{color:var(--gold)}
nav a{color:#cfd8e6;text-decoration:none;margin-left:16px;font-size:.95rem}nav a:hover{color:#fff}
.hero{background:linear-gradient(135deg,var(--navy),var(--navy2));color:#fff;padding:48px 0}
.hero .wrap{display:grid;grid-template-columns:1.1fr 1fr;gap:36px;align-items:center}
.hero h1{font-size:clamp(2rem,4.5vw,3.2rem);line-height:1.1;margin:0 0 14px;letter-spacing:-.02em}
.hero p{color:#c4cfdf;font-size:1.1rem;margin:0 0 22px}
.hero img{border-radius:14px;box-shadow:0 20px 50px rgba(0,0,0,.35)}
.btn{display:inline-block;background:var(--gold);color:var(--navy);font-weight:800;text-decoration:none;padding:13px 22px;border-radius:999px;border:0;cursor:pointer;font-size:1rem}
.btn:hover{filter:brightness(1.05)}.btn.ghost{background:transparent;color:#fff;border:2px solid #4a6390;margin-left:8px}
.trust{display:flex;gap:18px;flex-wrap:wrap;color:#c4cfdf;font-size:.9rem;margin-top:18px}
section{padding:44px 0}h2{font-size:1.7rem;letter-spacing:-.01em;margin:0 0 6px}.sub{color:var(--muted);margin:0 0 22px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;transition:transform .15s,box-shadow .15s}
.card:hover{transform:translateY(-3px);box-shadow:0 10px 28px rgba(15,32,58,.12)}
.card img{aspect-ratio:3/2;object-fit:cover;width:100%}
.card .body{padding:16px 18px 18px;display:flex;flex-direction:column;gap:8px;flex:1}
.card h3{margin:0;font-size:1.1rem;line-height:1.3}.card h3 a{text-decoration:none}
.card p{margin:0;color:var(--muted);font-size:.95rem;flex:1}
.row{display:flex;align-items:center;justify-content:space-between;gap:10px}
.price{font-weight:800;font-size:1.15rem}.tag{font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#8a6a10}
.btn.sm{padding:9px 16px;font-size:.92rem}
.band{background:#fff;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.split{display:grid;grid-template-columns:1fr 1fr;gap:28px;align-items:center}
.split img{border-radius:14px}
.tools{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.tool{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;text-decoration:none}
.tool b{display:block;margin-bottom:4px}.tool span{color:var(--muted);font-size:.93rem}
footer{background:var(--navy);color:#9fb0c8;font-size:.88rem;padding:30px 0;margin-top:30px}footer a{color:#cfd8e6}
.crumbs{font-size:.88rem;color:var(--muted);margin:18px 0}
.pgrid{display:grid;grid-template-columns:1.2fr 1fr;gap:34px;align-items:start}
.gallery img{border-radius:12px;margin-bottom:12px;border:1px solid var(--line)}
.buybox{background:#fff;border:1px solid var(--line);border-radius:14px;padding:22px;position:sticky;top:76px}
.buybox h1{font-size:1.6rem;line-height:1.2;margin:0 0 10px}.buybox .price{font-size:1.8rem}
.buybox ul{padding-left:18px;color:var(--muted)}.desc{max-width:760px}.desc h3{margin-top:26px}
.small{font-size:.85rem;color:var(--muted)}
.calc{background:#fff;border:1px solid var(--line);border-radius:14px;padding:22px;max-width:760px}
.calc label{display:block;font-weight:600;margin:12px 0 4px;font-size:.95rem}
.calc input,.calc select{width:100%;padding:11px 12px;border:1px solid #cfc8b8;border-radius:9px;font-size:1rem;background:#fffbe6}
.fields{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}
.result{margin-top:18px;background:var(--navy);color:#fff;border-radius:12px;padding:18px}
.result .big{font-size:1.9rem;font-weight:800;color:var(--gold)}.result p{margin:6px 0;color:#d6deea}
.upsell{margin-top:22px;display:flex;gap:16px;align-items:center;background:#fff8e1;border:1px solid #f1d88a;border-radius:12px;padding:14px}
.upsell img{width:150px;border-radius:8px}
table.t{border-collapse:collapse;width:100%;font-size:.95rem;margin-top:10px}table.t td,table.t th{border-bottom:1px solid var(--line);padding:8px;text-align:left}
@media (max-width:820px){.hero .wrap,.split,.pgrid{grid-template-columns:1fr}.fields{grid-template-columns:1fr}.buybox{position:static}nav a{margin-left:10px}.upsell{flex-direction:column;align-items:flex-start}}
"""
open(f"{OUT}/style.css", "w").write(CSS)

ANALYTICS = '<script>window.va=window.va||function(){(window.vaq=window.vaq||[]).push(arguments)};</script><script defer src="/_vercel/insights/script.js"></script>'

def page(title, desc, path, body, img="/img/og-square.jpg", extra_head=""):
    url = BASE + path
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc)}"><link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{BASE}{img}">
<meta name="twitter:card" content="summary_large_image"><meta name="theme-color" content="#0f203a">
<link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/style.css">{extra_head}{ANALYTICS}</head><body>
<header class="site"><div class="wrap"><a class="logo" href="/">The Digital <span>Shelf</span></a>
<nav><a href="/#finance">Finance</a><a href="/#printables">Printables</a><a href="/#engineering">Engineering</a><a href="/tools">Free tools</a></nav></div></header>
{body}
<footer><div class="wrap"><p><b>The Digital Shelf</b> · Practical digital downloads: spreadsheets, calculators and printables. Secure checkout and instant delivery by Gumroad.</p>
<p>Educational tools only, not financial, tax or engineering advice. Some product visuals and texts were made with the help of AI tools and checked by hand.</p>
<p>Photos: <a href="https://unsplash.com/@mailchimp">Mailchimp</a>, <a href="https://unsplash.com/@anniespratt">Annie Spratt</a> and <a href="https://unsplash.com/@spencerdavis">Spencer Davis</a> on <a href="https://unsplash.com/license">Unsplash</a> (product screens added).</p>
<p><a href="https://mydigitalshelf.gumroad.com">All products on Gumroad</a> · <a href="/tools">Free calculators</a></p></div></footer></body></html>"""

def buy_url(gid):
    return prods[gid]["short_url"] + "?wanted=true"

def price(gid):
    return prods[gid]["formatted_price"]

def card(slug, gid, cat, t, pitch, key):
    return f"""<article class="card"><a href="/products/{slug}"><img src="{card_img(key)}" alt="{esc(t)} shown on a laptop" loading="lazy" width="1200" height="800"></a>
<div class="body"><span class="tag">{esc(CATS[cat])}</span><h3><a href="/products/{slug}">{esc(t)}</a></h3><p>{esc(pitch)}</p>
<div class="row"><span class="price">{price(gid)}</span><a class="btn sm" href="{buy_url(gid)}" rel="nofollow">Buy now</a></div></div></article>"""

# ---------- home ----------
sections = ""
intro = {"finance": "Spreadsheets with formulas already built, yellow input cells and a pre-filled example. Open, type your numbers, done.",
         "printables": "Print at home, play tonight. Instant PDF download.",
         "engineering": "Shop-floor calculators for mechanical designers, in Excel, English and French."}
for cat in CATS:
    cards = "".join(card(*p) for p in P if p[2] == cat)
    sections += f'<section id="{cat}"><div class="wrap"><h2>{CATS[cat]}</h2><p class="sub">{intro[cat]}</p><div class="grid">{cards}</div></div></section>'

TOOLS = [("net-worth-by-age", "Net worth by age", "Compare your net worth with the US median for your age (Federal Reserve data)."),
         ("fire-calculator", "FIRE calculator", "How much you need to retire early, and when you get there."),
         ("compound-interest-calculator", "Compound interest calculator", "See how monthly investing grows over time."),
         ("debt-payoff-calculator", "Debt payoff calculator", "Months to debt-free and interest saved with an extra payment.")]
tools_html = "".join(f'<a class="tool" href="/tools/{s}"><b>{n} →</b><span>{d}</span></a>' for s, n, d in TOOLS)

home = f"""<div class="hero"><div class="wrap"><div><h1>Spreadsheets and printables that do the work for you.</h1>
<p>Ready-to-use Excel calculators and printable packs. Instant download, pay once, keep forever.</p>
<a class="btn" href="#finance">Browse the shelf</a><a class="btn ghost" href="/tools">Free calculators</a>
<div class="trust"><span>✓ Instant download</span><span>✓ Formulas checked</span><span>✓ Secure checkout by Gumroad</span></div></div>
<img src="/img/fire-laptop.jpg" alt="FIRE Number Calculator spreadsheet on a laptop" width="1200" height="800"></div></div>
{sections}
<section class="band"><div class="wrap split"><img src="/img/family.jpg" alt="Family gathered around a Christmas table" loading="lazy">
<div><h2>A screen-free Christmas evening</h2><p class="sub">Trivia with answer key, 20 unique bingo cards, a scavenger hunt, Would You Rather and 40 charades. Print it in 2 minutes.</p>
<a class="btn" href="/products/christmas-family-game-night-pack">See the Game Night Pack</a></div></div></section>
<section><div class="wrap"><h2>Free money calculators</h2><p class="sub">No sign-up. Try them, then grab the full spreadsheet if you want to go further.</p><div class="tools">{tools_html}</div></div></section>"""
ld = {"@context": "https://schema.org", "@type": "Organization", "name": "The Digital Shelf", "url": BASE}
open(f"{OUT}/index.html", "w").write(page("The Digital Shelf | Excel calculators, finance spreadsheets & printables",
    "Ready-to-use Excel spreadsheets (FIRE calculator, budget & net worth by age), engineering calculators and printable packs. Instant download.",
    "/", home, extra_head=f'<script type="application/ld+json">{json.dumps(ld)}</script>'))

# ---------- product pages ----------
def clean_desc(h):
    h = re.sub(r"<(script|style|iframe)[^>]*>.*?</\1>", "", h or "", flags=re.S | re.I)
    h = re.sub(r"\son\w+=\"[^\"]*\"", "", h)
    return h

for slug, gid, cat, t, pitch, key in P:
    p = prods[gid]
    covers = sorted(f for f in os.listdir(f"{OUT}/img") if f.startswith(f"{key}-cover-"))
    gallery = f'<img src="/img/{key}-laptop.jpg" alt="{esc(t)} on a laptop" width="1200" height="800">' + "".join(
        f'<img src="/img/{c}" alt="{esc(t)} preview {i+1}" loading="lazy">' for i, c in enumerate(covers))
    related = "".join(card(*q) for q in P if q[2] == cat and q[0] != slug)
    if not related:
        related = "".join(card(*q) for q in P if q[2] == "finance")
    summ = p.get("custom_summary") or pitch
    cta_tool = ""
    if cat == "finance":
        cta_tool = '<p class="small">Want to try first? Use our <a href="/tools">free calculators</a>.</p>'
    body = f"""<div class="wrap"><div class="crumbs"><a href="/">Home</a> › <a href="/#{cat}">{CATS[cat]}</a> › {esc(t)}</div>
<div class="pgrid"><div class="gallery">{gallery}</div>
<aside class="buybox"><span class="tag">{esc(CATS[cat])}</span><h1>{esc(p['name'])}</h1><p>{esc(summ)}</p>
<p class="price">{p['formatted_price']}</p><a class="btn" style="width:100%;text-align:center" href="{buy_url(gid)}" rel="nofollow">Buy now · instant download</a>
<ul><li>Secure checkout by Gumroad (card, PayPal)</li><li>Download link by email right after purchase</li><li>Pay once, keep forever</li></ul>{cta_tool}</aside></div>
<section class="desc"><h2>What's inside</h2>{clean_desc(p['description'])}<p><a class="btn" href="{buy_url(gid)}" rel="nofollow">Get it for {p['formatted_price']}</a></p></section>
<section><h2>You may also like</h2><div class="grid">{related}</div></section></div>"""
    ldp = {"@context": "https://schema.org", "@type": "Product", "name": p["name"], "description": summ,
           "image": [f"{BASE}/img/{key}-laptop.jpg"], "brand": {"@type": "Brand", "name": "The Digital Shelf"},
           "offers": {"@type": "Offer", "price": f"{p['price']/100:.2f}", "priceCurrency": p["currency"].upper(),
                      "availability": "https://schema.org/InStock", "url": p["short_url"]}}
    open(f"{OUT}/products/{slug}.html", "w").write(page(f"{t} | The Digital Shelf", summ[:155], f"/products/{slug}", body,
        img=f"/img/{key}-laptop.jpg", extra_head=f'<script type="application/ld+json">{json.dumps(ldp)}</script>'))

# ---------- tools ----------
def upsell(slug):
    q = next(x for x in P if x[0] == slug)
    return f"""<div class="upsell"><img src="/img/{q[5]}-laptop.jpg" alt="{esc(q[3])}" loading="lazy"><div><b>Go further with the {esc(q[3])}</b><br>
<span class="small">{esc(q[4])}</span><br><a class="btn sm" style="margin-top:8px" href="/products/{slug}">See it · {price(q[1])}</a></div></div>"""

TOOLJS = {}
TOOLJS["net-worth-by-age"] = ("Net Worth by Age Calculator (US medians, Federal Reserve 2025)",
 "Compare your net worth with the median US family for your age group, using Federal Reserve Survey of Consumer Finances 2025 data.",
 """<h1>Net worth by age: are you ahead?</h1><p class="sub">Enter your age and net worth (what you own minus what you owe). We compare it with the median US family in your age group.</p>
<div class="calc"><div class="fields"><div><label for="age">Your age</label><input id="age" type="number" min="18" max="100" value="32"></div>
<div><label for="nw">Your net worth ($)</label><input id="nw" type="number" step="1000" value="25000"></div></div>
<div class="result" id="out"></div>
<table class="t"><tr><th>Age of head of family</th><th>Median net worth (2025)</th></tr>
<tr><td>Under 35</td><td>$33,000</td></tr><tr><td>35-44</td><td>$155,600</td></tr><tr><td>45-54</td><td>$253,700</td></tr><tr><td>55-64</td><td>$411,900</td></tr><tr><td>65-74</td><td>$431,300</td></tr><tr><td>75 or older</td><td>$504,900</td></tr></table>
<p class="small">Source: Board of Governors of the Federal Reserve System, "Changes in U.S. Family Finances from 2022 to 2025: Evidence from the Survey of Consumer Finances", Table 2 (median family net worth by age of head of family). Median = half of families have more, half have less.</p>
UPSELL</div>""",
 """const M=[[35,33000,'under 35'],[45,155600,'35-44'],[55,253700,'45-54'],[65,411900,'55-64'],[75,431300,'65-74'],[999,504900,'75 or older']];
function fmt(x){return (x<0?'-$':'$')+Math.abs(Math.round(x)).toLocaleString('en-US')}
function nwCalc(age,nw){const b=M.find(m=>age<m[0]);return {median:b[1],group:b[2],ratio:nw/b[1]}}
function run(){const a=+age.value,n=+nw.value;if(!a){out.innerHTML='<p>Enter your age.</p>';return}const r=nwCalc(a,n);
out.innerHTML=`<p>Median for families aged ${r.group}</p><div class="big">${fmt(r.median)}</div><p>Your net worth is <b>${Math.round(r.ratio*100)}%</b> of the median: ${r.ratio>=1?'you are above the typical family in your age group.':'you are below the median for now. A budget and a debt plan are the fastest way to close the gap.'}</p>`}
age.oninput=nw.oninput=run;run();""", "money-by-age-toolkit")

TOOLJS["fire-calculator"] = ("FIRE Calculator: how much do you need to retire early?",
 "Free FIRE calculator: your FIRE number (4% rule), years until financial independence and the age you get there.",
 """<h1>FIRE calculator</h1><p class="sub">Your FIRE number is your yearly spending divided by a safe withdrawal rate (4% = 25× spending). All amounts in today's dollars.</p>
<div class="calc"><div class="fields"><div><label for="age">Current age</label><input id="age" type="number" value="30"></div>
<div><label for="assets">Invested today ($)</label><input id="assets" type="number" step="1000" value="40000"></div>
<div><label for="save">Invested per year ($)</label><input id="save" type="number" step="1000" value="20000"></div>
<div><label for="spend">Yearly spending in retirement ($)</label><input id="spend" type="number" step="1000" value="40000"></div>
<div><label for="ret">Real return per year (%)</label><input id="ret" type="number" step="0.5" value="5"></div>
<div><label for="swr">Withdrawal rate (%)</label><input id="swr" type="number" step="0.25" value="4"></div></div>
<div class="result" id="out"></div><p class="small">Assumes a constant real (after-inflation) return and contributions at the end of each year. The ~4% rule comes from Bengen (1994) and the Trinity study (1998) on 30-year retirements. Educational only, not financial advice.</p>
UPSELL</div>""",
 """function fmt(x){return '$'+Math.round(x).toLocaleString('en-US')}
function fireCalc(A,S,E,r,w){const T=E/w;if(A>=T)return {T,years:0};if(S<=0&&r<=0)return {T,years:null};
if(r===0)return {T,years:(T-A)/S};if(S<=0&&A<=0)return {T,years:null};const y=Math.log((T*r+S)/(A*r+S))/Math.log(1+r);return {T,years:isFinite(y)?y:null}}
function run(){const r=fireCalc(+assets.value,+save.value,+spend.value,+ret.value/100,+swr.value/100);
out.innerHTML=`<p>Your FIRE number</p><div class="big">${fmt(r.T)}</div>`+(r.years===null?'<p>Not reachable with these inputs: invest something each year.</p>':`<p>Financially independent in <b>${r.years.toFixed(1)} years</b>, at about age <b>${(+age.value+r.years).toFixed(1)}</b>.</p>`)}
document.querySelectorAll('input').forEach(i=>i.oninput=run);run();""", "fire-number-calculator")

TOOLJS["compound-interest-calculator"] = ("Compound Interest Calculator with monthly contributions",
 "Free compound interest calculator: see how a starting amount plus monthly investing grows over the years.",
 """<h1>Compound interest calculator</h1><p class="sub">Starting amount + monthly investing, compounded monthly.</p>
<div class="calc"><div class="fields"><div><label for="p0">Starting amount ($)</label><input id="p0" type="number" step="100" value="1000"></div>
<div><label for="pm">Monthly contribution ($)</label><input id="pm" type="number" step="50" value="300"></div>
<div><label for="ret">Average return per year (%)</label><input id="ret" type="number" step="0.5" value="7"></div>
<div><label for="yrs">Years</label><input id="yrs" type="number" value="30"></div></div>
<div class="result" id="out"></div><p class="small">Monthly rate = yearly rate ÷ 12, contributions at the end of each month. Returns are not guaranteed. Educational only.</p>
UPSELL</div>""",
 """function fmt(x){return '$'+Math.round(x).toLocaleString('en-US')}
function ciCalc(P,M,r,y){let b=P;const i=r/12;for(let k=0;k<Math.round(y*12);k++){b=b*(1+i)+M}const dep=P+M*Math.round(y*12);return {fv:b,dep,growth:b-dep}}
function run(){const r=ciCalc(+p0.value,+pm.value,+ret.value/100,+yrs.value);
out.innerHTML=`<p>Value after ${+yrs.value} years</p><div class="big">${fmt(r.fv)}</div><p>You put in <b>${fmt(r.dep)}</b>; growth adds <b>${fmt(r.growth)}</b>.</p>`}
document.querySelectorAll('input').forEach(i=>i.oninput=run);run();""", "money-by-age-toolkit")

TOOLJS["debt-payoff-calculator"] = ("Debt Payoff Calculator: months to debt-free and interest saved",
 "Free debt payoff calculator: how long to pay off a credit card or loan, total interest, and what an extra monthly payment saves.",
 """<h1>Debt payoff calculator</h1><p class="sub">How long until this debt is gone, and what an extra payment saves you.</p>
<div class="calc"><div class="fields"><div><label for="bal">Balance ($)</label><input id="bal" type="number" step="100" value="6000"></div>
<div><label for="apr">Interest rate (APR %)</label><input id="apr" type="number" step="0.1" value="22"></div>
<div><label for="pay">Monthly payment ($)</label><input id="pay" type="number" step="10" value="200"></div>
<div><label for="extra">Extra per month ($)</label><input id="extra" type="number" step="10" value="100"></div></div>
<div class="result" id="out"></div><p class="small">Interest charged monthly at APR ÷ 12; fixed payment, no new charges. Educational only.</p>
UPSELL</div>""",
 """function fmt(x){return '$'+Math.round(x).toLocaleString('en-US')}
function payoff(B,apr,P){const i=apr/12;let b=B,m=0,int=0;if(P<=b*i)return null;while(b>0.005&&m<1200){const c=b*i;int+=c;b=b+c-P;m++;if(b<0)b=0}return {months:m,interest:int}}
function yrs(m){const y=Math.floor(m/12),r=m%12;return (y?y+' yr ':'')+r+' mo'}
function run(){const B=+bal.value,a=+apr.value/100,P=+pay.value,X=+extra.value;const r1=payoff(B,a,P),r2=payoff(B,a,P+X);
if(!r1){out.innerHTML=`<p>Your payment does not cover the monthly interest (${fmt(B*a/12)}). The debt will never be paid off: increase the payment.</p>`;return}
out.innerHTML=`<p>Debt-free in</p><div class="big">${yrs(r1.months)}</div><p>Total interest: <b>${fmt(r1.interest)}</b></p>`+(X>0&&r2?`<p>With ${fmt(X)} extra per month: <b>${yrs(r2.months)}</b>, interest <b>${fmt(r2.interest)}</b>. You save <b>${fmt(r1.interest-r2.interest)}</b> and <b>${r1.months-r2.months} months</b>.</p>`:'')}
document.querySelectorAll('input').forEach(i=>i.oninput=run);run();""", "money-by-age-toolkit")

for slug, (title, desc, body, js, up) in TOOLJS.items():
    b = f'<div class="wrap"><div class="crumbs"><a href="/">Home</a> › <a href="/tools">Free tools</a></div>' + body.replace("UPSELL", upsell(up)) + f"</div><script>{js}</script>"
    open(f"{OUT}/tools/{slug}.html", "w").write(page(title, desc, f"/tools/{slug}", b))
tb = f'<div class="wrap"><div class="crumbs"><a href="/">Home</a> › Free tools</div><h1>Free money calculators</h1><p class="sub">No sign-up, nothing stored: everything runs in your browser.</p><div class="tools">{tools_html}</div></div>'
open(f"{OUT}/tools/index.html", "w").write(page("Free money calculators | The Digital Shelf", "Free net worth by age, FIRE, compound interest and debt payoff calculators.", "/tools", tb))

# ---------- misc ----------
open(f"{OUT}/favicon.svg", "w").write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#0f203a"/><rect x="12" y="40" width="40" height="6" rx="2" fill="#f6be3b"/><rect x="16" y="18" width="8" height="22" rx="2" fill="#fff"/><rect x="28" y="22" width="8" height="18" rx="2" fill="#fff"/><rect x="40" y="14" width="8" height="26" rx="2" fill="#f6be3b"/></svg>')
urls = ["/", "/tools"] + [f"/products/{p[0]}" for p in P] + [f"/tools/{s}" for s in TOOLJS]
open(f"{OUT}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{BASE}{u}</loc></url>" for u in urls) + "</urlset>\n")
open(f"{OUT}/robots.txt", "w").write(f"User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n")
open(f"{OUT}/vercel.json", "w").write(json.dumps({"cleanUrls": True, "trailingSlash": False,
    "headers": [{"source": "/img/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=604800"}]}]}, indent=2))
open(f"{OUT}/404.html", "w").write(page("Page not found | The Digital Shelf", "Page not found.", "/404", '<div class="wrap"><h1>Page not found</h1><p><a class="btn" href="/">Back to the shelf</a></p></div>'))
print("pages:", urls)
