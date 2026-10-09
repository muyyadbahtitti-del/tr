"""Generates dev_intro.mp4 — a 20s animated intro of a 27-year-old developer.
1280x720 @30fps, H.264 + AAC (X/Twitter compatible). Usage: python3 make_video.py out.mp4
"""
import math, random, subprocess, sys, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H, FPS, DUR = 1280, 720, 30, 20.0
N = int(FPS * DUR)
OUT = sys.argv[1] if len(sys.argv) > 1 else "dev_intro.mp4"
TMP = os.path.dirname(os.path.abspath(OUT))

MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F = lambda p, s: ImageFont.truetype(p, s)
f_code, f_small, f_title = F(MONO, 24), F(MONO_B, 20), F(MONO_B, 40)
f_chip, f_huge, f_big = F(SANS_B, 30), F(MONO_B, 260), F(MONO_B, 64)
f_term = F(MONO_B, 54)

CYAN, PINK, PURPLE, GREEN, YELLOW = (60, 230, 255), (255, 70, 170), (140, 100, 255), (80, 255, 150), (255, 210, 90)
rnd = random.Random(7)


def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def ease_out(x): return 1 - (1 - x) ** 3
def ease_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def mix(c1, c2, k): return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))


# ---------- static assets ----------
yy = np.linspace(0, 1, H)[:, None, None]
bg = (np.array([10, 8, 30]) * (1 - yy) + np.array([28, 12, 56]) * yy) * np.ones((H, W, 3))
BG = bg.astype(np.uint8)
xx, yv = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
VIG = (1 - 0.55 * np.clip(xx ** 2 * 0.6 + yv ** 2 * 0.9, 0, 1))[..., None]
SCAN = np.ones((H, W, 1)); SCAN[::3] = 0.9

particles = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(15, 60), rnd.uniform(1.5, 4), rnd.choice([CYAN, PINK, PURPLE])) for _ in range(70)]
rain = [(x, rnd.uniform(60, 220), rnd.uniform(0, H), "".join(rnd.choice("01<>{}/;=+*") for _ in range(14))) for x in range(0, W, 34)]
floaters = [(rnd.uniform(0, 560), rnd.uniform(0, 500), rnd.uniform(0.5, 1.5), rnd.choice(["</>", "{ }", ";", "=>", "[]", "01", "#", "&&"]), rnd.uniform(0, 6)) for _ in range(9)]

CODE = [
    [("class ", PINK), ("Developer", YELLOW), (":", (230, 230, 240))],
    [("    age ", (230, 230, 240)), ("= ", PINK), ("27", PURPLE)],
    [("    skills ", (230, 230, 240)), ("= ", PINK), ('["Python", "JS", "AI"]', GREEN)],
    [("", None)],
    [("    def ", PINK), ("run", CYAN), ("(self):", (230, 230, 240))],
    [("        while ", PINK), ("True", PURPLE), (":", (230, 230, 240))],
    [("            code", CYAN), ("()", (230, 230, 240))],
    [("            coffee", CYAN), ("()", (230, 230, 240))],
    [("            ship", CYAN), ("()  ", (230, 230, 240)), ("# \U0001f680".replace("\U0001f680", "again"), (120, 130, 160))],
]
CODE_TOTAL = sum(len("".join(s for s, _ in l)) for l in CODE)
T_CODE0, T_CODE1 = 4.6, 12.4
def chars_at(t): return int(CODE_TOTAL * prog(t, T_CODE0, T_CODE1))

CHIPS = [("Python", CYAN), ("JavaScript", YELLOW), ("AI / ML", PINK), ("Cloud", PURPLE), ("Open Source", GREEN)]
CHIP_POS = [(700, 520), (900, 520), (700, 590), (850, 590), (990, 590)]
T_CHIP0 = 12.4

def text_c(d, xy, s, font, fill, anchor="mm"): d.text(xy, s, font=font, fill=fill, anchor=anchor)

def glow_text(img, xy, s, font, fill, glow=None, radius=10, anchor="mm"):
    glow = glow or fill
    layer = Image.new("RGB", img.size, (0, 0, 0))
    ImageDraw.Draw(layer).text(xy, s, font=font, fill=glow, anchor=anchor)
    layer = layer.filter(ImageFilter.GaussianBlur(radius))
    img.paste(ImageChops.add(img, layer))
    ImageDraw.Draw(img).text(xy, s, font=font, fill=fill, anchor=anchor)


# ---------- background ----------
def draw_bg(t):
    img = Image.fromarray(BG)
    d = ImageDraw.Draw(img, "RGBA")
    # perspective-ish moving grid
    off = (t * 40) % 60
    for i in range(-2, 24):
        y = 420 + i * 60 + off
        if 380 < y < H: d.line([(0, y), (W, y)], fill=(120, 80, 255, int(70 * (y - 380) / 340)), width=1)
    for i in range(-12, 13):
        d.line([(W / 2 + i * 30, 380), (W / 2 + i * 190, H)], fill=(120, 80, 255, 55), width=1)
    # code rain
    for x, sp, y0, s in rain:
        for k, ch in enumerate(s):
            y = (y0 + t * sp + k * 26) % (H + 380) - 190
            a = int(70 * (k / len(s)) ** 2)
            d.text((x, y), ch, font=f_small, fill=(60, 230, 255, a))
    for x, y, sp, r, c in particles:
        yp = (y - t * sp) % H
        xp = x + math.sin(t + x) * 12
        d.ellipse([xp - r, yp - r, xp + r, yp + r], fill=c + (120,))
    return img


# ---------- character ----------
def draw_character(t, fade):
    S = 2
    lay = Image.new("RGBA", (600 * S, 520 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    s = lambda *a: [v * S for v in a]
    b = math.sin(t * 4) * 3
    skin, hair, hood = (240, 200, 170), (35, 28, 30), (95, 75, 215)
    # floating glyphs
    for fx, fy, sp, g, ph in floaters:
        y = (fy - t * 20 * sp) % 480
        d.text((fx * S, y * S), g, font=F(MONO_B, 26 * S), fill=CYAN + (int(110 + 60 * math.sin(t * 2 + ph)),))
    # desk
    d.rectangle(s(0, 440, 600, 520), fill=(26, 28, 56, 255))
    d.rectangle(s(0, 438, 600, 443), fill=PINK + (255,))
    # body + hood
    d.rounded_rectangle(s(170, 290 + b * .4, 430, 470), radius=80 * S, fill=hood + (255,))
    d.ellipse(s(235, 262 + b * .5, 365, 320 + b * .5), fill=mix(hood, (0, 0, 0), .25) + (255,))
    d.line(s(285, 320 + b, 280, 375 + b), fill=(235, 235, 245, 255), width=3 * S)
    d.line(s(315, 320 + b, 320, 375 + b), fill=(235, 235, 245, 255), width=3 * S)
    # neck + head
    d.rectangle(s(272, 245 + b, 328, 285 + b), fill=mix(skin, (0, 0, 0), .15) + (255,))
    d.ellipse(s(236, 128 + b, 364, 268 + b), fill=skin + (255,))
    d.ellipse(s(228, 190 + b, 246, 222 + b), fill=skin + (255,)); d.ellipse(s(354, 190 + b, 372, 222 + b), fill=skin + (255,))
    # beard (stubble) + hair
    d.pieslice(s(238, 190 + b, 362, 282 + b), 0, 180, fill=(72, 52, 46, 255))
    d.ellipse(s(262, 212 + b, 338, 250 + b), fill=skin + (255,))
    d.pieslice(s(230, 116 + b, 370, 236 + b), 180, 360, fill=hair + (255,))
    for hx in range(244, 360, 22):
        d.ellipse(s(hx - 6, 112 + b - (hx % 3) * 4, hx + 24, 150 + b), fill=hair + (255,))
    # mouth (smile grows slowly)
    d.arc(s(276, 205 + b, 324, 238 + b), 20, 160, fill=(250, 245, 240, 255), width=4 * S)
    # eyes + blink
    blink = (t % 3.2) > 3.05
    eh = 2 if blink else 13
    for ex in (275, 325):
        d.ellipse(s(ex - 7, 190 + b - eh / 2, ex + 7, 190 + b + eh / 2), fill=(25, 25, 40, 255))
    # glasses
    for ex in (275, 325):
        d.rounded_rectangle(s(ex - 25, 170 + b, ex + 25, 210 + b), radius=12 * S, outline=CYAN + (255,), width=4 * S)
    d.line(s(300, 188 + b, 300, 188 + b), fill=CYAN + (255,), width=4 * S)
    d.line(s(298, 186 + b, 302, 186 + b), fill=CYAN + (255,), width=4 * S)
    gl = (t * 0.5) % 1
    gx = 255 + gl * 40
    d.line(s(gx, 176 + b, gx + 8, 168 + b + 6), fill=(255, 255, 255, int(200 * math.sin(gl * math.pi))), width=3 * S)
    # headphones
    d.arc(s(222, 110 + b, 378, 270 + b), 195, 345, fill=(55, 58, 90, 255), width=10 * S)
    for ex in (222, 378):
        d.rounded_rectangle(s(ex - 18, 175 + b, ex + 18, 230 + b), radius=12 * S, fill=PINK + (255,))
        d.rounded_rectangle(s(ex - 9, 183 + b, ex + 9, 222 + b), radius=7 * S, fill=(30, 20, 50, 255))
    # laptop lid (back) with glowing logo + base
    d.polygon(s(150, 470, 450, 470, 470, 495, 130, 495), fill=(70, 74, 108, 255))
    d.rounded_rectangle(s(195, 335, 405, 462), radius=14 * S, fill=(52, 56, 86, 255))
    pulse = 0.6 + 0.4 * math.sin(t * 3)
    d.ellipse(s(278, 372, 322, 416), fill=mix((60, 60, 90), CYAN, pulse) + (255,))
    # arms + hands typing
    for side, hx in ((-1, 190), (1, 410)):
        bounce = math.sin(t * 17 + (0 if side < 0 else 1.7)) * 6
        d.line(s(300 + side * 105, 310 + b * .5, hx, 455 + bounce), fill=hood + (255,), width=40 * S)
        d.ellipse(s(hx - 22, 442 + bounce, hx + 22, 478 + bounce), fill=skin + (255,))
    # coffee mug + steam
    d.rounded_rectangle(s(500, 398, 548, 442), radius=8 * S, fill=(235, 235, 245, 255))
    d.arc(s(538, 405, 566, 435), 270, 90, fill=(235, 235, 245, 255), width=5 * S)
    d.rectangle(s(500, 398, 548, 408), fill=(110, 70, 50, 255))
    for k in range(3):
        for j in range(8):
            ph = t * 2.2 + k * 1.3 + j * .4
            sx = 512 + k * 12 + math.sin(ph) * 5
            sy = 392 - j * 9 - ((t * 20 + k * 10) % 18)
            d.ellipse(s(sx - 2, sy - 2, sx + 2, sy + 2), fill=(255, 255, 255, int(110 - j * 13)))
    lay = lay.resize((600, 520), Image.LANCZOS)
    if fade < 1:
        a = lay.getchannel("A").point(lambda v: int(v * fade)); lay.putalpha(a)
    return lay


# ---------- scenes ----------
def terminal_text(img, t):
    d = ImageDraw.Draw(img)
    l1, l2 = "> hello, world", "> age = 27"
    n1 = int(len(l1) * prog(t, 0.3, 1.5)); n2 = int(len(l2) * prog(t, 1.7, 2.6))
    x0 = 330
    d.text((x0, 270), l1[:n1], font=f_term, fill=GREEN)
    cur = "_" if int(t * 3) % 2 == 0 else " "
    if t < 1.7: d.text((x0 + 33 * n1, 270), cur, font=f_term, fill=GREEN)
    if t >= 1.7:
        d.text((x0, 360), l2[:n2], font=f_term, fill=CYAN)
        if n2 < len(l2) or int(t * 3) % 2 == 0: d.text((x0 + 33 * n2, 360), "_", font=f_term, fill=CYAN)


def scene_intro(img, t):
    terminal_text(img, t)
    if t > 2.8:
        k = ease_back(prog(t, 2.8, 3.3)); sh = (3.6 - t) * 14 if t > 3.3 else 0
        n = int(27 * prog(t, 2.8, 3.2))
        sz = max(1, int(260 * k))
        glow_text(img, (W // 2 + random.uniform(-sh, sh), 560 + random.uniform(-sh, sh)), "%d" % n, F(MONO_B, sz), PINK, PINK, 18)


def scene_main(img, t):
    k = t - 3.6
    # character slides in
    cx = -620 + 660 * ease_out(prog(k, 0, .9))
    cx = int(cx); cy = 175
    ch = draw_character(t, 1)
    img.paste(ch, (cx, cy), ch)
    d = ImageDraw.Draw(img, "RGBA")
    # title
    ta = ease_out(prog(k, .5, 1.3))
    glow_text(img, (W // 2 + int((1 - ta) * -200), 80), "27 · DEVELOPER", f_big, (255, 255, 255), PINK, 14)
    d = ImageDraw.Draw(img, "RGBA")
    # code window
    wa = ease_back(prog(t, 4.0, 4.7))
    if wa > 0:
        wx, wy, ww, wh = 660, 160, 580, 330
        sc = clamp(wa, 0, 1.15)
        cxm, cym = wx + ww / 2, wy + wh / 2
        win = Image.new("RGBA", (ww, wh), (0, 0, 0, 0))
        wd = ImageDraw.Draw(win)
        wd.rounded_rectangle([0, 0, ww - 1, wh - 1], radius=16, fill=(18, 16, 40, 235), outline=CYAN + (200,), width=2)
        wd.rounded_rectangle([0, 0, ww - 1, 40], radius=16, fill=(40, 36, 80, 255))
        for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))): wd.ellipse([18 + i * 26, 13, 34 + i * 26, 29], fill=c)
        wd.text((ww / 2, 21), "developer.py", font=f_small, fill=(170, 175, 210), anchor="mm")
        left = chars_at(t); y = 58; cur = None
        for line in CODE:
            x = 18
            for seg, col in line:
                part = seg[:left]; left -= len(part)
                if part: wd.text((x, y), part, font=f_code, fill=col or (230, 230, 240))
                x += 14.4 * len(part)
                if left <= 0 and cur is None: cur = (x, y)
            if cur is not None: break
            y += 29
        if cur is None: cur = (18, y)
        if t < T_CODE1 + 0.3 or int(t * 4) % 2 == 0:
            wd.rectangle([cur[0] + 2, cur[1] + 2, cur[0] + 12, cur[1] + 28], fill=CYAN)
        win = win.resize((max(1, int(ww * sc)), max(1, int(wh * sc))), Image.LANCZOS)
        img.paste(win, (int(cxm - win.width / 2), int(cym - win.height / 2)), win)
    # skill chips
    for i, ((name, col), (px, py)) in enumerate(zip(CHIPS, CHIP_POS)):
        a = ease_back(prog(t, T_CHIP0 + i * .45, T_CHIP0 + i * .45 + .45))
        if a <= 0: continue
        w = int(f_chip.getlength(name)) + 40
        chip = Image.new("RGBA", (w, 46), (0, 0, 0, 0))
        cd = ImageDraw.Draw(chip)
        cd.rounded_rectangle([0, 0, w - 1, 45], radius=23, fill=col + (50,), outline=col + (255,), width=3)
        cd.text((w / 2, 23), name, font=f_chip, fill=(255, 255, 255), anchor="mm")
        chip = chip.resize((max(1, int(w * a)), max(1, int(46 * a))), Image.LANCZOS)
        bob = math.sin(t * 2 + i) * 4
        img.paste(chip, (int(px - chip.width / 2) + 0, int(py - chip.height / 2 + bob)), chip)


def scene_outro(img, t):
    k = t - 16.0
    ov = Image.new("RGBA", (W, H), (8, 6, 24, int(225 * ease_out(prog(k, 0, .6)))))
    img.paste(ov, (0, 0), ov)
    if k > .5:
        n = int(12 * prog(k, .5, 1.5)); glow_text(img, (W // 2, 270), ("27 YEARS OLD"[:n] or " "), f_big, (255, 255, 255), CYAN, 14)
    if k > 1.8:
        s = "STILL COMPILING..."; n = int(len(s) * prog(k, 1.8, 2.8))
        glow_text(img, (W // 2, 370), s[:n], F(MONO_B, 50), PINK, PINK, 12)
    if k > 3.0:
        a = ease_back(prog(k, 3.0, 3.6))
        glow_text(img, (W // 2, 480), "LET'S BUILD SOMETHING.", F(MONO_B, max(8, int(46 * a))), GREEN, GREEN, 12)


# ---------- post effects ----------
GLITCH_AT = [3.55, 8.2, 12.4, 15.95, 18.9]
def glitch(arr, t, f):
    for g in GLITCH_AT:
        if 0 <= t - g < 0.25:
            r = random.Random(f)
            amt = int(14 + 14 * r.random())
            arr = arr.copy()
            for _ in range(7):
                y0 = r.randint(0, H - 60); h = r.randint(6, 55); sh = r.randint(-70, 70)
                arr[y0:y0 + h] = np.roll(arr[y0:y0 + h], sh, axis=1)
            arr[..., 0] = np.roll(arr[..., 0], amt, axis=1)
            arr[..., 2] = np.roll(arr[..., 2], -amt, axis=1)
    return arr

def post(img, t, f):
    sm = img.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR)
    img = ImageChops.screen(img, sm.point(lambda v: int(v * .55)))
    arr = np.asarray(img).astype(np.float32)
    arr *= VIG * SCAN
    arr += np.random.RandomState(f).randn(H, W, 1) * 3
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    arr = glitch(arr, t, f)
    fade = min(prog(t, 0, .5), 1 - prog(t, DUR - .6, DUR))
    return (arr * fade).astype(np.uint8)


# ---------- audio ----------
def make_audio(path):
    sr = 44100; n = int(sr * DUR)
    y = np.zeros(n, np.float32)
    tt = np.arange(n) / sr
    def add(t0, sig, gain=1.0):
        i = int(t0 * sr); j = min(n, i + len(sig))
        if i < n: y[i:j] += sig[:j - i] * gain
    def tone(freq, dur, kind="saw", env=8):
        x = np.arange(int(sr * dur)) / sr
        if kind == "saw": s = 2 * ((x * freq) % 1) - 1
        elif kind == "sq": s = np.sign(np.sin(2 * np.pi * freq * x))
        else: s = np.sin(2 * np.pi * freq * x)
        return (s * np.exp(-env * x) * np.minimum(1, x * 400)).astype(np.float32)
    bpm = 120; beat = 60 / bpm
    notes = [57, 60, 64, 67, 55, 59, 62, 67, 53, 57, 60, 64, 55, 59, 62, 66]  # Am, G, F, G(maj-ish)
    mid = lambda m: 440 * 2 ** ((m - 69) / 12)
    t = 0; i = 0
    while t < DUR - .1:
        if t >= 3.5:
            m = notes[(int((t - 3.5) / (beat * 4)) % 4) * 4 + (i % 4)]
            add(t, tone(mid(m + 12), .35, "sq", 9), .06)
            if i % 2 == 0: add(t, tone(mid(m - 24), .5, "sin", 4), .22)
        t += beat / 2; i += 1
    # kick every beat from 3.5
    t = 3.5
    while t < DUR - .3:
        x = np.arange(int(sr * .25)) / sr
        add(t, (np.sin(2 * np.pi * (110 * np.exp(-14 * x) + 40) * x) * np.exp(-12 * x)).astype(np.float32), .45)
        t += beat
    # intro bleeps while typing
    for tc in np.arange(.3, 1.5, .06): add(tc, tone(900 + random.random() * 300, .03, "sq", 40), .05)
    for tc in np.arange(1.7, 2.6, .06): add(tc, tone(900 + random.random() * 300, .03, "sq", 40), .05)
    # code typing clicks
    for c in range(CODE_TOTAL):
        tc = T_CODE0 + (T_CODE1 - T_CODE0) * (c / CODE_TOTAL)
        noise = (np.random.randn(int(sr * .02)) * np.exp(-np.arange(int(sr * .02)) / sr * 220)).astype(np.float32)
        add(tc, noise, .12)
    # impacts / whooshes at glitches and chips
    for g in GLITCH_AT:
        x = np.arange(int(sr * .4)) / sr
        add(g, (np.random.randn(len(x)) * np.exp(-9 * x) * np.sin(2 * np.pi * 40 * x)).astype(np.float32), .35)
        add(g, tone(1200, .15, "sq", 20), .06)
    for i2 in range(5): add(T_CHIP0 + i2 * .45, tone(520 + i2 * 130, .2, "sin", 10), .25)
    x = np.arange(int(sr * 1.2)) / sr
    add(2.8, (np.random.randn(len(x)) * np.minimum(1, x * 3) * np.exp(-3 * x)).astype(np.float32), .08)
    # final chord
    for m in (57, 64, 69, 72): add(18.4, tone(mid(m), 1.5, "saw", 2.2), .06)
    y *= np.minimum(1, tt / .4) * np.minimum(1, (DUR - tt) / .8)
    y = np.tanh(y * 1.6) * .8
    st = np.stack([y, y], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def main():
    random.seed(3); np.random.seed(3)
    wav = os.path.join(TMP, "_audio.wav")
    make_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(DUR), OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(N):
        t = f / FPS
        img = draw_bg(t)
        if t < 3.6: scene_intro(img, t)
        else:
            scene_main(img, t)
            if t >= 16.0: scene_outro(img, t)
        p.stdin.write(post(img, t, f).tobytes())
        if f % 60 == 0: print("frame", f, "/", N, flush=True)
    p.stdin.close(); p.wait(); os.remove(wav)
    print("done", OUT)

if __name__ == "__main__":
    main()
