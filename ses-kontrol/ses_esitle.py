"""Paydos Usta ses eşitleme: kaydın perdesini sabit hedefe (148 Hz) çeker, formantları korur.
Kullanım: python3 ses_esitle.py girdi.mp3 cikti.wav"""
import sys, subprocess
from ses_kontrol import profile
HEDEF_HZ = 148.0
src, dst = sys.argv[1], sys.argv[2]
f0 = profile(src)["perde_hz"]
ratio = HEDEF_HZ / f0
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af",
                f"rubberband=pitch={ratio:.5f}:formant=preserved:pitchq=quality:transients=smooth", "-ar", "48000", "-ac", "1", dst], check=True)
print(f"{src}: {f0:.1f} Hz -> x{ratio:.4f}")
