"""Silvo Lists - one tile per Trakt list, with poster-collage art.

Each tile opens the link built from the "List link template" add-on setting
(default: the list through TMDb Helper). {slug} and {name} are replaced per tile.
"""
import json
import os
import sys
from urllib.parse import quote

import xbmcaddon
import xbmcgui
import xbmcplugin

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
ROOT = ADDON.getAddonInfo("path")
DEFAULT_TEMPLATE = "plugin://plugin.video.themoviedb.helper/?info=trakt_userlist&list_slug={slug}"


def tile_url(template, tile):
    return template.replace("{slug}", tile["slug"]).replace("{name}", quote(tile["name"]))


def main():
    template = ADDON.getSetting("list_url_template").strip() or DEFAULT_TEMPLATE
    with open(os.path.join(ROOT, "resources", "lists.json"), encoding="utf8") as f:
        tiles = json.load(f)
    for t in tiles:
        li = xbmcgui.ListItem(t["name"])
        art = os.path.join(ROOT, t["art"])
        li.setArt({"thumb": art, "poster": art, "icon": art,
                   "fanart": os.path.join(ROOT, t["fanart"]) if t.get("fanart") else ADDON.getAddonInfo("fanart")})
        info = li.getVideoInfoTag()
        info.setTitle(t["name"])
        info.setPlot("Trakt list: %d shows, %d movies" % (t.get("shows", 0), t.get("movies", 0)))
        xbmcplugin.addDirectoryItem(HANDLE, tile_url(template, t), li, True)
    xbmcplugin.setContent(HANDLE, "videos")
    xbmcplugin.endOfDirectory(HANDLE)


main()
