import os
import re
import struct
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
PLUGIN_DIR = os.path.join(GAME_DIR, "plugin")

print("=== plugin/ files ===")
for fn in sorted(os.listdir(PLUGIN_DIR)):
    print(" ", fn, os.path.getsize(os.path.join(PLUGIN_DIR, fn)))

for dll in ("psbfile.dll", "fstat.dll", "PackinOne.dll"):
    p = os.path.join(PLUGIN_DIR, dll)
    if not os.path.exists(p):
        continue
    b = open(p, "rb").read()
    # Look for UTF-16 method/class strings or ASCII exports
    u16 = sorted(set(s.decode("utf-16-le") for s in re.findall(rb"(?:[\x20-\x7e]\x00){3,}", b)))
    print(f"\n=== {dll} interesting U16 ===")
    for s in u16:
        if any(w in s.lower() for w in ("psb", "load", "save", "file", "stream", "binary", "storage", "proxy", "root", "serialize", "export", "dump", "get", "set", "read", "write", "cxdec", "xp3")):
            if len(s) < 80:
                print(" ", repr(s))
