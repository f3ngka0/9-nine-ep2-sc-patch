import os
import re
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as d
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def main():
    # 1. Check overlap between adult.xp3 and data.xp3
    de = set(xp3.parse_xp3_entries(os.path.join(GAME_DIR, "data.xp3")).keys())
    ae = set(xp3.parse_xp3_entries(os.path.join(GAME_DIR, "adult.xp3")).keys())
    print("adult & data overlap:", sorted(de & ae))

    # 2. Check KAGEnvironment.tjs when envscript.tjs is called
    d_entries = xp3.parse_xp3_entries(os.path.join(GAME_DIR, "data.xp3"))
    raw, _ = xp3.read_entry(os.path.join(GAME_DIR, "data.xp3"), d_entries["system/KAGEnvironment.tjs"])
    objs = d.parse_tjs2_objs(safe_decrypt_tjs2(raw))
    print("\n=== KAGEnvironment.tjs OBJ[87] disasm ===")
    print(d.disasm_tjs2(objs[87][2], objs[87][3], 0, len(objs[87][2])))

    # 3. Check nine_sorairo.exe for option/log strings (-logerror, -debugwin, krkr.console.log, etc.)
    with open(os.path.join(GAME_DIR, "nine_sorairo.exe"), "rb") as f:
        exe = f.read()
    u16 = [m.decode("utf-16-le") for m in re.findall(rb"(?:[\x20-\x7e]\x00){4,}", exe)]
    print("\n=== Option/Log UTF-16 strings in exe ===")
    for s in sorted(set(u16)):
        sl = s.lower()
        if any(k in sl for k in ("log", "error", "console", "debug", "cf", "plugin", "xp3", "auto", "override")):
            if len(s) < 100 and not s.startswith(("TVP", "D3D", "TJS")):
                print(" ", repr(s))


if __name__ == "__main__":
    main()
