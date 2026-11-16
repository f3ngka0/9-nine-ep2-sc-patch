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
    if len(raw) <= 0x750:
        return dec1
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


def parse_data(dec: bytes):
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
    return {"byte": bvals, "short": svals, "int": ivals, "long": lvals, "double": dvals, "str": strs}


def dump_obj(body: bytes, data_pool, label: str):
    hdr = struct.unpack_from("<14i", body, 0)
    code_words = hdr[13]
    print(f"\n=== {label} (sz={len(body)}) hdr={hdr[:13]} code_words={code_words} ===")
    code = struct.unpack_from(f"<{code_words}H", body, 56)
    off = 56 + code_words * 2
    if off % 4 != 0:
        off += 2
    vcount = struct.unpack_from("<I", body, off)[0]; off += 4
    consts = []
    # In TJS2 bytecode: voff holds pairs of (uint32 type, uint32 index)? Let's print hex if unsure!
    print(f"  vcount={vcount} off={off} first_variants={body[off:off+32].hex()}")
    TYPE_OBJ = -1
    for vi in range(vcount):
        if off + 4 > len(body): break
        t, idx = struct.unpack_from("<hh", body, off); off += 4
        if t == 2 and 0 <= idx < len(data_pool["str"]): val = data_pool["str"][idx]
        elif t == 6 and 0 <= idx < len(data_pool["byte"]): val = data_pool["byte"][idx]
        elif t == 7 and 0 <= idx < len(data_pool["short"]): val = data_pool["short"][idx]
        elif t == 4 and 0 <= idx < len(data_pool["int"]): val = data_pool["int"][idx]
        elif t == 5 and 0 <= idx < len(data_pool["double"]): val = data_pool["double"][idx]
        elif t == 0: val = None
        else: val = f"({t},{idx})"
        consts.append(val)
    print("  variants:", [(i, v) for i, v in enumerate(consts) if v is not None][:80])
    print("  first 40 code words:", [hex(x) for x in code[:40]])


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    raw, _ = xp3.read_entry(data_xp3, de["system/Initialize.tjs"])
    dec = decrypt_tjs2(raw)
    pool = parse_data(dec)

    opos = dec.find(b"OBJS")
    p = opos + 16
    objs = []
    for i in range(39):
        sz = struct.unpack_from("<I", dec, p + 4)[0]
        objs.append(dec[p + 8:p + 8 + sz])
        p += 8 + sz

    for idx in (0, 8, 9, 10, 11, 12, 13, 14):
        nidx = struct.unpack_from("<I", objs[idx], 8)[0]
        dump_obj(objs[idx], pool, f"OBJ[{idx}] {pool['str'][nidx] if 0 <= nidx < len(pool['str']) else nidx}")

    # Check main/custom.tjs around updateTitleCaption and main/default.tjs
    for fname in ("main/custom.tjs", "main/default.tjs"):
        r, _ = xp3.read_entry(data_xp3, de[fname])
        txt = xp3.decode_txtobf(r)
        print(f"\n=== {fname} relevant lines ===")
        lines = txt.splitlines()
        for idx, line in enumerate(lines):
            if any(w in line.lower() for w in ("titlecaption", "updatetitle", "lang", "env_gamename")):
                start = max(0, idx - 2)
                end = min(len(lines), idx + 8)
                for k in range(start, end):
                    print(f"  L{k+1}: {lines[k]}")
                print("  ---")


if __name__ == "__main__":
    main()
