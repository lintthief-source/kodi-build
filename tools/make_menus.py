"""Generate Aeon Nox SiLVO menu entries for every Trakt list.

Reads trakt_lists.json (see fetch_trakt_lists.py) and writes into overlay/:
  userdata/addon_data/script.skinshortcuts/tvshows.DATA.xml
  userdata/addon_data/script.skinshortcuts/movies-showall.DATA.xml   (if there are movie lists)
  userdata/addon_data/script.skinshortcuts/skin.aeon.nox.silvo.properties
Each list becomes a sub-menu item that opens the list (TMDb Helper) AND is widget #1 for
that item, so the shows appear as a poster wall.

Usage: make_menus.py [--apply]   (--apply copies overlay into live Kodi; Kodi must be closed)
"""
import json, os, re, shutil, subprocess, sys, time
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KODI = os.path.join(os.environ["APPDATA"], "Kodi")
SS_LIVE = os.path.join(KODI, "userdata", "addon_data", "script.skinshortcuts")
OUT = os.path.join(ROOT, "overlay", "userdata", "addon_data", "script.skinshortcuts")
TMDBH = "plugin://plugin.video.themoviedb.helper/"
ICON = "special://home/addons/plugin.video.themoviedb.helper/resources/icons/trakt/mylist.png"

def item_id(label):
    return re.sub(r"[^a-z0-9]", "", label.lower())

def list_url(slug):
    return f"{TMDBH}?info=trakt_userlist&list_slug={slug}"

def shortcut_xml(label, slug):
    action = f'ActivateWindow(Videos,"{list_url(slug)}",return)'
    return (f"\t<shortcut>\n\t\t<defaultID />\n\t\t<label>{escape(label)}</label>\n"
            f"\t\t<label2>Trakt List</label2>\n\t\t<icon>{ICON}</icon>\n\t\t<thumb>{ICON}</thumb>\n"
            f"\t\t<action>{escape(action)}</action>\n\t\t</shortcut>\n")

def props_for(group, label, slug):
    i, url = item_id(label), list_url(slug)
    action = f'ActivateWindow(Videos,"{url}",return)'
    rows = [("translatedPath", action), ("icon", ICON), ("thumb", ICON),
            ("widget", "Addon"), ("widgetName", f"Trakt - {label}"), ("widgetType", "videos"),
            ("widgetTarget", "videos"), ("widgetPath", url), ("widgetStyle", "Panel"),
            ("widgetCase", "Glass"), ("widgetArt", "Poster"), ("widgetBack", "Default"),
            ("widgetTitle", "Panel"), ("widgetPanelInfo", "true")]
    return [[group, i, k, v] for k, v in rows]

def build_group(group, lists, xml_name, props, keep_defaults_from=None):
    ids = {item_id(l["name"]) for l in lists}
    body = "".join(shortcut_xml(l["name"], l["slug"]) for l in lists)
    if keep_defaults_from and os.path.exists(keep_defaults_from):
        old = open(keep_defaults_from, encoding="utf8").read()
        old_items = re.findall(r"\t<shortcut>.*?</shortcut>\n", old, re.S)
        body += "".join(s for s in old_items
                        if not re.search(r"<label>(%s)</label>" % "|".join(re.escape(l["name"]) for l in lists), s))
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, xml_name), "w", encoding="utf8", newline="\n").write(f"<shortcuts>\n{body}\t</shortcuts>\n")
    props[:] = [p for p in props if not (p[0] == group and p[1] in ids)]
    for l in lists:
        props.extend(props_for(group, l["name"], l["slug"]))

def main():
    lists = json.load(open(os.path.join(ROOT, "trakt_lists.json"), encoding="utf8"))
    tv = [l for l in lists if l["shows"]]
    mv = [l for l in lists if l["movies"]]
    props = json.load(open(os.path.join(SS_LIVE, "skin.aeon.nox.silvo.properties"), encoding="utf8"))
    build_group("tvshows", tv, "tvshows.DATA.xml", props)
    if mv:
        build_group("movies-showall", mv, "movies-showall.DATA.xml", props,
                    keep_defaults_from=os.path.join(SS_LIVE, "movies-showall.DATA.xml"))
    json.dump(props, open(os.path.join(OUT, "skin.aeon.nox.silvo.properties"), "w", encoding="utf8"), indent=4)
    print(f"wrote overlay: {len(tv)} TV lists, {len(mv)} movie lists")
    if "--apply" in sys.argv:
        if "kodi.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower():
            sys.exit("Kodi is running - close it first, then re-run with --apply")
        bak = os.path.join(ROOT, "backups", time.strftime("skinshortcuts-%Y%m%d-%H%M%S"))
        shutil.copytree(SS_LIVE, bak)
        for f in os.listdir(OUT):
            shutil.copy2(os.path.join(OUT, f), os.path.join(SS_LIVE, f))
        h = os.path.join(SS_LIVE, "skin.aeon.nox.silvo.hash")
        if os.path.exists(h): os.remove(h)  # force skinshortcuts to rebuild the skin includes
        print("applied to Kodi; backup in", bak)

if __name__ == "__main__":
    main()
