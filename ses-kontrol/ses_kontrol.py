"""NOT: Perde kaydırma (ses_esitle.py) yankı yaptığı için KULLANILMIYOR. Tutarsız kayıt yeniden üretilir.
Paydos Usta ses kontrolü: her kaydın ses profilini çıkarır ve referansla karşılaştırır.
Kullanım: python3 ses_kontrol.py ref.mp3 aday1.mp3 [aday2.mp3 ...]
Ölçülenler: perde (ortanca + oynaklık), konuşma hızı (hece/sn), tını (spektral merkez), enerji dinamiği, duraklama oranı.
"""
import sys, subprocess
import numpy as np
import librosa

SR = 22050
VOWELS = set("aeıioöuüAEIİOÖUÜ")


def load(f):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(r, np.float32).copy()


def profile(f):
    y = load(f)
    f0, vflag, _ = librosa.pyin(y, fmin=60, fmax=300, sr=SR, frame_length=2048, hop_length=512)
    f0 = f0[vflag & ~np.isnan(f0)]
    semis = 12 * np.log2(f0 / np.median(f0))
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    db = 20 * np.log10(rms + 1e-6)
    speech = db > (db.max() - 35)
    cent = librosa.feature.spectral_centroid(y=y, sr=SR, hop_length=512)[0][speech]
    # hece çekirdekleri ~ enerji tepe sayısı (konuşma hızı tahmini)
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=256)
    peaks = librosa.util.peak_pick(env, pre_max=3, post_max=3, pre_avg=5, post_avg=5, delta=0.35, wait=4)
    dur_speech = speech.sum() * 512 / SR
    # yankı/kuyruk: kelime bitişlerinden 60-120 ms sonra kalan enerji (yüksek = yankılı/çamurlu)
    h = 80 * SR // 16000
    e = np.array([np.sqrt(np.mean(y[i:i + h] ** 2)) for i in range(0, len(y) - h, h)])
    d2 = 20 * np.log10(e + 1e-7)
    tails = [np.mean(d2[i + 8:i + 20]) - d2[i - 5] for i in range(10, len(d2) - 30) if d2[i - 5] > -25 and d2[i + 5] < d2[i - 5] - 20]
    return dict(
        yanki_db=float(np.median(tails)) if tails else 0.0,
        perde_hz=float(np.median(f0)),
        perde_oynaklik=float(np.percentile(semis, 90) - np.percentile(semis, 10)),
        hiz=float(len(peaks) / dur_speech),
        tini_hz=float(np.median(cent)),
        dinamik_db=float(np.percentile(db[speech], 95) - np.percentile(db[speech], 20)),
        duraklama=float(1 - speech.mean()),
    )


# izin verilen sapma (referansa göre)
TOL = dict(yanki_db=("abs", 3.0), perde_hz=("%", 6), perde_oynaklik=("%", 20), hiz=("%", 10), tini_hz=("%", 10), dinamik_db=("abs", 3.0), duraklama=("abs", 0.08))
NAMES = dict(yanki_db="Yankı (kuyruk)", perde_hz="Perde", perde_oynaklik="Tonlama genişliği", hiz="Konuşma hızı", tini_hz="Tını (parlaklık)", dinamik_db="Ses dinamiği", duraklama="Duraklama oranı")


def compare(ref, cand):
    out = []
    for k, (kind, tol) in TOL.items():
        d = (cand[k] - ref[k]) / ref[k] * 100 if kind == "%" else cand[k] - ref[k]
        out.append((k, d, abs(d) <= tol))
    return out


if __name__ == "__main__":
    files = sys.argv[1:]
    profs = {f: profile(f) for f in files}
    ref = profs[files[0]]
    print(f"REFERANS: {files[0]}")
    print("  " + "  ".join(f"{NAMES[k]}={v:.2f}" for k, v in ref.items()))
    for f in files[1:]:
        res = compare(ref, profs[f])
        ok = all(r[2] for r in res)
        print(f"\n{'✅' if ok else '⚠️ '} {f}")
        for k, d, good in res:
            unit = "%" if TOL[k][0] == "%" else ""
            print(f"   {'ok ' if good else 'FARK'} {NAMES[k]:<18} {d:+6.1f}{unit}   ({profs[f][k]:.2f})")
