import os
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
entries = xp3.parse_xp3_entries(DATA_XP3)

print("=== Finding all anomalous bytes in txtobf files ===")
anoms = []
for name in sorted(entries):
    if not name.lower().endswith((".ini", ".tjs", ".ks", ".csv", ".txt", ".func")):
        continue
    raw, adlr = xp3.read_entry(DATA_XP3, entries[name])
    if len(raw) < 100:
        continue
    votes = Counter([raw[0] ^ 0xFE, raw[1] ^ 0xFE, raw[2] ^ 0x01, raw[3] ^ 0xFF, raw[4] ^ 0xFE])
    k1, cnt = votes.most_common(1)[0]
    if cnt < 4:
        continue
    # Scan even indices (UTF-16 high byte for index 6, 8, 10...)
    evens = Counter(raw[i] for i in range(6, len(raw), 2))
    common_keys = [k for k, c in evens.most_common(5)]
    # Check where raw[i] (even i >= 6) is neither k1 nor k2 (assuming ASCII high byte == 0)
    # Wait, first find switch point between k1 and k2
    k2 = Counter(raw[i] for i in range(max(6, (len(raw) - 400) & ~1), len(raw), 2)).most_common(1)[0][0]
    bad = []
    for i in range(6, len(raw), 2):
        if raw[i] != k1 and raw[i] != k2:
            # Check if adjacent bytes are ASCII (high byte would be k1/k2) -> if non-ASCII char, neighbor might also be non-ASCII
            # Print anyway if surrounded by k1/k2 evens
            prev_ok = (i - 2 >= 6 and raw[i - 2] in (k1, k2))
            next_ok = (i + 2 < len(raw) and raw[i + 2] in (k1, k2))
            if prev_ok and next_ok:
                bad.append((i, raw[i]))
    if bad:
        anoms.append((name, adlr, len(raw), k1, k2, bad))

print(f"Found {len(anoms)} txtobf files with isolated even-byte anomalies:")
for name, adlr, ln, k1, k2, bad in anoms[:30]:
    bad_str = ", ".join(f"0x{off:x}(val=0x{v:02x},xor_k1=0x{v^k1:02x},xor_k2=0x{v^k2:02x})" for off, v in bad[:8])
    print(f"  {name:35s} adlr=0x{adlr:08x} len=0x{ln:x} k1=0x{k1:02x} k2=0x{k2:02x} bad={bad_str}")

# Also inspect raw[2000:2200] in embfontlist.tjs around `"face"=`"`!
raw_ef, adlr_ef = xp3.read_entry(DATA_XP3, entries["font/embfontlist.tjs"])
dec_ef = xp3.decode_txtobf(raw_ef)
for line in dec_ef.splitlines():
    if "Source Han" in line:
        print("EF line:", repr(line))
idx_bug = dec_ef.find('`')
if idx_bug != -1:
    off = 5 + idx_bug * 2
    print(f"embfontlist backtick at char idx={idx_bug}, byte off=0x{off:x}: raw[{off-4}:{off+6}]={raw_ef[off-4:off+6].hex()}")
