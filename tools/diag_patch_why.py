import os
import struct
import sys
import zlib
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def decrypt_tjs2(raw: bytes):
    k1 = Counter(raw[i] ^ b"TJS2100\x00"[i] for i in range(min(8, len(raw)))).most_common(1)[0][0]
    dec1 = bytes(b ^ k1 for b in raw)
    if len(raw) <= 0x750:
        return dec1, k1, k1, len(raw)
    tail = raw[0xA00:] if len(raw) > 0xA00 else raw[0x880:]
    k2 = Counter(tail).most_common(1)[0][0]
    dec2 = bytes(b ^ k2 for b in raw)
    # Try finding exact split using 0-byte scoring across 0x750..min(len,0xA00)
    n = min(len(raw), 0xA00)
    s1 = [1 if ((raw[i] ^ k1) == 0) else 0 for i in range(n)]
    s2 = [1 if ((raw[i] ^ k2) == 0) else 0 for i in range(n)]
    p1 = [0]
    for x in s1:
        p1.append(p1[-1] + x)
    best_val, best_sp = -1, n
    suf = 0
    for sp_c in range(n - 1, 0x750 - 1, -1):
        suf += s2[sp_c]
        if p1[sp_c] + suf > best_val:
            best_val = p1[sp_c] + suf
            best_sp = sp_c
    return dec1[:best_sp] + dec2[best_sp:], k1, k2, best_sp


def parse_tjs2_data_safe(dec: bytes):
    pos = dec.find(b"DATA")
    if pos == -1:
        return []
    dsize = struct.unpack_from("<I", dec, pos + 4)[0]
    p = pos + 8
    c_byte = struct.unpack_from("<I", dec, p)[0]; p += 4 + ((c_byte + 3) // 4) * 4
    c_short = struct.unpack_from("<I", dec, p)[0]; p += 4 + ((c_short * 2 + 3) // 4) * 4
    c_int = struct.unpack_from("<I", dec, p)[0]; p += 4 + c_int * 4
    c_long = struct.unpack_from("<I", dec, p)[0]; p += 4 + c_long * 8
    c_double = struct.unpack_from("<I", dec, p)[0]; p += 4 + c_double * 8
    c_str = struct.unpack_from("<I", dec, p)[0]; p += 4
    strs = []
    for i in range(c_str):
        if p + 4 > pos + 8 + dsize:
            strs.append(f"<ERR_OOB_LEN i={i} p={hex(p)}>")
            break
        slen = struct.unpack_from("<I", dec, p)[0]; p += 4
        if slen > 50000 or p + slen * 2 > len(dec):
            strs.append(f"<ERR_BAD_SLEN i={i} slen={slen} p={hex(p)} hex={dec[p-4:p+16].hex()}>")
            # Scan forward to resync? Better yet just break and inspect
            break
        s = dec[p:p + slen * 2].decode("utf-16-le", errors="replace")
        strs.append(s)
        p += slen * 2
        if (slen * 2) % 4 != 0:
            p += 2
    return strs


def dump_xp3_raw_index(path: str):
    with open(path, "rb") as f:
        hdr = f.read(40)
        print(f"XP3 {path}: hdr={hdr.hex()}")
        if hdr[11] == 0x17:
            tbl_off = struct.unpack_from("<Q", hdr, 32)[0]
            f.seek(tbl_off)
            flg = f.read(1)[0]
            zsize, osize = struct.unpack("<QQ", f.read(16))
            raw = f.read(zsize)
            tbl = zlib.decompress(raw) if (flg & 1) else raw
            print(f"  tbl_off={tbl_off} flg={flg} zsize={zsize} osize={osize} tbl_len={len(tbl)}")
            # Parse first File chunk completely
            if tbl[:4] == b"File":
                fsize = struct.unpack_from("<Q", tbl, 4)[0]
                chunk = tbl[12:12 + fsize]
                cp = 0
                while cp < len(chunk):
                    tag = chunk[cp:cp + 4]
                    sz = struct.unpack_from("<Q", chunk, cp + 4)[0]
                    body = chunk[cp + 12:cp + 12 + sz]
                    print(f"    subchunk {tag!r} sz={sz} body={body[:64].hex()}")
                    cp += 12 + sz


def main():
    print("=== Compare test_patch.xp3 vs data.xp3 structure ===")
    dump_xp3_raw_index(r"d:\code\translate\build\test_patch.xp3")
    dump_xp3_raw_index(os.path.join(GAME_DIR, "steam.xp3"))

    print("\n=== TitleCaption inside test_patch.xp3 ===")
    pe = xp3.parse_xp3_entries(r"d:\code\translate\build\test_patch.xp3")
    for k, ent in pe.items():
        data, _ = xp3.read_entry(r"d:\code\translate\build\test_patch.xp3", ent)
        txt = xp3.decode_txtobf(data)
        for line in txt.splitlines():
            if "TitleCaption" in line or "Menu" in line:
                print(f"  {k}: {line!r}")

    print("\n=== Check Initialize.tjs, Storages.tjs, multilang.tjs, steam.tjs ===")
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    steam_xp3 = os.path.join(GAME_DIR, "steam.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    se = xp3.parse_xp3_entries(steam_xp3)

    # Full main/Storages.tjs
    raw_st, _ = xp3.read_entry(data_xp3, de["main/Storages.tjs"])
    print("--- main/Storages.tjs FULL ---")
    print(xp3.decode_txtobf(raw_st))

    # Strings in multilang.tjs, MainWindow.tjs, Override.tjs, steam.tjs, steam_r18hack.tjs
    for arc, entries, name in [
        (steam_xp3, se, "steam.tjs"),
        (steam_xp3, se, "steam_r18hack.tjs"),
        (data_xp3, de, "sysscn/multilang.tjs"),
        (data_xp3, de, "sysscn/Override.tjs"),
        (data_xp3, de, "system/MainWindow.tjs"),
    ]:
        raw, _ = xp3.read_entry(arc, entries[name])
        dec, k1, k2, sp = decrypt_tjs2(raw)
        strs = parse_tjs2_data_safe(dec)
        print(f"\n--- {name} k1={hex(k1)} k2={hex(k2)} sp={hex(sp)} len_strs={len(strs)} ---")
        for i, s in enumerate(strs):
            if "<ERR" in s or any(w in s.lower() for w in ("title", "caption", "patch", "xp3", "archive", "syslang", "lang", "menu", "multilang", "font", "9-nine", "episode")):
                print(f"  [{i}] {s!r}")


if __name__ == "__main__":
    main()
