"""Silvo Build Wizard - installs the Aeon Nox SiLVO + Trakt build from a GitHub release."""
import json
import os
import re
import sys
import time
import zipfile
from urllib.parse import parse_qsl, urlencode

import requests
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs

ADDON = xbmcaddon.Addon()
HANDLE = int(sys.argv[1])
BASE = sys.argv[0]
HOME = xbmcvfs.translatePath("special://home/")
TEMP = xbmcvfs.translatePath("special://temp/")
SCREENSHOTS = os.path.join(HOME, "media", "screenshots")
SKIN_ID = "skin.aeon.nox.silvo"
TRAKT_ADDON = "plugin.video.themoviedb.helper"


def log(msg):
    xbmc.log("[SilvoBuild] %s" % msg, xbmc.LOGINFO)


def url(**kw):
    return "%s?%s" % (BASE, urlencode(kw))


def fetch_builds():
    try:
        r = requests.get(ADDON.getSetting("builds_url"), timeout=20)
        r.raise_for_status()
        return r.json().get("builds", [])
    except Exception as e:  # noqa: BLE001 - show any network/parse problem to the user
        xbmcgui.Dialog().ok("Silvo Build Wizard", "Could not load the build list.\n%s" % e)
        return []


def add_item(label, params, folder=False, plot=""):
    li = xbmcgui.ListItem(label)
    li.setArt({"icon": ADDON.getAddonInfo("icon"), "fanart": ADDON.getAddonInfo("fanart")})
    if plot:
        li.setInfo("video", {"plot": plot})
    xbmcplugin.addDirectoryItem(HANDLE, url(**params), li, folder)


def menu():
    installed = ADDON.getSetting("installed_version") or "none"
    for b in fetch_builds():
        flag = "  [update available]" if installed not in ("none", b["version"]) else ""
        add_item("Install: %s  v%s%s" % (b["name"], b["version"], flag),
                 {"action": "install", "id": b["id"]},
                 plot="%s\nSize: %.0f MB\nInstalled version: %s" % (b.get("description", ""), b.get("size", 0) / 1048576, installed))
    add_item("Set list link template (where the TV Shows tiles open)", {"action": "template"},
             plot="Type or paste the link pattern the tiles open ({slug} = list name). Leave empty for the default (TMDb Helper). "
                  "Stored on this device only.")
    add_item("Install missing dependencies (fixes JellyCon / helper errors)", {"action": "deps"},
             plot="Installs any helper modules the add-ons in the build need from Kodi's repositories.")
    add_item("Authorize Trakt (TMDb Helper)", {"action": "trakt"})
    add_item("Settings", {"action": "settings"})
    xbmcplugin.endOfDirectory(HANDLE)


def download(src, dest, dlg):
    with requests.get(src, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done, t0 = 0, time.time()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=262144):
                if dlg.iscanceled():
                    raise RuntimeError("Download cancelled")
                f.write(chunk)
                done += len(chunk)
                if total:
                    speed = done / max(time.time() - t0, 1) / 1048576
                    dlg.update(int(done * 100 / total), "Downloading build...\n%.0f / %.0f MB  (%.1f MB/s)" % (done / 1048576, total / 1048576, speed))


def extract(zpath, dlg):
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
        root = os.path.realpath(HOME)
        for i, name in enumerate(names):
            target = os.path.realpath(os.path.join(HOME, name))
            if not target.startswith(root + os.sep):  # zip-slip guard
                continue
            if name.endswith("/"):
                os.makedirs(target, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(name) as src, open(target, "wb") as out:
                    out.write(src.read())
            if i % 50 == 0:
                dlg.update(int(i * 100 / len(names)), "Installing files...\n%d / %d" % (i, len(names)))
        return sorted({n.split("/")[1] for n in names if n.startswith("addons/") and n.count("/") >= 2})


def jsonrpc(method, params):
    return json.loads(xbmc.executeJSONRPC(json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})))


def addon_imports(addon_id):
    """Required (non-optional) dependencies of an add-on folder in special://home/addons, minus Kodi core."""
    try:
        with open(os.path.join(HOME, "addons", addon_id, "addon.xml"), encoding="utf8") as f:
            xml = f.read()
    except OSError:
        return []
    out = []
    for tag in re.findall(r"<import\s[^>]*>", xml):
        m = re.search(r'addon="([^"]+)"', tag)
        if m and 'optional="true"' not in tag and not m.group(1).startswith(("xbmc.", "kodi.")):
            out.append(m.group(1))
    return out


def install_dependencies(addon_ids, dlg=None):
    """Files copied in by the wizard are not dependency-resolved by Kodi, so install anything missing from the repos.
    Returns the list of dependencies that are still missing afterwards."""
    missing = []
    for a in addon_ids:
        for dep in addon_imports(a):
            if dep not in missing and not xbmc.getCondVisibility("System.HasAddon(%s)" % dep):
                missing.append(dep)
    still = []
    for n, dep in enumerate(missing):
        if dlg:
            dlg.update(int(n * 100 / max(len(missing), 1)), "Installing dependency %d / %d\n%s" % (n + 1, len(missing), dep))
        xbmc.executebuiltin("InstallAddon(%s)" % dep, True)
        xbmc.sleep(1500)
        if not xbmc.getCondVisibility("System.HasAddon(%s)" % dep):
            still.append(dep)
    return still


def fix_dependencies():
    """Menu action: scan every add-on in special://home/addons and install missing dependencies."""
    dlg = xbmcgui.DialogProgress()
    dlg.create("Silvo Build Wizard", "Checking dependencies...")
    ids = [d for d in os.listdir(os.path.join(HOME, "addons")) if os.path.isfile(os.path.join(HOME, "addons", d, "addon.xml"))]
    xbmc.executebuiltin("UpdateLocalAddons")
    xbmc.sleep(2000)
    still = install_dependencies(ids, dlg)
    dlg.close()
    xbmcgui.Dialog().ok("Silvo Build Wizard",
                        "All dependencies are installed.\nRestart Kodi to finish." if not still else
                        "Could not install: %s\nCheck your internet connection and try again." % ", ".join(still))


def post_install(addon_ids, dlg=None):
    os.makedirs(SCREENSHOTS, exist_ok=True)
    xbmc.executebuiltin("UpdateLocalAddons")
    xbmc.sleep(3000)
    still = install_dependencies(addon_ids, dlg)
    if still:
        xbmcgui.Dialog().ok("Silvo Build Wizard", "Some dependencies could not be installed:\n%s\nUse 'Install missing dependencies' in the wizard menu later." % ", ".join(still))
    for a in addon_ids:
        jsonrpc("Addons.SetAddonEnabled", {"addonid": a, "enabled": True})
    jsonrpc("Settings.SetSettingValue", {"setting": "debug.screenshotpath", "value": SCREENSHOTS + os.sep})
    for addon_id, setting, value in (("plugin.video.themoviedb.helper", "trakt_watchedindicators", "true"),
                                     ("plugin.video.jellycon", "hide_unwatched_details", "false")):
        try:
            xbmcaddon.Addon(addon_id).setSetting(setting, value)
        except Exception as e:  # noqa: BLE001 - add-on may not be loaded yet; not fatal
            log("could not set %s/%s: %s" % (addon_id, setting, e))
    jsonrpc("Settings.SetSettingValue", {"setting": "lookandfeel.skin", "value": SKIN_ID})


def install(build_id):
    build = next((b for b in fetch_builds() if b["id"] == build_id), None)
    if not build:
        return
    dialog = xbmcgui.Dialog()
    if not dialog.yesno("Install %s" % build["name"],
                        "This downloads about %.0f MB and overwrites the skin, menus and widgets.\nContinue?" % (build.get("size", 0) / 1048576)):
        return
    zpath = os.path.join(TEMP, "silvobuild.zip")
    dlg = xbmcgui.DialogProgress()
    dlg.create("Silvo Build Wizard", "Starting...")
    try:
        download(build["url"], zpath, dlg)
        addon_ids = extract(zpath, dlg)
    except Exception as e:  # noqa: BLE001
        dlg.close()
        dialog.ok("Silvo Build Wizard", "Install failed:\n%s" % e)
        return
    finally:
        if os.path.exists(zpath):
            os.remove(zpath)
    dlg.update(100, "Finishing up...")
    post_install(addon_ids, dlg)
    dlg.close()
    ADDON.setSetting("installed_version", build["version"])
    if dialog.yesno("Silvo Build Wizard",
                    "Build installed.\nTo see your Trakt lists, authorize Trakt in TMDb Helper.\nOpen the Trakt authorization now?"):
        xbmc.executebuiltin("RunScript(%s,authenticate_trakt)" % TRAKT_ADDON)
    if dialog.yesno("Silvo Build Wizard", "Set where the TV Shows list tiles open now?\n(You can also do this later from this wizard's menu.)"):
        set_template()
    if dialog.yesno("Silvo Build Wizard", "Kodi should restart to finish. Close Kodi now?\n(Then just open it again.)"):
        xbmc.executebuiltin("Quit")


def set_template():
    """Prompt for the Silvo Lists link template; empty restores the default. Device-local, never shipped."""
    try:
        lists = xbmcaddon.Addon("plugin.video.silvolists")
    except RuntimeError:
        xbmcgui.Dialog().ok("Silvo Build Wizard", "Silvo Lists is not installed or enabled yet. Install the build first.")
        return
    value = xbmcgui.Dialog().input("List link template ({slug} = list name; empty = default)",
                                   defaultt=lists.getSetting("list_url_template"))
    if value is None:
        return
    lists.setSetting("list_url_template", value.strip())
    xbmcgui.Dialog().notification("Silvo Build Wizard", "Template saved" if value.strip() else "Template reset to default", time=3000)


def main():
    params = dict(parse_qsl(sys.argv[2][1:]))
    action = params.get("action")
    if action == "deps":
        fix_dependencies()
    elif action == "template":
        set_template()
    elif action == "install":
        install(params["id"])
    elif action == "trakt":
        xbmc.executebuiltin("RunScript(%s,authenticate_trakt)" % TRAKT_ADDON)
    elif action == "settings":
        ADDON.openSettings()
    else:
        menu()


main()
