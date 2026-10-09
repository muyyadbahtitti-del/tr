"""ai_video.mp4 - 30s beat-synced video about AI, X-ready (H.264 Main, AAC 44.1k, 1280x720@30).
Reuses the montage toolkit from make_video_v2.py.   Usage: python3 make_ai_video.py out.mp4
"""
import math, random, subprocess, sys, os, wave
import numpy as np
from PIL import Image, ImageDraw
from scipy.signal import lfilter
import make_video_v2 as v
from make_video_v2 import (W, H, FPS, CYAN, PINK, PURPLE, GREEN, YELLOW, WHITE, font, MONO_B, MONO, SANS_B,
                           prog, eo, eio, back, lerp, slam, tlayer, put, draw_hero, rays, speedlines, ring, shockwave, bg_fx)

DUR = 30.0
N = int(FPS * DUR)
OUT = sys.argv[1] if len(sys.argv) > 1 else "ai_video.mp4"
NAME = "MUAYYAD"
v.DUR = DUR
BIG = [2.5, 9.0, 16.0, 23.0, 27.0]
v.BIG = BIG
v.CUTS = sorted(BIG + [4.0, 5.5, 7.0, 8.0, 17.75, 19.5, 21.25, 24.0, 25.0, 26.0])
DARK = (10, 8, 30)

def fit(text, mx=340, width=1150): return min(mx, int(width / (0.6 * len(text))))

# ---------------- 0-2.5 hook ----------------
HOOK = [(0.3, "AI", WHITE, PINK), (0.8, "IS", WHITE, CYAN), (1.2, "CHANGING", YELLOW, PINK), (1.75, "EVERYTHING.", WHITE, PINK)]
def shot_hook(img, t):
    bg_fx(img, t, grid=False, rainA=80)
    cur = None
    for h in HOOK:
        if t >= h[0]: cur = h
    if cur:
        t0, w, col, st = cur
        slam(img, w, (640, 340), font(MONO_B, fit(w)), col, t, t0, 8, st, dur=.1)
        if t < t0 + .15: shockwave(img, 640, 340, t, t0, col)
    if t > 2.0:
        slam(img, "IN 30 SECONDS", (640, 560), font(MONO_B, 60), CYAN, t, 2.05, 4, (10, 10, 40))

# ---------------- 2.5-9 history ----------------
EVENTS = [(1956, "AI IS BORN", "THE TERM 'ARTIFICIAL INTELLIGENCE' IS COINED", 2.5),
          (1997, "MACHINE BEATS KASPAROV", "DEEP BLUE WINS AT CHESS", 4.0),
          (2016, "ALPHAGO BEATS LEE SEDOL", "AI MASTERS THE GAME OF GO", 5.5),
          (2017, "TRANSFORMERS", "'ATTENTION IS ALL YOU NEED'", 7.0),
          (2022, "CHATGPT", "AI GOES MAINSTREAM", 8.0)]
def shot_history(img, t):
    bg_fx(img, t, grid=True, rainA=70)
    idx = max(i for i, e in enumerate(EVENTS) if t >= e[3])
    yr, title, sub, t0 = EVENTS[idx]
    cols = [PINK, CYAN, PURPLE, YELLOW, GREEN]
    rays(img, t, 640, 300, cols[idx], 40, 12)
    # timeline bar
    d = ImageDraw.Draw(img, "RGBA")
    xs = [140 + i * 250 for i in range(5)]
    d.line([(140, 70), (1140, 70)], fill=(255, 255, 255, 70), width=3)
    px = lerp(xs[idx - 1] if idx else 140, xs[idx], eo(prog(t, t0, t0 + .3))) if idx else 140
    d.line([(140, 70), (px, 70)], fill=cols[idx] + (255,), width=5)
    for i, (y2, *_r) in enumerate(EVENTS):
        on = i <= idx
        d.ellipse([xs[i] - 9, 61, xs[i] + 9, 79], fill=(cols[i] if on else (90, 90, 130)) + (255,))
        d.text((xs[i], 105), str(y2), font=font(MONO_B, 22), fill=(255, 255, 255, 255 if on else 110), anchor="mm")
    # year with scramble
    k = t - t0
    if k < .3: txt = "".join(str(random.Random(int(t * 60) + j).randint(0, 9)) for j in range(4))
    else: txt = str(yr)
    slam(img, txt, (640, 300), font(MONO_B, 270), WHITE, t, t0, 7, cols[idx], dur=.12)
    slam(img, title, (640, 505), font(MONO_B, min(54, int(1180 / (.6 * len(title))))), cols[idx], t, t0 + .12, 4, (10, 10, 40))
    slam(img, sub, (640, 580), font(MONO_B, 26), (225, 225, 245), t, t0 + .3, 0)
    if k < .15: speedlines(img, int(t * 30), 640, 300, 1.0)
    shockwave(img, 640, 300, t, t0, cols[idx])

# ---------------- 9-16 how it works ----------------
LAYERS = [(220, 4), (450, 6), (640, 7), (830, 6), (1060, 3)]
NODES = [[(x, 160 + (i + .5) * (350 / n)) for i in range(n)] for x, n in LAYERS]
PROMPT = "write me a poem about the sea"
ANSWER = ["The sea breathes in silver light,", "waves write names upon the sand,", "and every tide is a new draft."]
T_P0, T_P1, T_A0, T_A1 = 9.7, 11.4, 12.0, 15.4
def mix(c1, c2, k): return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))

def shot_network(img, t):
    bg_fx(img, t, grid=False, rainA=40)
    act = prog(t, 9.3, 11.8) * .8 + .2
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for li in range(4):
        for ai, a in enumerate(NODES[li]):
            for bi, b in enumerate(NODES[li + 1]):
                hsh = (li * 37 + ai * 11 + bi * 7) % 17 / 17
                d.line([a, b], fill=CYAN + (int(22 + 40 * act * hsh),), width=1)
                ph = (t * 1.1 + hsh * 3 + li * .3) % 1
                if hsh * act > .25:
                    px, py = lerp(a[0], b[0], ph), lerp(a[1], b[1], ph)
                    d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=mix(CYAN, PINK, ph) + (230,))
    sweep = (t * 1.6) % 3.2
    for li, col in enumerate(NODES):
        la = max(0, 1 - abs(sweep - li * .7) * 1.4) * act
        for (x, y) in col:
            r = 12 + 9 * la
            d.ellipse([x - r - 8, y - r - 8, x + r + 8, y + r + 8], fill=PINK + (int(70 * la),))
            d.ellipse([x - r, y - r, x + r, y + r], fill=mix((30, 40, 90), WHITE if li == 4 else CYAN, .35 + .65 * la) + (255,), outline=CYAN + (255,), width=2)
    img.paste(ov, (0, 0), ov)
    for x, lab in ((220, "PROMPT"), (640, "THE MODEL"), (1060, "ANSWER")):
        slam(img, lab, (x, 112), font(MONO_B, 26), (200, 205, 240), t, 9.15, 0)
    slam(img, "HOW IT WORKS", (640, 56), font(MONO_B, 54), WHITE, t, 9.05, 4, PINK)
    # prompt + streamed answer
    n = int(len(PROMPT) * prog(t, T_P0, T_P1))
    dd = ImageDraw.Draw(img, "RGBA")
    dd.rounded_rectangle([110, 545, 1170, 590], radius=12, fill=(20, 16, 50, 220), outline=CYAN + (255,), width=2)
    dd.text((130, 567), "> " + PROMPT[:n] + ("_" if int(t * 3) % 2 == 0 and t < T_A0 else ""), font=font(MONO_B, 26), fill=GREEN, anchor="lm")
    total = sum(len(s) for s in ANSWER); left = int(total * prog(t, T_A0, T_A1))
    for i, line in enumerate(ANSWER):
        part = line[:max(0, left)]; left -= len(line)
        if part: dd.text((130, 625 + i * 33), part, font=font(MONO, 26), fill=(255, 235, 255), anchor="lm")

# ---------------- 16-23 what AI does now ----------------
CARDS = [("CODE", "WRITES CODE", PINK, 16.0), ("IMAGES", "PAINTS IMAGES", PURPLE, 17.75),
         ("MUSIC", "COMPOSES MUSIC", GREEN, 19.5), ("VIDEO", "MAKES VIDEO", YELLOW, 21.25)]
def card_visual(kind, t, cw, ch):
    im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if kind == "CODE":
        r = random.Random(3); y = 20; shown = int(14 * prog(t % 100, 0, 1) * 0)
        cols = [PINK, CYAN, YELLOW, GREEN, WHITE]
        for i in range(10):
            x = 20 + (i % 3 == 1) * 40 + (i % 4 == 2) * 40
            for _ in range(r.randint(2, 4)):
                wd = r.randint(40, 150); c = r.choice(cols)
                k = prog(t, i * .1, i * .1 + .35)
                d.rounded_rectangle([x, y, x + wd * k, y + 14], radius=5, fill=c + (230,)); x += wd + 12
            y += 30
        if int(t * 4) % 2 == 0: d.rectangle([cw - 60, 20, cw - 48, 44], fill=CYAN)
    elif kind == "IMAGES":
        gw, gh = 48, 24
        xx, yy = np.meshgrid(np.linspace(0, 6, gw), np.linspace(0, 3, gh))
        a = np.sin(xx + t * 2) + np.sin(yy * 1.7 - t * 1.6) + np.sin((xx + yy) * .9 + t)
        r_ = (128 + 127 * np.sin(a + 0)).astype(np.uint8); g_ = (128 + 127 * np.sin(a + 2.1)).astype(np.uint8); b_ = (128 + 127 * np.sin(a + 4.2)).astype(np.uint8)
        im2 = Image.fromarray(np.dstack([r_, g_, b_])).resize((cw - 20, ch - 20), Image.BICUBIC)
        m = Image.new("L", im2.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im2.width - 1, im2.height - 1], radius=16, fill=255)
        im.paste(im2, (10, 10), m)
    elif kind == "MUSIC":
        nb = 30; bw = (cw - 20) / nb
        for i in range(nb):
            h = (.25 + .75 * abs(math.sin(t * 5 + i * .6) * math.cos(t * 2.3 + i * .21))) * (ch - 20)
            c = mix(CYAN, PINK, i / nb)
            d.rounded_rectangle([10 + i * bw + 2, ch - 10 - h, 10 + (i + 1) * bw - 2, ch - 10], radius=4, fill=c + (255,))
    else:
        d.rounded_rectangle([10, 10, cw - 10, ch - 40], radius=14, fill=(25, 20, 60, 255), outline=WHITE + (180,), width=2)
        for i in range(8):
            x = ((t * 140 + i * 90) % (cw + 80)) - 40
            d.ellipse([x - 30, ch / 2 - 60 + 30 * math.sin(t * 2 + i), x + 30, ch / 2 + 0 + 30 * math.sin(t * 2 + i)], fill=mix(PINK, YELLOW, i / 8) + (150,))
        d.polygon([(cw / 2 - 25, ch / 2 - 55), (cw / 2 - 25, ch / 2 + 15), (cw / 2 + 35, ch / 2 - 20)], fill=WHITE + (235,))
        pr = (t * .35) % 1
        d.rounded_rectangle([10, ch - 24, cw - 10, ch - 14], radius=5, fill=(255, 255, 255, 60))
        d.rounded_rectangle([10, ch - 24, 10 + (cw - 20) * pr, ch - 14], radius=5, fill=YELLOW + (255,))
    return im

def shot_cards(img, t):
    idx = max(i for i, c in enumerate(CARDS) if t >= c[3])
    kind, cap, col, t0 = CARDS[idx]
    bg_fx(img, t, grid=True, rainA=60)
    rays(img, t, 640, 330, col, 38, 12)
    k = t - t0
    cw, ch = 760, 330
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0)); cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, cw - 1, ch - 1], radius=24, fill=(18, 14, 46, 235), outline=col + (255,), width=4)
    vis = card_visual(kind, k, cw - 40, ch - 40); card.paste(vis, (20, 20), vis)
    flip = max(.02, eo(prog(k, 0, .25)))
    put(img, card, (cw / 2, ch / 2), (640, 300), flip * 1.0, 0, 1)
    slam(img, cap, (640, 560), font(MONO_B, 74), WHITE, t, t0 + .1, 5, col)
    slam(img, "AI", (140, 90), font(MONO_B, 54), col, t, t0, 4, (10, 10, 40))
    for i in range(4):
        dd = ImageDraw.Draw(img, "RGBA")
        dd.rounded_rectangle([1000 + i * 55, 70, 1040 + i * 55, 80], radius=4, fill=(CARDS[i][2] if i <= idx else (90, 90, 130)) + (255,))
    if k < .15: speedlines(img, int(t * 30), 640, 300, .9)

# ---------------- 23-27 message ----------------
def shot_message(img, t):
    k = t - 23.0
    beat = int(k / .5)
    bg_fx(img, t, grid=False, rainA=80)
    rays(img, t, 640, 360, [PINK, YELLOW, CYAN][beat % 3], 55, 18)
    speedlines(img, int(t * 30), 640, 360, .7)
    if t < 25.0:
        slam(img, "AI WON'T", (640, 250), font(MONO_B, 150), WHITE, t, 23.1, 7, PINK, dur=.1)
        slam(img, "REPLACE YOU.", (640, 440), font(MONO_B, 120), WHITE, t, 23.6, 7, PINK, dur=.1)
        shockwave(img, 640, 340, t, 23.1, PINK); shockwave(img, 640, 340, t, 23.6, WHITE)
    else:
        slam(img, "SOMEONE USING AI", (640, 230), font(MONO_B, 90), WHITE, t, 25.05, 6, CYAN, dur=.1)
        slam(img, "WILL.", (640, 430), font(MONO_B, 230), YELLOW, t, 25.75, 8, (80, 30, 0), dur=.1)
        shockwave(img, 640, 340, t, 25.75, YELLOW)

# ---------------- 27-30 finale ----------------
def shot_finale(img, t):
    k = t - 27.0
    bg_fx(img, t, plate=.8, rainA=60)
    rays(img, t, 420, 330, PINK, 55, 16)
    speedlines(img, int(t * 30), 420, 360, max(0, 1 - k * 1.3))
    ring(img, 420, 330, 270, CYAN, t, 4, 220, 3, 1); ring(img, 420, 330, 305, PINK, -t, 3, 200, 4, 1.3)
    p = eo(prog(t, 27.0, 27.8))
    draw_hero(img, t, "base", "pink", (500, 500), (lerp(640, 420, p), 380 + math.sin(t * 2) * 6), lerp(1.5, .84, p) * (1 + .03 * v.kick(t)), lerp(-4, 0, p))
    shockwave(img, 420, 330, t, 27.0)
    slam(img, "LEARN IT.", (930, 200), font(MONO_B, 76), WHITE, t, 27.7, 5, PINK)
    slam(img, "BUILD WITH IT.", (930, 295), font(MONO_B, 54), GREEN, t, 28.2, 5, (10, 40, 30))
    slam(img, NAME, (930, 440), font(MONO_B, 96), CYAN, t, 28.7, 6, (10, 20, 60))
    slam(img, "27 · DEVELOPER", (930, 520), font(MONO_B, 36), (230, 230, 250), t, 29.0, 3, (10, 10, 40))

def scene(t):
    img = Image.new("RGB", (W, H), DARK)
    if t < 2.5: shot_hook(img, t)
    elif t < 9.0: shot_history(img, t)
    elif t < 16.0: shot_network(img, t)
    elif t < 23.0: shot_cards(img, t)
    elif t < 27.0: shot_message(img, t)
    else: shot_finale(img, t)
    if 2.5 <= t < 27.0:
        L = tlayer(NAME, font(MONO_B, 30), (255, 255, 255), 3, (30, 10, 70))
        put(img, L, (L.width, L.height / 2), (W - 20, H - 34), 1.0, 0, .85 * prog(t, 2.5, 3.0))
    return img

# ---------------- audio ----------------
SR = 44100
def make_audio(path):
    n = int(SR * DUR); y = np.zeros(n, np.float32); music = np.zeros(n, np.float32); drums = np.zeros(n, np.float32)
    rs = np.random.RandomState(2); tt = np.arange(n) / SR
    def add(buf, t0, sig, g=1.0):
        i = int(t0 * SR)
        if i < 0 or i >= n: return
        j = min(n, i + len(sig)); buf[i:j] += sig[:j - i] * g
    X = lambda d: np.arange(int(SR * d)) / SR
    def tone(fr, d, kind="saw", env=8):
        x = X(d); s = {"saw": 2 * ((x * fr) % 1) - 1, "sq": np.sign(np.sin(2 * np.pi * fr * x)), "sin": np.sin(2 * np.pi * fr * x)}[kind]
        return (s * np.exp(-env * x) * np.minimum(1, x * 300)).astype(np.float32)
    mid = lambda m: 440 * 2 ** ((m - 69) / 12)
    lp = lambda s, a: lfilter([a], [1, -(1 - a)], s).astype(np.float32)
    hp = lambda s, a: (s - lp(s, a)).astype(np.float32)
    x = X(.28); K = (np.sin(2 * np.pi * (45 + 120 * np.exp(-22 * x)) * x) * np.exp(-9 * x)).astype(np.float32)
    t = 2.5
    while t < DUR - .3:
        if not (t >= 8.5 and t < 9.0) and not (t >= 15.5 and t < 16.0) and not (t >= 22.5 and t < 23.0) and not (t >= 26.5 and t < 27.0): add(drums, t, K, .9)
        t += .5
    for tc in (.3, .8, 1.2, 1.75): add(drums, tc, K, .6)
    t = 4.5
    while t < DUR - .5:
        if not (8.5 <= t < 9 or 15.5 <= t < 16 or 22.5 <= t < 23 or 26.5 <= t < 27):
            add(drums, t, (hp(rs.randn(int(SR * .18)).astype(np.float32), .35) * np.exp(-X(.18) * 28)).astype(np.float32), .45)
        t += 1.0
    t = 4.0
    while t < DUR - .5:
        step = .125 if (16 <= t < 23) else .25
        add(drums, t, (hp(rs.randn(int(SR * .05)).astype(np.float32), .6) * np.exp(-X(.05) * 90)).astype(np.float32), .2 if step > .2 else .13)
        t += step
    roots = [33, 29, 31, 28]; t = 2.5
    while t < DUR - .4:
        root = roots[int((t - 2.5) / 2) % 4]
        for i in range(4):
            tb = t + i * .5
            if tb >= DUR - .5: break
            add(music, tb, lp(tone(mid(root + (12 if i % 2 else 0)), .45, "saw", 5), .06), .55)
        t += 2
    arp = [0, 7, 12, 16, 12, 7, 15, 12]; t = 9.0
    while t < 26.5:
        root = roots[int((t - 2.5) / 2) % 4] + 36
        for i in range(8):
            if t + i * .125 < 26.5: add(music, t + i * .125, tone(mid(root + arp[i]), .14, "sq", 22), .06)
        t += 1.0
    for tc, notes in ((2.5, (57, 60, 64)), (9.0, (57, 60, 64, 69)), (27.0, (57, 61, 64, 69))):
        for m in notes: add(music, tc, tone(mid(m), 4 if tc == 27 else 3, "saw", .8) * .5, .05)
    def riser(te, d, g=.35):
        x = X(d); sw = np.sin(2 * np.pi * np.cumsum(200 + 2400 * (x / d) ** 2) / SR) * (x / d) ** 2
        add(y, te - d, ((sw + hp(rs.randn(len(x)).astype(np.float32), .2) * (x / d) ** 3) * g).astype(np.float32))
    for te, d in ((2.5, 1.0), (9.0, 1.5), (16.0, 1.5), (23.0, 1.5), (27.0, 1.2)): riser(te, d)
    def boom(t0, g=.8):
        x = X(1.4); add(y, t0, (np.sin(2 * np.pi * (38 + 60 * np.exp(-6 * x)) * x) * np.exp(-3.2 * x)).astype(np.float32), g)
        add(y, t0, (hp(rs.randn(len(x)).astype(np.float32), .3) * np.exp(-5 * x)).astype(np.float32), .35)
    for c in BIG: boom(c)
    for c in v.CUTS:
        if c not in BIG:
            x = X(.22); add(y, c, (hp(rs.randn(len(x)).astype(np.float32), .25) * np.exp(-12 * x)).astype(np.float32), .3)
            add(y, c, (np.sin(2 * np.pi * (300 + 600 * np.exp(-30 * x)) * x) * np.exp(-14 * x)).astype(np.float32), .18)
    for h in HOOK: add(y, h[0], tone(110, .3, "sin", 6), .5); add(y, h[0], tone(1400, .08, "sq", 30), .08)
    for tc in np.arange(T_P0, T_P1, .06): add(y, tc, tone(900 + rs.rand() * 400, .025, "sq", 50), .06)
    for tc in np.arange(T_A0, T_A1, .05): add(y, tc, (rs.randn(int(SR * .02)) * np.exp(-np.arange(int(SR * .02)) / SR * 220)).astype(np.float32), .1)
    for k in range(4): add(y, CARDS[k][3], tone(500 + k * 150, .25, "sin", 9), .3)
    pump = 1 - .55 * np.exp(-(tt % .5) * 9)
    mix = y + drums + music * pump * (tt >= 2.5)
    mix *= np.minimum(1, tt / .1) * np.minimum(1, (DUR - tt) / .9)
    mix = np.tanh(mix * 1.4) * .85
    st = np.stack([mix, mix], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())

def main():
    random.seed(3); np.random.seed(3)
    wav = OUT + ".wav"; make_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "slow", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-profile:v", "main", "-level", "4.0",
           "-g", "60", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
           "-movflags", "+faststart", "-t", str(DUR), OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(N):
        t = f / FPS
        p.stdin.write(v.post(scene(t), t, f).tobytes())
        if f % 90 == 0: print("frame", f, "/", N, flush=True)
    p.stdin.close(); p.wait(); os.remove(wav); print("done", OUT)

if __name__ == "__main__":
    main()
