"""Bekçi: GitHub'ın zamanlayıcısı güvenilmez olduğu için, önümüzdeki saatlerdeki paylaşımları
dakikasında yapmak üzere bekler. Bir iş en fazla ~5 saat 50 dk çalışır; iki iş art arda zincirlenir.
Kullanım: python yayin/bekci.py <pencere_dakika>"""
import json, os, sys, time, subprocess, datetime as dt

KOK = os.path.dirname(os.path.abspath(__file__))
PENCERE = dt.timedelta(minutes=int(sys.argv[1]) if len(sys.argv) > 1 else 345)


def sh(*a):
    return subprocess.run(a, cwd=os.path.dirname(KOK), capture_output=True, text=True)


def bekleyenler(bitis):
    sh("git", "pull", "-q", "--rebase")
    takvim = json.load(open(os.path.join(KOK, "takvim.json"), encoding="utf-8"))
    try:
        kayit = json.load(open(os.path.join(KOK, "kayit.json"), encoding="utf-8"))
    except FileNotFoundError:
        kayit = {}
    simdi = dt.datetime.now(dt.timezone.utc)
    out = []
    for p in takvim:
        if p.get("durum") == "taslak":
            continue
        z = dt.datetime.fromisoformat(p["zaman"])
        if z > bitis:
            continue
        if all(kayit.get(f'{p["id"]}:{a}', {}).get("durum") == "yayinda" for a in p["aglar"]):
            continue
        if simdi - z > dt.timedelta(hours=6):
            continue
        out.append(z)
    return sorted(set(out))


def uyar():
    """Yeni bir paylaşım hatası varsa GitHub'da konu (issue) açar; GitHub sahibine bildirim/e-posta gönderir."""
    try:
        kayit = json.load(open(os.path.join(KOK, "kayit.json"), encoding="utf-8"))
    except FileNotFoundError:
        return
    simdi = dt.datetime.now(dt.timezone.utc)
    yeni = [(k, v) for k, v in kayit.items() if v.get("durum") == "hata" and not v.get("uyarildi")
            and simdi - dt.datetime.fromisoformat(v["zaman"]) < dt.timedelta(minutes=30)]
    if not yeni:
        return
    govde = "\n\n".join(f"**{k}**\n```\n{v.get('hata','')[:600]}\n```" for k, v in yeni)
    sh("gh", "issue", "create", "--title", f"Paylaşım hatası: {', '.join(k for k, _ in yeni)}",
       "--body", "Robot paylaşamadı. Claude'a haber ver.\n\n" + govde)
    for k, _ in yeni:
        kayit[k]["uyarildi"] = True
    json.dump(kayit, open(os.path.join(KOK, "kayit.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    bitis = dt.datetime.now(dt.timezone.utc) + PENCERE
    while True:
        zs = bekleyenler(bitis)
        if not zs:
            kalan = (bitis - dt.datetime.now(dt.timezone.utc)).total_seconds()
            print(f"Bu pencerede bekleyen paylaşım yok; pencere sonuna kadar {int(max(kalan,0))} sn bekleniyor.", flush=True)
            if kalan > 0:
                time.sleep(kalan)
            return
        z = zs[0]
        bekle = (z - dt.datetime.now(dt.timezone.utc)).total_seconds() - 20
        if bekle > 0:
            print(f"{z.isoformat()} için {int(bekle)} sn bekleniyor", flush=True)
            time.sleep(bekle)
        r = sh(sys.executable, os.path.join(KOK, "yayinla.py"))
        print(r.stdout[-3000:], r.stderr[-2000:], flush=True)
        uyar()
        sh("git", "add", "yayin/kayit.json")
        if sh("git", "diff", "--cached", "--quiet").returncode:
            sh("git", "commit", "-q", "-m", "yayin kaydi (bekci)")
            for _ in range(3):
                if sh("git", "push", "-q").returncode == 0:
                    break
                sh("git", "pull", "-q", "--rebase")
        time.sleep(30)


if __name__ == "__main__":
    main()
