import os
import struct
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def decrypt_tjs2(raw: bytes):
    k1 = Counter(raw[i] ^ b"TJS2100\x00"[i] for i in range(8)).most_common(1)[0][0]
    dec1 = bytes(b ^ k1 for b in raw)
    tail = raw[0xA00:]
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


def parse_tjs2_objs(dec: bytes):
    pos = dec.find(b"DATA")
    p = pos + 8
    c_byte = struct.unpack_from("<I", dec, p)[0]; p += 4
    bvals = list(dec[p:p + c_byte]); p += ((c_byte + 3) // 4) * 4
    c_short = struct.unpack_from("<I", dec, p)[0]; p += 4
    svals = list(struct.unpack_from(f"<{c_short}h", dec, p)); p += ((c_short * 2 + 3) // 4) * 4
    c_int = struct.unpack_from("<I", dec, p)[0]; p += 4
    ivals = list(struct.unpack_from(f"<{c_int}i", dec, p)); p += c_int * 4
    c_long = struct.unpack_from("<I", dec, p)[0]; p += 4
    lvals = list(struct.unpack_from(f"<{c_long}q", dec, p)); p += c_long * 8
    c_dbl = struct.unpack_from("<I", dec, p)[0]; p += 4
    dvals = list(struct.unpack_from(f"<{c_dbl}d", dec, p)); p += c_dbl * 8
    c_str = struct.unpack_from("<I", dec, p)[0]; p += 4
    strs = []
    for _ in range(c_str):
        slen = struct.unpack_from("<I", dec, p)[0]; p += 4
        if p + slen * 2 > len(dec): break
        strs.append(dec[p:p + slen * 2].decode("utf-16-le", errors="replace"))
        p += slen * 2
        if (slen * 2) % 4 != 0: p += 2
    opos = dec.find(b"OBJS")
    _, count = struct.unpack_from("<II", dec, opos + 8)
    p = opos + 16
    out = []
    for i in range(count):
        sz = struct.unpack_from("<I", dec, p + 4)[0]
        body = dec[p + 8:p + 8 + sz]
        p += 8 + sz
        hdr = struct.unpack_from("<14i", body, 0)
        name_idx = hdr[2]
        name = strs[name_idx] if 0 <= name_idx < len(strs) else f"#{name_idx}"
        code_words = hdr[13]
        code = struct.unpack_from(f"<{code_words}H", body, 56)
        off = 56 + code_words * 2
        if off % 4 != 0: off += 2
        vcount = struct.unpack_from("<I", body, off)[0]; off += 4
        consts = []
        for _ in range(vcount):
            if off + 4 > len(body): break
            t, idx = struct.unpack_from("<hh", body, off); off += 4
            if t == 3 and 0 <= idx < len(strs): val = strs[idx]
            elif t == 6 and 0 <= idx < len(bvals): val = bvals[idx]
            elif t == 7 and 0 <= idx < len(svals): val = svals[idx]
            elif t == 8 and 0 <= idx < len(ivals): val = ivals[idx]
            elif t == 9 and 0 <= idx < len(lvals): val = lvals[idx]
            elif t == 5 and 0 <= idx < len(dvals): val = dvals[idx]
            elif t == 0: val = None
            else: val = f"({t},{idx})"
            consts.append(val)
        out.append((i, name, code, consts))
    return out


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    raw, _ = xp3.read_entry(data_xp3, de["system/Initialize.tjs"])
    objs = parse_tjs2_objs(decrypt_tjs2(raw))
    _, _, code0, c0 = objs[0]
    print("=== Initialize.tjs sequence of string constants in code[0:1500] ===")
    # Print whenever code0[i] == 1 (CONST dst, const_idx) or 0x64 (CALLD ...)
    i = 0
    while i < min(1500, len(code0)):
        op = code0[i]
        if op == 1 and i + 2 < len(code0): # CONST %reg, *const
            ci = code0[i + 2]
            v = c0[ci] if ci < len(c0) else f"?{ci}"
            print(f"  {i:4d}: CONST r{code0[i+1]} = {v!r}")
            i += 3
            continue
        if op in (0x67, 0x64, 0x63) and i + 3 < len(code0):
            # Print nearby string const indices
            pass
        # Check for method/prop names referenced directly in word i
        i += 1
    print("\n=== Also dump OBJ[0] ALL string refs in order up to 1500 (excluding lockKey) ===")
    for ci in range(1500):
        w = code0[ci]
        if 2 <= w < len(c0) and isinstance(c0[w], str) and c0[w] not in ("", "lockKey", "EX 3.27-dev.20070519", "bishamon", "Debug", "message", "dm"):
            # filter obvious non-idx small numbers matching ASCII opcodes (< 20 except known)
            if w >= 17 or c0[w] in ("System", "Storages"):
                print(f"  {ci:4d}: [{w:3d}] {c0[w]!r}")


if __name__ == "__main__":
    main()
