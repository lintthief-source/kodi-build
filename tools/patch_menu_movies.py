"""Movies main-menu item: click -> list of movie folders (Silvo Movies add-on), hover -> 'New Movies' library as widget.

Works on the LIVE skinshortcuts data (the source of truth since make_menus.py; it keeps Live TV, hover backgrounds and
any items you added by hand) and changes ONLY the Movies item (id movies-showall):
    action / translatedPath -> plugin://plugin.video.silvomovies/        (tiles for every Jellyfin movie library)
    widget #1               -> JellyCon 'New Movies' library, newest first (Panel / Poster)
and maps the tiles page to Silvo's Landscape view.
Needs build_addons/plugin.video.silvomovies (run make_movie_tiles.py first).

Writes overlay/ for packaging (never containing items that point at the add-ons in PACKAGE_EXCLUDE).
--apply also updates the live Kodi files + installs the add-on (Kodi must be closed; a backup is made first).
"""
import json, os, re, shutil, sqlite3, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KODI = os.path.join(os.environ["APPDATA"], "Kodi")
SS = os.path.join(KODI, "userdata", "addon_data", "script.skinshortcuts")
VT = os.path.join(KODI, "userdata", "addon_data", "script.skinvariables", "skin.aeon.nox.silvo-viewtypes.json")
OUT = os.path.join(ROOT, "overlay", "userdata", "addon_data")
ADDON_DIR = os.path.join(ROOT, "build_addons", "plugin.video.silvomovies")
ADDON_ID = "plugin.video.silvomovies"
MOVIES_ID = "movies-showall"
ACTION = 'ActivateWindow(Videos,"plugin://%s/",return)' % ADDON_ID
TILES_VIEW = "52"   # Silvo Landscape view for the folder tiles page
# menu items that point straight at these add-ons are kept in YOUR Kodi but never written into the packaged overlay
PACKAGE_EXCLUDE = ("plugin.video.thecrew", "plugin.video.madtitansports", "plugin.video.sporthdme", "plugin.video.OnePlay.Matrix")
# defaultIDs of main-menu items removed from the menu on request (Pictures; the 'Popular Movies' item)
REMOVE_FROM_MENU = {"pictures", "plugin.video.madtitansports/get_list/trakt/movies/popular"}
WIDGET_KEYS = ("widget", "widgetName", "widgetType", "widgetTarget", "widgetPath", "widgetStyle", "widgetCase",
               "widgetArt", "widgetBack", "widgetTitle", "widgetPanelInfo")


def items_of(xml):
    return re.findall(r"\t<shortcut>.*?</shortcut>\n", xml, re.S)


def new_movies_path():
    d = json.load(open(os.path.join(ADDON_DIR, "resources", "folders.json"), encoding="utf8"))
    lib = next((t for t in d["folders"] if t["name"] == "New Movies"), None)
    if not lib:
        sys.exit("No 'New Movies' library found - create it in Jellyfin, give your Kodi user access, then run make_movie_tiles.py")
    url = d["url_template"].replace("{id}", lib["id"])
    return url.replace("%26ParentId", "%26SortBy%3DDateCreated%26SortOrder%3DDescending%26ParentId", 1)


MOVIES_PID = "plugin.video.silvomovies/"    # Silvo derives an item's id from its plugin action, so properties live here
LIVE_PID = "plugin.video.silvolivetv/"
BG = "special://home/media/menubg/%s.jpg"
FAVOURITES_WIDGET = {"widget": "library", "widgetName": "Favourites", "widgetType": "favourite", "widgetTarget": "videos",
                     "widgetPath": "favourites://", "widgetStyle": "Panel", "widgetCase": "Glass", "widgetArt": "Square Poster",
                     "widgetBack": "Default", "widgetTitle": "Panel", "widgetPanelInfo": "false"}


def is_movies(s):
    return "<defaultID>%s</defaultID>" % MOVIES_ID in s or "plugin.video.silvomovies" in s


def set_props(props, ids, values, strip=WIDGET_KEYS + ("background", "backgroundName", "translatedPath")):
    """Replace the given properties for the main-menu item(s) `ids` (several ids = stale ones are cleaned up)."""
    props = [p for p in props if not (p[0] == "mainmenu" and p[1] in ids and p[2] in strip)]
    props.extend(["mainmenu", ids[-1], k, v] for k, v in values.items())
    return props


def patch(menu, props):
    """Return (menu_xml, props) with the Movies and Live TV items fixed up (works on copies)."""
    items = items_of(menu)
    n = 0
    for i, s in enumerate(items):
        if is_movies(s):
            items[i] = re.sub(r"<action>.*?</action>", lambda m: "<action>" + ACTION.replace("&", "&amp;") + "</action>", s, count=1, flags=re.S)
            n += 1
    if n != 1:
        sys.exit("Movies item not found in the live mainmenu.DATA.xml")
    gone, kept = set(), []
    for s in items:      # items you asked to remove from the main menu
        d = (re.search(r"<defaultID>([^<]*)</defaultID>", s) or [None, ""])[1]
        if d in REMOVE_FROM_MENU:
            gone.add(d)
        else:
            kept.append(s)
    items = kept
    menu = "<shortcuts>\n" + "".join(items) + "\t</shortcuts>\n"
    gone_ids = {"1" if g == "pictures" else g for g in gone}      # Pictures is item id "1" in the properties file
    props = [p for p in props if not (p[0] == "mainmenu" and p[1] in gone_ids)]

    # Movies: click -> folder tiles, hover -> New Movies (same widget settings you chose by hand), plus the hover background
    movies = {"translatedPath": ACTION, "widget": "Addon", "widgetName": "New Movies", "widgetType": "movies",
              "widgetTarget": "videos", "widgetPath": new_movies_path(), "widgetStyle": "Extended Panel",
              "widgetArt": "Poster", "widgetCase": "Case", "background": BG % "movies", "backgroundName": "Movies"}
    props = set_props(props, [MOVIES_ID, MOVIES_PID], movies)
    # Live TV: hover background + Kodi Favourites as the widget (each device keeps its own favourites)
    live = dict(FAVOURITES_WIDGET, background=BG % "livetv", backgroundName="Live TV")
    props = set_props(props, ["31502", LIVE_PID], live)
    return menu, props


def package_copy(menu, props):
    """Same data without items that point at PACKAGE_EXCLUDE add-ons."""
    kept, dropped_ids = [], set()
    for s in items_of(menu):
        if any(a in s for a in PACKAGE_EXCLUDE):
            dropped_ids.add((re.search(r"<defaultID>([^<]*)</defaultID>", s) or [None, ""])[1])
            continue
        kept.append(s)
    menu = "<shortcuts>\n" + "".join(kept) + "\t</shortcuts>\n"
    props = [p for p in props if not (p[0] == "mainmenu" and p[1] in dropped_ids and p[1])]
    props = [p for p in props if not any(a in str(p[3]) for a in PACKAGE_EXCLUDE)]
    return menu, props, dropped_ids


def viewtypes():
    v = json.load(open(VT, encoding="utf8"))
    v.setdefault(ADDON_ID, {}).update({"videos": TILES_VIEW})
    return v


def enable_in_db(addon_id):
    db = os.path.join(KODI, "userdata", "Database", "Addons33.db")
    c = sqlite3.connect(db)
    row = c.execute("select id from installed where addonID=?", (addon_id,)).fetchone()
    if row:
        c.execute("update installed set enabled=1, disabledReason=0 where addonID=?", (addon_id,))
    else:
        c.execute("insert into installed (addonID, enabled, installDate, origin, disabledReason) values (?,1,?,'',0)",
                  (addon_id, time.strftime("%Y-%m-%d %H:%M:%S")))
    c.commit()
    c.close()


def main():
    menu = open(os.path.join(SS, "mainmenu.DATA.xml"), encoding="utf8").read()
    props = json.load(open(os.path.join(SS, "skin.aeon.nox.silvo.properties"), encoding="utf8"))
    menu2, props2 = patch(menu, props)
    vt = viewtypes()
    pm, pp, dropped = package_copy(menu2, props2)

    os.makedirs(os.path.join(OUT, "script.skinshortcuts"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "script.skinvariables"), exist_ok=True)
    open(os.path.join(OUT, "script.skinshortcuts", "mainmenu.DATA.xml"), "w", encoding="utf8", newline="\n").write(pm)
    json.dump(pp, open(os.path.join(OUT, "script.skinshortcuts", "skin.aeon.nox.silvo.properties"), "w", encoding="utf8"), indent=4)
    json.dump(vt, open(os.path.join(OUT, "script.skinvariables", "skin.aeon.nox.silvo-viewtypes.json"), "w", encoding="utf8"))
    print("overlay written. Movies -> %s ; hover widget = New Movies. Kept out of the package: %s" % (ACTION, sorted(dropped) or "nothing"))

    if "--apply" in sys.argv:
        if "kodi.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower():
            sys.exit("Kodi is running - close it first, then re-run with --apply")
        bak = os.path.join(ROOT, "backups", time.strftime("skinshortcuts-%Y%m%d-%H%M%S"))
        shutil.copytree(SS, bak)
        shutil.copy2(VT, bak + "-viewtypes.json")
        open(os.path.join(SS, "mainmenu.DATA.xml"), "w", encoding="utf8", newline="\n").write(menu2)      # live keeps your other items
        json.dump(props2, open(os.path.join(SS, "skin.aeon.nox.silvo.properties"), "w", encoding="utf8"), indent=4)
        json.dump(vt, open(VT, "w", encoding="utf8"))
        sk = os.path.join(KODI, "userdata", "addon_data", "skin.aeon.nox.silvo", "settings.xml")
        txt = open(sk, encoding="utf8").read()
        open(sk, "w", encoding="utf8", newline="").write(
            re.sub(r'[ \t]*<setting id="script-skinviewtypes-(checksum|hash)"[^>]*>[^<]*</setting>\r?\n?', "", txt))
        h = os.path.join(SS, "skin.aeon.nox.silvo.hash")
        if os.path.exists(h):
            os.remove(h)
        shutil.copytree(ADDON_DIR, os.path.join(KODI, "addons", ADDON_ID), dirs_exist_ok=True)
        enable_in_db(ADDON_ID)
        print("applied to Kodi; backup in", bak)


if __name__ == "__main__":
    main()
