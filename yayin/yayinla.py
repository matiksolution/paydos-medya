"""Paydos yayın robotu: yayin/takvim.json'daki zamanı gelmiş paylaşımları
Meta'nın resmi API'si ile Instagram ve Facebook'a gönderir. GitHub Actions her 15 dakikada çalıştırır.

Gerekli GitHub Secrets (Ayarlar > Secrets and variables > Actions):
  META_TOKEN   : Facebook sayfasının uzun ömürlü erişim anahtarı (asla sohbete yapıştırma)
  IG_USER_ID   : Instagram profesyonel hesap kimliği
  FB_PAGE_ID   : Facebook sayfa kimliği
"""
import json, os, sys, time, datetime as dt, urllib.request, urllib.parse

def _temiz(ad):
    """Secret'a yanlışlıkla 'AD=deger' yazılmışsa baştaki 'AD=' kısmını ve tırnak/boşlukları at."""
    v = os.environ.get(ad, "").strip().strip('"').strip("'")
    if v.upper().startswith(ad + "="):
        v = v[len(ad) + 1:].strip().strip('"').strip("'")
    return v


API = "https://graph.facebook.com/v25.0"
RAW = "https://raw.githubusercontent.com/matiksolution/paydos-medya/main/"
TOKEN = _temiz("META_TOKEN")
IG = _temiz("IG_USER_ID")
PAGE = _temiz("FB_PAGE_ID")
HERE = os.path.dirname(os.path.abspath(__file__))
TAKVIM = os.path.join(HERE, "takvim.json")
KAYIT = os.path.join(HERE, "kayit.json")
GEC_KALMA_SINIRI = dt.timedelta(hours=6)  # 6 saatten eski kaçmış paylaşımı atla, kendiliğinden geç gönderme


def req(method, url, data=None, headers=None):
    body = urllib.parse.urlencode(data).encode() if data and not isinstance(data, bytes) else data
    r = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{e.code}: {e.read().decode()[:500]}")


def ig_bekle(cid):
    for _ in range(60):
        s = req("GET", f"{API}/{cid}?fields=status_code,status&access_token={TOKEN}")
        if s.get("status_code") == "FINISHED":
            return
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram işleyemedi: {s}")
        time.sleep(10)
    raise RuntimeError("Instagram video işleme zaman aşımı")


def ig_reel(p):
    c = req("POST", f"{API}/{IG}/media", {
        "media_type": "REELS", "video_url": RAW + p["medya"], "caption": p.get("metin", ""),
        "share_to_feed": "true", "thumb_offset": str(p.get("kapak_ms", 0)),
        "is_ai_generated": "true" if p.get("ai_etiketi", True) else "false", "access_token": TOKEN})
    ig_bekle(c["id"])
    return req("POST", f"{API}/{IG}/media_publish", {"creation_id": c["id"], "access_token": TOKEN})


def ig_story(p):
    url = RAW + p["medya"]
    key = "video_url" if url.lower().endswith(".mp4") else "image_url"
    c = req("POST", f"{API}/{IG}/media", {"media_type": "STORIES", key: url, "access_token": TOKEN,
                                           "is_ai_generated": "true" if p.get("ai_etiketi", False) else "false"})
    ig_bekle(c["id"])
    return req("POST", f"{API}/{IG}/media_publish", {"creation_id": c["id"], "access_token": TOKEN})


def fb_reel(p):
    s = req("POST", f"{API}/{PAGE}/video_reels", {"upload_phase": "start", "access_token": TOKEN})
    vid = s["video_id"]
    req("POST", s["upload_url"], b"", {"Authorization": f"OAuth {TOKEN}", "file_url": RAW + p["medya"]})
    return req("POST", f"{API}/{PAGE}/video_reels", {
        "upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED",
        "description": p.get("metin", ""), "access_token": TOKEN})


ISLEM = {("instagram", "reel"): ig_reel, ("instagram", "story"): ig_story, ("facebook", "reel"): fb_reel}


def main():
    if not (TOKEN and IG and PAGE):
        print("META_TOKEN / IG_USER_ID / FB_PAGE_ID tanımlı değil; çıkıyorum."); return 0
    takvim = json.load(open(TAKVIM, encoding="utf-8"))
    kayit = json.load(open(KAYIT, encoding="utf-8")) if os.path.exists(KAYIT) else {}
    simdi = dt.datetime.now(dt.timezone.utc)
    degisti = False
    for p in takvim:
        zaman = dt.datetime.fromisoformat(p["zaman"])
        if zaman > simdi:
            continue
        for ag in p["aglar"]:
            k = f'{p["id"]}:{ag}'
            if kayit.get(k, {}).get("durum") == "yayinda":
                continue
            if simdi - zaman > GEC_KALMA_SINIRI:
                if k not in kayit:
                    kayit[k] = {"durum": "atlandi", "neden": "zamanı 6 saatten fazla geçmişti"}; degisti = True
                continue
            try:
                sonuc = ISLEM[(ag, p["tur"])](p)
                kayit[k] = {"durum": "yayinda", "sonuc": sonuc, "zaman": simdi.isoformat()}
                print("YAYINDA", k, sonuc)
            except Exception as e:  # noqa
                kayit[k] = {"durum": "hata", "hata": str(e)[:500], "zaman": simdi.isoformat()}
                print("HATA", k, e)
            degisti = True
    if degisti:
        json.dump(kayit, open(KAYIT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
