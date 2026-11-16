import os
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as d
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def main():
    p = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(p)

    # 1. Check steam_r18hack.tjs
    sp = os.path.join(GAME_DIR, "steam.xp3")
    se = xp3.parse_xp3_entries(sp)
    r, _ = xp3.read_entry(sp, se["steam_r18hack.tjs"])
    objs = d.parse_tjs2_objs(safe_decrypt_tjs2(r))
    print("=== steam_r18hack.tjs ===")
    for i, o in enumerate(objs):
        print(f"--- OBJ[{i}] {o[1]} ---")
        print(d.disasm_tjs2(o[2], o[3], 0, len(o[2])))

    # 2. Check KAGEnvironment.tjs OBJ[87]
    r2, _ = xp3.read_entry(p, de["system/KAGEnvironment.tjs"])
    o2 = d.parse_tjs2_objs(safe_decrypt_tjs2(r2))
    print("\n=== KAGEnvironment.tjs OBJ[87] (envscript.tjs?) ===")
    print("consts:", [c for c in o2[87][3] if isinstance(c, str)])

    # 3. Check Initialize.tjs OBJ[10]..OBJ[12] (setupSubFolders etc.)
    r3, _ = xp3.read_entry(p, de["system/Initialize.tjs"])
    o3 = d.parse_tjs2_objs(safe_decrypt_tjs2(r3))
    print("\n=== Initialize.tjs OBJ[10..12] ===")
    for i in (10, 11, 12):
        print(f"--- OBJ[{i}] {o3[i][1]} ---")
        print(d.disasm_tjs2(o3[i][2], o3[i][3], 0, len(o3[i][2])))

    # 4. Check Storages.tjs & Override.tjs OBJ[0] constants
    r4, _ = xp3.read_entry(p, de["sysscn/Override.tjs"])
    o4 = d.parse_tjs2_objs(safe_decrypt_tjs2(r4))
    print("\n=== Override.tjs OBJ[0] str consts ===")
    print([c for c in o4[0][3] if isinstance(c, str)])


if __name__ == "__main__":
    main()
