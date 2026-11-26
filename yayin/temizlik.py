"""Son paylaşımları listeler; temizlik_sil.txt'deki kimlikleri siler. Jeton yazdırılmaz."""
import json, os, urllib.request, urllib.error, urllib.parse
API = "https://graph.facebook.com/v25.0"
def _t(ad):
    v = os.environ.get(ad, "").strip().strip('"').strip("'")
    return v[len(ad) + 1:] if v.upper().startswith(ad + "=") else v
T, IG, PAGE = _t("META_TOKEN"), _t("IG_USER_ID"), _t("FB_PAGE_ID")
KOK = os.path.dirname(os.path.abspath(__file__))

def call(method, path):
    sep = "&" if "?" in path else "?"
    req = urllib.request.Request(f"{API}/{path}{sep}access_token={T}", method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return {"ok": True, "veri": json.loads(r.read().decode())}
    except urllib.error.HTTPError as e:
        try:
            return {"ok": False, "hata": json.loads(e.read().decode()).get("error", {}).get("message")}
        except Exception:
            return {"ok": False, "hata": f"HTTP {e.code}"}

out = {}
sil_yol = os.path.join(KOK, "temizlik_sil.txt")
if os.path.exists(sil_yol):
    out["silinen"] = {}
    for line in open(sil_yol):
        i = line.split("#")[0].strip()
        if i:
            out["silinen"][i] = call("DELETE", i)
    os.remove(sil_yol)
out["ig_stories"] = call("GET", f"{IG}/stories?fields=id,timestamp,media_type,permalink")
out["ig_media"] = call("GET", f"{IG}/media?fields=id,timestamp,media_product_type,permalink&limit=8")
out["fb_reels"] = call("GET", f"{PAGE}/video_reels?fields=id,created_time,description&limit=6")
out["fb_stories"] = call("GET", f"{PAGE}/stories")
json.dump(out, open(os.path.join(KOK, "temizlik_sonuc.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok")
