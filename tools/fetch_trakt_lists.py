"""Fetch the user's Trakt lists (name, slug, counts, first items' TMDb ids) using the token Kodi's
The Crew already stored plus the Trakt app client id from the HA LCARS config.
Writes list metadata only - never prints or saves the token."""
import json, os, re, sys, urllib.request
kodi = os.path.join(os.environ["APPDATA"], "Kodi")
st = open(os.path.join(kodi, "userdata/addon_data/plugin.video.thecrew/settings.xml"), encoding="utf8").read()
def get(i):
    m = re.search(r'id="%s"[^>]*>([^<]*)<' % re.escape(i), st); return m.group(1).strip() if m else ""
token = get("trakt.token")
cid = re.search(r"TRAKT_CLIENT_ID\s*=\s*'([0-9A-Za-z_-]+)'", open(r"Z:/www/lcars-config.js", encoding="utf8").read()).group(1)
def api(path):
    req = urllib.request.Request("https://api.trakt.tv" + path, headers={
        "Content-Type": "application/json", "trakt-api-version": "2", "trakt-api-key": cid,
        "Authorization": "Bearer " + token, "User-Agent": "KodiBuildTools/1.0"})
    return json.load(urllib.request.urlopen(req, timeout=30))
out = []
for l in api("/users/me/lists"):
    slug = l["ids"]["slug"]
    items = api("/users/me/lists/%s/items" % slug)
    first = [{"type": i["type"], "title": i[i["type"]]["title"], "tmdb": i[i["type"]]["ids"].get("tmdb")}
             for i in items if i["type"] in ("show", "movie")][:8]
    out.append({"name": l["name"], "slug": slug, "privacy": l["privacy"],
                "shows": sum(i["type"] == "show" for i in items),
                "movies": sum(i["type"] == "movie" for i in items), "first": first})
json.dump(out, open(sys.argv[1], "w"), indent=2)
for l in out: print({k: v for k, v in l.items() if k != "first"})
