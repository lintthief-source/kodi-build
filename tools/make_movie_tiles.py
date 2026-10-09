"""Build the 'Silvo Movies' add-on content: one poster-collage tile per Jellyfin MOVIES library (folder).

Reads the libraries your Kodi/JellyCon user can see (JellyCon's stored login is used only to read library and image
data, never printed or saved) and writes into build_addons/plugin.video.silvomovies/resources/:
    folders.json                (tile order, library ids, art paths, the JellyCon link template)
    art/<slug>.jpg              (2x2 poster collage)   art/<slug>-fanart.jpg  (a backdrop)
Re-run whenever you add / rename a movie library or want fresh art.
"""
import io, json, os, re, sys, urllib.request
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KODI = os.path.join(os.environ["APPDATA"], "Kodi")
JC = os.path.join(KODI, "userdata", "addon_data", "plugin.video.jellycon")
ADDON = os.path.join(ROOT, "build_addons", "plugin.video.silvomovies")
ART = os.path.join(ADDON, "resources", "art")
W, H = 600, 900
ORDER = ["New Movies", "Christmas Movies", "Halloween Movies", "Family Movies", "Comedy Movies", "Action and Adventure Movies",
         "Sci-Fi and Fantasy Movies", "Horror and Thriller Movies", "Romance Movies", "Drama Movies"]

auth = json.load(open(os.path.join(JC, "auth.json"), encoding="utf8"))["Main"]
SERVER = re.search(r'id="server_address"[^>]*>([^<]*)<', open(os.path.join(JC, "settings.xml"), encoding="utf8").read()).group(1).strip()
HDR = {"Authorization": 'MediaBrowser Client="Kodi", Device="KodiBuildTools", DeviceId="kodibuildtools", Version="1.0", Token="%s"' % auth["token"],
       "Accept": "application/json"}


def get(path):
    return urllib.request.urlopen(urllib.request.Request(SERVER + path, headers=HDR), timeout=60).read()


def api(path):
    return json.loads(get(path))


def image(item_id, kind, width):
    return Image.open(io.BytesIO(get("/Items/%s/Images/%s?maxWidth=%d&quality=85" % (item_id, kind, width)))).convert("RGB")


def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((max(w, round(img.width * s)), max(h, round(img.height * s))), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def collage(posters):
    sheet = Image.new("RGB", (W, H), (11, 18, 32))
    n = len(posters)
    if n == 1:
        sheet.paste(cover(posters[0], W, H), (0, 0))
    elif n == 2:
        for i, p in enumerate(posters):
            sheet.paste(cover(p, W // 2, H), (i * W // 2, 0))
    elif n == 3:
        sheet.paste(cover(posters[0], W // 2, H), (0, 0))
        for i, p in enumerate(posters[1:]):
            sheet.paste(cover(p, W // 2, H // 2), (W // 2, i * H // 2))
    elif n >= 4:
        for i, p in enumerate(posters[:4]):
            sheet.paste(cover(p, W // 2, H // 2), ((i % 2) * W // 2, (i // 2) * H // 2))
    return sheet


def url_template():
    """The exact JellyCon link your 'Movies' item uses, with the library id swapped for {id}."""
    xml = open(os.path.join(KODI, "userdata", "addon_data", "script.skinshortcuts", "mainmenu.DATA.xml"), encoding="utf8").read()
    item = next(s for s in re.findall(r"\t<shortcut>.*?</shortcut>\n", xml, re.S) if "<defaultID>movies-showall</defaultID>" in s)
    action = re.search(r"<action>(.*?)</action>", item, re.S).group(1).replace("&amp;", "&")
    url = re.search(r'"(plugin://plugin\.video\.jellycon/[^"]+)"', action).group(1)
    if "plugin.video.jellycon" not in url or not re.search(r"ParentId%3D[0-9a-f]{32}", url):
        raise SystemExit("could not read the JellyCon movies link from the live menu")
    return re.sub(r"(ParentId%3D)[0-9a-f]{32}", r"\1{id}", url)


def main():
    uid = auth["user_id"]
    views = [v for v in api("/UserViews?userId=%s" % uid)["Items"] if v.get("CollectionType") == "movies"]
    os.makedirs(ART, exist_ok=True)
    tiles = []
    for v in views:
        items = api("/Items?userId=%s&ParentId=%s&Recursive=true&IncludeItemTypes=Movie&SortBy=DateCreated&SortOrder=Descending"
                    "&Fields=BackdropImageTags&Limit=60" % (uid, v["Id"]))["Items"]
        posters, fan = [], None
        for it in items:
            try:
                if it.get("ImageTags", {}).get("Primary") and len(posters) < 4:
                    posters.append(image(it["Id"], "Primary", 400))
                if not fan and it.get("BackdropImageTags"):
                    fan = image(it["Id"], "Backdrop", 1280)
            except Exception as e:      # noqa
                print("skip", it.get("Name"), e)
            if len(posters) == 4 and fan:
                break
        slug = re.sub(r"[^a-z0-9]+", "-", v["Name"].lower()).strip("-")
        if posters:
            collage(posters).save(os.path.join(ART, slug + ".jpg"), quality=88)
        if fan:
            fan.save(os.path.join(ART, slug + "-fanart.jpg"), quality=82)
        count = api("/Items?userId=%s&ParentId=%s&Recursive=true&IncludeItemTypes=Movie&Limit=1" % (uid, v["Id"]))["TotalRecordCount"]
        tiles.append({"name": v["Name"], "slug": slug, "id": v["Id"], "count": count,
                      "art": "resources/art/%s.jpg" % slug if posters else "", "fanart": "resources/art/%s-fanart.jpg" % slug if fan else ""})
        print("%-28s %3d movies, %d posters%s" % (v["Name"], count, len(posters), ", backdrop" if fan else ""))
    tiles.sort(key=lambda t: (ORDER.index(t["name"]) if t["name"] in ORDER else len(ORDER), t["name"]))
    json.dump({"url_template": url_template(), "folders": tiles}, open(os.path.join(ADDON, "resources", "folders.json"), "w", encoding="utf8"), indent=2)
    new = next((t for t in tiles if t["name"] == "New Movies"), None)
    print("New Movies library id:", new["id"] if new else "(none)")


if __name__ == "__main__":
    main()
