"""Silvo Live TV - one list of the live TV add-ons. Only add-ons that are installed are shown."""
import sys
from urllib.parse import parse_qsl

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin

HANDLE = int(sys.argv[1])
BASE = sys.argv[0]
FANART = xbmcaddon.Addon().getAddonInfo("fanart")

# (add-on id, label override or None)
PVR = "pvr.iptvsimple"
ADDONS = ("plugin.video.madtitansports", "plugin.video.the-loop", "plugin.video.looptv", "plugin.video.loopguide",
          "plugin.video.sporthdme", "plugin.video.OnePlay.Matrix")


def info(addon_id):
    try:
        a = xbmcaddon.Addon(addon_id)
    except RuntimeError:
        return None
    return a.getAddonInfo("name"), a.getAddonInfo("icon"), a.getAddonInfo("fanart") or FANART, a.getAddonInfo("summary")


def add(label, url, icon, fanart, plot, folder):
    li = xbmcgui.ListItem(label)
    li.setArt({"thumb": icon, "icon": icon, "poster": icon, "fanart": fanart})
    li.getVideoInfoTag().setPlot(plot)
    if not folder:
        li.setProperty("IsPlayable", "false")
    xbmcplugin.addDirectoryItem(HANDLE, url, li, folder)


def main():
    params = dict(parse_qsl(sys.argv[2][1:]))
    if params.get("open") == "pvr":
        xbmc.executebuiltin("ActivateWindow(TVChannels)")
        return
    pvr = info(PVR)
    if pvr:
        add("Live TV (IPTV Simple Client)", BASE + "?open=pvr", pvr[1], FANART,
            "Your IPTV Simple Client channels and guide.", False)
    for addon_id in ADDONS:
        i = info(addon_id)
        if i:
            add(i[0], "plugin://%s/" % addon_id, i[1], i[2], i[3], True)
    xbmcplugin.setContent(HANDLE, "videos")
    xbmcplugin.endOfDirectory(HANDLE)


main()
