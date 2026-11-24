"""Taşma/çakışma kontrolü: videonun her 0,2 sn'sini çizer, kart içindeki her yazı ve kutunun
kartın iç kenarlarını aşıp aşmadığına ve yazıların birbirinin üstüne binip binmediğine bakar.
Kullanım (video betiğinin içinden):  from tasma_kontrol import kontrol; kontrol(R)"""
from PIL import ImageDraw
import rail

PAD = 26  # kart kenarına en az bu kadar boşluk


def kontrol(R, step=0.2, verbose=True):
    rec = {"on": False, "items": []}
    orig_text, orig_rr, orig_rect = ImageDraw.ImageDraw.text, ImageDraw.ImageDraw.rounded_rectangle, ImageDraw.ImageDraw.rectangle

    def p_text(self, xy, text, fill=None, font=None, anchor=None, *a, **k):
        if rec["on"] and text and text.strip() and tuple(self.im.size) == (1080, 1920):
            try:
                bb = self.textbbox(xy, text, font=font, anchor=anchor)
                rec["items"].append(("yazı", text, bb, len(text.strip()) > 1))
            except Exception:
                pass
        return orig_text(self, xy, text, fill, font, anchor, *a, **k)

    def p_box(kind, orig):
        def f(self, xy, *a, **k):
            if rec["on"] and tuple(self.im.size) == (1080, 1920):
                x0, y0, x1, y1 = xy
                if (x1 - x0) > 8 and (y1 - y0) > 8:
                    rec["items"].append(("kutu", kind, (x0, y0, x1, y1), False))
            return orig(self, xy, *a, **k)
        return f

    ImageDraw.ImageDraw.text = p_text
    ImageDraw.ImageDraw.rounded_rectangle = p_box("yuvarlak kutu", orig_rr)
    ImageDraw.ImageDraw.rectangle = p_box("kutu", orig_rect)
    segs0 = list(R.segs)
    problems = {}

    def wrap(fn, i):
        def g(im, d, t, y0):
            rec["on"] = True; rec["y0"] = y0
            try:
                return fn(im, d, t, y0)
            finally:
                rec["on"] = False
        return g

    R.segs[:] = [wrap(fn, i) for i, fn in enumerate(segs0)]
    try:
        t = 0.0
        while t < R.DUR:
            rec["items"] = []
            R.frame(t)
            act = R.active(t)
            y_focus = R.node_y(act) - R.cam(t) + 44
            items = rec["items"]
            lo, hi = rail.CARD_X0 + PAD, rail.CARD_X1 - PAD
            for kind, txt, (x0, y0, x1, y1), _ in items:
                if x0 < lo - 1 or x1 > hi + 1:
                    key = (kind, f"{str(txt)[:30]} [bölüm {act + 1}] x={int(x0)}..{int(x1)} y={int(y0 - y_focus)}")
                    over = max(lo - x0, x1 - hi)
                    if key not in problems or problems[key][1] < over:
                        problems[key] = (round(t, 1), round(over))
            texts = [it for it in items if it[0] == "yazı" and it[3]]
            for a in range(len(texts)):
                for b in range(a + 1, len(texts)):
                    A, B = texts[a][2], texts[b][2]
                    ix = min(A[2], B[2]) - max(A[0], B[0]); iy = min(A[3], B[3]) - max(A[1], B[1])
                    if ix > 4 and iy > 4 and texts[a][1] != texts[b][1]:
                        key = ("çakışma", f"{texts[a][1][:18]} × {texts[b][1][:18]}")
                        if key not in problems:
                            problems[key] = (round(t, 1), round(min(ix, iy)))
            t += step
    finally:
        ImageDraw.ImageDraw.text, ImageDraw.ImageDraw.rounded_rectangle, ImageDraw.ImageDraw.rectangle = orig_text, orig_rr, orig_rect
        R.segs[:] = segs0
    if verbose:
        if not problems:
            print("✅ TAŞMA YOK")
        for (kind, txt), (t, px) in sorted(problems.items(), key=lambda x: x[1][0]):
            print(f"⚠️  {t:5.1f}s  {kind:<14} {px:4d}px  {txt}")
    return problems
