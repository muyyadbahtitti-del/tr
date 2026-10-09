"""AI_v3: 30s flat / neo-brutalist sticker-style video about AI, 128 BPM funk-house score.
1280x720@30, H.264 Main + AAC 44.1k (X-ready).   Usage: python3 make_ai_v3.py out.mp4
Rendered at 2x then downscaled for clean edges.  Hero = background-removed avatar (assets/avatar_cut.png).
"""
import math, random, subprocess, sys, os, wave
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
from scipy.signal import lfilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "AI_v3.mp4")
W, H, S, FPS, DUR = 1280, 720, 2, 30, 30.0
N = int(FPS * DUR)
BPM = 128; B = 60 / BPM  # 30s == 64 beats exactly
NAME = "MUAYYAD"

INK, WHITE = (18, 16, 38), (255, 255, 255)
BLUE, ORANGE, YELLOW, MINT, PINK, SKY = (40, 70, 255), (255, 98, 36), (255, 214, 48), (40, 214, 150), (255, 130, 190), (150, 210, 255)
F_BLK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
F_XB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
F_SYM = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
@lru_cache(None)
def font(p, s): return ImageFont.truetype(p, int(s))

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def eo(x): return 1 - (1 - x) ** 3
def back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
def lerp(a, b, k): return a + (b - a) * k
def spring(k, dur=.22, lo=.25): return lo + (1 - lo) * back(prog(k, 0, dur))
def tb(n): return n * B

# ---------------- hero sticker ----------------
_cut = Image.open(os.path.join(HERE, "assets/avatar_cut.png")).convert("RGBA").resize((1000, 1000), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 90, 2))
def _sticker():
    a = _cut.getchannel("A")
    outline = a.filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(1.5)).point(lambda v: 255 if v > 90 else 0)
    ring = Image.new("RGBA", _cut.size, WHITE + (0,)); ring.putalpha(outline)
    edge = outline.filter(ImageFilter.MaxFilter(9)).point(lambda v: 255 if v > 90 else 0)
    ink = Image.new("RGBA", _cut.size, INK + (0,)); ink.putalpha(edge)
    return Image.alpha_composite(Image.alpha_composite(ink, ring), _cut)
STICKER = _sticker()

# ---------------- canvas helpers (all coords in 1280x720 space, drawn at S x) ----------------
class C:
    def __init__(self, color):
        self.im = Image.new("RGB", (W * S, H * S), color); self.d = ImageDraw.Draw(self.im, "RGBA")
    def rect(self, box, fill=None, outline=None, w=0, r=0):
        b = [v * S for v in box]
        if r: self.d.rounded_rectangle(b, radius=r * S, fill=fill, outline=outline, width=int(w * S))
        else: self.d.rectangle(b, fill=fill, outline=outline, width=int(w * S))
    def ell(self, cx, cy, rx, ry=None, fill=None, outline=None, w=0):
        ry = ry or rx
        self.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=fill, outline=outline, width=int(w * S))
    def poly(self, pts, fill=None): self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill)
    def line(self, pts, fill, w): self.d.line([(x * S, y * S) for x, y in pts], fill=fill, width=int(w * S), joint="curve")
    def place(self, layer, pos, scale=1.0, rot=0.0, alpha=1.0):
        """layer is an RGBA image at S x resolution; pos = its center in 1280-space."""
        if alpha <= .01 or scale <= .01: return
        w, h = layer.size; th = math.radians(rot); c, s_ = math.cos(th), math.sin(th)
        hw = (abs(w * c) + abs(h * s_)) * scale / 2 + 2; hh = (abs(w * s_) + abs(h * c)) * scale / 2 + 2
        cx, cy = pos[0] * S, pos[1] * S; x0, y0 = int(cx - hw), int(cy - hh); bw, bh = int(2 * hw), int(2 * hh)
        ox, oy = x0 - cx, y0 - cy
        co = (c / scale, s_ / scale, w / 2 + (ox * c + oy * s_) / scale, -s_ / scale, c / scale, h / 2 + (-ox * s_ + oy * c) / scale)
        out = layer.transform((bw, bh), Image.AFFINE, co, Image.BILINEAR)
        if alpha < 1: out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
        self.im.paste(out, (x0, y0), out)
    def text(self, s, pos, size, fill=INK, fnt=F_BLK, stroke=0, sfill=INK, shadow=0, shcol=INK, scale=1.0, rot=0.0, alpha=1.0):
        self.place(tlayer(s, size, fill, fnt, stroke, sfill, shadow, shcol), pos, scale, rot, alpha)
    def star(self, cx, cy, r, fill, rot=0, pts=5, inner=.45, outline=INK, w=4):
        P = []
        for i in range(pts * 2):
            rr = r if i % 2 == 0 else r * inner; a = rot + i * math.pi / pts - math.pi / 2
            P.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        self.poly(P, fill)
        if outline: self.line(P + [P[0]], outline, w)

@lru_cache(512)
def tlayer(s, size, fill, fnt, stroke, sfill, shadow, shcol):
    f = font(fnt, size * S); sw = stroke * S; sh = shadow * S
    bb = f.getbbox(s, stroke_width=sw); w = bb[2] - bb[0] + sw * 2 + sh + 24; h = int(size * S * 1.35) + sh + sw * 2
    L = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    ox, oy = 12 + sw - bb[0], h / 2 - sh / 2
    if sh: d.text((ox + sh, oy + sh), s, font=f, fill=shcol + (255,), anchor="lm", stroke_width=sw, stroke_fill=shcol + (255,))
    d.text((ox, oy), s, font=f, fill=fill + (255,), anchor="lm", stroke_width=sw, stroke_fill=sfill + (255,))
    return L

def fit(s, mx, width, k=.68): return int(min(mx, width / (k * max(1, len(s)))))

def halftone(c, color, t, alpha=38):
    cols, rows = 32, 18; sx, sy = W / cols, H / rows
    for j in range(rows + 1):
        for i in range(cols + 1):
            x, y = i * sx + (j % 2) * sx / 2 + (t * 12) % sx, j * sy
            dist = math.hypot(x - W / 2, y - H / 2) / 760
            r = 11 * clamp(dist) ** 1.2
            if r > .8: c.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=color + (alpha,))

def pill_name(c, t):
    L = tlayer(NAME, 26, INK, F_BLK, 0, INK, 0, INK)
    w, h = L.width / S + 28, 46
    x1, y1 = W - 20, H - 18
    c.rect((x1 - w + 6, y1 - h + 6, x1 + 6, y1 + 6), fill=INK, r=23)
    c.rect((x1 - w, y1 - h, x1, y1), fill=WHITE, outline=INK, w=4, r=23)
    c.place(L, (x1 - w / 2, y1 - h / 2 - 1))

# ---------------- scenes ----------------
HOOK = [("AI", YELLOW, INK), ("IS", BLUE, WHITE), ("CHANGING", ORANGE, INK), ("EVERYTHING.", MINT, INK)]
def sc_hook(c, t, ref):
    idx = min(3, int(ref / B)); k = t - idx * B
    prev = HOOK[idx - 1][1] if idx else HOOK[0][1]
    c.rect((0, 0, W, H), fill=prev)
    word, col, tc = HOOK[idx]
    r = 1000 * eo(prog(k, 0, .28)) if idx else 1400
    c.ell(W / 2, H / 2, r, fill=col)
    if k < 0: return
    rr = random.Random(idx)
    for j in range(5):
        a = rr.uniform(0, 6.28); d_ = rr.uniform(300, 520); sc = back(prog(k, .05 + j * .03, .3 + j * .03))
        c.star(W / 2 + d_ * math.cos(a) * 1.2, H / 2 + d_ * math.sin(a) * .8, 38 * sc, [PINK, WHITE, YELLOW, INK, SKY][j], rr.uniform(0, 1), 5 if j % 2 else 4, .5, INK, 4)
    c.text(word, (W / 2, H / 2), fit(word, 430, 1120), tc, F_BLK, 0, INK, 14, INK if tc == WHITE else WHITE, spring(k), [-5, 4, -3, 2][idx])

EVENTS = [(1956, "AI IS BORN", "THE TERM ‘ARTIFICIAL INTELLIGENCE’ IS COINED", BLUE),
          (1997, "MACHINE BEATS KASPAROV", "DEEP BLUE WINS AT CHESS", ORANGE),
          (2016, "ALPHAGO BEATS LEE SEDOL", "AI MASTERS THE GAME OF GO", MINT),
          (2022, "CHATGPT", "AI GOES MAINSTREAM", PINK)]
def card_layer(cw, ch, fill=WHITE, shadow=12):
    L = Image.new("RGBA", ((cw + shadow + 8) * S, (ch + shadow + 8) * S), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rounded_rectangle([shadow * S, shadow * S, (cw + shadow) * S, (ch + shadow) * S], radius=26 * S, fill=INK + (255,))
    d.rounded_rectangle([4 * S, 4 * S, (cw + 4) * S, (ch + 4) * S], radius=26 * S, fill=fill + (255,), outline=INK + (255,), width=6 * S)
    return L, d

def ill_history(idx, k):
    cw, ch = 440, 400; L, d = card_layer(cw, ch, WHITE)
    X = lambda v: (v + 4) * S
    if idx == 0:
        d.rounded_rectangle([X(20), X(20), X(cw - 20), X(ch - 20)], radius=14 * S, fill=(30, 70, 60, 255))
        d.text((X(cw / 2), X(ch / 2 - 10)), "A.I.", font=font(F_BLK, 190 * S), fill=WHITE + (255,), anchor="mm")
        wd = 300 * eo(prog(k, .3, .9)); d.line([X(cw / 2 - 150), X(ch / 2 + 90), X(cw / 2 - 150 + wd), X(ch / 2 + 90)], fill=YELLOW + (255,), width=10 * S)
        d.text((X(cw / 2), X(ch - 60)), "1956 · DARTMOUTH", font=font(F_XB, 26 * S), fill=WHITE + (230,), anchor="mm")
    elif idx == 1:
        n = 6; sq = (cw - 60) / n
        for j in range(n):
            for i in range(n):
                d.rectangle([X(30 + i * sq), X(30 + j * sq), X(30 + (i + 1) * sq), X(30 + (j + 1) * sq)], fill=(INK if (i + j) % 2 else (240, 236, 224)) + (255,))
        d.rectangle([X(30), X(30), X(cw - 30), X(ch - 70) if False else X(30 + n * sq)], outline=INK + (255,), width=5 * S)
        bob = abs(math.sin(k * 5)) * 18
        d.text((X(cw / 2), X(ch / 2 - bob)), "♞", font=font(F_SYM, 250 * S), fill=ORANGE + (255,), anchor="mm", stroke_width=6 * S, stroke_fill=INK + (255,))
    elif idx == 2:
        d.rounded_rectangle([X(20), X(20), X(cw - 20), X(ch - 20)], radius=14 * S, fill=(236, 190, 110, 255))
        n = 7; g = (cw - 100) / (n - 1)
        for i in range(n):
            d.line([X(50 + i * g), X(50), X(50 + i * g), X(50 + (n - 1) * g)], fill=INK + (255,), width=3 * S)
            d.line([X(50), X(50 + i * g), X(50 + (n - 1) * g), X(50 + i * g)], fill=INK + (255,), width=3 * S)
        stones = [(3, 3, 0), (2, 3, 1), (3, 2, 1), (4, 3, 0), (3, 4, 1), (4, 2, 0), (2, 4, 0), (5, 3, 1), (4, 4, 1)]
        for si, (a, b, col) in enumerate(stones):
            sc = back(prog(k, .15 + si * .13, .35 + si * .13))
            if sc > 0: d.ellipse([X(50 + a * g) - 22 * S * sc, X(50 + b * g) - 22 * S * sc, X(50 + a * g) + 22 * S * sc, X(50 + b * g) + 22 * S * sc], fill=(INK if col == 0 else WHITE) + (255,), outline=INK + (255,), width=3 * S)
    else:
        d.rounded_rectangle([X(20), X(20), X(cw - 20), X(ch - 20)], radius=14 * S, fill=SKY + (255,))
        for j, (bx, by, bw, bh, col, right) in enumerate([(40, 50, 270, 80, WHITE, False), (110, 160, 290, 100, YELLOW, True)]):
            sc = back(prog(k, .15 + j * .35, .4 + j * .35));
            if sc > 0:
                cx, cy = X(bx + bw / 2), X(by + bh / 2)
                d.rounded_rectangle([cx - bw * S * sc / 2, cy - bh * S * sc / 2, cx + bw * S * sc / 2, cy + bh * S * sc / 2], radius=30 * S, fill=col + (255,), outline=INK + (255,), width=5 * S)
                for q in range(3):
                    h_ = 8 + 6 * max(0, math.sin(k * 8 - q * 1.2))
                    d.ellipse([cx - 40 * S + q * 40 * S - h_ * S, cy - h_ * S, cx - 40 * S + q * 40 * S + h_ * S, cy + h_ * S], fill=INK + (255,))
        d.text((X(cw / 2), X(ch - 70)), "ASK ANYTHING", font=font(F_BLK, 44 * S), fill=INK + (255,), anchor="mm")
    return L

def sc_history(c, t, ref):
    lt = ref - tb(4); idx = min(3, int(lt / (4 * B))); k = t - tb(4) - idx * 4 * B
    yr, title, sub, col = EVENTS[idx]
    c.rect((0, 0, W, H), fill=col); halftone(c, INK, t)
    if k < 0: return
    txt = "".join(str(random.Random(int(t * 60) + j).randint(0, 9)) for j in range(4)) if k < .2 else str(yr)
    c.text(txt, (350, 275), 250, WHITE, F_BLK, 12, INK, 14, INK, spring(k), -3 + 3 * prog(k, 0, .3))
    c.place(ill_history(idx, k), (965, 285), spring(k, .28, .1), 3 + 6 * (1 - eo(prog(k, 0, .4))))
    c.text(title, (640, 530), fit(title, 66, 1100), INK, F_BLK, 0, INK, 0, INK, spring(k - .12))
    c.text(sub, (640, 600), fit(sub, 30, 1000, .62), INK, F_XB, 0, INK, 0, INK, 1, 0, prog(k, .25, .45))
    for i in range(4):
        c.rect((545 + i * 54, 44, 585 + i * 54, 56), fill=INK if i <= idx else None, outline=INK, w=3, r=6)

LAY = [(720, 3), (860, 5), (1000, 5), (1140, 2)]
NODES = [[(x, 150 + (i + .5) * (430 / n)) for i in range(n)] for x, n in LAY]
PROMPT = ["Write me a poem", "about the sea"]
POEM = ["The sea breathes in silver light,", "waves write names upon the sand,", "and every tide is a new draft."]
def sc_network(c, t, ref):
    k = t - tb(20)
    c.rect((0, 0, W, H), fill=BLUE); halftone(c, WHITE, t, 26)
    if k < 0: return
    act = clamp(.25 + prog(k, 0, 5 * B))
    for li in range(3):
        for ai, a in enumerate(NODES[li]):
            for bi, b in enumerate(NODES[li + 1]):
                hs = (li * 31 + ai * 11 + bi * 7) % 13 / 13
                c.line([a, b], WHITE + (int(70 + 80 * hs * act),), 3)
                if hs * act > .3:
                    ph = (k * 1.4 + hs * 4) % 1; px, py = lerp(a[0], b[0], ph), lerp(a[1], b[1], ph)
                    c.rect((px - 6, py - 6, px + 6, py + 6), fill=YELLOW, outline=INK, w=2)
    sweep = (k / B * .5) % 4.5
    for li, col in enumerate(NODES):
        la = clamp(1 - abs(sweep - li * .9) * 1.1) * act
        for (x, y) in col:
            r = 20 + 6 * la
            c.ell(x + 5, y + 5, r, fill=INK)
            c.ell(x, y, r, fill=mix(WHITE, ORANGE if li == 3 else YELLOW, la), outline=INK, w=5)
    for x, lab in ((720, "INPUT"), (930, "HIDDEN LAYERS"), (1140, "OUTPUT")):
        c.text(lab, (x if lab != "INPUT" else x + 20, 96), 24, WHITE, F_XB, 0, INK, 0, INK, 1, 0, prog(k, B, 2 * B))
    c.text("HOW IT WORKS", (350, 62), 56, WHITE, F_BLK, 0, INK, 6, INK, spring(k, .22))
    # chat
    u = spring(k - B, .25, .1)
    L, d = card_layer(540, 130, WHITE, 10)
    for i, ln in enumerate(PROMPT): d.text((34 * S, (44 + i * 44) * S), ln, font=font(F_BLK, 36 * S), fill=INK + (255,), anchor="lm")
    c.place(L, (350, 205), u, -2)
    if k >= 4 * B:
        a = spring(k - 4 * B, .25, .1)
        L2, d2 = card_layer(540, 270, YELLOW, 10)
        shown = int(sum(map(len, POEM)) * prog(k, 5 * B, 11.5 * B));
        if k < 5 * B:
            for q in range(3):
                h = 9 + 7 * max(0, math.sin(k * 9 - q * 1.2)); x = 150 + q * 50
                d2.ellipse([(x - h) * S, (130 - h) * S, (x + h) * S, (130 + h) * S], fill=INK + (255,))
        for i, ln in enumerate(POEM):
            part = ln[:max(0, shown)]; shown -= len(ln)
            if part: d2.text((30 * S, (60 + i * 64) * S), part, font=font(F_XB, 25 * S), fill=INK + (255,), anchor="lm")
        c.place(L2, (350, 460), a, 2)
    if k >= 11.5 * B: c.text("TOKEN BY TOKEN.", (940, 650), 40, YELLOW, F_BLK, 0, INK, 5, INK, spring(k - 11.5 * B), -2)

def mix(c1, c2, k): return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))

CARDS = [("WRITES", "CODE.", ORANGE), ("PAINTS", "IMAGES.", PINK), ("COMPOSES", "MUSIC.", MINT), ("MAKES", "VIDEO.", YELLOW)]
def card_visual(idx, k):
    cw, ch = 540, 400; L, d = card_layer(cw, ch, WHITE if idx != 2 else INK, 14)
    X = lambda v: (v + 4) * S
    if idx == 0:
        for q, col in enumerate((ORANGE, YELLOW, MINT)): d.ellipse([X(24 + q * 34), X(22), X(46 + q * 34), X(44)], fill=col + (255,), outline=INK + (255,), width=3 * S)
        r = random.Random(5); y = 80; cols = [BLUE, ORANGE, PINK, INK, MINT]
        for i in range(9):
            x = 36 + (i % 3 == 1) * 44 + (i % 4 == 2) * 44
            for _ in range(r.randint(2, 4)):
                wd = r.randint(50, 130); kk = prog(k, .1 + i * .08, .4 + i * .08)
                if x + wd > cw - 50: break
                d.rounded_rectangle([X(x), X(y), X(x + wd * kk), X(y + 20)], radius=10 * S, fill=r.choice(cols) + (255,)); x += wd + 14
            y += 36
        if int(k * 4) % 2 == 0: d.rectangle([X(cw - 80), X(80), X(cw - 66), X(108)], fill=INK + (255,))
    elif idx == 1:
        gw, gh = 60, 42
        xx, yy = np.meshgrid(np.linspace(0, 6, gw), np.linspace(0, 4.2, gh))
        a = np.sin(xx + k * 2) + np.sin(yy * 1.7 - k * 1.5) + np.sin((xx + yy) * .9 + k)
        pal = np.array([BLUE, SKY, MINT, YELLOW, ORANGE, PINK], np.uint8)
        im = pal[np.clip(((a + 3) / 6 * 6).astype(int), 0, 5)]
        im2 = Image.fromarray(im).resize(((cw - 40) * S, (ch - 40) * S), Image.NEAREST)
        m = Image.new("L", im2.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im2.width - 1, im2.height - 1], radius=16 * S, fill=255)
        L.paste(im2, (X(20), X(20)), m); d.rounded_rectangle([X(20), X(20), X(cw - 20), X(ch - 20)], radius=16 * S, outline=INK + (255,), width=5 * S)
    elif idx == 2:
        nb = 22; bw = (cw - 60) / nb
        for i in range(nb):
            h = (.2 + .8 * abs(math.sin(k * 6 + i * .55) * math.cos(k * 2.1 + i * .23))) * (ch - 90)
            d.rounded_rectangle([X(30 + i * bw + 3), X(ch - 40 - h), X(30 + (i + 1) * bw - 3), X(ch - 40)], radius=8 * S, fill=[YELLOW, PINK, MINT, ORANGE, SKY][i % 5] + (255,))
    else:
        d.rounded_rectangle([X(22), X(22), X(cw - 22), X(ch - 80)], radius=14 * S, fill=SKY + (255,), outline=INK + (255,), width=5 * S)
        sx = 80 + ((k * 90) % 360); d.ellipse([X(sx - 36), X(70), X(sx + 36), X(142)], fill=YELLOW + (255,), outline=INK + (255,), width=4 * S)
        d.polygon([(X(22), X(ch - 80)), (X(180), X(190)), (X(300), X(ch - 80))], fill=MINT + (255,)); d.polygon([(X(200), X(ch - 80)), (X(400), X(170)), (X(cw - 22), X(ch - 80))], fill=(30, 170, 120, 255))
        d.polygon([(X(cw / 2 - 28), X(130)), (X(cw / 2 - 28), X(210)), (X(cw / 2 + 36), X(170))], fill=WHITE + (255,), outline=INK + (255,))
        pr = (k * .3) % 1; d.rounded_rectangle([X(22), X(ch - 52), X(cw - 22), X(ch - 32)], radius=10 * S, fill=WHITE + (255,), outline=INK + (255,), width=4 * S)
        d.rounded_rectangle([X(22), X(ch - 52), X(22 + (cw - 44) * pr), X(ch - 32)], radius=10 * S, fill=ORANGE + (255,), outline=INK + (255,), width=4 * S)
    return L

def sc_cards(c, t, ref):
    lt = ref - tb(32); idx = min(3, int(lt / (4 * B))); k = t - tb(32) - idx * 4 * B
    a, b2, col = CARDS[idx]
    c.rect((0, 0, W, H), fill=col); halftone(c, INK, t)
    if k < 0: return
    left = idx % 2 == 0
    cx_card, cx_txt = (330, 950) if left else (950, 335)
    c.place(card_visual(idx, k), (cx_card, 340), spring(k, .3, .1), (-3 if left else 3) * (1 + (1 - eo(prog(k, 0, .4))) * 2))
    sz = fit(max(a, b2, key=len), 130, 470, .72)
    c.text(a, (cx_txt, 280), sz, WHITE, F_BLK, 8, INK, 10, INK, spring(k - .08))
    c.text(b2, (cx_txt, 280 + sz * 1.05), sz, INK, F_BLK, 0, INK, 0, INK, spring(k - .2))
    c.text("AI", (cx_txt, 120), 60, INK, F_BLK, 0, INK, 0, INK, spring(k - .02))
    for i in range(4): c.rect((560 + i * 54, 662, 600 + i * 54, 674), fill=INK if i <= idx else None, outline=INK, w=3, r=6)

def ticker(c, text, y, rot, t, speed, fill, tcol, h=84, size=54):
    L = Image.new("RGBA", (W * 2 * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    d.rectangle([0, 0, L.width, h * S], fill=fill + (255,))
    d.line([0, 0, L.width, 0], fill=INK + (255,), width=5 * S); d.line([0, h * S - 3, L.width, h * S - 3], fill=INK + (255,), width=5 * S)
    f = font(F_BLK, size * S); unit = text + "   •   "; uw = int(f.getlength(unit)); x = -((t * speed) % uw)
    while x < L.width: d.text((x, h * S / 2), unit, font=f, fill=tcol + (255,), anchor="lm"); x += uw
    c.place(L, (W / 2, y), 1, rot)

def sc_message(c, t, ref):
    k = t - tb(48); second = ref >= tb(52); k2 = t - tb(52)
    if not second:
        c.rect((0, 0, W, H), fill=INK); halftone(c, WHITE, t, 22)
        if k < 0: return
        ticker(c, "AI • AI • AI • AI", 96, -4, t, 260, YELLOW, INK)
        ticker(c, "AI • AI • AI • AI", 624, 4, -t, 260, PINK, INK)
        c.text("AI WON'T", (640, 270), 170, WHITE, F_BLK, 0, INK, 12, BLUE, spring(k), -3)
        hk = prog(k, 2 * B, 2.5 * B)
        if hk > 0: c.rect((250, 372, 250 + 780 * eo(hk), 478), fill=YELLOW, outline=INK, w=5, r=14)
        c.text("REPLACE YOU.", (640, 425), 115, INK if hk > .5 else WHITE, F_BLK, 0, INK, 0, INK, spring(k - 2 * B), 2)
    else:
        c.rect((0, 0, W, H), fill=YELLOW); halftone(c, INK, t, 34)
        if k2 < 0: return
        ticker(c, "LEARN • BUILD • SHIP", 92, 3, t, 300, BLUE, WHITE)
        ticker(c, "LEARN • BUILD • SHIP", 628, -3, -t, 300, BLUE, WHITE)
        c.text("SOMEONE USING AI", (640, 215), 84, INK, F_BLK, 0, INK, 0, INK, spring(k2), -2)
        c.text("WILL.", (640, 400), 300, BLUE, F_BLK, 14, WHITE, 16, INK, spring(k2 - 2 * B, .28), 2)
        sw = prog(k2, 3 * B, 3.8 * B)
        if sw > 0: c.line([(330, 560), (330 + 620 * eo(sw), 548)], ORANGE, 14)

def confetti(c, t, k, n=46):
    r = random.Random(11)
    for i in range(n):
        x0 = r.uniform(0, W); sp = r.uniform(80, 220); y = (r.uniform(-300, 0) + (k + 4) * sp) % (H + 120) - 60
        x = x0 + math.sin(t * 2 + i) * 30; col = r.choice([YELLOW, PINK, MINT, ORANGE, WHITE]); kind = i % 3; rot = t * (1 + i % 3) + i
        if kind == 0: c.rect((x - 9, y - 9, x + 9, y + 9), fill=col, outline=INK, w=3)
        elif kind == 1: c.ell(x, y, 9, fill=col, outline=INK, w=3)
        else: c.star(x, y, 13, col, rot, 4, .4, INK, 3)

def sc_finale(c, t, ref):
    k = t - tb(56)
    c.rect((0, 0, W, H), fill=BLUE)
    if k < 0: return
    for i in range(16):
        a0 = t * .25 + i * math.pi / 8; a1 = a0 + math.pi / 16
        c.poly([(400, 380), (400 + 1600 * math.cos(a0), 380 + 1600 * math.sin(a0)), (400 + 1600 * math.cos(a1), 380 + 1600 * math.sin(a1))], fill=(70, 100, 255, 255))
    confetti(c, t, k)
    p = spring(k, .35, .1)
    c.ell(405, 395, 275 * p, fill=YELLOW, outline=INK, w=8)
    bob = math.sin(t * 3) * 7
    c.place(STICKER, (405, 400 + bob), .88 * p * S, -3 * (1 - eo(prog(k, 0, .6))))
    c.text("LEARN IT.", (925, 190), 108, WHITE, F_BLK, 0, INK, 10, INK, spring(k - B), 2)
    c.text("BUILD WITH IT.", (925, 292), 66, YELLOW, F_BLK, 0, INK, 6, INK, spring(k - 2 * B), -2)
    sc = spring(k - 3 * B, .3, .1)
    L, d = card_layer(430, 190, WHITE, 12)
    d.text((215 * S + 4 * S, 82 * S), NAME, font=font(F_BLK, 84 * S), fill=INK + (255,), anchor="mm")
    d.rounded_rectangle([90 * S, 134 * S, 350 * S, 176 * S], radius=21 * S, fill=ORANGE + (255,), outline=INK + (255,), width=4 * S)
    d.text((220 * S, 155 * S), "27 · DEVELOPER", font=font(F_BLK, 26 * S), fill=INK + (255,), anchor="mm")
    c.place(L, (930, 470), sc, 2)

SECS = [(0, sc_hook), (tb(4), sc_history), (tb(20), sc_network), (tb(32), sc_cards), (tb(48), sc_message), (tb(56), sc_finale)]
def scene_raw(t, ref):
    fn = [f for s, f in SECS if ref >= s][-1]
    c = C(INK); fn(c, t, ref)
    if tb(4) <= ref < tb(56): pill_name(c, t)
    return c.im

CUTS_B = [4, 8, 12, 16, 20, 32, 36, 40, 44, 48, 52, 56]
CUTS = [tb(b) for b in CUTS_B]
WIPE_COL = [INK, YELLOW, PINK, MINT, ORANGE, WHITE]
WIN = .17
def render(t):
    near = [(i, c) for i, c in enumerate(CUTS) if abs(t - c) < WIN]
    if not near: return scene_raw(t, t)
    i, cut = near[0]
    A = scene_raw(t, cut - 1e-3); Bi = scene_raw(t, cut + 1e-3)
    u = (t - cut + WIN) / (2 * WIN); n = 7; vertical = i % 2 == 0; col = WIPE_COL[i % len(WIPE_COL)]
    base = A.copy(); d = ImageDraw.Draw(base)
    span = (W if vertical else H) * S / n; full = (H if vertical else W) * S
    for s in range(n):
        lu = clamp((u - s * .045) / (1 - 6 * .045))
        a0, a1 = int(s * span), int((s + 1) * span) + 1
        box = (a0, 0, a1, H * S) if vertical else (0, a0, W * S, a1)
        if lu >= .5: base.paste(Bi.crop(box), box[:2])
        lo, hi = (0, full * 2 * lu) if lu < .5 else (full * (2 * lu - 1), full)
        if lu <= 0 or lu >= 1: continue
        d.rectangle([a0, lo, a1, hi] if vertical else [lo, a0, hi, a1], fill=col)
    return base

# ---------------- post ----------------
def kick(t): return math.exp(-(t % B) * 9)
def post(img, t):
    im = img.resize((W, H), Image.LANCZOS)
    pop = 1 + .012 * kick(t) * (t > tb(4))
    if pop > 1.0005:
        co = (1 / pop, 0, W / 2 - W / 2 / pop, 0, 1 / pop, H / 2 - H / 2 / pop); im = im.transform((W, H), Image.AFFINE, co, Image.BILINEAR)
    arr = np.asarray(im).astype(np.float32)
    fade = min(prog(t, 0, .12), 1 - prog(t, DUR - .6, DUR))
    return (arr * fade).astype(np.uint8)

# ---------------- audio: 128 BPM funk-house, C major ----------------
SR = 44100
def make_audio(path):
    n = int(SR * DUR); rs = np.random.RandomState(4); tt = np.arange(n) / SR
    drums, bass, mus, fx = (np.zeros(n, np.float32) for _ in range(4))
    def add(buf, t0, sig, g=1.0):
        i = int(t0 * SR)
        if i < 0 or i >= n: return
        j = min(n, i + len(sig)); buf[i:j] += sig[:j - i] * g
    X = lambda d: np.arange(int(SR * d)) / SR
    mid = lambda m: 440 * 2 ** ((m - 69) / 12)
    lp = lambda s, a: lfilter([a], [1, -(1 - a)], s).astype(np.float32)
    hp = lambda s, a: (s - lp(s, a)).astype(np.float32)
    def nz(d): return rs.randn(int(SR * d)).astype(np.float32)
    x = X(.32); KICK = (np.sin(2 * np.pi * np.cumsum(48 + 130 * np.exp(-26 * x)) / SR) * np.exp(-8 * x)).astype(np.float32)
    CLAP = sum(hp(nz(.2), .3) * np.exp(-X(.2) * (26 - j * 3)) * (1 if j == 0 else .5) for j in range(2)).astype(np.float32)
    HAT = (hp(nz(.05), .65) * np.exp(-X(.05) * 80)).astype(np.float32)
    OHAT = (hp(nz(.22), .6) * np.exp(-X(.22) * 14)).astype(np.float32)
    SHK = (hp(nz(.04), .5) * np.exp(-X(.04) * 90)).astype(np.float32)
    def pluck(m, d=.28, env=9, harm=(1, .45, .2)):
        x = X(d); s = sum(h * np.sin(2 * np.pi * mid(m) * (i + 1) * x) for i, h in enumerate(harm))
        return (s * np.exp(-env * x) * np.minimum(1, x * 500)).astype(np.float32)
    def bassn(m, d=.22):
        x = X(d); s = np.sin(2 * np.pi * mid(m) * x) + .35 * np.sin(2 * np.pi * mid(m) * 2 * x) + .15 * (2 * ((x * mid(m)) % 1) - 1)
        return (s * np.exp(-6 * x) * np.minimum(1, x * 300)).astype(np.float32)
    chords = [(64, 67, 71, 74), (60, 64, 67, 69), (65, 69, 72, 76), (62, 67, 71, 74)]  # Cmaj9, Am7, Fmaj7, G6
    roots = [36, 33, 29, 31]
    mel = [[76, 0, 79, 81, 0, 79, 76, 0], [72, 0, 76, 79, 0, 76, 74, 0], [77, 0, 81, 84, 0, 81, 77, 0], [79, 0, 83, 86, 0, 83, 79, 74]]
    bass_pat = [1, 0, 1, 1, 0, 1, 0, 1]
    for beat in range(64):
        t0 = beat * B; bar = beat // 4; ch = bar % 4; bib = beat % 4
        full = 4 <= beat < 48 and not (beat in (47,)) or 52 <= beat < 63
        groove = 4 <= beat < 48 or 52 <= beat < 63
        drop = 52 <= beat < 63
        if groove and beat != 47:
            add(drums, t0, KICK, .95)
        if groove and bib in (1, 3) and beat >= 8 or (beat in (5, 7) and groove): add(drums, t0, CLAP, .5)
        if groove:
            add(drums, t0 + B / 2, OHAT, .22 if beat >= 8 else .14)
            if beat >= 20: [add(drums, t0 + q * B / 4, SHK, .12 + .06 * (q % 2 == 0)) for q in range(4)]
            else: add(drums, t0, HAT, .12)
        if 4 <= beat < 63 and beat not in (47, 51):
            for q in range(2):
                if bass_pat[(beat % 4) * 2 % 8 + q if False else (bib * 2 + q) % 8]: add(bass, t0 + q * B / 2, bassn(roots[ch] + (12 if (q == 1 and bib % 2) else 0)), .75)
        if 8 <= beat < 63 and bib in (1,) or (12 <= beat < 63 and bib == 2):
            # stabs on the "and" of beats
            for m in chords[ch]: add(mus, t0 + B * .5, pluck(m, .2, 14, (1, .6, .3)), .09)
        if 20 <= beat < 32 or 56 <= beat < 63:  # arp
            for q in range(8):
                add(mus, t0 + q * B / 2 * 0 + 0, np.zeros(1, np.float32), 0)
            for q in range(2):
                m = chords[ch][(beat * 2 + q) % 4] + 12
                s = pluck(m, .3, 10); add(mus, t0 + q * B / 2, s, .1); add(mus, t0 + q * B / 2 + B * .75, s, .035)
        if 32 <= beat < 48 or 56 <= beat < 63 or 52 <= beat < 56:  # lead melody
            for q in range(2):
                m = mel[bar % 4][bib * 2 + q]
                if m:
                    s = pluck(m, .34, 7, (1, .5, .25, .12)); add(mus, t0 + q * B / 2, s, .13); add(mus, t0 + q * B / 2 + B * .75, s, .05)
    # hook: word pops + riser
    for w in range(4):
        x = X(.16); add(fx, w * B, (np.sin(2 * np.pi * np.cumsum(520 - 380 * (x / .16)) / SR) * np.exp(-14 * x)).astype(np.float32), .6)
        add(drums, w * B, KICK, .6)
    # message breakdown: sub hits + snare roll into the drop
    for b_ in (48, 49, 50, 51):
        x = X(.5); add(fx, tb(b_), (np.sin(2 * np.pi * (46 + 14 * np.exp(-8 * x)) * x) * np.exp(-5 * x)).astype(np.float32), .9)
        add(mus, tb(b_) + B / 2, pluck(33 if b_ < 50 else 31, .4, 4, (1, .4)), .22)
    for q in range(16):
        sn = (hp(nz(.12), .4) * np.exp(-X(.12) * 30)).astype(np.float32); add(drums, tb(51) + q * B / 4, sn, .15 + .35 * q / 16)
    # risers + whooshes at transitions
    def riser(te, d, g=.3):
        x = X(d); sw = np.sin(2 * np.pi * np.cumsum(220 + 2600 * (x / d) ** 2) / SR) * (x / d) ** 2
        add(fx, te - d, ((sw + hp(nz(d), .25) * (x / d) ** 3) * g).astype(np.float32))
    for b_ in (4, 20, 32, 48, 56): riser(tb(b_), B * 2)
    for b_ in CUTS_B:
        d = .34; x = X(d); w_ = hp(nz(d), .2) * np.sin(np.pi * x / d) ** 1.5
        add(fx, tb(b_) - .17, w_.astype(np.float32), .28)
    for b_ in (4, 20, 32, 48, 52, 56):
        x = X(1.1); add(fx, tb(b_), (np.sin(2 * np.pi * (40 + 40 * np.exp(-9 * x)) * x) * np.exp(-3.5 * x)).astype(np.float32), .8)
    # chat typing ticks + card pops
    for tc in np.arange(tb(25), tb(31.5), .07): add(fx, tc, (pluck(84 + int(rs.rand() * 4), .03, 70, (1,))), .1)
    for b_ in (21, 24): add(fx, tb(b_), pluck(91, .25, 12), .18)
    for b_ in (8, 12, 16, 36, 40, 44, 53, 54): add(fx, tb(b_) + .02, pluck(76 + (b_ % 5) * 2, .2, 12), .12)
    # finale chord + sparkle
    for m in (60, 64, 67, 71, 74, 79): add(mus, tb(63), pluck(m, 1.6, 2.2, (1, .5, .25)), .09)
    for i in range(8): add(fx, tb(56) + i * .09, pluck(88 + (i * 3) % 10, .4, 10), .06)
    pump = 1 - .6 * np.exp(-(tt % B) * 11)
    mix = drums * 1.0 + bass * pump * 1.0 + mus * pump + fx
    mix *= np.minimum(1, tt / .05) * np.minimum(1, (DUR - tt) / .5)
    mix = np.tanh(mix * 1.5) * .88
    st = np.stack([mix, mix], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())

def main():
    wav = OUT + ".wav"; make_audio(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p", "-profile:v", "main", "-level", "4.0",
           "-g", "60", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
           "-movflags", "+faststart", "-t", str(DUR), OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(N):
        t = f / FPS; p.stdin.write(post(render(t), t).tobytes())
        if f % 90 == 0: print("frame", f, "/", N, flush=True)
    p.stdin.close(); p.wait(); os.remove(wav); print("done", OUT)

if __name__ == "__main__":
    main()
