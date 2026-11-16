import os
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)

    for k in ("sysscn/first.ks", "sysscn/title.ks", "sysscn/option.ks", "sysscn/saveload.ks", "sysscn/backlog.ks", "main/custom.ks", "scenario/start.ks"):
        if k in de:
            raw, _ = xp3.read_entry(data_xp3, de[k])
            txt = xp3.decode_txtobf(raw)
            print(f"=== {k} ({'txtobf' if txt else 'BIN len=' + str(len(raw))}) ===")
            if txt:
                print("\n".join(txt.splitlines()[:45]))
            else:
                print("  head:", raw[:32].hex())

    # Also check AppData/data_anchor.ksd header/snippet and AppConfig.tjs full
    r_app, _ = xp3.read_entry(data_xp3, de["AppConfig.tjs"])
    print("\n=== AppConfig.tjs FULL ===")
    print(xp3.decode_txtobf(r_app))


if __name__ == "__main__":
    main()
