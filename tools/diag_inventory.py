import os
import sys
from collections import defaultdict

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def summarize_xp3(name: str):
    path = os.path.join(GAME_DIR, name)
    entries = xp3.parse_xp3_entries(path)
    by_ext = defaultdict(list)
    for k, (info, segms, adlr) in sorted(entries.items()):
        ext = os.path.splitext(k)[1].lower()
        by_ext[ext].append((k, info, adlr))
    print(f"=== {name}: {len(entries)} entries ===")
    for ext, items in sorted(by_ext.items()):
        print(f"  {ext or '<noext>'}: {len(items)}")
        if ext not in (".ogg", ".tlg", ".png", ".mpg", ".wmv", ".jpg"):
            for k, info, adlr in items:
                print(f"    {k} info={info} adlr={hex(adlr)}")
        elif ext == ".png" or ("cn" in "".join(i[0] for i in items) and ext == ".tlg"):
            for k, info, adlr in items:
                if any(tag in k.lower() for tag in ("cn", "lang", "title", "conf", "attention", "load", "save", "extra", "bgm", "popup")):
                    print(f"    [IMG] {k} info={info} adlr={hex(adlr)}")


if __name__ == "__main__":
    for arc in ("data.xp3", "steam.xp3", "adult.xp3"):
        summarize_xp3(arc)
