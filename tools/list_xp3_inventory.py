import os
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
for fn in sorted(os.listdir(GAME_DIR)):
    if fn.lower().endswith((".xp3", ".exe", ".cf")):
        print("FILE:", fn, os.path.getsize(os.path.join(GAME_DIR, fn)))

for xname in ("data.xp3", "steam.xp3"):
    xp = os.path.join(GAME_DIR, xname)
    if not os.path.exists(xp):
        continue
    e = xp3.parse_xp3_entries(xp)
    dirs = Counter(k.split("/")[0] if "/" in k else "(root)" for k in e)
    exts = Counter(os.path.splitext(k)[1].lower() for k in e)
    print(f"\n=== {xname}: {len(e)} entries ===")
    print("  top dirs:", dirs.most_common())
    print("  exts:", exts.most_common())
    # List non-fgimage/bgimage/evimage/sound/voice/bgm/rule files
    print("  text/ui/image candidates:")
    for k in sorted(e):
        if k.startswith(("image/", "bgimage/")) and not k.startswith("image/particle"):
            print("   ", k)
        elif k.startswith(("main/", "scn/", "scenario/", "font/", "uipsd/", "init/")) or "/" not in k:
            print("   ", k)
