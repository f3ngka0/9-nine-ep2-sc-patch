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


def dump_objs(dec: bytes, data_pool):
    opos = dec.find(b"OBJS")
    size = struct.unpack_from("<I", dec, opos + 4)[0]
    p = opos + 8
    toplevel, count = struct.unpack_from("<II", dec, p); p += 8
    print(f"OBJS toplevel={toplevel} count={count}")
    objs = []
    for i in range(count):
        tag = dec[p:p + 4]
        assert tag == b"FILE" or tag == b"TJS2", (i, tag, dec[p:p+16])
        # Actually inspect tag + size
        objsz = struct.unpack_from("<I", dec, p + 4)[0]
        body = dec[p + 8:p + 8 + objsz]
        p += 8 + objsz
        parent, name_idx, ctx_type, max_var, max_reg, num_funcdecl, this_proxy, call_parent = struct.unpack_from("<iIIIIIii", body, 0)
        # Wait let's inspect first 44 bytes of body[0..] for TJS2 obj format:
        # parent(4), name(4), ctx_type(4), max_vars(4), max_regs(4), max_args(4), funcdecl_vardecl?(4) ...
        hdr = struct.unpack_from("<10i", body, 0)
        name = data_pool["str"][name_idx] if 0 <= name_idx < len(data_pool["str"]) else f"#{name_idx}"
        code_len = struct.unpack_from("<I", body, 40)[0]
        print(f"  OBJ[{i:2d}] tag={tag} sz={objsz} name={name!r} ctx={ctx_type} hdr[5:10]={hdr[5:10]} code_words={code_len}")
        objs.append((i, name, body))
    # Parse variants table after code in OBJ 0 (Initialize.tjs top-level)
    _, name, body = objs[0]
    code_len = struct.unpack_from("<I", body, 40)[0]
    # Code is code_len uint32s? wait 44 + code_len*4 vs 44 + code_len*2? Look at objsz=8092, code_len=0xcc7=3271 -> 3271*2 = 6542 (< 8092)! 3271*4 = 13084 (> 8092)! So code_len is in uint16 (tjs_uint16/int16) OR uint32? Wait 44 + 3271*2 = 6586 -> remaining ~1500 bytes!
    voff = 44 + code_len * 2
    if voff % 4 != 0:
        voff += 2
    print(f"  OBJ[0] after code voff={voff}/{len(body)} tail_hex={body[voff:voff+48].hex()}")
    # variant data count: in TJS2 bytecode each variant ref is (int16 type, int16 index) = 4 bytes! Look: first 4 bytes count of variants, then count * 4 bytes!
    vcount = struct.unpack_from("<I", body, voff)[0]
    print(f"  vcount={vcount} (voff+4+vcount*4={voff+4+vcount*4})")
    voff += 4
    consts = []
    TYPE_NAMES = {0: "void", 1: "obj", 2: "str", 3: "oct", 4: "int", 5: "real", 6: "byte", 7: "short", 8: "long", -1: "interobj", -2: "intergen"}
    for vi in range(vcount):
        if voff + 4 > len(body): break
        t, idx = struct.unpack_from("<hh", body, voff)
        voff += 4
        if t == 2:
            val = data_pool["str"][idx] if 0 <= idx < len(data_pool["str"]) else f"str#{idx}"
        elif t == 6:
            val = data_pool["byte"][idx]
        elif t == 7:
            val = data_pool["short"][idx]
        elif t == 4:
            val = data_pool["int"][idx]
        elif t == 5:
            val = data_pool["double"][idx]
        elif t == 0:
            val = None
        else:
            val = (t, idx)
        consts.append((vi, t, idx, val))
        if isinstance(val, str) or vi < 60:
            print(f"    var[{vi:3d}] t={t} idx={idx} val={val!r}")
    return objs


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    steam_xp3 = os.path.join(GAME_DIR, "steam.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    se = xp3.parse_xp3_entries(steam_xp3)

    # 1. Search where "Episode2" (without space) vs "Episode 2" appears in data.xp3 / steam.xp3
    print("=== Searching for Episode2 / TitleCaption in ini & tjs ===")
    for k in sorted(de.keys()):
        if k.endswith((".ini", ".tjs", ".ks", ".txt")):
            raw, _ = xp3.read_entry(data_xp3, de[k])
            txt = xp3.decode_txtobf(raw)
            if txt and ("Episode" in txt or "TitleCaption" in txt or "patch.xp3" in txt or "ENV_GameName" in txt):
                print(f"  [txtobf] {k}:")
                for line in txt.splitlines():
                    if any(w in line for w in ("Episode", "TitleCaption", "patch", "ENV_GameName")):
                        print(f"    {line.strip()[:120]}")

    # 2. Check Initialize.tjs OBJS
    raw, _ = xp3.read_entry(data_xp3, de["system/Initialize.tjs"])
    dec = decrypt_tjs2(raw)
    pool = parse_data(dec)
    objs = dump_objs(dec, pool)
    # Print any objs mentioning archive/patch/useArchiveIfExists
    for oi, oname, body in objs:
        print(f"OBJ[{oi}] {oname!r}")


if __name__ == "__main__":
    main()
