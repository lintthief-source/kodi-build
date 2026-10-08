"""Generate the Aeon Nox SiLVO main menu + widgets for the build.

Main bar (in order): Pictures, Music, Movies (JellyCon), TV Shows, Jellyfin TV, Add-ons, Settings, Power.
  * TV Shows        -> widget #1 = 'Silvo Lists' (poster-collage tile per Trakt list, incl. the to-watch lists).
                       Each tile opens the list full-screen in Silvo's Landscape view (52); seasons -> MyFlix (509),
                       episodes -> Episode (502).
  * Jellyfin TV     -> its own item; widget = JellyCon shows wall.
Writes into overlay/ (see package_build.py):
  userdata/addon_data/script.skinshortcuts/mainmenu.DATA.xml + skin.aeon.nox.silvo.properties
  userdata/addon_data/script.skinvariables/skin.aeon.nox.silvo-viewtypes.json  (TMDb Helper lists -> views 52/509/502)

Usage: make_menus.py [--apply]   (--apply copies overlay + build_addons into live Kodi; Kodi must be closed)
"""
import json, os, re, shutil, subprocess, sys, time
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KODI = os.path.join(os.environ["APPDATA"], "Kodi")
SS_LIVE = os.path.join(KODI, "userdata", "addon_data", "script.skinshortcuts")
OUT = os.path.join(ROOT, "overlay", "userdata", "addon_data", "script.skinshortcuts")
LISTS_URL = "plugin://plugin.video.silvolists/"
JELLY_ICON = "special://home/addons/plugin.video.jellycon/icon.png"
KEEP = ("pictures", "music", "tvshows", "programs", "settings", "power", "movies-showall")   # defaultIDs kept from the live menu
KEEP_LABELS = ("Movies - Show All",)                                        # custom (JellyCon) movies item
WIDGET_KEYS = ("widget", "widgetName", "widgetType", "widgetTarget", "widgetPath", "widgetStyle", "widgetCase",
               "widgetArt", "widgetBack", "widgetTitle", "widgetPanelInfo")


def item_id(label):
    return re.sub(r"[^a-z0-9]", "", label.lower())


def split_items(xml):
    return re.findall(r"\t<shortcut>.*?</shortcut>\n", xml, re.S)


def keep_item(s):
    if "<label2>Jellyfin</label2>" in s:
        return False                                   # regenerated below
    m = re.search(r"<defaultID>([^<]*)</defaultID>", s)
    if m and m.group(1) in KEEP:
        return True
    return any("<label>%s</label>" % l in s for l in KEEP_LABELS)


def jellyfin_widget(props):
    """Find the existing JellyCon shows widget (on TV Shows, as #1 or #2, or already on Jellyfin TV)."""
    for gid in ("jellyfintv", "tvshows"):
        for suffix in ("", ".2"):
            d = {k[: len(k) - len(suffix)] if suffix else k: v for g, i, k, v in props
                 if g == "mainmenu" and i == gid and k.startswith("widget") and k.endswith(suffix)
                 and (suffix or not k.endswith(".2"))}
            if "jellycon" in d.get("widgetPath", ""):
                return d
    sys.exit("could not find the JellyCon shows widget in the properties file")


def set_widget(props, iid, values):
    props[:] = [p for p in props if not (p[0] == "mainmenu" and p[1] == iid and p[2].startswith("widget"))]
    props.extend(["mainmenu", iid, k, v] for k, v in values.items())


def main_menu(props):
    jw = jellyfin_widget(props)
    jelly_path = re.sub(r"&reload=.*$", "", jw["widgetPath"])
    jelly_action = 'ActivateWindow(Videos,"%s",return)' % jelly_path
    jelly_xml = ("\t<shortcut>\n\t\t<defaultID />\n\t\t<label>Jellyfin TV</label>\n\t\t<label2>Jellyfin</label2>\n"
                 "\t\t<icon>DefaultShortcut.png</icon>\n\t\t<thumb>%s</thumb>\n\t\t<action>%s</action>\n\t\t</shortcut>\n"
                 % (JELLY_ICON, escape(jelly_action)))
    items = [s for s in split_items(open(os.path.join(SS_LIVE, "mainmenu.DATA.xml"), encoding="utf8").read()) if keep_item(s)]
    items = [s.replace("<label>Movies - Show All</label>", "<label>Movies</label>")
              .replace("<defaultID />", "<defaultID>movies-showall</defaultID>") if "Movies - Show All" in s else s
             for s in items]
    order = ("pictures", "music", "movies-showall", "tvshows", "Jellyfin TV", "programs", "settings", "power")
    items.append(jelly_xml)

    def rank(s):
        for n, key in enumerate(order):
            if "<defaultID>%s</defaultID>" % key in s or "<label>%s</label>" % key in s:
                return n
        return len(order)
    items.sort(key=rank)
    os.makedirs(OUT, exist_ok=True)
    xml_text = "<shortcuts>" + chr(10) + "".join(items) + chr(9) + "</shortcuts>" + chr(10)
    open(os.path.join(OUT, "mainmenu.DATA.xml"), "w", encoding="utf8", newline=chr(10)).write(xml_text)

    # properties: drop widgets/leftovers of removed items, give TV Shows the tiles and Jellyfin TV the shows wall
    kept_ids = {"1", "2", "music", "pictures", "movies-showall", "tvshows", "jellyfintv", "programs", "settings", "power",
                "31957", "13000", "33060"}   # numeric ids are the skin's own label ids for programs/settings/power
    props[:] = [p for p in props if p[0] != "mainmenu" or p[1] in kept_ids]
    props[:] = [p for p in props if p[0] not in ("tvshows", "movies-showall")]
    set_widget(props, "tvshows", {
        "widget": "Addon", "widgetName": "Trakt - My Lists", "widgetType": "videos", "widgetTarget": "videos",
        "widgetPath": LISTS_URL, "widgetStyle": "Panel", "widgetCase": "Glass", "widgetArt": "Poster",
        "widgetBack": "Default", "widgetTitle": "Panel", "widgetPanelInfo": "true"})
    props[:] = [p for p in props if not (p[0] == "mainmenu" and p[1] == "tvshows" and p[2].endswith(".2"))]
    jelly_widget = {k: v for k, v in jw.items() if k in WIDGET_KEYS}
    jelly_widget.update({"widgetStyle": "Panel", "widgetPanelInfo": "false"})   # no season/episode info card
    set_widget(props, "jellyfintv", jelly_widget)
    for k, v in (("translatedPath", jelly_action), ("icon", "DefaultShortcut.png"), ("thumb", JELLY_ICON)):
        props.append(["mainmenu", "jellyfintv", k, v])


VIEWS_LIVE = os.path.join(KODI, "userdata", "addon_data", "script.skinvariables", "skin.aeon.nox.silvo-viewtypes.json")
VIEWS_OUT = os.path.join(ROOT, "overlay", "userdata", "addon_data", "script.skinvariables", "skin.aeon.nox.silvo-viewtypes.json")
LIST_VIEW = "52"     # Silvo "Landscape" view (+ logo): series / lists
SEASON_VIEW = "509"  # MyFlix
EPISODE_VIEW = "502"  # Episode


def views_overlay():
    v = json.load(open(VIEWS_LIVE, encoding="utf8"))
    v.setdefault("plugin.video.themoviedb.helper", {}).update({"videos": LIST_VIEW, "tvshows": LIST_VIEW, "movies": LIST_VIEW,
                                                               "seasons": SEASON_VIEW, "episodes": EPISODE_VIEW})
    # appearance only: same views for The Crew's show / season / episode pages (does not install or enable anything)
    v.setdefault("plugin.video.thecrew", {}).update({"tvshows": LIST_VIEW, "seasons": SEASON_VIEW, "episodes": EPISODE_VIEW})
    os.makedirs(os.path.dirname(VIEWS_OUT), exist_ok=True)
    json.dump(v, open(VIEWS_OUT, "w", encoding="utf8"))


def set_setting(txt, sid, value, typ=None):
    """Set <setting id=sid>value</setting> in a Kodi settings.xml text (insert if missing)."""
    pat = re.compile(r'<setting id="%s"([^>]*)>[^<]*</setting>' % re.escape(sid), re.I)
    if pat.search(txt):
        return pat.sub(lambda m: '<setting id="%s"%s>%s</setting>' % (sid, re.sub(r'\sdefault="[^"]*"', "", m.group(1)), value), txt, 1)
    attr = ' type="%s"' % typ if typ else ""
    return txt.replace("</settings>", '    <setting id="%s"%s>%s</setting>\n</settings>' % (sid, attr, value))


def remove_settings(txt, pattern):
    return re.sub(r'[ \t]*<setting id="(?:%s)"[^>]*>[^<]*</setting>\r?\n?' % pattern, "", txt, flags=re.I)


def patch_skin_settings():
    """View options: status (watched) indicators stay on, HD/SD/3D flags off for the Landscape / MyFlix / Episode views,
    top bar on, default media flags, MyFlix cases off + info on + default dimmer, episode alternate layout."""
    sk = os.path.join(KODI, "userdata", "addon_data", "skin.aeon.nox.silvo", "settings.xml")
    txt = open(sk, encoding="utf8").read()
    for sid in ("noindicatorlist", "noindicatorfanartlist", "noindicatorwall", "noindicatorgallery", "noindicatorbiglist"):
        txt = set_setting(txt, sid, "true", "bool")
    txt = remove_settings(txt, r"(52|509|502)\.[A-Za-z]*\.?DisableOverlay|(52|509|502)\.NoTopBar|(52|509|502)\.[A-Za-z]+\.ViewFlags|MyFlix\.Dimmer")
    for sid, val in (("LandscapeWrapList", "false"), ("Enable.Landscape.Logo", "true"), ("Enable.MyFlix.Cases", "false"),
                     ("Disable.MyFlixInfo", "false"), ("alternatelayoutepisode", "true")):
        txt = set_setting(txt, sid, val, "bool")
    open(sk, "w", encoding="utf8", newline="").write(txt)


def patch_addon_settings():
    """TMDb Helper: use Trakt watched indicators. JellyCon: hide unwatched details. (The wizard does the same on
    other devices via setSetting - tokens/credentials in these files are never packaged.)"""
    for addon, sid, val in (("plugin.video.themoviedb.helper", "trakt_watchedindicators", "true"),
                            ("plugin.video.jellycon", "hide_unwatched_details", "false")):
        f = os.path.join(KODI, "userdata", "addon_data", addon, "settings.xml")
        os.makedirs(os.path.dirname(f), exist_ok=True)
        txt = open(f, encoding="utf8").read() if os.path.exists(f) else '<settings version="2">\n</settings>\n'
        open(f, "w", encoding="utf8", newline="").write(set_setting(txt, sid, val))


def main():
    props =json.load(open(os.path.join(SS_LIVE, "skin.aeon.nox.silvo.properties"), encoding="utf8"))
    main_menu(props)
    views_overlay()
    json.dump(props, open(os.path.join(OUT, "skin.aeon.nox.silvo.properties"), "w", encoding="utf8"), indent=4)
    print("wrote overlay: main menu = Pictures, Music, Movies, TV Shows, Jellyfin TV, Add-ons, Settings, Power")
    if "--apply" in sys.argv:
        if "kodi.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower():
            sys.exit("Kodi is running - close it first, then re-run with --apply")
        bak = os.path.join(ROOT, "backups", time.strftime("skinshortcuts-%Y%m%d-%H%M%S"))
        shutil.copytree(SS_LIVE, bak)
        for f in os.listdir(OUT):
            shutil.copy2(os.path.join(OUT, f), os.path.join(SS_LIVE, f))
        shutil.copy2(VIEWS_OUT, VIEWS_LIVE)
        # make script.skinvariables regenerate the skin's view includes on next start
        sk = os.path.join(KODI, "userdata", "addon_data", "skin.aeon.nox.silvo", "settings.xml")
        txt = open(sk, encoding="utf8").read()
        open(sk, "w", encoding="utf8", newline="").write(
            re.sub(r'[ \t]*<setting id="script-skinviewtypes-(checksum|hash)"[^>]*>[^<]*</setting>\r?\n?', "", txt))
        patch_skin_settings()
        patch_addon_settings()
        for stale in ("tvshows.DATA.xml", "startrek.DATA.xml"):       # leftover sub-menus from earlier layouts
            p = os.path.join(SS_LIVE, stale)
            if os.path.exists(p): os.remove(p)
        m = os.path.join(SS_LIVE, "movies-showall.DATA.xml")
        if os.path.exists(m):
            kept = [s for s in split_items(open(m, encoding="utf8").read()) if "<label2>Trakt List</label2>" not in s]
            open(m, "w", encoding="utf8", newline=chr(10)).write("<shortcuts>" + chr(10) + "".join(kept) + chr(9) + "</shortcuts>" + chr(10))
        h = os.path.join(SS_LIVE, "skin.aeon.nox.silvo.hash")
        if os.path.exists(h): os.remove(h)  # force skinshortcuts to rebuild the skin includes
        src = os.path.join(ROOT, "build_addons")                       # add-ons that ship in the build (Silvo Lists)
        for a in os.listdir(src):
            shutil.copytree(os.path.join(src, a), os.path.join(KODI, "addons", a), dirs_exist_ok=True)
        print("applied to Kodi; backup in", bak)


if __name__ == "__main__":
    main()
