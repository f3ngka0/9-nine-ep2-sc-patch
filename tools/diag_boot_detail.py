import os
import struct
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def decrypt_cxdec_heuristic(raw: bytes, magic: bytes = None):
    if magic:
        k1 = Counter(raw[i] ^ magic[i] for i in range(min(len(magic), len(raw)))).most_common(1)[0][0]
    else:
        # Assume UTF-16LE BOM FF FE or ASCII even/odd nulls
        if len(raw) >= 4:
            # try UTF-16LE (high bytes mostly 0)
            cand = Counter(raw[1:min(len(raw), 0x700):2]).most_common(1)[0][0]
            k1 = cand
        else:
            k1 = 0
    dec1 = bytes(b ^ k1 for b in raw)
    if len(raw) <= 0x750:
        return dec1, k1, k1, len(raw)
    tail = raw[0xA00:] if len(raw) > 0xA00 else raw[0x880:]
    # For UTF-16LE text vs TJS2 bytecode:
    if magic == b"TJS2100\x00":
        k2 = Counter(tail).most_common(1)[0][0]
    else:
        k2 = Counter(tail[1::2]).most_common(1)[0][0]
        if (dec1[0], dec1[1]) != (0xFF, 0xFE):
            # Could be UTF-8 (\n or space most common)
            pass
    dec2 = bytes(b ^ k2 for b in raw)
    n = min(len(raw), 0xA00)
    s1 = [1 if ((raw[i] ^ k1) == 0) else 0 for i in range(n)]
    s2 = [1 if ((raw[i] ^ k2) == 0) else 0 for i in range(n)]
    p1 = [0]
    for x in s1:
        p1.append(p1[-1] + x)
    best_val, best_sp = -1, n
    suf = 0
    for sp_cand in range(n - 1, 0x750 - 1, -1):
        suf += s2[sp_cand]
        v = p1[sp_cand] + suf
        if v > best_val:
            best_val = v
            best_sp = sp_cand
    return dec1[:best_sp] + dec2[best_sp:], k1, k2, best_sp


def parse_tjs2_data(dec: bytes):
    pos = dec.find(b"DATA")
    if pos == -1:
        return None
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
        slen = struct.unpack_from("<I", dec, p)[0]; p += 4
        s = dec[p:p + slen * 2].decode("utf-16-le", errors="replace")
        strs.append(s)
        p += slen * 2
        if (slen * 2) % 4 != 0:
            p += 2
    return strs


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    steam_xp3 = os.path.join(GAME_DIR, "steam.xp3")
    d_entries = xp3.parse_xp3_entries(data_xp3)
    s_entries = xp3.parse_xp3_entries(steam_xp3)

    targets = [
        (data_xp3, d_entries, "startup.tjs#1"),
        (data_xp3, d_entries, "system/Initialize.tjs"),
        (data_xp3, d_entries, "main/Storages.tjs"),
        (data_xp3, d_entries, "sysscn/syslangtext.tjs"),
        (data_xp3, d_entries, "sysscn/AfterInit.tjs"),
        (steam_xp3, s_entries, "steam.tjs"),
        (steam_xp3, s_entries, "steam_r18hack.tjs"),
        (data_xp3, d_entries, "sysscn/multilang.tjs"),
    ]

    for arc, entries, name in targets:
        raw, _ = xp3.read_entry(arc, entries[name])
        print(f"\n================ {name} ({len(raw)} bytes) ================")
        # Check if TJS2100 or plain text
        k1_tjs = Counter(raw[i] ^ b"TJS2100\x00"[i] for i in range(8)).most_common(1)[0]
        if k1_tjs[1] >= 6:
            dec, k1, k2, sp = decrypt_cxdec_heuristic(raw, b"TJS2100\x00")
            strs = parse_tjs2_data(dec)
            print(f"TJS2100 k1={hex(k1)} k2={hex(k2)} sp={hex(sp)} n_strs={len(strs)}")
            if len(strs) <= 350:
                for i, s in enumerate(strs):
                    print(f"  [{i:3d}] {s!r}")
            else:
                for i, s in enumerate(strs):
                    if any(w in s.lower() for w in ("patch", "xp3", "archive", "title", "caption", "syslang", "lang", "font", "steam", "sig", "ini", "multilang", "storages", "sc", "cn", "en", "jp", "chinese", "uipsd")):
                        print(f"  [{i:3d}] {s!r}")
        else:
            # Try UTF-16LE BOM ff fe
            dec, k1, k2, sp = decrypt_cxdec_heuristic(raw, None)
            # verify BOM
            if len(raw) >= 2:
                bk1 = raw[0] ^ 0xFF
                if (raw[1] ^ bk1) == 0xFE:
                    dec1 = bytes(b ^ bk1 for b in raw)
                    # find k2 from tail high bytes
                    k2 = Counter(raw[0x880:][1::2]).most_common(1)[0][0] if len(raw) > 0x880 else bk1
                    dec2 = bytes(b ^ k2 for b in raw)
                    n = min(len(raw), 0xA00)
                    best_sp = n
                    if len(raw) > 0x750:
                        best_val = -1
                        for sp_c in range(0x750, n):
                            sc = sum(1 for i in range(0x751, sp_c, 2) if (raw[i] ^ bk1) == 0) + sum(1 for i in range(sp_c | 1, n, 2) if (raw[i] ^ k2) == 0)
                            if sc > best_val:
                                best_val = sc
                                best_sp = sp_c
                    dec = dec1[:best_sp] + dec2[best_sp:]
                    print(f"UTF16LE k1={hex(bk1)} k2={hex(k2)} sp={hex(best_sp)}")
                    print(dec.decode("utf-16", errors="replace"))
                else:
                    # Maybe UTF-8 or Shift-JIS or obfuscated txtobf
                    txt = xp3.decode_txtobf(raw)
                    print("txtobf?" , repr(txt[:300]) if txt else repr(raw[:100]))


if __name__ == "__main__":
    main()
