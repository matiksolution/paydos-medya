"""Tek sahneli videolar için taşma/çakışma kontrolü: her 0,2 sn'de çizilen yazıların ekran
kenarına (40 px) taşıp taşmadığına ve birbirine binip binmediğine bakar."""
from PIL import ImageDraw

def kontrol(frame, dur, step=0.2, pad=40, W=1080):
    rec = []
    orig = ImageDraw.ImageDraw.text
    def p_text(self, xy, text, fill=None, font=None, anchor=None, *a, **k):
        if text and text.strip() and tuple(self.im.size) == (1080, 1920):
            try:
                rec.append((text, self.textbbox(xy, text, font=font, anchor=anchor)))
            except Exception:
                pass
        return orig(self, xy, text, fill, font, anchor, *a, **k)
    ImageDraw.ImageDraw.text = p_text
    sorun = {}
    try:
        t = 0.0
        while t < dur:
            rec.clear(); frame(t)
            # harf aralıklı yazılar tek tek harf çizer; bunları birleştirme, sadece kenar kontrolü yap
            for s, (x0, y0, x1, y1) in rec:
                if x0 < pad or x1 > W - pad:
                    sorun.setdefault(("kenar", s[:30]), round(t, 1))
            words = [(s, b) for s, b in rec if len(s.strip()) > 1]
            for i in range(len(words)):
                for j in range(i + 1, len(words)):
                    A, B = words[i][1], words[j][1]
                    ix = min(A[2], B[2]) - max(A[0], B[0]); iy = min(A[3], B[3]) - max(A[1], B[1])
                    if ix > 4 and iy > 4 and words[i][0] != words[j][0]:
                        sorun.setdefault(("çakışma", f"{words[i][0][:20]} × {words[j][0][:20]}"), round(t, 1))
            t += step
    finally:
        ImageDraw.ImageDraw.text = orig
    if not sorun:
        print("✅ TAŞMA YOK")
    for (k, s), t in sorted(sorun.items(), key=lambda x: x[1]):
        print(f"⚠️  {t:5.1f}s {k:8} {s}")
    return sorun
