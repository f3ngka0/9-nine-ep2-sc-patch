import os
import sys
sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as d

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"

def main():
    p = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(p)
    raw, adlr = xp3.read_entry(p, de["main/Storages.tjs"])
    print(f"=== main/Storages.tjs (len={len(raw)}, adlr={hex(adlr)}) ===")
    print(xp3.decode_txtobf(raw))

    print("\n=== steam.xp3::steam.tjs consts & OBJ[0..1] ===")
    sp = os.path.join(GAME_DIR, "steam.xp3")
    se = xp3.parse_xp3_entries(sp)
    sraw, sadlr = xp3.read_entry(sp, se["steam.tjs"])
    sobj = d.parse_tjs2_objs(d.decrypt_tjs2(sraw))
    for i in (0, 1, 2):
        print(f"--- steam.tjs OBJ[{i}] {sobj[i][1]} ---")
        print(d.disasm_tjs2(sobj[i][2], sobj[i][3], 0, 220))

    print("\n=== Test xp3.encode_txtobf & xp3.pack_xp3 ===")
    enc = xp3.encode_txtobf('System.inform("OK");\r\n')
    print("encode_txtobf head:", enc[:30].hex(), "decode back:", repr(xp3.decode_txtobf(enc)))

if __name__ == "__main__":
    main()
