import os
import struct
import sys
import zlib
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
entries = xp3.parse_xp3_entries(DATA_XP3)

# 1. Inspect bgimage/bg002c.png first 256 bytes and last 256 bytes!
r, adlr = xp3.read_entry(DATA_XP3, entries["bgimage/bg002c.png"])
sig = b"\x89PNG\r\n\x1a\n"
k1 = Counter(r[i] ^ sig[i] for i in range(8)).most_common(1)[0][0]
iend = b"IEND\xaeB`\x82"
k2 = Counter(r[len(r) - 8 + i] ^ iend[i] for i in range(8)).most_common(1)[0][0]
print(f"bg002c: len={len(r)} k1={k1:#x} k2={k2:#x}")
print("  dec1[:64]:", bytes(b ^ k1 for b in r[:64]))
print("  dec2[-64:]:", bytes(b ^ k2 for b in r[-64:]))
# Scan chunks starting from offset 8 in dec1 until we hit split!
pos = 8
dec1 = bytes(b ^ k1 for b in r)
print("  walk chunks from 8 using k1:")
while pos + 8 <= len(r) and pos < 0x10000:
    clen = struct.unpack_from(">I", dec1, pos)[0]
    ctype = dec1[pos+4:pos+8]
    print(f"    @0x{pos:x}: len={clen} type={ctype}")
    if not all(32 <= b < 127 for b in ctype) or pos + 12 + clen > len(r):
        break
    pos += 12 + clen

# 2. Check attention_cn.png & attention2_cn.png: decompress raw deflate skipping zlib adler, AND check where in image data differs!
for k in ("image/attention_cn.png", "image/attention2_cn.png", "image/eyecatch/eyecatch_number02.png"):
    raw, adlr = xp3.read_entry(DATA_XP3, entries[k])
    k1 = Counter(raw[i] ^ sig[i] for i in range(8)).most_common(1)[0][0]
    k2 = Counter(raw[len(raw) - 8 + i] ^ iend[i] for i in range(8)).most_common(1)[0][0]
    print(f"\n=== {k} len=0x{len(raw):x} adlr={adlr:#010x} k1={k1:#x} k2={k2:#x} ===")
    dec1 = bytes(b ^ k1 for b in raw[:0x2000])
    pos = 8
    while pos + 8 <= len(dec1):
        clen = struct.unpack_from(">I", dec1, pos)[0]
        ctype = dec1[pos+4:pos+8]
        print(f"  chunk @{pos:#x}: len={clen} type={ctype}")
        if ctype == b"IDAT":
            idat_start = pos + 8
            idat_end = pos + 8 + clen
            # Notice IDAT starts at pos+8! For attention_cn.png pos+8 = 0xac3!
            # Test k2 from some split inside [0x800, 0x1000] vs exact zlib header 78 9c / 78 da!
            d2_slice = bytes(b ^ k2 for b in raw[idat_start:idat_start+16])
            print(f"  IDAT start @{idat_start:#x}: dec2[:16]={d2_slice.hex()}")
            # Check raw deflate from idat_start+2!
            dec_full = bytearray(b ^ k1 for b in raw[:0x800]) + bytearray(b ^ k2 for b in raw[0x800:])
            # Adjust split dynamically where dec1 looks like chunk!
            for sp in range(0x0, min(len(raw), 0x1000)):
                # Only test splits near idat_start or chunk boundaries
                pass
            if idat_start < 0x1000:
                # Test dec2 from idat_start vs dec1 up to idat_start
                # Actually scan where 78 9c or 78 da appears near idat_start!
                for sp in range(max(0, idat_start - 500), min(len(raw), idat_start + 50)):
                    t = bytes(b ^ k1 for b in raw[idat_start:sp]) + bytes(b ^ k2 for b in raw[max(idat_start, sp):idat_end])
                    if len(t) >= 2 and t[0] == 0x78 and t[1] in (0x01, 0x5e, 0x9c, 0xda):
                        try:
                            out = zlib.decompress(t)
                            print(f"  CLEAN ZLIB DECOMPRESS AT split={sp:#x}! out_len={len(out)}")
                            break
                        except zlib.error as e:
                            if "incorrect data check" in str(e):
                                # Check exact adler32 of raw deflate stream!
                                d_obj = zlib.decompressobj(-15)
                                raw_out = d_obj.decompress(t[2:-4])
                                ad_calc = zlib.adler32(raw_out) & 0xFFFFFFFF
                                ad_stored = struct.unpack_from(">I", t, len(t)-4)[0]
                                print(f"  PARTIAL @split={sp:#x}: raw_out={len(raw_out)} unused={len(d_obj.unused_data)} ad_calc={ad_calc:#010x} ad_stored={ad_stored:#010x}")
                                break
            break
        pos += 12 + clen
