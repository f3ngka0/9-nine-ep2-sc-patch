import os
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as dt
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
entries = xp3.parse_xp3_entries(DATA_XP3)

# 1. Check exact byte offsets of anomalies in syslangtext_cn.ini & _jp.ini & TJS2 headers
for name in ("main/syslangtext_cn.ini", "main/syslangtext_en.ini", "main/syslangtext_jp.ini"):
    raw, adlr = xp3.read_entry(DATA_XP3, entries[name])
    dec = xp3.decode_txtobf(raw)
    print(f"=== {name} len={len(raw)} adlr={adlr:#010x} ===")
    for idx, ch in enumerate(dec):
        if ord(ch) > 0xFFFF or (0xAC00 <= ord(ch) <= 0xD7AF) or ch in "`\x89\ufffd":
            off = 5 + idx * 2
            print(f"  char[{idx}]={ch!r} U+{ord(ch):04X} at raw[{off}:{off+2}]={raw[off:off+2].hex()} (ctx={dec[max(0,idx-10):idx+10]!r})")

# Check ALL TJS2 files in data.xp3 whose bytes[0:8] ^ k doesn't equal TJS2100\x00
print("\n=== TJS2 headers with byte anomalies in bytes[0..8] ===")
for name in sorted(entries):
    if not name.endswith(".tjs"):
        continue
    raw, adlr = xp3.read_entry(DATA_XP3, entries[name])
    if len(raw) < 16 or xp3.decode_txtobf(raw) is not None:
        continue
    votes = Counter(raw[i] ^ b"TJS2100\x00"[i] for i in range(8))
    k1, cnt = votes.most_common(1)[0]
    if 4 <= cnt < 8:
        dec8 = bytes(raw[i] ^ k1 for i in range(8))
        diffs = [(i, raw[i] ^ k1 ^ b"TJS2100\x00"[i]) for i in range(8) if raw[i] ^ k1 != b"TJS2100\x00"[i]]
        print(f"  {name:35s} len=0x{len(raw):06x} adlr=0x{adlr:08x} k1=0x{k1:02x} diffs={diffs}")

# 2. Dump all objects in system/Initialize.tjs, system/System.tjs, system/Storages... matching addArchive / setupSubFolders
print("\n=== Searching system/ & override for addArchive / setupSubFolders definition ===")
for name in sorted(entries):
    if not name.endswith(".tjs"):
        continue
    raw, adlr = xp3.read_entry(DATA_XP3, entries[name])
    if xp3.decode_txtobf(raw) is not None:
        continue
    # Fix header up to byte 8 just for inspection using majority k1
    dec = safe_decrypt_tjs2(raw)
    if b"TJS2100" not in dec[:16] and dec[1:8] != b"JS2100\x00":
        votes = Counter(raw[i] ^ b"TJS2100\x00"[i] for i in range(8))
        k1 = votes.most_common(1)[0][0]
        if votes[k1] >= 4:
            dec = b"TJS2100\x00" + dec[8:]
    if dec[:8] != b"TJS2100\x00":
        continue
    try:
        objs = dt.parse_tjs2_objs(dec)
    except Exception:
        continue
    for idx, oname, code, consts in objs:
        if any(isinstance(c, str) and ("addArchive" in c or "setupSubFolders" in c or "archive://" in c) for c in consts):
            print(f"  MATCH: {name} OBJ[{idx}] {oname} consts={consts}")
            if "setupSubFolders" in consts or "addArchive" in consts or "archive://" in repr(consts):
                print(dt.disasm_tjs2(code, consts))
