import os
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    for k in ("main/Config.tjs", "main/default.tjs"):
        raw, _ = xp3.read_entry(data_xp3, de[k])
        txt = xp3.decode_txtobf(raw)
        print(f"=== {k} storeCaption / restore / caption ===")
        for idx, line in enumerate(txt.splitlines(), 1):
            if any(w in line.lower() for w in ("caption", "title", "syslang", "lang")):
                print(f"  L{idx:4d}: {line}")

    ksd = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo\data_anchor.ksd")
    with open(ksd, "rb") as f:
        b = f.read()
    print(f"\n=== data_anchor.ksd ({len(b)} bytes) ===")
    print("  head:", b[:64])
    for pat in (b"9-nine", b"Episode", b"caption", b"language", b"uiLanguage"):
        print(f"  ascii {pat}: {b.count(pat)} | utf16: {b.count(pat.decode().encode('utf-16-le'))}")


if __name__ == "__main__":
    main()
