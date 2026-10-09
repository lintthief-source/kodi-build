"""Silvo Movies - one tile per Jellyfin movie library (folder), with poster-collage art. Opens the library via JellyCon."""
import json
import os
import sys

import xbmcaddon
import xbmcgui
import xbmcplugin

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
ROOT = ADDON.getAddonInfo("path")


def main():
    with open(os.path.join(ROOT, "resources", "folders.json"), encoding="utf8") as f:
        data = json.load(f)
    template = data["url_template"]
    for t in data["folders"]:
        li = xbmcgui.ListItem(t["name"])
        art = os.path.join(ROOT, t["art"]) if t.get("art") else ADDON.getAddonInfo("icon")
        fan = os.path.join(ROOT, t["fanart"]) if t.get("fanart") else ADDON.getAddonInfo("fanart")
        li.setArt({"thumb": art, "poster": art, "icon": art, "fanart": fan})
        info = li.getVideoInfoTag()
        info.setTitle(t["name"])
        info.setPlot("%d movie%s" % (t.get("count", 0), "" if t.get("count") == 1 else "s"))
        xbmcplugin.addDirectoryItem(HANDLE, template.replace("{id}", t["id"]), li, True)
    xbmcplugin.setContent(HANDLE, "videos")
    xbmcplugin.endOfDirectory(HANDLE)


main()
