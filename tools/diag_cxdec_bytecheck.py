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

sig = b"\x89PNG\r\n\x1a\n"
iend = b"IEND\xaeB`\x82"

for k in ("image/attention_cn.png", "image/attention2_cn.png", "bgimage/ef02.png", "bgimage/bg002c.png"):
    raw, adlr = xp3.read_entry(DATA_XP3, entries[k])
    k1 = Counter(raw[i] ^ sig[i] for i in range(8)).most_common(1)[0][0]
    k2 = Counter(raw[len(raw) - 8 + i] ^ iend[i] for i in range(8)).most_common(1)[0][0]
    dec2 = bytearray(b ^ k2 for b in raw)
    idx = dec2.find(b"IDAT")
    if idx == -1:
        dec1 = bytearray(b ^ k1 for b in raw)
        idx = dec1.find(b"IDAT")
        print(f"=== {k} len={len(raw):#x} k1={k1:#x} k2={k2:#x} IDAT_in_dec1@{idx:#x} ===")
        # Look for where zlib fails or test split in [idx+4..0x2000]!
        clen = struct.unpack_from(">I", dec1, idx - 4)[0]
        idat_end = idx + 4 + clen
        # Find where dec1[:sp] + dec2[sp:] works around split!
        for sp in range(idx + 4, min(len(raw), 0x2000)):
            z = bytes(dec1[idx+4:sp]) + bytes(dec2[sp:idat_end])
            try:
                out = zlib.decompress(z)
                print(f"  PERFECT ZLIB AT sp={sp:#x}, out_len={len(out)}! CRC={zlib.crc32(b'IDAT'+z)&0xFFFFFFFF == struct.unpack_from('>I', dec2, idat_end)[0]}")
                break
            except zlib.error:
                pass
        else:
            print("  No simple single split in 0..0x2000 worked cleanly!")
        continue

    clen = struct.unpack_from(">I", dec2, idx - 4)[0]
    z = bytes(dec2[idx + 4:idx + 4 + clen])
    crc_st = struct.unpack_from(">I", dec2, idx + 4 + clen)[0]
    crc_ca = zlib.crc32(b"IDAT" + z) & 0xFFFFFFFF
    d = zlib.decompressobj(-15)
    try:
        out = d.decompress(z[2:-4]) + d.flush()
    except Exception as e:
        out = b""
        print(f"  raw deflate err: {e}")
    ad_calc = zlib.adler32(out) & 0xFFFFFFFF
    ad_st = struct.unpack_from(">I", z, len(z) - 4)[0]
    print(f"=== {k} len={len(raw):#x} adlr={adlr:#010x} k1={k1:#x} k2={k2:#x} IDAT@{idx:#x} clen={clen} ===")
    print(f"  out_len={len(out)} eof={d.eof} unused={len(d.unused_data)} ad_calc={ad_calc:#010x} ad_st={ad_st:#010x} diff={ad_calc^ad_st:#010x}")
    print(f"  crc_calc={crc_ca:#010x} crc_st={crc_st:#010x} diff={crc_ca^crc_st:#010x}")
