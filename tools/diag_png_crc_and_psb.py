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


def inspect_png_chunks(name: str, raw: bytes, adlr: int):
    sig = b"\x89PNG\r\n\x1a\n"
    k1 = Counter(raw[i] ^ sig[i] for i in range(8)).most_common(1)[0][0]
    iend = b"IEND\xaeB`\x82"
    k2 = Counter(raw[len(raw) - 8 + i] ^ iend[i] for i in range(8)).most_common(1)[0][0]
    # Try every split in 0..0x1000 to verify IHDR CRC32!
    # Byte 0..7: sig, 8..11: IHDR len (13), 12..15: "IHDR", 16..28: data, 29..32: CRC32
    ihdr_b = bytearray(b ^ k1 for b in raw[:33])
    ihdr_b[:8] = sig
    crc_calc = zlib.crc32(ihdr_b[12:29]) & 0xFFFFFFFF
    crc_stored = struct.unpack_from(">I", ihdr_b, 29)[0]
    print(f"PNG {name:40s} adlr={adlr:#010x} len=0x{len(raw):06x} k1=0x{k1:02x} k2=0x{k2:02x} hdr0_diffs={[(i, hex(raw[i]^k1^sig[i])) for i in range(8) if (raw[i]^k1)!=sig[i]]} IHDR_crc_ok={crc_calc==crc_stored}")
    # Also scan PNG chunks assuming k2 after split (test sp candidates near IHDR or 0..0x2000!)
    dec2 = bytearray(b ^ k2 for b in raw)
    # Search for "IDAT" and "IEND" in dec2!
    idat_positions = []
    pos = 0
    while True:
        idx = dec2.find(b"IDAT", pos)
        if idx == -1:
            break
        idat_positions.append(idx)
        pos = idx + 1
    # For each IDAT after split, check chunk CRC32 and zlib stream!
    dec_idat_streams = []
    zlib_errs = []
    for idx in idat_positions:
        if idx < 4:
            continue
        clen = struct.unpack_from(">I", dec2, idx - 4)[0]
        if idx + 4 + clen + 4 <= len(dec2):
            c_calc = zlib.crc32(dec2[idx:idx + 4 + clen]) & 0xFFFFFFFF
            c_st = struct.unpack_from(">I", dec2, idx + 4 + clen)[0]
            if c_calc != c_st:
                zlib_errs.append((hex(idx), clen, hex(c_calc ^ c_st)))
            dec_idat_streams.append(bytes(dec2[idx + 4:idx + 4 + clen]))
    if idat_positions:
        print(f"   IDATs found via k2: {len(idat_positions)} first@{idat_positions[0]:#x}, crc_mismatches={zlib_errs[:5]}")
        # If first IDAT starts < 0x1000, find split where CRC/zlib passes, and see if later IDATs have ANY crc mismatch!
        if zlib_errs:
            full_z = b"".join(dec_idat_streams)
            try:
                zlib.decompress(full_z)
                print("   zlib decompress OK!")
            except Exception as e:
                print(f"   zlib err: {e}")


for k in (
    "image/attention2_cn.png",
    "image/attention_cn.png",
    "bgimage/bg002c.png",
    "bgimage/bg011c.png",
    "image/eyecatch/eyecatch_number02.png",
    "image/cdown/@発射カウント_8.png",
    "image/particle/羽_3列_fl96.png",
    "bgimage/ef02.png",
):
    r, adlr = xp3.read_entry(DATA_XP3, entries[k])
    inspect_png_chunks(k, r, adlr)
