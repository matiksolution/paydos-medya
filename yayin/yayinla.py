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


def _liste(p):
    m = p["medya"]
    return m if isinstance(m, list) else [m]


def ig_post(p):
    """Tek görsel ya da kaydırmalı (en fazla 10 JPEG)."""
    ai = "true" if p.get("ai_etiketi", False) else "false"
    ms = _liste(p)[:10]
    if len(ms) == 1:
        c = req("POST", f"{API}/{IG}/media", {"image_url": RAW + ms[0], "caption": p.get("metin", ""),
                                              "is_ai_generated": ai, "access_token": TOKEN})
    else:
        kids = []
        for m in ms:
            k = req("POST", f"{API}/{IG}/media", {"image_url": RAW + m, "is_carousel_item": "true", "access_token": TOKEN})
            kids.append(k["id"])
        for k in kids:
            ig_bekle(k)
        c = req("POST", f"{API}/{IG}/media", {"media_type": "CAROUSEL", "children": ",".join(kids),
                                              "caption": p.get("metin", ""), "is_ai_generated": ai, "access_token": TOKEN})
    ig_bekle(c["id"])
    return req("POST", f"{API}/{IG}/media_publish", {"creation_id": c["id"], "access_token": TOKEN})


def fb_post(p):
    ms = _liste(p)[:10]
    if len(ms) == 1:
        return req("POST", f"{API}/{PAGE}/photos", {"url": RAW + ms[0], "caption": p.get("metin", ""), "access_token": TOKEN})
    ids = [req("POST", f"{API}/{PAGE}/photos", {"url": RAW + m, "published": "false", "access_token": TOKEN})["id"] for m in ms]
    data = {"message": p.get("metin", ""), "access_token": TOKEN}
    for i, x in enumerate(ids):
        data[f"attached_media[{i}]"] = json.dumps({"media_fbid": x})
    return req("POST", f"{API}/{PAGE}/feed", data)


def fb_story(p):
    url = RAW + _liste(p)[0]
    if url.lower().endswith(".mp4"):
        s = req("POST", f"{API}/{PAGE}/video_stories", {"upload_phase": "start", "access_token": TOKEN})
        req("POST", s["upload_url"], b"", {"Authorization": f"OAuth {TOKEN}", "file_url": url})
        return req("POST", f"{API}/{PAGE}/video_stories", {"upload_phase": "finish", "video_id": s["video_id"], "access_token": TOKEN})
    ph = req("POST", f"{API}/{PAGE}/photos", {"url": url, "published": "false", "access_token": TOKEN})
    return req("POST", f"{API}/{PAGE}/photo_stories", {"photo_id": ph["id"], "access_token": TOKEN})


ISLEM = {("instagram", "reel"): ig_reel, ("instagram", "story"): ig_story, ("facebook", "reel"): fb_reel,
         ("instagram", "post"): ig_post, ("facebook", "post"): fb_post, ("facebook", "story"): fb_story}
ERKEN = dt.timedelta(minutes=0)   # saatinde paylaşımı bekçi yapar; zamanlayıcı yalnızca yedek
EN_FAZLA_DENEME = 3


def main():
    if not (TOKEN and IG and PAGE):
        print("META_TOKEN / IG_USER_ID / FB_PAGE_ID tanımlı değil; çıkıyorum."); return 0
    takvim = json.load(open(TAKVIM, encoding="utf-8"))
    kayit = json.load(open(KAYIT, encoding="utf-8")) if os.path.exists(KAYIT) else {}
    simdi = dt.datetime.now(dt.timezone.utc)
    degisti = False
    for p in takvim:
        zaman = dt.datetime.fromisoformat(p["zaman"])
        if zaman > simdi + ERKEN or p.get("durum") == "taslak":
            continue
        for ag in p["aglar"]:
            k = f'{p["id"]}:{ag}'
            onceki = kayit.get(k, {})
            if onceki.get("durum") == "yayinda" or onceki.get("deneme", 0) >= EN_FAZLA_DENEME:
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
                kayit[k] = {"durum": "hata", "hata": str(e)[:500], "zaman": simdi.isoformat(),
                            "deneme": onceki.get("deneme", 0) + 1}
                print("HATA", k, e)
            degisti = True
    if degisti:
        json.dump(kayit, open(KAYIT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
