"""Add hover backgrounds to every main-menu item and point Live TV at the Silvo Live TV add-on list.

Reads the LIVE skinshortcuts data (the source of truth, edited by hand since make_menus.py), changes only:
  * mainmenu.<id> `background` / `backgroundName`  -> special://home/media/menubg/<name>.jpg
  * Live TV (31502): action opens plugin.video.silvolivetv; widget = that list. Its sub-menu (IPTV Simple groups) is untouched.
Writes the result to overlay/ (so package_build.py ships it); --apply also copies it + media/menubg + the add-on into live Kodi
(Kodi must be closed, because Kodi rewrites these files on exit).
Usage: patch_menu_live.py [--apply]
"""
import json, os, re, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KODI = os.path.join(os.environ["APPDATA"], "Kodi")
SS = os.path.join(KODI, "userdata", "addon_data", "script.skinshortcuts")
OUT = os.path.join(ROOT, "overlay", "userdata", "addon_data", "script.skinshortcuts")
BG = "special://home/media/menubg/%s.jpg"
IDS = {"1": "pictures", "music": "music", "movies": "movies", "movies-showall": "movies", "tvshows": "tvshows",
       "jellyfintv": "jellyfintv", "31502": "livetv", "31957": "addons", "13000": "settings", "33060": "power"}
LIVE_PLUGIN = "plugin://plugin.video.silvolivetv/"
LIVE_ACTION = 'ActivateWindow(Videos,"%s",return)' % LIVE_PLUGIN
LIVE_WIDGET = {"widget": "Addon", "widgetName": "Live TV", "widgetType": "videos", "widgetTarget": "videos",
               "widgetPath": LIVE_PLUGIN, "widgetStyle": "Panel", "widgetCase": "Glass", "widgetArt": "FanArt",
               "widgetBack": "Default", "widgetTitle": "Panel", "widgetPanelInfo": "false"}


def main():
    props = json.load(open(os.path.join(SS, "skin.aeon.nox.silvo.properties"), encoding="utf8"))
    present = {p[1] for p in props if p[0] == "mainmenu"}
    props[:] = [p for p in props if not (p[0] == "mainmenu" and p[2] in ("background", "backgroundName"))]
    props[:] = [p for p in props if not (p[0] == "mainmenu" and p[1] == "31502" and p[2].startswith("widget"))]
    for iid, name in IDS.items():
        if iid in present or iid in ("1", "music", "tvshows", "jellyfintv", "31502", "31957", "13000", "33060"):
            props.append(["mainmenu", iid, "background", BG % name])
            props.append(["mainmenu", iid, "backgroundName", {"livetv": "Live TV", "tvshows": "TV Shows", "jellyfintv": "Jellyfin TV"}.get(name, name.capitalize())])
    props.extend(["mainmenu", "31502", k, v] for k, v in LIVE_WIDGET.items())

    menu = open(os.path.join(SS, "mainmenu.DATA.xml"), encoding="utf8").read()
    menu, n = re.subn(r"(<defaultID>livetv</defaultID>.*?<action>)[^<]*(</action>)",
                      lambda m: m.group(1) + LIVE_ACTION.replace("&", "&amp;") + m.group(2), menu, count=1, flags=re.S)
    if n != 1:
        sys.exit("livetv item not found in the live mainmenu.DATA.xml")

    os.makedirs(OUT, exist_ok=True)
    json.dump(props, open(os.path.join(OUT, "skin.aeon.nox.silvo.properties"), "w", encoding="utf8"), indent=4)
    open(os.path.join(OUT, "mainmenu.DATA.xml"), "w", encoding="utf8", newline="\n").write(menu)
    print("overlay written (backgrounds on %d items, Live TV -> add-on list)" % len({p[1] for p in props if p[2] == "background"}))

    if "--apply" in sys.argv:
        if "kodi.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower():
            sys.exit("Kodi is running - close it first, then re-run with --apply")
        bak = os.path.join(ROOT, "backups", time.strftime("skinshortcuts-%Y%m%d-%H%M%S"))
        shutil.copytree(SS, bak)
        for f in ("skin.aeon.nox.silvo.properties", "mainmenu.DATA.xml"):
            shutil.copy2(os.path.join(OUT, f), os.path.join(SS, f))
        h = os.path.join(SS, "skin.aeon.nox.silvo.hash")
        if os.path.exists(h):
            os.remove(h)                                                # force skinshortcuts to rebuild the skin includes
        shutil.copytree(os.path.join(ROOT, "media", "menubg"), os.path.join(KODI, "media", "menubg"), dirs_exist_ok=True)
        shutil.copytree(os.path.join(ROOT, "build_addons", "plugin.video.silvolivetv"),
                        os.path.join(KODI, "addons", "plugin.video.silvolivetv"), dirs_exist_ok=True)
        print("applied; backup in", bak)


if __name__ == "__main__":
    main()
