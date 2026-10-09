"""dev_intro_v2.mp4 — 20s beat-synced montage built around the user's anime avatar.
1280x720 @30fps, H.264 + AAC (X compatible).  Usage: python3 make_video_v2.py out.mp4
Needs assets/avatar.jpg + assets/avatar_cut.png (background-removed avatar).
"""
import math, random, subprocess, sys, wave, os
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops, ImageOps
from scipy.signal import lfilter

W, H, FPS, DUR = 1280, 720, 30, 20.0
N = int(FPS * DUR)
BEAT = 0.5
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "dev_intro_v2.mp4")

MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

@lru_cache(None)
def font(p, s): return ImageFont.truetype(p, int(s))

CYAN, PINK, PURPLE, GREEN, YELLOW, WHITE = (60, 230, 255), (255, 70, 170), (140, 100, 255), (80, 255, 150), (255, 210, 90), (255, 255, 255)
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def eo(x): return 1 - (1 - x) ** 3
def eio(x): return 3 * x * x - 2 * x ** 3
def back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def lerp(a, b, k): return a + (b - a) * k

# ---------------- assets ----------------
_cut = Image.open(os.path.join(HERE, "assets/avatar_cut.png")).convert("RGBA").resize((1000, 1000), Image.LANCZOS)
_cut = _cut.filter(ImageFilter.UnsharpMask(2, 90, 2))
_plate = Image.open(os.path.join(HERE, "assets/avatar.jpg")).convert("RGB").resize((1000, 1000), Image.LANCZOS)
_plate = ImageChops.multiply(_plate.filter(ImageFilter.GaussianBlur(3)), Image.new("RGB", (1000, 1000), (150, 110, 215)))
_plate = _plate.point(lambda v: int(v * .62))
PLATE = _plate.convert("RGBA")

@lru_cache(None)
def hero(treat="base", glow="cyan"):
    rgb = _cut.convert("RGB"); a = _cut.getchannel("A")
    g = ImageOps.grayscale(rgb)
    if treat == "duo": rgb = ImageOps.colorize(g, (12, 0, 45), (255, 140, 210), (130, 40, 220))
    elif treat == "duoc": rgb = ImageOps.colorize(g, (0, 8, 40), (170, 255, 255), (20, 110, 210))
    elif treat == "neg": rgb = ImageOps.invert(rgb)
    elif treat == "sil": rgb = Image.new("RGB", rgb.size, (6, 4, 20))
    elif treat == "hot": rgb = ImageEnhance_color(rgb)
    base = rgb.convert("RGBA"); base.putalpha(a)
    col = {"cyan": CYAN, "pink": PINK, "white": WHITE, "purple": PURPLE, "none": None}[glow]
    if col is None: return base
    ga = a.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(26)).point(lambda v: min(255, int(v * 1.5)))
    gl = Image.new("RGBA", rgb.size, col + (0,)); gl.putalpha(ga)
    return Image.alpha_composite(gl, base)

def ImageEnhance_color(rgb):
    from PIL import ImageEnhance
    return ImageEnhance.Brightness(ImageEnhance.Contrast(rgb).enhance(1.35)).enhance(1.15)

def xform(layer, anchor, pos, scale=1.0, rot=0.0):
    """Place `layer` so source point `anchor` lands at frame point `pos`, scaled/rotated (deg)."""
    th = math.radians(rot); c, s_ = math.cos(th), math.sin(th)
    px, py = pos; ax, ay = anchor
    co = (c / scale, s_ / scale, ax - (px * c + py * s_) / scale,
          -s_ / scale, c / scale, ay - (-px * s_ + py * c) / scale)
    return layer.transform((W, H), Image.AFFINE, co, Image.BICUBIC)

def put(img, layer, anchor, pos, scale=1.0, rot=0.0, alpha=1.0):
    if alpha <= 0.01 or scale <= 0.001: return
    if abs(scale - 1) < 1e-3 and abs(rot) < 1e-3:
        lay = layer
        if alpha < 1: lay = layer.copy(); lay.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        img.paste(lay, (int(pos[0] - anchor[0]), int(pos[1] - anchor[1])), lay); return
    lay = xform(layer, anchor, pos, scale, rot)
    if alpha < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(lay, (0, 0), lay)

_tc = {}
def tlayer(text, fnt, fill, stroke=0, sfill=(0, 0, 0)):
    k = (text, id(fnt), fill, stroke, sfill)
    if k not in _tc:
        w = int(fnt.getlength(text)) + 40 + stroke * 2; h = int(fnt.size * 1.5) + stroke * 2
        L = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(L).text((w / 2, h / 2), text, font=fnt, fill=fill + (255,), anchor="mm", stroke_width=stroke, stroke_fill=sfill + (255,))
        _tc[k] = L
    return _tc[k]

def slam(img, text, pos, fnt, fill, t, t0, stroke=0, sfill=(0, 0, 0), hold=None, rot=0.0, dur=.16):
    if t < t0: return
    k = prog(t, t0, t0 + dur); L = tlayer(text, fnt, fill, stroke, sfill)
    sc = lerp(3.2, 1.0, eo(k)); al = k
    sh = (1 - k) * 0
    jx = random.Random(int(t * 30)).uniform(-3, 3) * (1 - prog(t, t0 + dur, t0 + dur + .25))
    put(img, L, (L.width / 2, L.height / 2), (pos[0] + jx, pos[1]), sc, rot, al)

# ---------------- background ----------------
yy = np.linspace(0, 1, H)[:, None, None]
BGN = ((np.array([10, 8, 30]) * (1 - yy) + np.array([30, 12, 60]) * yy) * np.ones((H, W, 3))).astype(np.uint8)
rr = random.Random(7)
particles = [(rr.uniform(0, W), rr.uniform(0, H), rr.uniform(15, 80), rr.uniform(1.5, 4), rr.choice([CYAN, PINK, PURPLE])) for _ in range(90)]
rain = [(x, rr.uniform(60, 240), rr.uniform(0, H), "".join(rr.choice("01<>{}/;=+*") for _ in range(14))) for x in range(0, W, 34)]

def bg_plate(img, t, zoom=1.5, drift=40):
    put(img, PLATE, (500 + math.sin(t * .4) * drift, 500), (W / 2, H / 2), zoom + .02 * t % 1 * 0 + 0.0, 0, 1)

def bg_fx(img, t, plate=0.0, grid=True, rainA=70):
    if plate > 0:
        bg_plate(img, t, 1.45 + 0.02 * math.sin(t * .5))
        ov = Image.new("RGBA", (W, H), (10, 6, 32, int(255 * (1 - plate)))); img.paste(ov, (0, 0), ov)
    d = ImageDraw.Draw(img, "RGBA")
    if grid:
        off = (t * 60) % 60
        for i in range(-2, 24):
            y = 400 + i * 60 + off
            if 360 < y < H: d.line([(0, y), (W, y)], fill=(130, 90, 255, int(90 * (y - 360) / 360)), width=1)
        for i in range(-14, 15): d.line([(W / 2 + i * 30, 360), (W / 2 + i * 200, H)], fill=(130, 90, 255, 60), width=1)
    for x, sp, y0, s in rain:
        for k, ch in enumerate(s):
            y = (y0 + t * sp + k * 26) % (H + 380) - 190
            d.text((x, y), ch, font=font(MONO_B, 20), fill=(60, 230, 255, int(rainA * (k / len(s)) ** 2)))
    for x, y, sp, r, c in particles:
        yp = (y - t * sp) % H; xp = x + math.sin(t + x) * 14
        d.ellipse([xp - r, yp - r, xp + r, yp + r], fill=c + (130,))

def rays(img, t, cx, cy, col, alpha=55, n=14):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i in range(n):
        a0 = t * .35 + i * 2 * math.pi / n; a1 = a0 + math.pi / n * .55
        d.polygon([(cx, cy), (cx + 1800 * math.cos(a0), cy + 1800 * math.sin(a0)), (cx + 1800 * math.cos(a1), cy + 1800 * math.sin(a1))], fill=col + (alpha,))
    img.paste(ov, (0, 0), ov)

def speedlines(img, f, cx, cy, amt, col=(255, 255, 255)):
    r = random.Random(f); ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for _ in range(int(60 * amt)):
        a = r.uniform(0, 2 * math.pi); r0 = r.uniform(180, 420); r1 = r0 + r.uniform(250, 700)
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], fill=col + (int(110 * amt),), width=r.randint(1, 3))
    img.paste(ov, (0, 0), ov)

def ring(img, cx, cy, rad, col, t, width=4, alpha=255, arcs=3, speed=1.0):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i in range(arcs):
        a0 = (t * 90 * speed + i * 360 / arcs) % 360
        d.arc([cx - rad, cy - rad, cx + rad, cy + rad], a0, a0 + 360 / arcs * .6, fill=col + (alpha,), width=width)
    img.paste(ov, (0, 0), ov)

def shockwave(img, cx, cy, t, t0, col=WHITE):
    if not (t0 <= t < t0 + .6): return
    k = (t - t0) / .6; r = 40 + 900 * eo(k)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (int(255 * (1 - k)),), width=int(22 * (1 - k)) + 2)
    img.paste(ov, (0, 0), ov)

# ---------------- holographic windows & chips ----------------
CODE = [
    [("class ", PINK), ("Developer", YELLOW), (":", WHITE)],
    [("    age ", WHITE), ("= ", PINK), ("27", PURPLE)],
    [("    stack ", WHITE), ("= ", PINK), ('["Python","JS","AI"]', GREEN)],
    [("", None)],
    [("    def ", PINK), ("run", CYAN), ("(self):", WHITE)],
    [("        while ", PINK), ("True", PURPLE), (":", WHITE)],
    [("            code", CYAN), ("()", WHITE)],
    [("            ship", CYAN), ("()", WHITE)],
]
CODE_TOTAL = sum(len("".join(s for s, _ in l)) for l in CODE)
LOG = [("$ git push origin main", WHITE), ("  building…", (150, 160, 200)), ("  ✔ tests passed", GREEN), ("  ✔ deployed 🚀".replace(" 🚀", ""), GREEN), ("$ coffee --refill", WHITE), ("  ☕ ok".replace("☕ ", ""), YELLOW), ("$ ship --again", WHITE), ("  ✔ shipped", GREEN)]
T_CODE0, T_CODE1 = 8.3, 11.6
def code_window(t):
    ww, wh = 520, 300
    win = Image.new("RGBA", (ww, wh), (0, 0, 0, 0)); wd = ImageDraw.Draw(win)
    wd.rounded_rectangle([0, 0, ww - 1, wh - 1], radius=14, fill=(16, 14, 40, 225), outline=CYAN + (230,), width=2)
    wd.rounded_rectangle([0, 0, ww - 1, 36], radius=14, fill=(40, 36, 86, 255))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))): wd.ellipse([16 + i * 24, 12, 30 + i * 24, 26], fill=c)
    wd.text((ww / 2, 19), "developer.py", font=font(MONO_B, 17), fill=(170, 175, 210), anchor="mm")
    left = int(CODE_TOTAL * prog(t, T_CODE0, T_CODE1)); y = 50; cur = None
    for line in CODE:
        x = 16
        for seg, col in line:
            part = seg[:left]; left -= len(part)
            if part: wd.text((x, y), part, font=font(MONO, 21), fill=col or WHITE)
            x += 12.6 * len(part)
            if left <= 0 and cur is None: cur = (x, y)
        if cur: break
        y += 30
    cur = cur or (16, y)
    if int(t * 4) % 2 == 0: wd.rectangle([cur[0] + 2, cur[1] + 2, cur[0] + 11, cur[1] + 24], fill=CYAN)
    return win

def log_window(t):
    ww, wh = 400, 250
    win = Image.new("RGBA", (ww, wh), (0, 0, 0, 0)); wd = ImageDraw.Draw(win)
    wd.rounded_rectangle([0, 0, ww - 1, wh - 1], radius=14, fill=(16, 14, 40, 225), outline=PINK + (230,), width=2)
    wd.rounded_rectangle([0, 0, ww - 1, 34], radius=14, fill=(70, 30, 80, 255))
    wd.text((ww / 2, 18), "terminal", font=font(MONO_B, 16), fill=(220, 190, 220), anchor="mm")
    n = int(len(LOG) * prog(t, T_CODE0 + .4, T_CODE1 + 1.2))
    for i, (s, c) in enumerate(LOG[:n]): wd.text((14, 48 + i * 24), s, font=font(MONO, 18), fill=c)
    return win

CHIPS = [("Python", CYAN), ("JavaScript", YELLOW), ("AI / ML", PINK), ("Cloud", PURPLE), ("Open Source", GREEN)]
@lru_cache(None)
def chip(name, col):
    f = font(SANS_B, 30); w = int(f.getlength(name)) + 44
    c = Image.new("RGBA", (w, 52), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle([0, 0, w - 1, 51], radius=26, fill=col + (70,), outline=col + (255,), width=3)
    d.text((w / 2, 26), name, font=f, fill=WHITE, anchor="mm"); return c

def chips_layer(img, t, front, t0=9.0):
    for i, (n, c) in enumerate(CHIPS):
        a = back(prog(t, t0 + i * .3, t0 + i * .3 + .4))
        if a <= 0: continue
        ang = t * 1.0 + i * 2 * math.pi / 5
        depth = math.sin(ang)
        if (depth >= 0) != front: continue
        x = W / 2 + math.cos(ang) * 470; y = 330 + depth * 130 + math.sin(t * 2 + i) * 6
        L = chip(n, c); sc = (0.85 + 0.25 * depth) * a
        put(img, L, (L.width / 2, L.height / 2), (x, y), sc, 0, 1.0 if front else 0.65)

# ---------------- hero helpers ----------------
FACE, EYES, WATCH, GLASS = (500, 255), (505, 250), (400, 715), (505, 250)
LENS = Image.new("L", (1000, 1000), 0)
_d = ImageDraw.Draw(LENS)
for x0 in (413, 513): _d.rounded_rectangle([x0, 225, x0 + 86, 280], radius=14, fill=255)
LENS_BOX = (400, 215, 612, 292)
LENS_C = LENS.crop(LENS_BOX)

def hero_with_reflection(treat, glow, t):
    base = hero(treat, glow)
    H2 = base.copy()
    reg = H2.crop(LENS_BOX).convert("RGB")
    txt = Image.new("RGB", reg.size, (0, 0, 0)); td = ImageDraw.Draw(txt)
    for i in range(10):
        y = (i * 18 - (t * 90) % 180)
        s = "".join(random.Random(i + int(t * 6)).choice("01{}<>;=") for _ in range(12))
        td.text((6, y), s, font=font(MONO_B, 14), fill=(60, 255, 150)); td.text((112, y + 6), s[::-1], font=font(MONO_B, 14), fill=(60, 230, 255))
    scr = ImageChops.screen(reg, txt)
    a = H2.getchannel("A"); H2.paste(scr, LENS_BOX[:2], LENS_C)
    H2.putalpha(a); return H2

def draw_hero(img, t, treat="base", glow="cyan", anchor=(500, 500), pos=(640, 360), scale=.72, rot=0, alpha=1.0, refl=False):
    h = hero_with_reflection(treat, glow, t) if refl else hero(treat, glow)
    put(img, h, anchor, pos, scale, rot, alpha)

def kick(t, rate=8):  # decays after each beat
    return math.exp(-((t % BEAT)) * rate)

# ---------------- timeline ----------------
BIG = [1.5, 3.2, 4.0, 8.0, 13.0, 16.5]
CUTS = BIG + [4.5, 5.0, 5.5, 6.0, 6.25, 6.5, 6.75, 7.0, 7.25, 7.5, 7.75, 15.0, 15.25, 15.5, 15.75, 16.0, 16.25]
CUTS.sort()

QUICK = [  # (anchor, scale0, scale1, rot, treat, glow, word)
    ((500, 255), 3.4, 4.0, 0, "base", "cyan", "CODE", True),
    ((400, 715), 2.8, 3.3, -8, "base", "pink", "BUILD", False),
    ((500, 520), .78, .9, 0, "duo", "pink", "SHIP", False),
    ((500, 270), 2.2, 2.7, 6, "neg", "none", "REPEAT", False),
    ((470, 255), 5.0, 5.8, 0, "base", "cyan", "", True),
    ((520, 520), 1.6, 1.9, -5, "duoc", "cyan", "", False),
    ((500, 300), 2.0, 2.3, 4, "duo", "pink", "", False),
    ((430, 700), 3.6, 4.2, 10, "base", "cyan", "", False),
    ((500, 260), 3.0, 3.6, -6, "neg", "none", "", False),
    ((500, 500), .9, 1.1, 0, "base", "pink", "", False),
    ((505, 250), 4.4, 5.2, 0, "duoc", "cyan", "", True),
    ((500, 500), .75, 1.2, 0, "duo", "cyan", "", False),
]

def shot_intro(img, t):
    d = ImageDraw.Draw(img, "RGBA")
    lines = ["> init developer.exe", "> loading skills ...", "> age = 27"]
    for i, s in enumerate(lines):
        n = int(len(s) * prog(t, .1 + i * .35, .1 + i * .35 + .3))
        d.text((300, 250 + i * 70), s[:n], font=font(MONO_B, 44), fill=(GREEN, CYAN, PINK)[i])
    bar = prog(t, .3, 1.4)
    d.rectangle([300, 520, 980, 548], outline=CYAN + (255,), width=3)
    d.rectangle([304, 524, 304 + 672 * bar, 544], fill=CYAN + (255,))
    d.text((980, 580), "%d%%" % int(bar * 100), font=font(MONO_B, 28), fill=WHITE, anchor="ra")

def shot_reveal(img, t):
    k = t - 1.5
    pull = eio(prog(t, 1.5, 3.2))
    sc = lerp(5.5, .78, pull) if True else .78
    anc = (lerp(EYES[0], 500, pull), lerp(EYES[1], 500, pull))
    pos = (lerp(640, 790, pull), lerp(360, 380, pull))
    rays(img, t, pos[0], 330, PINK, 40)
    draw_hero(img, t, "sil" if t < 1.75 else "base", "cyan", anc, pos, sc, 0, 1, refl=(t < 3.0 and sc > 2))
    shockwave(img, pos[0], 330, t, 3.2)
    if t >= 3.2:
        slam(img, "27", (300, 300), font(MONO_B, 230), WHITE, t, 3.25, 6, PINK)
        slam(img, "YEARS", (300, 480), font(MONO_B, 80), CYAN, t, 3.5, 3, (10, 10, 40))
        slam(img, "DEVELOPER", (300, 575), font(MONO_B, 60), PINK, t, 3.7, 3, (10, 10, 40))

def shot_montage(img, t):
    if t < 6.0: idx = int((t - 4.0) / .5)
    else: idx = 4 + min(7, int((t - 6.0) / .25))
    st = 4.0 + idx * .5 if idx < 4 else 6.0 + (idx - 4) * .25
    ln = .5 if idx < 4 else .25
    a, s0, s1, rot, treat, glow, word, refl = QUICK[idx]
    k = prog(t, st, st + ln)
    sc = lerp(s0, s1, k)
    treat_bg = idx % 3
    bg_fx(img, t, plate=(0.5 if idx % 2 == 0 else 0.0), grid=idx % 2 == 1, rainA=90)
    if idx >= 4: rays(img, t, 640, 360, [PINK, CYAN, PURPLE][idx % 3], 40, 10)
    # background word
    if word:
        slam(img, word, (640, 360), font(MONO_B, 330), WHITE, t, st, 0)
        # darken big word to be subtle
    xs = random.Random(idx).choice([-60, 0, 60])
    draw_hero(img, t, treat, glow, a, (640 + xs * (1 - k), 360), sc, rot * (1 - k * .5), 1, refl=refl)
    if word:
        slam(img, word, (640, 640), font(MONO_B, 90), WHITE, t, st + .02, 4, PINK)

def shot_hero(img, t):
    k = t - 8.0
    bg_fx(img, t, plate=.9, rainA=60)
    rays(img, t, 640, 330, PURPLE, 38)
    # giant outlined word behind
    L = tlayer("DEVELOPER", font(MONO_B, 210), (0, 0, 0), 0)
    big = tlayer("DEVELOPER", font(MONO_B, 210), (255, 255, 255))
    ov = Image.new("RGBA", big.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).text((big.width / 2, big.height / 2), "DEVELOPER", font=font(MONO_B, 210), fill=(0, 0, 0, 0), anchor="mm", stroke_width=3, stroke_fill=(255, 255, 255, 120))
    put(img, ov, (ov.width / 2, ov.height / 2), (640 - ((t * 120) % 400) + 200, 330), 1, 0, 1)
    wa = back(prog(t, 8.1, 8.6))
    put(img, code_window(t), (260, 150), (330, 250 + math.sin(t * 1.5) * 8), .95 * wa, -7, .92)
    put(img, log_window(t), (200, 125), (960, 560 + math.cos(t * 1.7) * 8), .95 * wa, 6, .92)
    chips_layer(img, t, False)
    ring(img, 640, 300, 250, CYAN, t, 4, 220, 3, 1)
    ring(img, 640, 300, 285, PINK, -t, 3, 200, 4, 1.4)
    bob = math.sin(t * 2.2) * 8
    p = back(prog(t, 8.0, 8.5)); pun = 1 + .035 * kick(t)
    draw_hero(img, t, "base", "pink" if int(t) % 2 else "cyan", (500, 500), (640, 382 + bob), .8 * p * pun, math.sin(t * .9) * 1.5)
    chips_layer(img, t, True)
    slam(img, "27 · DEVELOPER", (640, 660), font(MONO_B, 64), WHITE, t, 8.3, 4, PINK)
    for i, s in enumerate(["BUGS FIXED  ∞", "COFFEE  ∞", "SHIPPED  ∞"]):
        slam(img, s, (1090, 150 + i * 56), font(MONO_B, 30), (GREEN, YELLOW, CYAN)[i], t, 10.4 + i * .35, 0)

def shot_tunnel(img, t):
    k = t - 13.0
    bg_fx(img, t, plate=.4 if t < 15 else 0, grid=True, rainA=110)
    rays(img, t, 640, 360, CYAN if t < 15 else PINK, 50, 18)
    nb = int((t - 13) / BEAT)
    num = tlayer("27", font(MONO_B, 700), (255, 255, 255), 5, PINK)
    pk = kick(t)
    put(img, num, (num.width / 2, num.height / 2), (640, 360), 1.0 + .08 * pk, 0, .22)
    # echoes
    pal = ["cyan", "pink", "purple"]
    for i in range(6, 0, -1):
        sc = .75 + i * .07 + .02 * math.sin(t * 3 + i)
        draw_hero(img, t, "duoc" if i % 2 else "duo", "none", (500, 500), (640 + math.sin(t * 2 + i) * 40 * i / 3, 360), sc, math.sin(t * 1.3 + i) * 2 * i / 3, .13)
    sc = .78 + .05 * pk + 0.1 * eo(prog(t, 13, 16.5))
    treats = ["base", "duo", "duoc", "neg"]
    tr = treats[int((t - 15) / .25) % 4] if t >= 15 else "base"
    draw_hero(img, t, tr, pal[nb % 3] if tr != "neg" else "none", (500, 500), (640, 372), sc, math.sin(t * 1.5) * 3)
    speedlines(img, int(t * 30), 640, 360, .6 + .6 * pk if t < 15 else 1.0)
    slam(img, "27 YEARS", (250, 130), font(MONO_B, 84), WHITE, t, 13.15, 5, PINK)
    if t < 15: slam(img, "∞ LINES OF CODE", (640, 640), font(MONO_B, 66), CYAN, t, 13.9, 4, (10, 10, 40))
    if t >= 15:
        slam(img, "NO SLEEP.", (640, 640), font(MONO_B, 66) if False else font(MONO_B, 80), YELLOW, t, 15.0, 5, (60, 10, 40)) if t < 15.75 else slam(img, "JUST SHIP.", (640, 640), font(MONO_B, 80), GREEN, t, 15.75, 5, (10, 40, 40))

def shot_finale(img, t):
    k = t - 16.5
    bg_fx(img, t, plate=.8, rainA=70)
    rays(img, t, 420, 330, YELLOW if k < 1 else PINK, 55, 16)
    speedlines(img, int(t * 30), 420, 360, max(0, 1 - k * 1.2))
    ring(img, 420, 330, 270, CYAN, t, 4, 220, 3, 1)
    ring(img, 420, 330, 305, PINK, -t, 3, 200, 4, 1.3)
    p = eo(prog(t, 16.5, 17.3)); bob = math.sin(t * 2) * 6
    sc = lerp(1.5, .84, p) * (1 + .03 * kick(t))
    draw_hero(img, t, "base", "pink", (500, 500), (lerp(640, 420, p), 380 + bob), sc, lerp(-4, 0, p))
    shockwave(img, 420, 330, t, 16.5)
    ov = Image.new("RGBA", (W, H), (8, 6, 24, int(150 * prog(t, 17.0, 17.6))));
    f = font(MONO_B, 78)
    slam(img, "27 YEARS OLD", (930, 230), font(MONO_B, 70), WHITE, t, 17.2, 5, PINK)
    s = "STILL COMPILING..."; n = int(len(s) * prog(t, 17.9, 18.7))
    if n > 0:
        L = tlayer(s[:n], font(MONO_B, 44), PINK); img.paste(L, (int(930 - L.width / 2) + 0, 330 - L.height // 2), L)
    slam(img, "LET'S BUILD", (930, 440), font(MONO_B, 78), GREEN, t, 18.9, 5, (10, 40, 30))
    slam(img, "SOMETHING.", (930, 525), font(MONO_B, 78), GREEN, t, 19.1, 5, (10, 40, 30))
    slam(img, "- MUAYYAD", (930, 625), font(MONO_B, 62), CYAN, t, 19.35, 4, (10, 20, 50))

def scene(t):
    img = Image.fromarray(BGN).convert("RGB")
    if t < 1.5: shot_intro(img, t)
    elif t < 4.0:
        bg_fx(img, t, plate=.3 if t > 3.0 else 0); shot_reveal(img, t)
    elif t < 8.0: shot_montage(img, t)
    elif t < 13.0: shot_hero(img, t)
    elif t < 16.5: shot_tunnel(img, t)
    else: shot_finale(img, t)
    if t >= 3.4 and t < 19.3:  # persistent name tag, bottom-right
        a = prog(t, 3.4, 3.9)
        L = tlayer("MUAYYAD", font(MONO_B, 30), (255, 255, 255), 3, (30, 10, 70))
        put(img, L, (L.width, L.height / 2), (W - 20, H - 34), 1.0, 0, .85 * a)
    return img

# ---------------- post ----------------
def cutstate(t):
    best = None
    for c in CUTS:
        if t >= c and t - c < .6:
            w = 1.0 if c in BIG else .55
            best = (t - c, w)
    return best

def post(img, t, f):
    cs = cutstate(t); r = random.Random(f)
    dt, w = cs if cs else (9, 0)
    shake = w * 16 * math.exp(-dt / .1) + 1.2 * kick(t, 10) * (t > 3.2)
    flash = w * .85 * math.exp(-dt / .045)
    rgb = w * 22 * math.exp(-dt / .13) + (3 if t > 3.2 else 0)
    zb = w * math.exp(-dt / .09)
    pun = 1.045 + .03 * kick(t, 9) * (t > 3.2) + w * .08 * math.exp(-dt / .12)
    ang = r.uniform(-1, 1) * shake * .12
    # camera: zoom punch + shake + roll
    ox, oy = r.uniform(-1, 1) * shake, r.uniform(-1, 1) * shake
    cam = xform_img(img, pun, ox, oy, ang)
    arr = np.asarray(cam).astype(np.float32)
    if zb > .08:
        acc = arr.copy(); n = 5
        for i in range(1, n):
            s = 1 + zb * .05 * i
            acc += np.asarray(xform_img(cam, s, 0, 0, 0)).astype(np.float32)
        arr = acc / n
    # bloom
    small = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)
    sa = np.asarray(small).astype(np.float32)
    arr = 255 - (255 - arr) * (255 - sa * .5) / 255
    # vignette, scanlines, grain
    arr *= VIG * SCAN
    arr += np.random.RandomState(f).randn(H, W, 1) * 3.5
    arr = np.clip(arr, 0, 255)
    # chromatic aberration + glitch bands
    ab = int(rgb)
    if ab:
        arr[..., 0] = np.roll(arr[..., 0], ab, axis=1); arr[..., 2] = np.roll(arr[..., 2], -ab, axis=1)
    if w and dt < .2:
        for _ in range(int(3 + 6 * w)):
            y0 = r.randint(0, H - 50); h = r.randint(5, 50); sh = r.randint(-90, 90)
            arr[y0:y0 + h] = np.roll(arr[y0:y0 + h], sh, axis=1)
    if cs and dt < .1 and w > .5:  # horizontal whip blur
        a2 = arr.copy()
        for i in range(1, 6): a2 += np.roll(arr, i * 14 * (1 if (CUTS.index(t - dt) if (t - dt) in CUTS else 0) % 2 else -1), axis=1)
        arr = a2 / 6
    arr = arr + (255 - arr) * flash
    fade = min(prog(t, 0, .35), 1 - prog(t, DUR - .7, DUR))
    return (np.clip(arr, 0, 255) * fade).astype(np.uint8)

def xform_img(img, s, ox, oy, ang):
    th = math.radians(ang); c, s_ = math.cos(th), math.sin(th)
    cx, cy = W / 2, H / 2
    # out->src: src = center + R(-ang)*(out-center-offset)/s
    a, b, d, e = c / s, s_ / s, -s_ / s, c / s
    co = (a, b, cx - a * (cx + ox) - b * (cy + oy), d, e, cy - d * (cx + ox) - e * (cy + oy))
    return img.transform((W, H), Image.AFFINE, co, Image.BILINEAR)

_xx, _yv = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
VIG = (1 - 0.5 * np.clip(_xx ** 2 * .6 + _yv ** 2 * .9, 0, 1))[..., None].astype(np.float32)
SCAN = np.ones((H, W, 1), np.float32); SCAN[::3] = .93

# ---------------- audio ----------------
SR = 44100
def make_audio(path):
    n = int(SR * DUR); y = np.zeros(n, np.float32); music = np.zeros(n, np.float32); drums = np.zeros(n, np.float32)
    rs = np.random.RandomState(1); tt = np.arange(n) / SR
    def add(buf, t0, sig, g=1.0):
        i = int(t0 * SR)
        if i < 0 or i >= n: return
        j = min(n, i + len(sig)); buf[i:j] += sig[:j - i] * g
    X = lambda d: np.arange(int(SR * d)) / SR
    def tone(fr, d, kind="saw", env=8):
        x = X(d)
        s = {"saw": 2 * ((x * fr) % 1) - 1, "sq": np.sign(np.sin(2 * np.pi * fr * x)), "sin": np.sin(2 * np.pi * fr * x)}[kind]
        return (s * np.exp(-env * x) * np.minimum(1, x * 300)).astype(np.float32)
    mid = lambda m: 440 * 2 ** ((m - 69) / 12)
    def lp(sig, a): return lfilter([a], [1, -(1 - a)], sig).astype(np.float32)
    def hp(sig, a): return (sig - lp(sig, a)).astype(np.float32)
    # kicks
    def kickf():
        x = X(.28); return (np.sin(2 * np.pi * (45 + 120 * np.exp(-22 * x)) * x) * np.exp(-9 * x)).astype(np.float32)
    K = kickf()
    t = 1.5
    while t < DUR - .3:
        if not (t >= 16.0 and t < 16.5): add(drums, t, K, .9)
        t += BEAT
    # heartbeat intro
    for tc in (.2, .5, .9, 1.2): add(drums, tc, K, .5)
    # claps on 2&4, hats
    t = 4.0 + BEAT
    while t < DUR - .5:
        noise = hp(rs.randn(int(SR * .18)).astype(np.float32), .35) * np.exp(-X(.18) * 28)
        add(drums, t, noise.astype(np.float32), .45); t += BEAT * 2
    t = 3.2
    while t < DUR - .5:
        step = .125 if (6 <= t < 8 or 13 <= t < 16.5) else .25
        h = hp(rs.randn(int(SR * .05)).astype(np.float32), .6) * np.exp(-X(.05) * 90)
        add(drums, t + (BEAT / 2 if step >= .25 else 0), h.astype(np.float32), .22 if step >= .25 else .15); t += step * (2 if step >= .25 else 1)
    # bass + arp
    prog_ = [33, 29, 31, 28]  # A F G E (low)
    t = 3.2
    while t < DUR - .4:
        bar = int((t - 3.2) / 2) % 4; root = prog_[bar]
        for i in range(4):
            tb = t + i * .5
            if tb >= DUR - .5: break
            b = tone(mid(root + (12 if i % 2 else 0)), .45, "saw", 5); b = lp(b, .06)
            add(music, tb, b, .55)
        t += 2
    arp = [0, 7, 12, 16, 12, 7, 15, 12]
    t = 8.0
    while t < 16.4:
        bar = int((t - 3.2) / 2) % 4; root = prog_[bar] + 36
        for i in range(8):
            ta = t + i * .125
            if ta >= 16.4: break
            add(music, ta, tone(mid(root + arp[i]), .14, "sq", 22), .06)
        t += 1.0
    # pads
    for tc, notes in ((3.2, (57, 60, 64)), (17.3, (57, 61, 64, 69))):
        for m in notes: add(music, tc, tone(mid(m), 3, "saw", .8) * .5, .05)
    # risers + impacts
    def riser(t_end, d, g=.35):
        x = X(d); sw = np.sin(2 * np.pi * np.cumsum(200 + 2400 * (x / d) ** 2) / SR) * (x / d) ** 2
        nz = hp(rs.randn(len(x)).astype(np.float32), .2) * (x / d) ** 3
        add(y, t_end - d, ((sw + nz) * g).astype(np.float32))
    riser(3.2, 1.7); riser(4.0, .8, .2); riser(8.0, 1.9); riser(13.0, 1.4); riser(16.5, 1.5, .4)
    def boom(t0, g=.8):
        x = X(1.4); add(y, t0, (np.sin(2 * np.pi * (38 + 60 * np.exp(-6 * x)) * x) * np.exp(-3.2 * x)).astype(np.float32), g)
        add(y, t0, (hp(rs.randn(len(x)).astype(np.float32), .3) * np.exp(-5 * x)).astype(np.float32), .35)
    for c in BIG: boom(c)
    for c in CUTS:
        if c not in BIG:
            x = X(.22); add(y, c, (hp(rs.randn(len(x)).astype(np.float32), .25) * np.exp(-12 * x)).astype(np.float32), .3)
            add(y, c, (np.sin(2 * np.pi * (300 + 600 * np.exp(-30 * x)) * x) * np.exp(-14 * x)).astype(np.float32), .18)
    # typing: intro + code
    for tc in np.arange(.1, 1.4, .05): add(y, tc, tone(900 + rs.rand() * 400, .025, "sq", 50), .05)
    for c in range(CODE_TOTAL):
        tc = T_CODE0 + (T_CODE1 - T_CODE0) * c / CODE_TOTAL
        add(y, tc, (rs.randn(int(SR * .02)) * np.exp(-np.arange(int(SR * .02)) / SR * 220)).astype(np.float32), .12)
    # sidechain pump on music, mix
    pump = 1 - .55 * np.exp(-((tt - 1.5) % BEAT) * 9)
    mix = y + drums + music * pump * (tt >= 3.2)
    mix *= np.minimum(1, tt / .15) * np.minimum(1, (DUR - tt) / .9)
    mix = np.tanh(mix * 1.4) * .85
    st = np.stack([mix, mix], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

def main():
    random.seed(3); np.random.seed(3)
    wav = OUT + ".wav"; make_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-profile:v", "main", "-level", "4.0", "-g", "60", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
           "-movflags", "+faststart", "-t", str(DUR), OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    only = os.environ.get("ONLY")
    for f in range(N):
        t = f / FPS
        p.stdin.write(post(scene(t), t, f).tobytes())
        if f % 60 == 0: print("frame", f, "/", N, flush=True)
    p.stdin.close(); p.wait(); os.remove(wav); print("done", OUT)

if __name__ == "__main__":
    main()
