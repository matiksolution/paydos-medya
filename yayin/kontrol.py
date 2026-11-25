"""Paylaşım yapmadan bağlantı kontrolü. Jetonu asla yazdırmaz; sonucu yayin/kontrol_sonuc.json'a yazar."""
import json, os, datetime as dt, urllib.request, urllib.error

API = "https://graph.facebook.com/v25.0"
T, IG, PAGE = (os.environ.get(k, "").strip() for k in ("META_TOKEN", "IG_USER_ID", "FB_PAGE_ID"))


def get(path):
    sep = "&" if "?" in path else "?"
    try:
        with urllib.request.urlopen(f"{API}/{path}{sep}access_token={T}", timeout=60) as r:
            return {"ok": True, "veri": json.loads(r.read().decode())}
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get("error", {})
            return {"ok": False, "hata": {k: err.get(k) for k in ("message", "type", "code", "error_subcode")}}
        except Exception:
            return {"ok": False, "hata": f"HTTP {e.code}"}


sonuc = {"zaman": dt.datetime.now(dt.timezone.utc).isoformat(),
         "secretler": {"META_TOKEN": bool(T), "IG_USER_ID": bool(IG), "FB_PAGE_ID": bool(PAGE)},
         # jetonun kendisi yazılmaz, sadece biçimi
         "jeton_bicimi": {"uzunluk": len(T), "EAA_ile_basliyor": T.startswith("EAA"),
                          "tirnak_var": any(c in T for c in "\"'"), "bosluk_var": any(c.isspace() for c in T),
                          "iki_nokta_var": ":" in T, "virgul_var": "," in T,
                          "harf_rakam_disi": sorted({c for c in T if not c.isalnum()})[:5] and len({c for c in T if not c.isalnum()})},
         "id_bicimi": {"IG_sadece_rakam": IG.isdigit(), "IG_uzunluk": len(IG),
                       "PAGE_sadece_rakam": PAGE.isdigit(), "PAGE_uzunluk": len(PAGE)}}
if T:
    sonuc["jeton_kimin"] = get("me?fields=id,name")
    if PAGE:
        sonuc["sayfa"] = get(f"{PAGE}?fields=id,name,instagram_business_account")
    if IG:
        sonuc["instagram"] = get(f"{IG}?fields=id,username,followers_count,media_count")
        sonuc["ig_kota"] = get(f"{IG}/content_publishing_limit?fields=quota_usage,config")
    s = sonuc
    me = s["jeton_kimin"].get("veri", {}).get("id")
    bagli = s.get("sayfa", {}).get("veri", {}).get("instagram_business_account", {}).get("id")
    s["ozet"] = {
        "jeton_sayfa_jetonu_mu": me == PAGE,
        "sayfa_okundu": s.get("sayfa", {}).get("ok", False),
        "instagram_okundu": s.get("instagram", {}).get("ok", False),
        "ig_id_sayfaya_bagli_olanla_ayni": bagli == IG if bagli else None,
        "paylasim_kotasi_okundu": s.get("ig_kota", {}).get("ok", False),
    }
json.dump(sonuc, open(os.path.join(os.path.dirname(__file__), "kontrol_sonuc.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(json.dumps(sonuc.get("ozet", sonuc["secretler"]), ensure_ascii=False))
