"""Generate the hover backgrounds for the Aeon Nox SiLVO main menu: media/menubg/<name>.jpg (1920x1080 mosaics).

Sources (all already on this PC, plus TMDb backdrops for Movies / TV Shows using the key in the HA LCARS config,
which is never written anywhere):
  movies   TMDb popular-movie backdrops          tvshows  Silvo Lists fanarts + TMDb popular-TV backdrops
  jellyfin Jellyfin backdrops cached by Kodi      livetv   live add-on fanarts + cached IPTV channel logos
  music    cached fanart.tv artist backdrops      pictures cached landscape backdrops
  addons   fanart of installed video add-ons      settings/power  darkened skin / blurred mosaics
Usage: make_menu_backgrounds.py
"""
import io, json, os, random, re, sqlite3, urllib.request
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KODI = os.path.join(os.environ["APPDATA"], "Kodi")
THUMBS = os.path.join(KODI, "userdata", "Thumbnails")
OUT = os.path.join(ROOT, "media", "menubg")
ART = os.path.join(ROOT, "build_addons", "plugin.video.silvolists", "resources", "art")
KEY = re.search(r"TMDB_API_KEY\s*=\s*'([^']+)'", open(r"Z:/www/lcars-config.js", encoding="utf8").read()).group(1)
W, H, COLS, ROWS, GAP = 1920, 1080, 4, 3, 6
LIVE_ADDONS = ("plugin.video.madtitansports", "plugin.video.looptv", "plugin.video.the-loop", "plugin.video.loopguide",
               "plugin.video.sporthdme", "plugin.video.OnePlay.Matrix")
rnd = random.Random(7)


def cached(url_like):
    db = sqlite3.connect("file:" + os.path.join(KODI, "userdata", "Database", "Textures13.db") + "?mode=ro", uri=True)
    rows = db.execute("select t.cachedurl, s.width, s.height from texture t join sizes s on s.idtexture=t.id where t.url like ?",
                      (url_like,)).fetchall()
    return [(os.path.join(THUMBS, c.replace("/", os.sep)), w, h) for c, w, h in rows if os.path.exists(os.path.join(THUMBS, c.replace("/", os.sep)))]


def tmdb_backdrops(kind, n):
    url = "https://api.themoviedb.org/3/%s/popular?api_key=%s" % (kind, KEY)
    out = []
    for item in json.load(urllib.request.urlopen(url, timeout=30))["results"]:
        if item.get("backdrop_path") and len(out) < n:
            data = urllib.request.urlopen("https://image.tmdb.org/t/p/w780" + item["backdrop_path"], timeout=30).read()
            out.append(Image.open(io.BytesIO(data)).convert("RGB"))
    return out


def load(paths):
    imgs = []
    for p in paths:
        try:
            imgs.append(Image.open(p).convert("RGB"))
        except OSError:
            pass
    return imgs


def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((max(w, round(img.width * s)), max(h, round(img.height * s))), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def logo_tile(path, w, h):
    tile = Image.new("RGB", (w, h), (18, 24, 38))
    try:
        logo = Image.open(path).convert("RGBA")
        logo.thumbnail((w * 6 // 10, h * 6 // 10))
        tile.paste(logo, ((w - logo.width) // 2, (h - logo.height) // 2), logo)
    except OSError:
        pass
    return tile


def mosaic(tiles, dim=0.55):
    """4x3 grid, tiles cover-cropped, darkened, with a bottom + left shade so menu text and widgets stay readable."""
    tiles = list(tiles)
    rnd.shuffle(tiles)
    while len(tiles) < COLS * ROWS:
        tiles += tiles
    tw, th = (W - GAP * (COLS - 1)) // COLS, (H - GAP * (ROWS - 1)) // ROWS
    sheet = Image.new("RGB", (W, H), (6, 8, 14))
    for i in range(COLS * ROWS):
        sheet.paste(cover(tiles[i], tw, th), ((i % COLS) * (tw + GAP), (i // COLS) * (th + GAP)))
    sheet = ImageEnhance.Brightness(sheet).enhance(dim)
    shade = Image.new("L", (1, H))
    for y in range(H):
        shade.putpixel((0, y), int(185 * max(0, (y - H * 0.35) / (H * 0.65)) ** 1.3))
    sheet.paste(Image.new("RGB", (W, H), (4, 6, 12)), (0, 0), shade.resize((W, H)))
    return sheet


def save(name, img):
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name + ".jpg"), quality=84)
    print("wrote", name)


def landscape(rows, min_w=1000):
    return [p for p, w, h in rows if w >= min_w and w > h * 1.4]


def main():
    local_fanarts = [os.path.join(ART, f) for f in os.listdir(ART) if f.endswith("-fanart.jpg")]
    addon_fanarts = [os.path.join(KODI, "addons", a, "fanart.jpg") for a in LIVE_ADDONS]
    all_video = [os.path.join(KODI, "addons", d, "fanart.jpg") for d in os.listdir(os.path.join(KODI, "addons"))
                 if d.startswith(("plugin.video.", "plugin.program.", "script.")) and os.path.exists(os.path.join(KODI, "addons", d, "fanart.jpg"))]
    all_land = landscape(cached("%"))
    jelly = landscape(cached("http://192.168.1.106:8096/%/Images/Backdrop/%"), 700)
    fanart_tv = landscape(cached("https://assets.fanart.tv/%"), 700)
    logos = [p for p, w, h in cached("image://pvrchannel_tv@%") if w >= 120]

    save("movies", mosaic(tmdb_backdrops("movie", 12)))
    save("tvshows", mosaic(load(local_fanarts) + tmdb_backdrops("tv", 8)))
    save("jellyfintv", mosaic(load(rnd.sample(jelly, min(12, len(jelly))))))
    seen, unique = set(), []                       # the three Loop add-ons share one fanart
    for p in addon_fanarts:
        h = os.path.getsize(p)
        if h not in seen:
            seen.add(h); unique.append(p)
    live = load(unique) + [logo_tile(p, 640, 360) for p in rnd.sample(logos, 12 - len(unique))]
    save("livetv", mosaic(live))
    save("music", mosaic(load(rnd.sample(fanart_tv, min(12, len(fanart_tv))))))
    save("pictures", mosaic(load(rnd.sample(all_land, 12))))
    save("addons", mosaic(load(rnd.sample(all_video, min(12, len(all_video))))))
    settings = Image.open(os.path.join(KODI, "addons", "skin.aeon.nox.silvo", "extras", "backgrounds", "default_settings.jpg")).convert("RGB")
    save("settings", mosaic([cover(settings, W, H)] * (COLS * ROWS), 0.5))
    power = mosaic(load(rnd.sample(all_land, 12)), 0.4).filter(ImageFilter.GaussianBlur(14))
    save("power", ImageEnhance.Brightness(power).enhance(0.7))


if __name__ == "__main__":
    main()
