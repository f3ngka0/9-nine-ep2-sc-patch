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


# TJS2 VM instruction decoder (kirikiri2 tjsInterCodeExec.h VM_*)
def disasm_tjs2(code, consts, start=0, end=None):
    if end is None: end = len(code)
    def reg(x):
        s = x - 65536 if x >= 32768 else x
        return f"%{s}"
    def cval(x):
        return repr(consts[x]) if x < len(consts) else f"*{x}"
    i = start
    lines = []
    while i < end:
        op = code[i]
        a = lambda k: code[i+k] if i+k < len(code) else 0
        sa = lambda k: (code[i+k] - 65536 if code[i+k] >= 32768 else code[i+k]) if i+k < len(code) else 0
        # Map known opcodes from krkr2 tjs2 VM:
        if op == 0x00: lines.append(f"{i:4d}: NOP"); i += 1
        elif op == 0x01: lines.append(f"{i:4d}: CONST {reg(a(1))}, {cval(a(2))}"); i += 3
        elif op == 0x02: lines.append(f"{i:4d}: CP {reg(a(1))}, {reg(a(2))}"); i += 3
        elif op == 0x03: lines.append(f"{i:4d}: CL {reg(a(1))}"); i += 2
        elif op == 0x04: lines.append(f"{i:4d}: CCL {reg(a(1))}..+{a(2)}"); i += 3
        elif op in (0x05, 0x06): lines.append(f"{i:4d}: {'TT' if op==5 else 'TF'} {reg(a(1))}"); i += 2
        elif op in (0x07, 0x08): lines.append(f"{i:4d}: CEQ/CDEQ {reg(a(1))}, {reg(a(2))}"); i += 3
        elif op in (0x09, 0x0a): lines.append(f"{i:4d}: CLT/CGT {reg(a(1))}, {reg(a(2))}"); i += 3
        elif op == 0x0b: lines.append(f"{i:4d}: SETF {reg(a(1))}"); i += 2
        elif op == 0x0c: lines.append(f"{i:4d}: SETNF {reg(a(1))}"); i += 2
        elif op == 0x0d: lines.append(f"{i:4d}: LNOT {reg(a(1))}"); i += 2
        elif op == 0x0e: lines.append(f"{i:4d}: NF {reg(a(1))}"); i += 2
        elif op == 0x0f: lines.append(f"{i:4d}: JF -> {i + sa(1)}"); i += 2
        elif op == 0x10: lines.append(f"{i:4d}: JNF -> {i + sa(1)}"); i += 2
        elif op == 0x11: lines.append(f"{i:4d}: JMP -> {i + sa(1)}"); i += 2
        elif op in (0x12, 0x13): lines.append(f"{i:4d}: INC/DEC {reg(a(1))}"); i += 2
        elif 0x14 <= op <= 0x62:
            # Arithmetic/prop: check 3-word vs 4-word
            # Look at OBJ[8]: 0x3a is ADD (%1, %2) -> 3 words!
            # Look at 0x25: SETF/EQ? Wait: check 0x14..0x62 lengths cleanly
            # Wait: 0x3a=ADD (3 words), 0x3e=ADDP?
            # Actually standard TJS2 VM: ops < 0x63 mostly 3 words (except INC/DEC/bitnot/neg/ret)
            lines.append(f"{i:4d}: OP_{op:#04x} {reg(a(1))}, {reg(a(2))}"); i += 3
        elif op in (0x63, 0x64): # CALL / CALLD
            argc = a(3) if op == 0x63 else a(4)
            # In OBJ[8]: '64', '2', '1', '6', '1', 'fffc' -> CALLD(0x64) dst=%2, obj=%1, prop=consts[6]='isExistentStorage', argc=1, arg0=%-4 !! Wait 6 words if argc>=0? No! argc=1 -> 1 arg = 6 words total!
            if op == 0x64:
                # Check special argc encodings (-1 = expand array, -2 = omit)
                nargs = 0 if argc >= 0x8000 else argc
                args = [reg(code[i+5+k]) for k in range(nargs)]
                lines.append(f"{i:4d}: CALLD {reg(a(1))} = {reg(a(2))}.{cval(a(3))}({', '.join(args)}) [raw_argc={sa(4)}]")
                i += 5 + nargs
            else:
                # CALL(0x63) dst, fn, argc, args...
                argc = a(3)
                nargs = 0 if argc >= 0x8000 else argc
                args = [reg(code[i+4+k]) for k in range(nargs)]
                lines.append(f"{i:4d}: CALL {reg(a(1))} = {reg(a(2))}({', '.join(args)}) [raw_argc={sa(3)}]")
                i += 4 + nargs
        elif op == 0x67: # GPD dst, obj, prop
            lines.append(f"{i:4d}: GPD {reg(a(1))} = {reg(a(2))}.{cval(a(3))}"); i += 4
        elif op == 0x68:
            lines.append(f"{i:4d}: GPDS {reg(a(1))} = {reg(a(2))}[{reg(a(3))}]"); i += 4
        elif op == 0x69:
            lines.append(f"{i:4d}: SPD {reg(a(1))}.{cval(a(2))} = {reg(a(3))}"); i += 4
        elif op in (0x6a, 0x6b, 0x6c, 0x6d):
            lines.append(f"{i:4d}: S/GP_{op:#x} {reg(a(1))}, {reg(a(2))}, {reg(a(3))}"); i += 4
        elif op == 0x76: lines.append(f"{i:4d}: SRV {reg(a(1))}"); i += 2
        elif op == 0x77: lines.append(f"{i:4d}: RET"); i += 1
        elif op == 0x7c: lines.append(f"{i:4d}: GLOBAL {reg(a(1))}"); i += 2
        else:
            lines.append(f"{i:4d}: RAW_{op:#04x} ({a(1):#x}, {a(2):#x})"); i += 1
    return "\n".join(lines)


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    raw, _ = xp3.read_entry(data_xp3, de["system/Initialize.tjs"])
    objs = parse_tjs2_objs(decrypt_tjs2(raw))

    print("=== OBJ[8] useArchiveIfExists ===")
    print(disasm_tjs2(objs[8][2], objs[8][3]))
    print("\n=== OBJ[9] addArchive ===")
    print(disasm_tjs2(objs[9][2], objs[9][3]))
    print("\n=== OBJ[0] code[200:340] ===")
    print(disasm_tjs2(objs[0][2], objs[0][3], 200, 340))
    print("\n=== OBJ[0] code[920:1080] ===")
    print(disasm_tjs2(objs[0][2], objs[0][3], 920, 1080))
    print("\n=== startup.tjs (plain?) & startup.tjs#1 ===")
    for k in ("startup.tjs", "startup.tjs#1"):
        if k in de:
            r, adlr = xp3.read_entry(data_xp3, de[k])
            print(f"{k}: adlr={hex(adlr)} len={len(r)} head={r[:40].hex()}")


if __name__ == "__main__":
    main()
