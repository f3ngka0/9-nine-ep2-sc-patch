import os
import struct
import sys
import zlib
from collections import Counter, defaultdict

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


def check_png_anomalies():
    by_slot = defaultdict(list)
    for arc_name in ("data.xp3", "adult.xp3"):
        arc = os.path.join(GAME_DIR, arc_name)
        entries = xp3.parse_xp3_entries(arc)
        for k, ent in sorted(entries.items()):
            if not k.lower().endswith(".png"):
                continue
            raw, adlr = xp3.read_entry(arc, ent)
            # Determine k1 from PNG_MAGIC (bytes 0..16, mode since at most 1-2 anomalies)
            k1 = Counter(raw[i] ^ PNG_MAGIC[i] for i in range(16)).most_common(1)[0][0]
            # Check IEND at end: 00 00 00 00 I E N D ae 42 60 82 (12 bytes)
            iend = b"\x00\x00\x00\x00IEND\xae\x42\x60\x82"
            k2 = Counter(raw[len(raw) - 12 + i] ^ iend[i] for i in range(12)).most_common(1)[0][0]
            # Find split around 0x750..0x950 using chunk CRCs and chunk structure
            # Try scanning split candidate where header/chunks remain valid? Wait:
            # Find which bytes in 0..16 differ from PNG_MAGIC XOR k1
            head_anom = [(i, raw[i] ^ k1 ^ PNG_MAGIC[i]) for i in range(16) if (raw[i] ^ k1) != PNG_MAGIC[i]]
            tail_anom = [(len(raw) - 12 + i, raw[len(raw) - 12 + i] ^ k2 ^ iend[i]) for i in range(12) if (raw[len(raw) - 12 + i] ^ k2) != iend[i]]
            by_slot[adlr & 0x7f].append((k, adlr, len(raw), k1, k2, head_anom, tail_anom))

    print(f"Total slots covered by PNGs: {len(by_slot)}/128")
    # Also check adlr & 0x7f for all 36 .scn files!
    de = xp3.parse_xp3_entries(os.path.join(GAME_DIR, "data.xp3"))
    scn_slots = {}
    for k, ent in sorted(de.items()):
        if k.endswith(".scn"):
            scn_slots[k] = ent[2] # adlr
            slot = ent[2] & 0x7f
            print(f"SCN {k:20s} adlr={hex(ent[2]):10s} slot={slot:#04x} png_matches={len(by_slot[slot])}")
            for pk, padlr, plen, pk1, pk2, ha, ta in by_slot[slot][:2]:
                print(f"   PNG {pk}: adlr={hex(padlr)} k1={hex(pk1)} k2={hex(pk2)} head_anom={[(o, hex(x)) for o, x in ha]} tail_anom={[(o, hex(x)) for o, x in ta]}")


if __name__ == "__main__":
    check_png_anomalies()
