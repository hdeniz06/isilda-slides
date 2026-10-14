"""Download the photos and app screenshots a slideshow needs.

Usage: python3 scripts/fetch_assets.py content/<id>.json
Photo source: PEXELS_API_KEY, else PIXABAY_API_KEY, else keyless Openverse (CC0/public domain). Runs in GitHub Actions (open internet).

- slide["photo"] = search query -> Pexels portrait photo, never reusing a photo id
  listed in history/photos_used.json
- slide type "app" -> App Store screenshot of the app (iTunes lookup by bundle id),
  slide["screenshot"] = index (default 0)
"""
import json, os, re, sys, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND = json.load(open(os.path.join(ROOT, "brand.json")))
HIST = os.path.join(ROOT, "history", "photos_used.json")
UA = {"User-Agent": "isilda-slides/1.0 (+https://github.com/hdeniz06/isilda-slides)"}
_ov_dead = False


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def download(url, path):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        f.write(r.read())


def openverse_pick(query, used):
    global _ov_dead
    if _ov_dead:
        return None
    """Keyless fallback: public-domain / CC0 photos via the Openverse API (no attribution needed)."""
    q = urllib.parse.urlencode({"q": query, "license": "cc0,pdm", "aspect_ratio": "tall",
                                "size": "large", "category": "photograph", "page_size": 40})
    data = get_json(f"https://api.openverse.org/v1/images/?{q}")
    for p in data.get("results", []):
        pid = "ov-" + p["id"]
        if pid in used or (p.get("height") or 0) < 1400:
            continue
        return {"id": pid, "src": p["url"], "url": p.get("foreign_landing_url", ""),
                "photographer": p.get("creator") or "", "provider": "openverse/" + (p.get("source") or "")}
    return None


def pixabay_pick(query, used, key):
    q = urllib.parse.urlencode({"key": key, "q": query, "image_type": "photo", "orientation": "vertical",
                                "per_page": 50, "safesearch": "true", "min_height": 1600})
    data = get_json(f"https://pixabay.com/api/?{q}")
    for p in data.get("hits", []):
        pid = "px-" + str(p["id"])
        if pid in used:
            continue
        return {"id": pid, "src": p.get("largeImageURL"), "url": p.get("pageURL", ""),
                "photographer": p.get("user", ""), "provider": "pixabay"}
    return None


def pexels_pick(query, used, key):
    for page in (1, 2, 3):
        q = urllib.parse.urlencode({"query": query, "orientation": "portrait", "per_page": 40, "page": page})
        data = get_json(f"https://api.pexels.com/v1/search?{q}", {"Authorization": key})
        for p in data.get("photos", []):
            if p["id"] in used or p["height"] < 1600:
                continue
            return p
    return None


def app_screenshots():
    a = BRAND["app_store"]
    q = urllib.parse.urlencode({"bundleId": a["bundle_id"], "country": a["country"]})
    res = get_json(f"https://itunes.apple.com/lookup?{q}")["results"]
    if not res:
        raise SystemExit("App not found on the App Store for " + a["bundle_id"])
    return res[0].get("screenshotUrls", []), res[0]


def main(content_path):
    data = json.load(open(content_path))
    sid = data["id"]
    out = os.path.join(ROOT, "build", "assets", sid)
    os.makedirs(out, exist_ok=True)
    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    hist = json.load(open(HIST)) if os.path.exists(HIST) else {}
    used = set(hist)
    shots = None

    for i, s in enumerate(data["slides"], 1):
        if s.get("photo") and data.get("style", "photo") == "photo":
            p = None
            try:
                if os.environ.get("PEXELS_API_KEY"):
                    r = pexels_pick(s["photo"], used, os.environ["PEXELS_API_KEY"])
                    if r:
                        p = {"id": str(r["id"]), "src": r["src"]["original"] + "?auto=compress&cs=tinysrgb&fit=crop&w=1080&h=1920",
                             "url": r["url"], "photographer": r["photographer"], "provider": "pexels"}
                if not p and os.environ.get("PIXABAY_API_KEY"):
                    p = pixabay_pick(s["photo"], used, os.environ["PIXABAY_API_KEY"])
                if not p:
                    p = openverse_pick(s["photo"], used)
            except Exception as e:
                print(f"slide {i}: photo search failed: {e}")
            if not p:
                print(f"slide {i}: no photo for '{s['photo']}', rendering without")
                continue
            try:
                download(p["src"], os.path.join(out, f"{i:02d}.jpg"))
            except Exception as e:
                print(f"slide {i}: download failed: {e}")
                continue
            used.add(p["id"])
            hist[p["id"]] = {"slideshow": sid, "query": s["photo"], "url": p["url"],
                             "photographer": p["photographer"], "provider": p["provider"]}
            print(f"slide {i}: {p['provider']} {p['id']} ({s['photo']})")
        if s["type"] == "app":
            if shots is None:
                try:
                    shots, _ = app_screenshots()
                except Exception as e:
                    print(f"app screenshots unavailable: {e}")
                    shots = []
            idx = s.get("screenshot", 0)
            if idx < len(shots):
                dst = os.path.join(out, f"{i:02d}-app.png")
                hi = re.sub(r"/\d+x\d+bb\.(jpg|png|webp)$", "/1290x2796bb.png", shots[idx])
                try:
                    download(hi, dst)
                except Exception:
                    download(shots[idx], dst)
                print(f"slide {i}: app screenshot {idx}")

    json.dump(hist, open(HIST, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
