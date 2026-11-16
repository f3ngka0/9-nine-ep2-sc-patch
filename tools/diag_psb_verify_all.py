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

# 1. Verify single-byte fix on attention2_cn.png & 羽_3列_fl96.png!
sig = b"\x89PNG\r\n\x1a\n"
iend = b"IEND\xaeB`\x82"
for k, fix_off, fix_val in [
    ("image/attention2_cn.png", 0x9118, 0xce),
    ("image/particle/羽_3列_fl96.png", 0xfb54, 0x20),
]:
    raw, adlr = xp3.read_entry(DATA_XP3, entries[k])
    k1 = Counter(raw[i] ^ sig[i] for i in range(8)).most_common(1)[0][0]
    k2 = Counter(raw[len(raw) - 8 + i] ^ iend[i] for i in range(8)).most_common(1)[0][0]
    dec2 = bytearray(b ^ k2 for b in raw)
    dec2[fix_off] ^= fix_val
    idx = dec2.find(b"IDAT")
    clen = struct.unpack_from(">I", dec2, idx - 4)[0]
    z = bytes(dec2[idx + 4:idx + 4 + clen])
    crc_st = struct.unpack_from(">I", dec2, idx + 4 + clen)[0]
    crc_ca = zlib.crc32(b"IDAT" + z) & 0xFFFFFFFF
    try:
        out = zlib.decompress(z)
        print(f"VERIFIED {k}: zlib=OK! out_len={len(out)}, crc_ok={crc_st == crc_ca}")
    except Exception as e:
        print(f"VERIFIED {k}: err={e}")

# 2. Check all 36 scn + 52 pimg PSB files: inspect PSB v3 layout & detect ANY byte anomaly in PSB header/string/chunk tables!
def decrypt_psb_best(raw: bytes):
    k1 = Counter(raw[i] ^ b"PSB\x00\x03\x00\x00\x00"[i] for i in range(8)).most_common(1)[0][0]
    dec1 = bytearray(b ^ k1 for b in raw[:min(len(raw), 0x1000)])
    dec1[:8] = b"PSB\x00\x03\x00\x00\x00"
    # Fix header[8:44]: header[8:12] == header[12:16] == 0x2c (or 0x28)! Wait check if ANY header byte < 44 looks weird:
    # Actually let's check both k1 and k2!
    # Where is k2? Last 100 bytes of PSB are usually chunk/name bytes or string/offsets! Wait: test end bytes OR padding OR high bytes of offsets!
    # Wait: in a PSB, off_chunk_data >= off_chunk_lens >= off_chunk_offs >= off_str_data >= off_strings!
    # Even simpler: check common byte values at the end? Wait no: string_data ends with null bytes `\x00` or chunk_offs/lens are tiny uint32s (`0x00`), so trailing 200 bytes have plenty of `0x00` if chunk_data is empty! Look at earlier output:
    # b01: off_chunk_offs=0x1ae150, off_chunk_lens=0x1ae153, off_chunk_data=0x1ae156 == len(raw)!!
    # So the LAST 16 bytes of .scn have lots of 0s? NO, string_data is ASCII/UTF-8 null-terminated strings, wait or offsets in `off_strings` (0x187dbf..0x189d6d) have high bytes `0x00`!
    return k1


print("\n=== Checking PSB string_data / off_strings in ALL 88 PSB files ===")
# Let's see how each .scn file encodes offsets and where k2 shows up in off_strings!
for k in ("scn/b01.txt.scn", "scn/b02.txt.scn", "scn/b07.txt.scn", "uipsd/conf_lang.pimg", "uipsd/cn/conf_cn.pimg"):
    r, adlr = xp3.read_entry(DATA_XP3, entries[k])
    k1 = Counter(r[i] ^ b"PSB\x00\x03\x00\x00\x00"[i] for i in range(8)).most_common(1)[0][0]
    h = bytearray(b ^ k1 for b in r[:44])
    h[:8] = b"PSB\x00\x03\x00\x00\x00"
    vals = struct.unpack_from("<11I", h, 0)
    print(f"  {k:28s} len=0x{len(r):06x} k1={k1:#x} v2..10={[hex(x) for x in vals[2:]]}")
    # Check byte frequency at tail and around off_strings (vals[4]..vals[5])!
    # Wait: in PSB, chunk_offs (vals[6]) starts with N + 1/2/3/4 byte type integer (0x0d..0x10) then small ints!
    # And names/strings arrays also have lots of 0x00 high bytes!
    tail_c = Counter(r[max(0x1000, len(r)-2000):]).most_common(3)
    print(f"    tail top3 bytes: {[(hex(x), c) for x, c in tail_c]}")
