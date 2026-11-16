import os
import re
import struct
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def decrypt_tjs2(raw: bytes):
    k1 = Counter(raw[i] ^ b"TJS2100\x00"[i] for i in range(8)).most_common(1)[0][0]
    dec1 = bytes(b ^ k1 for b in raw)
    if len(raw) <= 0x750: return dec1
    tail = raw[0xA00:] if len(raw) > 0xA00 else raw[0x880:]
    k2 = Counter(tail).most_common(1)[0][0]
    dec2 = bytes(b ^ k2 for b in raw)
    n = min(len(raw), 0xA00)
    s1 = [1 if ((raw[i] ^ k1) == 0) else 0 for i in range(n)]
    s2 = [1 if ((raw[i] ^ k2) == 0) else 0 for i in range(n)]
    p1 = [0]
    for x in s1: p1.append(p1[-1] + x)
    best_sp, best_sc, suf = n, -1, 0
    for sp_c in range(n - 1, 0x750 - 1, -1):
        suf += s2[sp_c]
        if p1[sp_c] + suf > best_sc:
            best_sc = p1[sp_c] + suf
            best_sp = sp_c
    return dec1[:best_sp] + dec2[best_sp:]


def parse_tjs2_strs(dec: bytes):
    pos = dec.find(b"DATA")
    p = pos + 8
    c_byte = struct.unpack_from("<I", dec, p)[0]; p += 4 + ((c_byte + 3) // 4) * 4
    c_short = struct.unpack_from("<I", dec, p)[0]; p += 4 + ((c_short * 2 + 3) // 4) * 4
    c_int = struct.unpack_from("<I", dec, p)[0]; p += 4 + c_int * 4
    c_long = struct.unpack_from("<I", dec, p)[0]; p += 4 + c_long * 8
    c_dbl = struct.unpack_from("<I", dec, p)[0]; p += 4 + c_dbl * 8
    c_str = struct.unpack_from("<I", dec, p)[0]; p += 4
    strs = []
    for _ in range(c_str):
        if p + 4 > len(dec): break
        slen = struct.unpack_from("<I", dec, p)[0]; p += 4
        if p + slen * 2 > len(dec): break
        strs.append(dec[p:p + slen * 2].decode("utf-16-le", errors="replace"))
        p += slen * 2
        if (slen * 2) % 4 != 0: p += 2
    return strs


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    steam_xp3 = os.path.join(GAME_DIR, "steam.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    se = xp3.parse_xp3_entries(steam_xp3)

    # 1. Print custom.tjs lines around updateTitleCaption and qualia_extra.tjs
    for fname in ("main/custom.tjs", "main/qualia_extra.tjs", "main/default.tjs"):
        raw, _ = xp3.read_entry(data_xp3, de[fname])
        txt = xp3.decode_txtobf(raw)
        lines = txt.splitlines()
        print(f"=== {fname} ({len(lines)} lines) ===")
        for i, l in enumerate(lines):
            if any(w in l.lower() for w in ("titlecaption", "updatetitle", "caption", "system.title", "addarchive", "autopath")):
                for k in range(max(0, i-1), min(len(lines), i+4)):
                    print(f"  L{k+1:4d}: {lines[k]}")
                print("  --")

    # 2. Check steam.tjs ALL strings
    raw_st, _ = xp3.read_entry(steam_xp3, se["steam.tjs"])
    print("\n=== steam.tjs strings ===")
    for i, s in enumerate(parse_tjs2_strs(decrypt_tjs2(raw_st))):
        print(f"  [{i:3d}] {s!r}")

    # 3. Check AppConfig & Config.tjs & steam.xp3/achievement.ini & nine_sorairo.exe plain UTF-16/ASCII strings matching Episode2 or signature
    exe_path = os.path.join(GAME_DIR, "nine_sorairo.exe")
    with open(exe_path, "rb") as f:
        exeb = f.read()
    print("\n=== nine_sorairo.exe literal matches ===")
    for pat in (b"Episode2", b"Episode 2", b"SIGNATURE", b".xp3.sig", b"patch.xp3", b"useArchive", b"data.xp3"):
        print(f"  ascii {pat!r}: count={exeb.count(pat)}")
        u16 = pat.decode("ascii").encode("utf-16-le")
        print(f"  utf16 {pat!r}: count={exeb.count(u16)}")


if __name__ == "__main__":
    main()
