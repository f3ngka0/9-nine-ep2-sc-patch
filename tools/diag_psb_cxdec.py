import os
import struct
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def inspect_scn_headers():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    for name in ("scn/b02.txt.scn", "scn/b07.txt.scn", "scn/b01.txt.scn", "scn/b15a.txt.scn", "scn/b12c.txt.scn", "scn/b18_2a.txt.scn"):
        raw, adlr = xp3.read_entry(data_xp3, de[name])
        magic = b"PSB\x00\x03\x00\x00\x00\x00\x00\x00\x00"
        k1 = Counter(raw[i] ^ magic[i] for i in range(12)).most_common(1)[0][0]
        hdr_dec = bytes(raw[i] ^ k1 for i in range(56))
        anom = [(i, hex(hdr_dec[i]), hex(raw[i] ^ magic[i])) for i in range(12) if hdr_dec[i] != magic[i]]
        # Decrypt tail sample to guess k2
        # Scan last 1KB for `\0` padded string end or type markers; actually test all 256 k2 on tail[0x1000:0x2000]
        sample = raw[-4096:]
        best_k2 = max(range(256), key=lambda k: sum(1 for b in sample if (b ^ k) == 0 or 32 <= (b ^ k) <= 126))
        print(f"{name:22s} len={len(raw):7d} adlr={hex(adlr):10s} slot={adlr&0x7f:#04x} k1={k1:#04x} k2_est={best_k2:#04x} hdr_anom={anom}")
        # Print decrypted 56-byte header assuming k1
        if not anom:
            vals = struct.unpack_from("<4sIIIIIIIIII", hdr_dec, 0)
            print(f"  hdr={vals}")
        else:
            fixed = bytearray(hdr_dec)
            for i, _, _ in anom:
                fixed[i] = magic[i]
            vals = struct.unpack_from("<4sIIIIIIIIII", fixed, 0)
            print(f"  hdr(fixed)={vals}")


if __name__ == "__main__":
    inspect_scn_headers()
