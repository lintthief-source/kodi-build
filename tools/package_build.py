"""Package the build zip from the live Kodi install (whitelist only) + overlay/.

Zip layout (extracted into Kodi's special://home by the wizard):
  addons/<id>/...   userdata/addon_data/...   media/screenshots/README.txt
Secrets, tokens, databases, caches and other skins' data are never included.
Usage: package_build.py          -> dist/silvo-build-<version>.zip
"""
import json, os, re, sys, zipfile
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KODI = os.path.join(os.environ["APPDATA"], "Kodi")
META = json.load(open(os.path.join(ROOT, "build.json"), encoding="utf8"))

ADDONS = [
    "skin.aeon.nox.silvo", "script.skinshortcuts", "script.skinvariables", "script.embuary.helper",
    "script.aeon.tajo.helper", "plugin.video.themoviedb.helper", "plugin.video.jellycon",
    "script.module.jurialmunkey", "script.module.infotagger", "script.module.simpleeval",
    "script.module.addon.signals", "script.module.pyqrcode", "script.module.defusedxml",
    "script.module.unidecode", "script.module.beautifulsoup4", "script.module.soupsieve",
    "resource.images.studios.white", "resource.images.recordlabels.white",
]
# addon_data folders to include, and per-folder file filter
DATA = {
    "skin.aeon.nox.silvo": lambda f: f == "settings.xml",
    "script.skinvariables": lambda f: f.startswith("skin.aeon.nox.silvo"),
    # other skins' menus are prefixed "skin.<id>-"; Silvo's are unprefixed. Hashes are rebuilt on device.
    "script.skinshortcuts": lambda f: not f.endswith(".hash") and (
        not f.startswith("skin.") or f.startswith("skin.aeon.nox.silvo")),
}
SKIP = re.compile(r"(__pycache__|\.pyc$|\.pyo$|\.orig$|\.git/)")

def portable(text):
    # image://C%3a%5cUsers%5c<u>%5cAppData%5cRoaming%5cKodi%5caddons%5c<x>/  ->  special://home/addons/<x>
    def fix(m):
        return "special://home/addons/" + unquote(m.group(1)).replace("\\", "/").rstrip("/")
    return re.sub(r"image://[A-Za-z]%3a%5cUsers%5c[^%]+%5cAppData%5cRoaming%5cKodi%5caddons%5c([^\"<]+?)/(?=[\"<])", fix, text)

def main():
    out_dir = os.path.join(ROOT, "dist"); os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "silvo-build-%s.zip" % META["version"])
    files = {}  # arcname -> source path or bytes
    for a in ADDONS:
        base = os.path.join(KODI, "addons", a)
        if not os.path.isdir(base):
            sys.exit("missing addon on this PC: " + a)
        for r, _, fs in os.walk(base):
            for f in fs:
                p = os.path.join(r, f); rel = os.path.relpath(p, KODI).replace("\\", "/")
                if not SKIP.search(rel): files[rel] = p
    for a, ok in DATA.items():
        base = os.path.join(KODI, "userdata", "addon_data", a)
        for f in os.listdir(base) if os.path.isdir(base) else []:
            if os.path.isfile(os.path.join(base, f)) and ok(f) and not re.search(r"madtitansports|sporthdme|oneplay|thecrew", f, re.I):
                files["userdata/addon_data/%s/%s" % (a, f)] = os.path.join(base, f)
    bdir = os.path.join(ROOT, "build_addons")                   # add-ons that live in this repo (Silvo Lists)
    for r, _, fs in os.walk(bdir):
        for f in fs:
            p = os.path.join(r, f)
            if not SKIP.search(p.replace("\\", "/")):
                files["addons/" + os.path.relpath(p, bdir).replace("\\", "/")] = p
    for r, _, fs in os.walk(os.path.join(ROOT, "media")):       # screenshots folder
        for f in fs:
            files["media/" + os.path.relpath(os.path.join(r, f), os.path.join(ROOT, "media")).replace("\\", "/")] = os.path.join(r, f)
    for r, _, fs in os.walk(os.path.join(ROOT, "overlay")):     # generated menus win over live files
        for f in fs:
            files[os.path.relpath(os.path.join(r, f), os.path.join(ROOT, "overlay")).replace("\\", "/")] = os.path.join(r, f)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for arc, src in sorted(files.items()):
            if arc.startswith("userdata/addon_data/script.skinshortcuts/") and arc.endswith((".xml", ".properties")):
                z.writestr(arc, portable(open(src, encoding="utf8").read()))
            else:
                z.write(src, arc)
        z.writestr("media/screenshots/.keep", "")
    print("%s  (%d files, %.1f MB)" % (out, len(files), os.path.getsize(out) / 1048576))

if __name__ == "__main__":
    main()
