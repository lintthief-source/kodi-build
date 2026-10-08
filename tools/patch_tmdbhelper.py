"""Idempotent fix for TMDb Helper 5.4.16 on Kodi 21: ListItem.setProperties() rejects non-str values
(TypeError in items/listitem.py get_listitem), which breaks every Trakt list. Converts keys/values to str.
Run with Kodi closed; re-run after any TMDb Helper update/reinstall."""
import os, shutil
p = os.path.join(os.environ["APPDATA"], "Kodi", "addons", "plugin.video.themoviedb.helper",
                 "resources", "tmdbhelper", "lib", "items", "listitem.py")
old = "        listitem.setProperties(self.infoproperties)\n"
new = "        listitem.setProperties({str(k): str(v) for k, v in self.infoproperties.items() if v is not None})  # patched: Kodi 21 needs str\n"
s = open(p, encoding="utf8", newline="").read()
nl = "\r\n" if "\r\n" in s else "\n"
if new.strip() in s:
    print("already patched")
else:
    old_n, new_n = old.replace("\n", nl), new.replace("\n", nl)
    assert old_n in s, "expected line not found - TMDb Helper changed?"
    if not os.path.exists(p + ".orig"): shutil.copy2(p, p + ".orig")
    open(p, "w", encoding="utf8", newline="").write(s.replace(old_n, new_n, 1))
    print("patched", p)
