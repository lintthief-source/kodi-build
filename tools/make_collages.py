"""Generate poster-collage tile art for the 'Silvo Lists' add-on from trakt_lists.json.

For every list: build_addons/plugin.video.silvolists/resources/art/<slug>.jpg  (2x2 poster collage, 2:3)
                                                                   <slug>-fanart.jpg (first item's backdrop)
and resources/lists.json (the tile order + art paths).
Posters come from TMDb using the key in the HA LCARS config; the key is never written anywhere.
"""
import io, json, os, re, sys, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(ROOT, "build_addons", "plugin.video.silvolists")
ART = os.path.join(ADDON, "resources", "art")
KEY = re.search(r"TMDB_API_KEY\s*=\s*'([^']+)'", open(r"Z:/www/lcars-config.js", encoding="utf8").read()).group(1)
IMG = "https://image.tmdb.org/t/p/"
FIRST_TILES = ("tv-shows-to-watch", "movies-to-watch")   # shown first in the widget
W, H = 600, 900                                           # tile size; 2x2 posters of 300x450

def tmdb(path):
    sep = "&" if "?" in path else "?"
    return json.load(urllib.request.urlopen("https://api.themoviedb.org/3/%s%sapi_key=%s" % (path, sep, KEY), timeout=30))

def image(path):
    return Image.open(io.BytesIO(urllib.request.urlopen(IMG + path, timeout=30).read())).convert("RGB")

def details(item):
    kind = "tv" if item["type"] == "show" else "movie"
    return tmdb("%s/%s" % (kind, item["tmdb"]))

def main():
    lists = json.load(open(os.path.join(ROOT, "trakt_lists.json"), encoding="utf8"))
    os.makedirs(ART, exist_ok=True)
    lists.sort(key=lambda l: (l["slug"] not in FIRST_TILES, FIRST_TILES.index(l["slug"]) if l["slug"] in FIRST_TILES else 0))
    tiles = []
    for l in lists:
        posters, fanart = [], None
        for it in l["first"]:
            if not it.get("tmdb"): continue
            try:
                d = details(it)
                if d.get("poster_path") and len(posters) < 4: posters.append(image("w342" + d["poster_path"]))
                if not fanart and d.get("backdrop_path"): fanart = image("w1280" + d["backdrop_path"])
            except Exception as e:
                print("skip", it["title"], e)
            if len(posters) == 4 and fanart: break
        sheet = Image.new("RGB", (W, H), (11, 18, 32))
        for n, p in enumerate(posters):
            sheet.paste(p.resize((W // 2, H // 2)), ((n % 2) * W // 2, (n // 2) * H // 2))
        sheet.save(os.path.join(ART, l["slug"] + ".jpg"), quality=88)
        if fanart: fanart.save(os.path.join(ART, l["slug"] + "-fanart.jpg"), quality=82)
        tiles.append({"name": l["name"], "slug": l["slug"], "art": "resources/art/%s.jpg" % l["slug"],
                      "fanart": "resources/art/%s-fanart.jpg" % l["slug"] if fanart else "",
                      "shows": l["shows"], "movies": l["movies"]})
        print(l["name"], len(posters), "posters")
    json.dump(tiles, open(os.path.join(ADDON, "resources", "lists.json"), "w", encoding="utf8"), indent=2)

if __name__ == "__main__":
    main()
