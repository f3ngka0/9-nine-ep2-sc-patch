import os
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def main():
    p = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(p)
    for k in ("AppConfig.tjs", "main/Config.tjs", "main/default.tjs"):
        raw, adlr = xp3.read_entry(p, de[k])
        print(f"\n================ {k} (len={len(raw)}, adlr={hex(adlr)}) ================")
        txt = xp3.decode_txtobf(raw)
        print(txt[:3000] if txt else f"NOT TXTOBF: {raw[:32].hex()}")

    ap = os.path.expandvars(r"%APPDATA%\PALETTE")
    print(f"\n=== %APPDATA%\\PALETTE ({ap}) ===")
    if os.path.isdir(ap):
        for root, dirs, files in os.walk(ap):
            for fn in files:
                fp = os.path.join(root, fn)
                print(f"  {fp} ({os.path.getsize(fp)}B)")


if __name__ == "__main__":
    main()
