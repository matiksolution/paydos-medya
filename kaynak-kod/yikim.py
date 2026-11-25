"""SAHADA NASIL ÇALIŞIR? #1 — Yıkım makinesi binadan nasıl iner (tıraşlama).
Seri stili 'beton': brüt beton zemin, siyah mürekkep, turuncu/ikaz sarısı. Tek sahne: bina kesiti.
Kullanım: python3 yikim.py --stills | --check | --video | --finish ses.mp3"""
import sys, os, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import explainer as E
from explainer import black, bold, mono, spaced, mix, ease, tea_icon, paste_icon
from rail import clamp, p, eob, FPS
from railvid import Rail

W, H = 1080, 1920
INK = (24, 24, 26)
PAPER = (245, 243, 238)
ORANGE = (240, 108, 22)
SARI = (246, 190, 0)
MUTE = (92, 90, 86)
SLAB = (64, 64, 68)
ROOM = (226, 223, 216)
SHAFT = (204, 200, 192)
RUB = [(150, 146, 138), (120, 117, 111), (172, 168, 160), (98, 96, 92)]

GROUND = 1300
FH = 120                      # kat yüksekliği
BX0, BX1 = 330, 750           # bina
HL0, HR0 = 500, 580           # orta boşluk (merdiven/asansör boşluğu)
CUT = 600                     # sağda makinenin durduğu son parça
def LV(L): return GROUND - L * FH   # L. katın döşeme üst kotu (0 = zemin)


# ---------------- ses / zamanlama ----------------
RAW = [tuple(x) for x in json.load(open("/home/claude/video/yikim_words.json"))]
assert len(RAW) == 124
PARAS = [(0, 7), (8, 19), (20, 39), (40, 57), (58, 82), (83, 93), (94, 114), (115, 123)]
NODES = [(f"{i + 1:02d}", "") for i in range(len(PARAS))]
CMAP = {64: (64, "6"), 67: (67, "2"), 73: (74, "38"), 79: (79, "3"), 105: (105, "3.")}
HI = {"rampa", "lazım.", "tıraşlama.", "İzmir'de", "dikmelerle", "zarar", "Yorumlara"}
R = Rail(RAW, PARAS, NODES, "", [None] * len(PARAS), gap_add=0.3, caption_map=CMAP, hiwords=HI)
Wt, WE = R.W, R.WE
_cuts = "/home/claude/ses/yikim_cuts.json"     # sessizlik (enerji dibi) noktalarında kes
if os.path.exists(_cuts):
    R.cut_points = [tuple(x) for x in json.load(open(_cuts))]
for wi in (14, 44, 57, 63, 72, 100, 113):
    R.pop(Wt(wi))

# döngüler: makinenin bulunduğu kat L'den L-1'e inişi
# kır (sol taraf), yığ (moloz), rampa, in, kalan parçayı kır
C = [
    dict(L=6, b0=Wt(27), b1=Wt(33), p1=Wt(39) + .3, r1=Wt(45), d0=Wt(46), d1=WE(50), x0=Wt(51), x1=WE(54)),
    dict(L=5, w=0.45, b0=Wt(63) - 0.2, b1=Wt(66), p1=Wt(67), r1=Wt(68), d0=Wt(68), d1=Wt(70), x0=Wt(70), x1=WE(71)),
    dict(L=4, w=0.45, b0=Wt(72), b1=Wt(76), p1=Wt(77), r1=Wt(78), d0=Wt(78), d1=Wt(80), x0=Wt(80), x1=WE(82)),
]


def cyc(t):
    for c in C:
        if t < c["x1"]:
            return c
    return None


# ---------------- arka plan: brüt beton ----------------
_BG = None


def background():
    global _BG
    if _BG is None:
        rng = np.random.default_rng(7)
        k = (np.arange(H) / H)[:, None, None]
        base = np.array((200, 198, 193), np.float32) + (np.array((182, 180, 175), np.float32) - (200, 198, 193)) * k
        base = np.broadcast_to(base, (H, W, 3)).copy()
        n = rng.normal(0, 1, (H // 4 + 1, W // 4 + 1)).astype(np.float32)
        n = np.kron(n, np.ones((4, 4), np.float32))[:H, :W]
        base += (n * 3.0 + rng.normal(0, 2.2, (H, W)))[:, :, None]
        im = Image.fromarray(np.clip(base, 0, 255).astype("uint8"))
        d = ImageDraw.Draw(im)
        for x in range(0, W + 1, 270):            # kalıp panel derzleri
            d.line((x, 0, x, H), fill=(172, 170, 165), width=2)
        for y in range(0, H + 1, 540):
            d.line((0, y, W, y), fill=(172, 170, 165), width=2)
        for x in range(67, W, 135):               # kalıp bağlantı delikleri
            for y in range(67, H, 135):
                d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=(166, 163, 157))
                d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(140, 137, 131))
        _BG = im
    return _BG.copy()


def stripes(im, box, a=1.0, w=26):
    """ikaz şeridi (sarı-siyah çapraz)"""
    x0, y0, x1, y1 = [int(v) for v in box]
    if x1 <= x0 or y1 <= y0 or a <= 0:
        return
    t = Image.new("RGB", (x1 - x0, y1 - y0), SARI)
    d = ImageDraw.Draw(t)
    hh = y1 - y0
    for x in range(-hh, x1 - x0 + hh, w * 2):
        d.polygon([(x, hh), (x + w, hh), (x + w + hh, 0), (x + hh, 0)], fill=INK)
    m = Image.new("L", t.size, int(255 * a))
    im.paste(t, (x0, y0), m)


def header(im, d):
    E.handle(im, d)
    d.text((170, 136), "paydosmuhabbeti", font=mono(26, True), fill=INK, anchor="lm")
    f = mono(28, True)
    s = "SAHADA NASIL ÇALIŞIR?"
    spaced(d, (W / 2 + 2, 226), s, f, INK, spacing=8)
    tw = sum(d.textlength(c, font=f) for c in s) + 8 * (len(s) - 1)
    stripes(im, (W / 2 - tw / 2, 252, W / 2 + tw / 2, 262), w=10)


def caption(im, words, hi=(), y=1462):
    d = ImageDraw.Draw(im)
    f = bold(54, 800)
    sp = d.textlength(" ", font=f)
    ws = [d.textlength(w, font=f) for w in words]
    tw = sum(ws) + sp * (len(words) - 1)
    box = (W / 2 - tw / 2 - 34, y - 46, W / 2 + tw / 2 + 34, y + 46)
    d.rectangle(box, fill=INK)
    stripes(im, (box[0], box[3], box[2], box[3] + 10), w=10)
    x = W / 2 - tw / 2
    for i, (w_, wl) in enumerate(zip(words, ws)):
        d.text((x, y + 2), w_, font=f, fill=ORANGE if i in hi else PAPER, anchor="lm")
        x += wl + sp


def info(d, im, y, top, big, src, a):
    """üstte bilgi kartı"""
    if a <= 0:
        return
    k = eob(a)
    x0, x1 = 110, 970
    h = 210
    yy = y + (1 - k) * 30
    d.rectangle((x0, yy, x1, yy + h), fill=mix((200, 198, 193), PAPER, a), outline=INK, width=4)
    stripes(im, (x0, yy, x0 + 18, yy + h), a, w=8)
    d = ImageDraw.Draw(im)
    spaced(d, (x0 + 50, yy + 46), top, mono(26, True), mix(PAPER, MUTE, a), spacing=6, anchor="lm")
    d.text((x0 + 48, yy + 120), big, font=black(64), fill=mix(PAPER, INK, a), anchor="lm")
    d.text((x0 + 50, yy + 180), src, font=mono(21, True), fill=mix(PAPER, MUTE, a), anchor="lm")


# ---------------- makine ----------------
def machine_sprite(arm=0.0, s=1.0, ghost=False, pose='down'):
    """küçük yıkım makinesi (paletli, uzun kollu, kırıcı uçlu). Sprite merkezi = palet altı orta."""
    S = 2
    Wd, Hd = 420 * S, 300 * S
    im = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ox, oy = Wd / 2, Hd - 40 * S          # palet altı orta
    col = ORANGE + (255,)
    ink = INK + (255,)
    if ghost:
        col, ink = (0, 0, 0, 0), ORANGE + (255,)
    lw = 4 * S

    def P(x, y): return (ox + x * S, oy + y * S)
    # palet
    d.rounded_rectangle((*P(-66, -26), *P(66, 0)), 13 * S, fill=ink if not ghost else (0, 0, 0, 0), outline=ink, width=lw)
    if not ghost:
        for x in range(-50, 60, 20):
            d.ellipse((*P(x - 6, -19), *P(x + 6, -7)), fill=(90, 90, 94, 255))
    # gövde + kabin
    d.rectangle((*P(-58, -62), *P(44, -28)), fill=col, outline=ink, width=lw)
    d.polygon([P(-50, -62), P(-50, -104), P(-6, -104), P(10, -62)], fill=col, outline=ink)
    d.line([P(-50, -62), P(-50, -104), P(-6, -104), P(10, -62)], fill=ink, width=lw)
    d.polygon([P(-42, -66), P(-42, -96), P(-10, -96), P(2, -66)], fill=(70, 92, 104, 255) if not ghost else (0, 0, 0, 0))
    d.rectangle((*P(30, -56), *P(44, -34)), fill=ink)            # karşı ağırlık çizgisi
    # kol: omuz (40,-50) -> dirsek -> uç (sola doğru)
    sh = P(36, -54)
    if pose == 'down':
        a1, a2 = math.radians(163 + 5 * arm), math.radians(256 + 9 * arm)
    elif pose == 'carry':
        a1, a2 = math.radians(128), math.radians(222)
    else:
        a1, a2 = math.radians(120 + 5 * arm), math.radians(200 + 9 * arm)
    L1, L2 = 110, 92
    el = (sh[0] + math.cos(a1) * L1 * S, sh[1] - math.sin(a1) * L1 * S)
    tp = (el[0] + math.cos(a2) * L2 * S, el[1] - math.sin(a2) * L2 * S)
    for pa, pb, wdt in ((sh, el, 16), (el, tp, 13)):
        d.line([pa, pb], fill=ink, width=(wdt + 6) * S)
        d.line([pa, pb], fill=col if not ghost else (0, 0, 0, 0), width=wdt * S)
    # kırıcı uç
    ang = math.atan2(tp[1] - el[1], tp[0] - el[0])
    ux, uy = math.cos(ang), math.sin(ang)
    hb = [(tp[0] - uy * 9 * S, tp[1] + ux * 9 * S), (tp[0] + uy * 9 * S, tp[1] - ux * 9 * S),
          (tp[0] + uy * 4 * S + ux * 30 * S, tp[1] - ux * 4 * S + uy * 30 * S),
          (tp[0] - uy * 4 * S + ux * 30 * S, tp[1] + ux * 4 * S + uy * 30 * S)]
    d.polygon(hb, fill=ink)
    for c_ in (sh, el):
        d.ellipse((c_[0] - 7 * S, c_[1] - 7 * S, c_[0] + 7 * S, c_[1] + 7 * S), fill=ink)
    tip = (tp[0] + ux * 30 * S, tp[1] + uy * 30 * S)
    im = im.resize((int(Wd / S * s), int(Hd / S * s)), Image.LANCZOS)
    return im, ((tip[0] - ox) / S * s, (tip[1] - oy) / S * s)


def put_machine(im, x, y, arm=0.0, rot=0.0, s=1.0, a=1.0, ghost=False, flip=False, pose='down'):
    sp, tip = machine_sprite(arm, s, ghost, pose)
    if flip:
        sp = sp.transpose(Image.FLIP_LEFT_RIGHT); tip = (-tip[0], tip[1])
    ox, oy = sp.width / 2, sp.height - 40 * s
    if rot:
        big = Image.new("RGBA", (sp.width * 2, sp.height * 2), (0, 0, 0, 0))
        big.paste(sp, (int(sp.width / 2), int(sp.height / 2)))
        cx, cy = sp.width / 2 + ox, sp.height / 2 + oy
        big = big.rotate(rot, resample=Image.BICUBIC, center=(cx, cy))
        sp, ox, oy = big, cx, cy
        r = math.radians(-rot)
        tip = (tip[0] * math.cos(r) - tip[1] * math.sin(r), tip[0] * math.sin(r) + tip[1] * math.cos(r))
    m = sp.split()[3].point(lambda v: int(v * a))
    im.paste(sp.convert("RGB"), (int(x - ox), int(y - oy)), m)
    return (x + tip[0], y + tip[1])


# ---------------- moloz parçacıkları ----------------
def rubble_fall(d, t, t0, t1, xa, xb, y_from, y_to, n=60, seed=1):
    rng = np.random.default_rng(seed)
    S = rng.uniform(t0, t1, n); X = rng.uniform(xa, xb, n); SZ = rng.uniform(6, 15, n); C_ = rng.integers(0, 4, n)
    g = 2600.0
    for s_, x, sz, c in zip(S, X, SZ, C_):
        dt = t - s_
        if dt < 0:
            continue
        y = y_from + 0.5 * g * dt * dt
        if y > y_to - sz / 2:
            continue
        d.rectangle((x - sz / 2, y - sz / 2, x + sz / 2, y + sz / 2), fill=RUB[c])


def dust(d, t, x, y, a=1.0, seed=0):
    rng = np.random.default_rng(seed)
    for i in range(7):
        ph = (t * 1.7 + i / 7) % 1
        r = 10 + 34 * ph
        dx = rng.uniform(-50, 50)
        c = mix((228, 226, 221), (200, 198, 193), ph)
        if a * (1 - ph) > 0.05:
            d.ellipse((x + dx * ph - r, y - 30 * ph - r, x + dx * ph + r, y - 30 * ph + r), fill=c)


# ---------------- bina ----------------
def draw_building(im, d, t):
    c = cyc(t)
    top = c["L"] if c else 3            # en üstteki (kısmen de olsa) var olan döşeme
    hl, hr = HL0 + 40, HL0 + 40         # üst döşemedeki boşluk
    right_col = True
    left_col = True
    keep_right = (BX0, BX1)
    if c:
        if t >= c["b0"] + c.get("w", 0):
            k = ease(clamp((t - c["b0"] - c.get("w", 0)) / (c["b1"] - c["b0"] - c.get("w", 0))))
            hl = (HL0 + 40) - (HL0 + 40 - BX0) * k
            hr = (HL0 + 40) + (CUT - HL0 - 40) * k
            left_col = k < 0.98
        if t >= c["x0"]:
            k = ease(clamp((t - c["x0"]) / (c["x1"] - c["x0"])))
            keep_right = (CUT + (BX1 - CUT) * k, BX1)
            right_col = k < 0.6
    # katlar (zeminden üst döşemenin altına kadar)
    for L in range(1, top + 1):
        y0, y1 = LV(L), LV(L - 1)
        is_top = L == top
        if not is_top or (left_col and right_col and t < (c["b0"] if c else 1e9)):
            d.rectangle((BX0, y0, BX1, y1), fill=ROOM)
            d.rectangle((HL0, y0, HR0, y1), fill=SHAFT)
            d.line((HL0, y0, HL0, y1), fill=(170, 166, 158), width=2)
            d.line((HR0, y0, HR0, y1), fill=(170, 166, 158), width=2)
            for wx in (BX0 + 60, BX1 - 130):                 # pencere izi
                d.rectangle((wx, y0 + 34, wx + 70, y0 + 84), outline=(186, 182, 174), width=3)
        else:
            # en üst kat boşalıyor: sadece kalan dikmeler
            pass
        if not is_top or left_col:
            d.rectangle((BX0, y0, BX0 + 22, y1), fill=SLAB)
        if not is_top or right_col:
            d.rectangle((BX1 - 22, y0, BX1, y1), fill=SLAB)
    # döşemeler
    for L in range(1, top):
        d.rectangle((BX0 - 6, LV(L) - 8, BX1 + 6, LV(L) + 8), fill=SLAB)
    yT = LV(top)
    pieces = []
    if hl > BX0 + 2:
        pieces.append((BX0 - 6, hl))
    if keep_right[0] < BX1 - 2:
        pieces.append((max(hr, keep_right[0]), BX1 + 6))
    for xa, xb in pieces:
        if xb - xa > 4:
            d.rectangle((xa, yT - 8, xb, yT + 8), fill=SLAB)
    # çatlaklar (sahne 2)
    a = p(t, Wt(24), 0.5) * (1 - p(t, Wt(27), 0.3))
    if a > 0 and top == 6:
        for k_, (sx, dirx) in enumerate(((540, -1), (540, 1), (540, -1))):
            pts = [(sx, yT - 8)]
            for j in range(1, 6):
                pts.append((sx + dirx * j * 16 * a * (1 + k_ * .3), yT - 8 + (j % 2) * 10 + k_ * 3))
            d.line(pts, fill=INK, width=3)
    # zemin
    d.rectangle((0, GROUND, W, GROUND + 70), fill=(140, 132, 118))
    for x in range(-40, W, 28):
        d.line((x, GROUND + 70, x + 40, GROUND + 10), fill=(122, 114, 101), width=3)
    d.line((0, GROUND, W, GROUND), fill=INK, width=6)
    # boşluk dibinde biriken moloz
    hgt = 0
    for c_ in C:
        if t > c_["b0"]:
            hgt += 26 * clamp((t - c_["b0"]) / (c_["b1"] - c_["b0"]))
        if t > c_["x0"]:
            hgt += 12 * clamp((t - c_["x0"]) / (c_["x1"] - c_["x0"]))
    if hgt > 1:
        d.polygon([(HL0 + 4, GROUND), (HL0 + 20, GROUND - hgt), (HR0 - 18, GROUND - hgt * .8), (HR0 - 4, GROUND)], fill=RUB[1])
    return top, yT


def pile_and_ramp(d, t):
    c = cyc(t)
    if not c:
        return
    L = c["L"]
    yb, yt = LV(L - 1), LV(L)
    if t < c["b1"] - 0.5:
        return
    hpile = 60 * ease(clamp((t - (c["b1"] - 0.5)) / (c["p1"] - c["b1"] + 0.5)))
    mound = [(BX0 + 40, yb - 8), (BX0 + 110, yb - 8 - hpile), (BX0 + 200, yb - 8 - hpile * 1.05), (HL0 + 30, yb - 8)]
    ramp = [(BX0 + 30, yb - 8), (CUT - 6, yt - 6), (CUT + 2, yt + 10), (CUT + 2, yb - 8)]
    k = ease(clamp((t - c["p1"]) / max(0.3, c["r1"] - c["p1"])))
    fade = 1 - clamp((t - c["x0"]) / (c["x1"] - c["x0"]))
    if fade <= 0:
        return
    pts = [(m[0] + (r[0] - m[0]) * k, m[1] + (r[1] - m[1]) * k) for m, r in zip(mound, ramp)]
    col = mix((200, 198, 193), RUB[1], fade)
    d.polygon(pts, fill=col)
    rng = np.random.default_rng(L)
    for i in range(26):
        u, v = rng.uniform(0.05, 0.95), rng.uniform(0.1, 0.9)
        # noktayı çokgen içine yerleştir (iki kenar arası)
        xa = pts[0][0] + (pts[1][0] - pts[0][0]) * u
        ya = pts[0][1] + (pts[1][1] - pts[0][1]) * u
        yy = ya + (yb - 8 - ya) * v
        sz = rng.uniform(5, 11)
        d.rectangle((xa - sz / 2, yy - sz / 2, xa + sz / 2, yy + sz / 2), fill=mix(col, RUB[(i % 3) + 1], fade))


def machine_pos(t):
    """(x, y, rot, hammer, flip, pose)"""
    if t < Wt(8):
        return 670, LV(6) - 8, 0, True, False, "down"
    if t < Wt(20):
        # vinçle kaldırma
        x0, y0 = 165, GROUND
        a1 = clamp((t - Wt(16)) / (WE(17) + .25 - Wt(16)))
        a2 = clamp((t - (WE(17) + .25)) / (WE(19) - WE(17) - .25))
        if a2 <= 0:
            return x0, y0 - (GROUND - (LV(6) - 64)) * ease(a1), 0, False, False, "carry"
        k = ease(a2)
        return x0 + (670 - x0) * k, (LV(6) - 64) + 56 * k * k, 0, False, False, "carry"
    c = cyc(t)
    if not c:
        return 470, LV(3) - 8, 0, True, False, "down"
    L = c["L"]
    yt, yb = LV(L) - 8, LV(L - 1) - 8
    if t < c["d0"]:
        if c is not C[0]:
            k = ease(clamp((t - c["b0"]) / c["w"]))
            return 470 + (670 - 470) * k, yt, 0, k >= 1 and t > Wt(21), False, "down"
        return 670, yt, 0, t > Wt(21), False, "down"
    if t < c["x0"]:
        k = clamp((t - c["d0"]) / (c["d1"] - c["d0"]))
        if k < 0.25:
            return 670 + (CUT + 10 - 670) * ease(k / 0.25), yt, 0, False, False, "carry"
        kk = ease((k - 0.25) / 0.75)
        x = (CUT + 10) + (430 - CUT - 10) * kk
        frac = clamp((x - (BX0 + 30)) / (CUT - BX0 - 30))
        y = yb + (yt - yb) * frac
        slope = math.degrees(math.atan2(yt - yb, CUT - BX0 - 30))   # negatif: sola doğru aşağı
        rot = slope if 0.03 < frac < 0.97 else 0
        return x, y, -rot, False, False, "carry"
    # kalan parçayı kır: sağa dön, kolu yukarı
    k = ease(clamp((t - c["x0"]) / 0.35))
    return 430 + 40 * k, yb, 0, k >= 1, True, "up"


# ---------------- sahne ----------------
def scene(t):
    im = background()
    d = ImageDraw.Draw(im)
    # komşu binalar (sahne 6'dan sonra)
    nb = p(t, Wt(87), 0.6) * (1 - p(t, Wt(94), 0.4))
    if nb > 0:
        off = (1 - ease(nb)) * 260 if t < Wt(94) else (1 - nb) * 260
        for (x0, x1, n, sgn) in ((120, 318, 4, -1), (762, 962, 5, 1)):
            xo = sgn * off
            for L in range(1, n + 1):
                d.rectangle((x0 + xo, LV(L), x1 + xo, LV(L - 1)), fill=(214, 211, 204), outline=(150, 146, 138), width=3)
                d.rectangle((x0 + 30 + xo, LV(L) + 34, x0 + 90 + xo, LV(L) + 80), fill=(186, 196, 202))
            d.rectangle((x0 - 6 + xo, LV(n) - 10, x1 + 6 + xo, LV(n) + 6), fill=(120, 117, 111))
        sh = p(t, Wt(92), 0.4) * (1 - p(t, Wt(94), 0.3))
        if sh > 0:
            for cx, cy in ((219, LV(4) - 70), (862, LV(5) - 70)):
                r = 38 * eob(sh)
                d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PAPER, outline=INK, width=4)
                if sh > 0.5:
                    d.line([(cx - 16, cy + 2), (cx - 4, cy + 14), (cx + 18, cy - 12)], fill=(40, 140, 70), width=7)
            # mesafe okları
            for xa, xb in ((318, BX0), (BX1, 762)):
                d.line((xa + 4, LV(2) + 60, xb - 4, LV(2) + 60), fill=ORANGE, width=4)
    top, yT = draw_building(im, d, t)
    pile_and_ramp(d, t)
    # düşen moloz
    for c in C:
        if c["b0"] - 0.1 < t < c["x1"] + 1.5:
            rubble_fall(d, t, c["b0"], c["b1"], HL0 + 14, HR0 - 14, LV(c["L"]), GROUND - 6, n=70, seed=c["L"])
            rubble_fall(d, t, c["x0"], c["x1"], HL0 + 14, HR0 - 14, LV(c["L"] - 1), GROUND - 6, n=30, seed=c["L"] + 9)
    # dikmeler (sahne 7)
    for L in (1, 2):
        for j, x in enumerate((BX0 + 80, BX0 + 150, BX1 - 150, BX1 - 80)):
            k = p(t, Wt(113) + 0.08 * (j + 4 * (2 - L)), 0.3)
            if k > 0:
                y0, y1 = LV(L) + 8, LV(L - 1) - 8
                yy = y1 - (y1 - y0) * eob(k)
                d.rectangle((x - 5, yy, x + 5, y1), fill=ORANGE, outline=INK, width=2)
                d.rectangle((x - 16, y1 - 6, x + 16, y1), fill=INK)
                d.rectangle((x - 16, yy, x + 16, yy + 6), fill=INK)
    if p(t, Wt(113) + 0.3, 0.3) > 0:
        a = p(t, Wt(113) + 0.3, 0.3)
        spaced(d, (BX1 + 140, LV(1) + 60), "DİKME", mono(28, True), mix(PAPER, INK, a), spacing=6)
        d.line((BX1 - 70, LV(1) + 60, BX1 + 80, LV(1) + 60), fill=mix(PAPER, INK, a), width=3)
    # vinç (sahne 2)
    cr = p(t, Wt(12), 0.5) * (1 - p(t, Wt(20), 0.4))
    mx, my, rot, act, flip, pose = machine_pos(t)
    if cr > 0:
        off = (1 - ease(cr)) * 400
        px, py = 930 + off, 1210
        d.rectangle((830 + off, 1210, 1080 + off, 1272), fill=SARI, outline=INK, width=4)
        d.rectangle((960 + off, 1150, 1040 + off, 1210), fill=SARI, outline=INK, width=4)
        for wx in (870, 950, 1030):
            d.ellipse((wx - 26 + off, 1252, wx + 26 + off, 1304), fill=INK)
        hook_y = my - 150
        tipx, tipy = mx + 10, max(330, min(hook_y - 60, 420))
        if t < Wt(16):
            tipx, tipy = 165 + 10, 420
        ang = math.atan2(tipy - py, tipx - px)
        nx, ny = -math.sin(ang), math.cos(ang)
        for wdt, col in ((30, INK), (22, SARI)):
            d.line((px, py, tipx, tipy), fill=col, width=wdt)
        for i in range(1, 12):
            fx = px + (tipx - px) * i / 12; fy = py + (tipy - py) * i / 12
            d.line((fx + nx * 10, fy + ny * 10, fx - nx * 10 + (tipx - px) / 24, fy - ny * 10 + (tipy - py) / 24), fill=INK, width=3)
        ry = my - 112 if t >= Wt(14) else my - 112
        d.line((tipx, tipy, mx + 10, ry), fill=INK, width=3)
        d.line((mx - 40, ry + 30, mx + 10, ry), fill=INK, width=2)
        d.line((mx + 60, ry + 30, mx + 10, ry), fill=INK, width=2)
        d.rectangle((mx + 2, ry - 6, mx + 18, ry + 6), fill=INK)
    # makine
    hammer = act and t < R.T_HIT
    arm = math.sin(t * 2 * math.pi * 5.5) if hammer else 0.0
    tip = put_machine(im, mx, my, arm=arm, rot=rot, flip=flip, pose=pose)
    d = ImageDraw.Draw(im)
    if hammer and arm > 0.6:
        dust(d, t, tip[0], tip[1], seed=int(t * 3))
    # İzmir: hayalet makine kenardan devriliyor (sahne 7)
    g = p(t, Wt(102), 0.5) * (1 - p(t, Wt(109), 0.4))
    if g > 0:
        k = ease(clamp((t - Wt(102)) / 1.6))
        gx, gy = BX1 - 30 + 90 * k, LV(3) - 8 + 150 * k * k
        put_machine(im, gx, gy, rot=-38 * k, a=g, ghost=True, flip=True)
        d = ImageDraw.Draw(im)
        for i in range(3):
            ya = LV(3) + 40 + i * 70
            d.line((BX1 + 190, ya, BX1 + 190, ya + 44), fill=mix((200, 198, 193), ORANGE, g), width=6)
            d.polygon([(BX1 + 176, ya + 40), (BX1 + 204, ya + 40), (BX1 + 190, ya + 60)], fill=mix((200, 198, 193), ORANGE, g))
    return im


def overlay(im, t):
    d = ImageDraw.Draw(im)
    # 1: kanca
    a = 1 - p(t, Wt(8) - 0.2, 0.3)
    if a > 0:
        d.text((W / 2, 360), "NASIL İNECEK?", font=black(104), fill=mix((200, 198, 193), INK, a), anchor="mm")
    # 2: geri sar
    a = p(t, Wt(8), 0.25) * (1 - p(t, Wt(12), 0.3))
    if a > 0:
        f = mono(34, True)
        d.rectangle((W / 2 - 170, 330, W / 2 + 170, 400), fill=mix((200, 198, 193), INK, a))
        c_ = mix(INK, SARI, a)
        for k in range(2):
            x = W / 2 - 120 + k * 26
            d.polygon([(x, 365), (x + 24, 350), (x + 24, 380)], fill=c_)
        spaced(d, (W / 2 + 30, 366), "ÖNCE", f, mix(INK, PAPER, a), spacing=8)
    # 4: tıraşlama damgası
    a = p(t, Wt(57), 0.25) * (1 - p(t, Wt(58) + 0.4, 0.3))
    if a > 0:
        k = eob(a)
        fs = int(96 * k) + 2
        d.rectangle((W / 2 - 340 * k, 300, W / 2 + 340 * k, 430), fill=INK)
        stripes(im, (W / 2 - 340 * k, 430, W / 2 + 340 * k, 446), w=12)
        d = ImageDraw.Draw(im)
        d.text((W / 2, 366), "TIRAŞLAMA", font=black(fs), fill=SARI, anchor="mm")
    # 5: bilgi kartları
    a = p(t, Wt(63), 0.35) * (1 - p(t, Wt(72) - 0.2, 0.25))
    info(d, im, 300, "KÜÇÜKÇEKMECE · 6 KATLI BİNA", "2 GÜNDE 2 KAT" if t > Wt(67) else "?",
         "KAYNAK: YENİ AKİT, 9 KASIM 2019", a)
    d = ImageDraw.Draw(im)
    a = p(t, Wt(72), 0.35) * (1 - p(t, Wt(83) - 0.3, 0.25))
    info(d, im, 300, "KANADA · 38 KATLI OTEL KULESİ", "3 GÜNDE 1 KAT" if t > Wt(79) else "?",
         "KAYNAK: FOR CONSTRUCTION PROS", a)
    d = ImageDraw.Draw(im)
    # 6: neden
    a = p(t, Wt(83), 0.3) * (1 - p(t, Wt(94) - 0.3, 0.25))
    if a > 0:
        d.text((W / 2, 360), "NEDEN BU ZAHMET?", font=black(78), fill=mix((200, 198, 193), INK, a), anchor="mm")
        b = p(t, Wt(91), 0.3) * a
        if b > 0:
            d.text((W / 2, 440), "KOMŞU BİNALARA ZARAR GELMESİN", font=mono(30, True), fill=mix((200, 198, 193), ORANGE, b), anchor="mm")
    # 7: ikaz
    a = p(t, Wt(94), 0.2) * (1 - p(t, Wt(109) - 0.3, 0.25))
    if a > 0:
        stripes(im, (0, 290, W, 314), a, w=22)
        d = ImageDraw.Draw(im)
        d.text((W / 2, 380), "TEK HESAP HATASI", font=black(78), fill=mix((200, 198, 193), INK, a), anchor="mm")
        b = p(t, Wt(100), 0.3) * a
        if b > 0:
            d.text((W / 2, 460), "İZMİR · 2023 · 3. KATTAN DÜŞTÜ", font=mono(30, True), fill=mix((200, 198, 193), ORANGE, b), anchor="mm")
            d.text((W / 2, 506), "OPERATÖR KURTULDU · KAYNAK: CUMHURİYET", font=mono(22, True), fill=mix((200, 198, 193), MUTE, b), anchor="mm")
    a = p(t, Wt(109), 0.3) * (1 - p(t, Wt(115) - 0.3, 0.25))
    if a > 0:
        d.text((W / 2, 380), "ALT KATLAR DESTEKLENİR", font=black(64), fill=mix((200, 198, 193), INK, a), anchor="mm")
        b = p(t, Wt(113), 0.3) * a
        if b > 0:
            d.text((W / 2, 452), "MAKİNE + MOLOZ YÜKÜNÜ TAŞIMAK İÇİN", font=mono(28, True), fill=mix((200, 198, 193), ORANGE, b), anchor="mm")
    # 8: soru
    fade = 1 - p(t, R.T_HIT, 0.18)
    a = p(t, Wt(115), 0.3) * fade
    if a > 0:
        d.text((W / 2, 350), "Sen hangi işin", font=black(66), fill=mix((200, 198, 193), INK, a), anchor="mm")
        d.text((W / 2, 432), "perde arkasını merak ediyorsun?", font=black(46), fill=mix((200, 198, 193), INK, a), anchor="mm")
        b = p(t, Wt(122), 0.3) * fade
        if b > 0:
            k = eob(b)
            d.rectangle((W / 2 - 230 * k, 488, W / 2 + 230 * k, 556), fill=ORANGE)
            if b > .5:
                spaced(d, (W / 2, 523), "YORUMLARA YAZ ↓", mono(30, True), PAPER, spacing=6)


def endcard(im, t):
    lg = p(t, R.T_HIT + 0.18, 0.45)
    cover = p(t, R.T_HIT, 0.25)
    if cover <= 0:
        return im
    bg = background()
    im = Image.blend(im, bg, ease(cover) * 0.92)
    d = ImageDraw.Draw(im)
    header(im, d)
    if lg > 0:
        k = eob(lg)
        cy = 820
        paste_icon(im, tea_icon(int(220 * k) + 2), W / 2, cy - 120, lg)
        d.text((W / 2, cy + 120), "paydos", font=black(110), fill=mix((200, 198, 193), INK, lg), anchor="ms")
        d.text((W / 2, cy + 186), "muhabbeti", font=bold(46, 800), fill=mix((200, 198, 193), ORANGE, lg), anchor="ms")
        stripes(im, (W / 2 - 200, cy + 220, W / 2 + 200, cy + 232), lg, w=10)
        b = p(t, R.SIG_T + 0.1, 0.4)
        if b > 0:
            d.text((W / 2, cy + 300), "Bugün de çalıştık.", font=mono(32, True), fill=mix((200, 198, 193), MUTE, b), anchor="ms")
    return im


def frame(t):
    im = scene(t)
    overlay(im, t)
    d = ImageDraw.Draw(im)
    header(im, d)
    cur = None
    for chk in R.chunks:
        if chk[0][1] - 0.05 <= t <= chk[-1][2] + 0.25:
            cur = chk
    if cur and t < R.T_HIT:
        shown = [w for w in cur if t >= w[1] - 0.04]
        if shown:
            caption(im, [w[0] for w in shown], hi=tuple(j for j, w in enumerate(shown) if w[3] or any(ch.isdigit() for ch in w[0])))
    return endcard(im, t)


R.frame = frame

if __name__ == "__main__":
    out = "/home/claude/video/out/paydos_sahada1_yikim"
    if "--stills" in sys.argv:
        ts = [0.3, Wt(10), WE(17) + .5, Wt(23), Wt(31), Wt(37), Wt(44) + .4, Wt(48), Wt(54), Wt(57) + .2,
              Wt(65), Wt(70), Wt(79) + .3, Wt(92) + .3, Wt(104), Wt(114) + .3, Wt(122) + .3, R.SIG_T + .8]
        ims = [frame(t) for t in ts]
        cols = 6
        s = Image.new("RGB", (1100 * cols, 1940 * math.ceil(len(ims) / cols)), (40, 40, 40))
        for i, im in enumerate(ims):
            s.paste(im, ((i % cols) * 1100, (i // cols) * 1940))
        s.resize((s.width // 4, s.height // 4)).save(out + "_sheet.png")
        for t in [0.3, Wt(48), Wt(104)]:
            frame(t).save(out + f"_t{t:.1f}.png")
        print("DUR", R.DUR); sys.exit()
    if "--video" in sys.argv:
        R.render_video(out + "_video.mp4"); print("video ok", R.DUR); sys.exit()
    if "--finish" in sys.argv:
        R.finish(out + "_video.mp4", sys.argv[sys.argv.index("--finish") + 1], out); print("done")
