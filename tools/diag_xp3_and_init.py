import os
import struct
import sys
import zlib
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def inspect_tbl(path: str):
    with open(path, "rb") as f:
        hdr = f.read(40)
        tbl_off = struct.unpack_from("<Q", hdr, 32)[0]
        f.seek(tbl_off)
        flg = f.read(1)[0]
        zsize, osize = struct.unpack("<QQ", f.read(16))
        raw = f.read(zsize)
        tbl = zlib.decompress(raw) if (flg & 1) else raw
    print(f"=== {os.path.basename(path)} tbl len={len(tbl)} ===")
    pos = 0
    count = 0
    while pos < len(tbl) and count < 6:
        tag = tbl[pos:pos + 4]
        sz = struct.unpack_from("<Q", tbl, pos + 4)[0]
        body = tbl[pos + 12:pos + 12 + sz]
        print(f"  chunk[{count}] tag={tag!r} sz={sz}")
        if tag == b"File":
            cp = 0
            while cp < len(body):
                stag = body[cp:cp + 4]
                ssz = struct.unpack_from("<Q", body, cp + 4)[0]
                sbody = body[cp + 12:cp + 12 + ssz]
                print(f"    sub {stag!r} sz={ssz} body={sbody[:80].hex()}")
                cp += 12 + ssz
        else:
            print(f"    body={body[:80].hex()}")
        pos += 12 + sz
        count += 1


def decrypt_tjs2(raw: bytes):
    k1 = Counter(raw[i] ^ b"TJS2100\x00"[i] for i in range(8)).most_common(1)[0][0]
    dec1 = bytes(b ^ k1 for b in raw)
    tail = raw[0xA00:]
    k2 = Counter(tail).most_common(1)[0][0]
    dec2 = bytes(b ^ k2 for b in raw)
    n = min(len(raw), 0xA00)
    best_sp, best_sc = n, -1
    s1 = [1 if ((raw[i] ^ k1) == 0) else 0 for i in range(n)]
    s2 = [1 if ((raw[i] ^ k2) == 0) else 0 for i in range(n)]
    p1 = [0]
    for x in s1: p1.append(p1[-1] + x)
    suf = 0
    for sp_c in range(n - 1, 0x750 - 1, -1):
        suf += s2[sp_c]
        if p1[sp_c] + suf > best_sc:
            best_sc = p1[sp_c] + suf
            best_sp = sp_c
    return dec1[:best_sp] + dec2[best_sp:], k1, k2, best_sp


def parse_tjs2_full(dec: bytes):
    pos = dec.find(b"DATA")
    p = pos + 8
    c_byte = struct.unpack_from("<I", dec, p)[0]; p += 4 + ((c_byte + 3) // 4) * 4
    c_short = struct.unpack_from("<I", dec, p)[0]; p += 4 + ((c_short * 2 + 3) // 4) * 4
    c_int = struct.unpack_from("<I", dec, p)[0]; p += 4; ints = struct.unpack_from(f"<{c_int}i", dec, p); p += c_int * 4
    c_long = struct.unpack_from("<I", dec, p)[0]; p += 4 + c_long * 8
    c_double = struct.unpack_from("<I", dec, p)[0]; p += 4 + c_double * 8
    c_str = struct.unpack_from("<I", dec, p)[0]; p += 4
    strs = []
    for _ in range(c_str):
        slen = struct.unpack_from("<I", dec, p)[0]; p += 4
        strs.append(dec[p:p + slen * 2].decode("utf-16-le", errors="replace"))
        p += slen * 2
        if (slen * 2) % 4 != 0: p += 2
    # Print OBJS overview
    opos = dec.find(b"OBJS")
    print("OBJS at", hex(opos), "len=", len(dec) - opos)
    # Search OBJS for variant refs or top-level function code
    # In TJS2 bytecode: each OBJ starts with 'OBJ ' or toplevel indices
    p = opos + 8
    toplevel, obj_count = struct.unpack_from("<II", dec, p)
    print(f"  toplevel={toplevel} obj_count={obj_count}")
    # Also scan code regions inside dec[opos:] for consecutive uint32s or references to string indices [15..25] and [75..85]
    return ints, strs, dec[opos:]


def main():
    inspect_tbl(os.path.join(GAME_DIR, "steam.xp3"))
    inspect_tbl(os.path.join(GAME_DIR, "data.xp3"))

    # Check Initialize.tjs for any anomaly bytes and dump string refs
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    raw, _ = xp3.read_entry(data_xp3, de["system/Initialize.tjs"])
    dec, k1, k2, sp = decrypt_tjs2(raw)
    print(f"\nInitialize.tjs k1={hex(k1)} k2={hex(k2)} sp={hex(sp)}")
    ints, strs, objs = parse_tjs2_full(dec)
    print("  ints:", ints)
    # Wait: let's parse OBJS chunk properly to inspect all OBJ names and string refs!
    p = 8
    toplevel, obj_count = struct.unpack_from("<II", objs, p); p += 8
    for oi in range(obj_count):
        if objs[p:p+4] != b"FILE":
            # check obj header: might be uint32 name_idx, context_type, max_reg, code_size...
            # Actually in TJS2100: TJS2ByteCodeLoader -> 'OBJ ' chunk? Wait print hex!
            print(f"  objs[{hex(p)}..]: {objs[p:p+64].hex()}")
            break


if __name__ == "__main__":
    main()
