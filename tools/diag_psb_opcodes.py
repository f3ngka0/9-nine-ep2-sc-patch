import os
import struct
import sys
import zlib

BASE = r"d:\code\translate\build\extracted\data"

# First check what +0x28 checksum matches in conf_lang.pimg and b04.txt.scn!
for rel in ("uipsd/conf_lang.pimg", "scn/b04.txt.scn", "uipsd/cn/conf_cn.pimg"):
    b = open(os.path.join(BASE, rel), "rb").read()
    hdr = struct.unpack_from("<4sHH9I", b, 0)
    _, _, _, u3, on, os_, osd, oco, ocl, ocd, oe, cksum = hdr
    # Check adler32 of various ranges!
    ranges = [
        ("4..28", b[4:0x28]),
        ("0..28", b[0:0x28]),
        ("names..entries", b[on:oe]),
        ("names..strs", b[on:os_]),
        ("names..sdata", b[on:osd]),
        ("entries..strs", b[oe:os_]),
        ("entries..sdata", b[oe:osd]),
        ("entries..coffs", b[oe:oco]),
        ("entries..eof", b[oe:]),
        ("0x2c..eof", b[0x2c:]),
    ]
    matches = [rn for rn, sl in ranges if (zlib.adler32(sl) & 0xFFFFFFFF) == cksum or (zlib.adler32(sl, 0) & 0xFFFFFFFF) == cksum]
    print(f"{rel}: cksum={cksum:#010x} adler matches={matches}")
    if not matches:
        # Also test small slices / crc32 / s1+s2 swapped!
        for rn, sl in ranges:
            a1 = zlib.adler32(sl, 1) & 0xFFFFFFFF
            a0 = zlib.adler32(sl, 0) & 0xFFFFFFFF
            c = zlib.crc32(sl) & 0xFFFFFFFF
            print(f"  {rn:15s}: a1={a1:#010x} a0={a0:#010x} crc={c:#010x}")

# Also inspect PSB standard name trie + int array + string table on conf_lang.pimg!
b = open(os.path.join(BASE, "uipsd/conf_lang.pimg"), "rb").read()
hdr = struct.unpack_from("<4sHH9I", b, 0)
u3, on, os_, osd, oco, ocl, ocd, oe, cksum = hdr[3:]

def read_int_array(buf, pos):
    t = buf[pos]; pos += 1
    assert 0x0d <= t <= 0x10, hex(t)
    w = t - 0x0c
    count = int.from_bytes(buf[pos:pos+w], "little"); pos += w
    t2 = buf[pos]; pos += 1
    assert 0x0d <= t2 <= 0x10, hex(t2)
    ew = t2 - 0x0c
    vals = [int.from_bytes(buf[pos+i*ew:pos+(i+1)*ew], "little") for i in range(count)]
    return vals, pos + count * ew

def decode_names(buf, pos):
    v1, p = read_int_array(buf, pos)   # charset / deltas?
    v2, p = read_int_array(buf, p)     # tree / offsets?
    v3, p = read_int_array(buf, p)     # leaf indexes?
    print(f"  names arrays: v1(len={len(v1)})={v1[:20]} v2(len={len(v2)})={v2[:20]} v3(len={len(v3)})={v3[:20]} next_pos={p:#x} (entries={oe:#x})")
    # Standard PSB name trie decoding:
    # For each entry i in v3: index = v3[i]
    # Walk parent in v2? Wait: in PSB v2/v3 trie:
    # Wait: v1 is value[], v2 is tree[]! Wait or v1=charset, v2=tree/nodes? Let's check conf_lang.pimg!
    # Look at conf_lang names[:32] earlier: 0d b6 ... -> len(v1) = 0xb6? No: v1 had 1-byte ints? Wait look!
    # Wait earlier names[:32]: 0d b6 0d 01 ...Wait!
    return v1, v2, v3

v1, v2, v3 = decode_names(b, on)
offs, p_s = read_int_array(b, os_)
strs = [b[osd+o:b.find(b"\x00", osd+o)].decode("utf-8") for o in offs]
print(f"conf_lang strings ({len(strs)}):", strs)
coffs, _ = read_int_array(b, oco)
clens, _ = read_int_array(b, ocl)
print("conf_lang chunks:", list(zip(coffs, clens)))
for i, (co, cl) in enumerate(zip(coffs, clens)):
    print(f"  chunk[{i}] off={co} len={cl} magic={b[ocd+co:ocd+co+16]!r}")
