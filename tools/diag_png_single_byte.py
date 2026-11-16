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

# Build reversed CRC32 step table over GF(2) so we can walk backward from end of chunk in O(n)!
# Standard CRC32 polynomial (reflected): 0xEDB88320
# To undo 1 zero-byte step: if (crc & 1) crc = ((crc ^ 0xEDB88320) >> 1) | 0x80000000 else crc >> 1 (for standard XOR-out? Better: forward gf2 matrix or step!)
# Wait: easier! crc(zero_buf_with_1byte_v_at_p) == crc32(v, len_after_p zero bytes)!
# We can compute crc_zero_step(c) = crc32(b'\x00', c) and find if ANY byte value v at ANY offset from end matches target_diff!
# Actually even simpler: forward CRC32(state=0, b'\x00'*k) only takes 256 table entries, or notice:
# crc32(A ^ B) = crc32(A) ^ crc32(B) ^ crc32(0)!
# Better: precompute crc_of_byte_at_dist_from_end? Even faster: in reflected CRC32, appending one 0x00 byte updates state `c` by `(c >> 8) ^ T[c & 0xff]`.
# That linear bijection M on 32-bit states has an EXACT inverse step `inv_step(c)`!!
# Specifically: top 8 bits of `(c >> 8) ^ T[c & 0xff]` ONLY come from `T[c & 0xff] >> 24`!! And all 256 entries of `T[i] >> 24` are DISTINCT!
# Verify that and build `inv_T` in 5 lines!
T = []
for i in range(256):
    c = i
    for _ in range(8):
        c = (c >> 1) ^ 0xEDB88320 if (c & 1) else (c >> 1)
    T.append(c)

inv_top = {T[i] >> 24: i for i in range(256)}
assert len(inv_top) == 256


def inv_zero_byte(c: int) -> int:
    # Given next = (prev >> 8) ^ T[prev & 0xff], find prev!
    low = inv_top[c >> 24]
    prev_shifted = c ^ T[low]
    return ((prev_shifted << 8) & 0xFFFFFFFF) | low


def find_single_byte_crc_fix(z_len: int, diff: int):
    # diff is target_crc ^ calc_crc (note: initial/final 0xffffffff cancel out in diff!)
    # If byte at index p from start of IDAT payload (so d = z_len - p bytes from end AFTER byte p, i.e. byte p then z_len-1-p zero bytes, plus 4? Wait: CRC doesn't include itself!)
    # After byte p gets XORed with v, its CRC contribution before trailing (z_len - 1 - p) zero bytes is:
    # state = T[v], followed by (z_len - 1 - p) zero bytes!
    # So invert (z_len - 1 - p) zero bytes starting from `diff`: whenever state has state <= 255 or matches T[v], we found (p, v)!
    # Wait: even simpler! `diff` after v at p = apply_zeros(T[v], z_len - 1 - p). Wait no: state before v is 0, adding v makes (0 >> 8) ^ T[0 ^ v] = T[v]!
    # So we invert zero bytes starting from `c = diff`; if `c in T_set`, we hit `(p, v)`!
    T_map = {T[v]: v for v in range(256)}
    c = diff
    hits = []
    for k in range(z_len):
        if c in T_map:
            p = z_len - 1 - k
            hits.append((p, T_map[c]))
        c = inv_zero_byte(c)
    return hits


sig = b"\x89PNG\r\n\x1a\n"
iend = b"IEND\xaeB`\x82"

for k in ("image/attention_cn.png", "image/attention2_cn.png", "bgimage/ef02.png", "image/particle/羽_3列_fl96.png"):
    raw, adlr = xp3.read_entry(DATA_XP3, entries[k])
    k1 = Counter(raw[i] ^ sig[i] for i in range(8)).most_common(1)[0][0]
    k2 = Counter(raw[len(raw) - 8 + i] ^ iend[i] for i in range(8)).most_common(1)[0][0]
    dec1 = bytes(b ^ k1 for b in raw[:64])
    w, h, bd, ct = struct.unpack_from(">IIBB", dec1, 16)
    bpp = {2: 3, 6: 4, 3: 1, 4: 2, 0: 1}.get(ct, 4)
    expected_raw = h * (1 + w * bpp)

    dec2 = bytearray(b ^ k2 for b in raw)
    idx = dec2.find(b"IDAT")
    clen = struct.unpack_from(">I", dec2, idx - 4)[0]
    z = bytes(dec2[idx + 4:idx + 4 + clen])
    crc_st = struct.unpack_from(">I", dec2, idx + 4 + clen)[0]
    crc_ca = zlib.crc32(b"IDAT" + z) & 0xFFFFFFFF
    diff = crc_ca ^ crc_st
    hits = find_single_byte_crc_fix(len(z), diff)
    print(f"=== {k} w={w} h={h} ct={ct} expected_raw={expected_raw} clen={clen} diff={diff:#010x} ===")
    print(f"  1-byte CRC hits in IDAT payload: {[(idx+4+p, hex(idx+4+p), hex(v)) for p, v in hits]}")
    # Also check out_len vs expected_raw
    d = zlib.decompressobj(-15)
    out = d.decompress(z[2:-4]) + d.flush()
    print(f"  actual out_len={len(out)} (delta={len(out)-expected_raw})")
