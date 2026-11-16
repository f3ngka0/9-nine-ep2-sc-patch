import os
import re
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as d
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def main():
    p = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(p)
    all_keys_lower = {k.lower(): k for k in de}
    all_basenames_lower = {os.path.basename(k).lower() for k in de}

    print("=== TXT scripts calling exec/load/AutoPath/isExistent ===")
    for name in sorted(de):
        if not name.lower().endswith((".tjs", ".ks")):
            continue
        raw, _ = xp3.read_entry(p, de[name])
        txt = xp3.decode_txtobf(raw)
        if txt is not None:
            for m in re.finditer(r'(?:KAGLoadScript|execStorage|isExistentStorage|useArchiveIfExists|addArchive|addAutoPath\w*|Plugins\.link)\s*\(\s*["\']([^"\']+)["\']', txt):
                fn = m.group(1)
                exists = (fn.lower() in all_keys_lower) or (fn.lower() in all_basenames_lower)
                if not exists or "patch" in fn.lower() or "override" in fn.lower() or "config" in fn.lower():
                    print(f"  {name} -> {m.group(0)} (in_data_xp3={exists})")
        else:
            tdec = safe_decrypt_tjs2(raw)
            objs = d.parse_tjs2_objs(tdec)
            for idx, oname, code, consts in objs:
                for ci, c in enumerate(consts):
                    if isinstance(c, str) and (c.endswith((".tjs", ".ks", ".ini", ".xp3", ".dll")) or "/" in c) and not c.startswith("http"):
                        cl = c.lower()
                        exists = (cl in all_keys_lower) or (os.path.basename(cl) in all_basenames_lower) or (cl.rstrip("/") in all_basenames_lower)
                        if not exists and not cl.endswith((".dll", ".wav", ".ogg", ".png", ".pimg", ".scn")) and len(c) < 60:
                            print(f"  {name} OBJ[{idx}] ({oname}) str not in data.xp3: {c!r}")

if __name__ == "__main__":
    main()
