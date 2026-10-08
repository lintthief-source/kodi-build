# Silvo Build

Kodi 21 build: Aeon Nox SiLVO + every Trakt list as a menu item / poster-wall widget (via TMDb Helper),
a screenshots folder, and a wizard add-on that installs it on any device.

## Install on a device (Xbox, Android TV, PC...)
1. Kodi > Settings > File manager > Add source > `https://lintthief-source.github.io/kodi-build/` > name it `silvo`.
2. Settings > Add-ons > Install from zip file > `silvo` > `repository.silvobuild` > `repository.silvobuild-1.0.0.zip`.
3. Install from repository > Silvo Build Repository > Program add-ons > **Silvo Build Wizard**.
4. Open the wizard > *Install: Aeon Nox SiLVO + Trakt*. Authorize Trakt when prompted; restart Kodi.

## Update the build (on the PC)
```
python tools/fetch_trakt_lists.py trakt_lists.json   # refresh Trakt lists (needs Kodi + HA share)
python tools/make_menus.py [--apply]                 # regenerate menus (--apply writes to live Kodi; close Kodi first)
# bump "version" in build.json, then:
python tools/package_build.py                        # dist/silvo-build-<ver>.zip
python tools/generate_repo.py                        # docs/ (repo + builds.json)
gh release create build-v<ver> dist/silvo-build-<ver>.zip   # upload the zip, then commit + push docs/
```
Bump the wizard/repo version in `src/*/addon.xml` when you change them.

## What is NOT in the build
Trakt/TMDb tokens, databases, caches, Jellyfin logins, and other skins' data. Authorize Trakt (TMDb Helper) and
log in to JellyCon once per device.

## Silvo Lists tiles
The TV Shows widget is the `Silvo Lists` add-on (poster collage per Trakt list; regenerate art with
`python tools/make_collages.py`). Where a tile opens is set per device in
Add-ons > My add-ons > Video add-ons > Silvo Lists > Configure > *List link template* (`{slug}` / `{name}` placeholders).
