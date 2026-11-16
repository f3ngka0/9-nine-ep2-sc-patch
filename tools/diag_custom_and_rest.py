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
    all_keys_lower = {k.lower() for k in de}
    all_basenames_lower = {os.path.basename(k).lower() for k in de}

    print("=== main/custom.tjs full ===")
    raw, _ = xp3.read_entry(p, de["main/custom.tjs"])
    print(xp3.decode_txtobf(raw))

    print("\n=== main/default.tjs tail (lines after 150) ===")
    raw2, _ = xp3.read_entry(p, de["main/default.tjs"])
    dtxt = xp3.decode_txtobf(raw2)
    print("\n".join(dtxt.splitlines()[130:]))

    print("\n=== Remaining TJS2 optional files check ===")
    for name in sorted(de):
        if not name.lower().endswith((".tjs", ".ks")) or name <= "sysscn/exroll.tjs":
            continue
        raw, _ = xp3.read_entry(p, de[name])
        if xp3.decode_txtobf(raw) is not None:
            continue
        try:
            tdec = safe_decrypt_tjs2(raw)
            objs = d.parse_tjs2_objs(tdec)
            for idx, oname, code, consts in objs:
                for c in consts:
                    if isinstance(c, str) and (c.endswith((".tjs", ".ks", ".ini", ".xp3")) or "Override" in c or "AfterInit" in c):
                        cl = c.lower()
                        exists = (cl in all_keys_lower) or (os.path.basename(cl) in all_basenames_lower)
                        if not exists:
                            print(f"  {name} OBJ[{idx}] ({oname}) str not in data.xp3: {c!r}")
        except Exception as e:
            print(f"  {name}: parse err {e}")

    print("\n=== krkrsteam.dll & PackinOne.dll UTF-16 + relevant ASCII ===")
    for dll in ("krkrsteam.dll", "PackinOne.dll"):
        with open(os.path.join(GAME_DIR, "plugin", dll), "rb") as f:
            b = f.read()
        u16 = sorted(set(s.decode("utf-16-le") for s in re.findall(rb"(?:[\x20-\x7e]\x00){4,}", b)))
        print(f"--- {dll} U16 ({len(u16)}) ---")
        for s in u16:
            if not s.startswith(("Microsoft", "kernel32", "api-ms")):
                print(" ", repr(s))


if __name__ == "__main__":
    main()
