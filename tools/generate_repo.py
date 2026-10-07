"""Build the Kodi repository under docs/ (served via raw.githubusercontent / GitHub Pages):
zips every addon in src/, writes addons.xml + .md5, builds.json and an index.html listing."""
import hashlib, json, os, re, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC, DOCS = os.path.join(ROOT, "src"), os.path.join(ROOT, "docs")
META = json.load(open(os.path.join(ROOT, "build.json"), encoding="utf8"))
os.makedirs(DOCS, exist_ok=True)
entries, links = [], []
for aid in sorted(os.listdir(SRC)):
    base = os.path.join(SRC, aid)
    xml = open(os.path.join(base, "addon.xml"), encoding="utf8").read()
    ver = re.search(r'<addon[^>]*\sversion="([^"]+)"', xml).group(1)
    entries.append(re.sub(r"^<\?xml[^>]*\?>\s*", "", xml).strip())
    zdir = os.path.join(DOCS, aid); os.makedirs(zdir, exist_ok=True)
    zpath = os.path.join(zdir, "%s-%s.zip" % (aid, ver))
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for r, _, fs in os.walk(base):
            for f in fs:
                if f.endswith((".pyc",)) or "__pycache__" in r: continue
                p = os.path.join(r, f); z.write(p, os.path.join(aid, os.path.relpath(p, base)).replace("\\", "/"))
    for ex in ("icon.png",):  # Kodi shows these in the repo browser
        if os.path.exists(os.path.join(base, ex)): open(os.path.join(zdir, ex), "wb").write(open(os.path.join(base, ex), "rb").read())
    links.append("%s/%s-%s.zip" % (aid, aid, ver))
addons = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n%s\n</addons>\n' % "\n".join(entries)
open(os.path.join(DOCS, "addons.xml"), "w", encoding="utf8", newline="\n").write(addons)
open(os.path.join(DOCS, "addons.xml.md5"), "w").write(hashlib.md5(addons.encode("utf8")).hexdigest())
bz = os.path.join(ROOT, "dist", "silvo-build-%s.zip" % META["version"])
size = os.path.getsize(bz) if os.path.exists(bz) else 0
json.dump({"builds": [{"id": META["id"], "name": META["name"], "version": META["version"],
    "description": META["description"], "size": size,
    "url": "https://github.com/%s/releases/download/build-v%s/silvo-build-%s.zip" % (META["github"], META["version"], META["version"])}]},
    open(os.path.join(DOCS, "builds.json"), "w", encoding="utf8"), indent=2)
open(os.path.join(DOCS, "index.html"), "w", encoding="utf8").write(
    "<!doctype html><html><head><meta charset=utf-8><title>Silvo Build Repository</title></head><body>\n<h1>Silvo Build Repository</h1>\n"
    + "\n".join('<a href="%s">%s</a><br>' % (l, l) for l in links) + "\n</body></html>\n")
print("repo ready:", links)
