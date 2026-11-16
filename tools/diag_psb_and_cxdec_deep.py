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


def check_png_cxdec(raw: bytes):
    sig = b"\x89PNG\r\n\x1a\n"
    votes = Counter(raw[i] ^ sig[i] for i in range(8))
    k1, cnt = votes.most_common(1)[0]
    if cnt < 6:
        return None
    # Guess k2 from trailing IEND\xaeB`\x82 (last 8 bytes)
    iend = b"IEND\xaeB`\x82"
    k2 = Counter(raw[len(raw) - 8 + i] ^ iend[i] for i in range(8)).most_common(1)[0][0]
    dec1 = bytes(b ^ k1 for b in raw)
    dec2 = bytes(b ^ k2 for b in raw)
    # Try finding exact split in [0x0..min(len, 0x1000)] where zlib decompresses IDAT or CRC checks!
    return k1, k2, len(raw), dec1[:16]


# 1. Check PNG IHDR/IEND anomalies
print("=== Checking attention & UI PNGs ===")
png_bad = []
png_ok = 0
for k in sorted(entries):
    if not k.lower().endswith(".png"):
        continue
    r, adlr = xp3.read_entry(DATA_XP3, entries[k])
    sig = b"\x89PNG\r\n\x1a\n"
    votes = Counter(r[i] ^ sig[i] for i in range(8))
    k1, cnt = votes.most_common(1)[0]
    iend = b"IEND\xaeB`\x82"
    ivotes = Counter(r[len(r) - 8 + i] ^ iend[i] for i in range(8))
    k2, icnt = ivotes.most_common(1)[0]
    if cnt < 8 or icnt < 8:
        png_bad.append((k, hex(adlr), len(r), f"hdr={cnt}/8@{[i for i in range(8) if (r[i]^k1)!=sig[i]]}", f"tail={icnt}/8@{[i for i in range(8) if (r[len(r)-8+i]^k2)!=iend[i]]}"))
    else:
        png_ok += 1
print(f"PNGs: {png_ok} clean header+tail, {len(png_bad)} partial:")
for x in png_bad[:20]:
    print(" ", x)

# 2. Try minimal PSB v3 parser on ALL 36 scn + 52 uipsd files!
# Look for any PSB parse failures or split boundary corruptions!
def quick_psb_check(raw: bytes, k1: int, k2: int):
    # PSB v3 header: 0..4="PSB\x00", 4..8=version(3), 8..12=encrypt, 12..16=off_names, 16..20=off_strings, 20..24=off_str_data, 24..28=off_chunk_offs, 28..32=off_chunk_lens, 32..36=off_chunk_data, 36..40=off_entries, 40..44=off_extra(optional? Let's inspect!)
    # Brute-force split point in 0..min(len, 0x1000) where off_strings > 36 and off_strings < len and off_names/etc are sane, AND parse strings table!
    n = min(len(raw), 0x1000)
    dec1 = bytes(b ^ k1 for b in raw[:n])
    dec2 = bytes(b ^ k2 for b in raw[:n])
    best = []
    # In PSB v3: header[0:8] = b"PSB\x00\x03\x00\x00\x00", header[8:12] = 0 (usually!), header[12:16] = 0x28 or 0x2c
    # Notice ALL header uint32s are < 0x1000! Wait: header is ALWAYS < 44 bytes, well below cxdec split (>= 0x80 usually unless split < 44)!
    # So check header[0:44] first!
    return dec1[:44], dec2[:44]


print("\n=== Checking PSB v3 header bytes 0..44 ===")
psb_list = [k for k in sorted(entries) if k.endswith((".scn", ".pimg"))]
for k in psb_list[:10]:
    r, adlr = xp3.read_entry(DATA_XP3, entries[k])
    k1 = Counter(r[i] ^ b"PSB\x00\x03\x00\x00\x00"[i] for i in range(8)).most_common(1)[0][0]
    k2 = Counter(r[-100:]).most_common(1)[0][0]
    h = bytearray(b ^ k1 for b in r[:44])
    h[:8] = b"PSB\x00\x03\x00\x00\x00"
    vals = struct.unpack_from("<11I", h, 0)
    print(f"  {k:32s} len=0x{len(r):06x} k1=0x{k1:02x} k2=0x{k2:02x} hdr={[hex(v) for v in vals[2:]]}")

# 3. Also inspect cxdec_decrypt vs full PNG/IDAT CRC check on 5 PNGs to determine EXACT split range & extra anomaly rule!
# Wait: look at `syslangtext_en.ini` raw[2100..2500] and `syslangtext_cn.ini` raw[2150..2350] and raw[6750..6800]!
print("\n=== syslangtext_cn.ini exact split and byte 6780 check ===")
r_cn, adlr_cn = xp3.read_entry(DATA_XP3, entries["main/syslangtext_cn.ini"])
# Decode assuming k1=0x01 up to sp, k2=0x54 from sp! Check where high byte changes from 0x01 to 0x54!
switches = [i for i in range(6, min(len(r_cn), 0x1000), 2) if r_cn[i] == 0x54]
first_k2 = min(switches)
last_k1 = max(i for i in range(6, first_k2 + 100, 2) if r_cn[i] == 0x01)
print(f"  cn high bytes: first 0x54 at 0x{first_k2:x}, last 0x01 near there at 0x{last_k1:x}")
for pos in range(last_k1 - 4, first_k2 + 8, 2):
    print(f"    off=0x{pos-1:x}..0x{pos:x}: raw={r_cn[pos-1]:02x} {r_cn[pos]:02x}")
print("  around 6780 (0x1a7c):")
for pos in range(6770, 6792, 2):
    print(f"    off=0x{pos-1:x}..0x{pos:x}: raw={r_cn[pos-1]:02x} {r_cn[pos]:02x}")
