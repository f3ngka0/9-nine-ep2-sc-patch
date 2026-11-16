"""Inspect Initialize.tjs TJS2 bytecode strings/constants around patch.xp3 and test xp3 roundtrip."""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import xp3

game_dir = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
data_xp3 = os.path.join(game_dir, "data.xp3")
entries = xp3.parse_xp3_entries(data_xp3)

# Also inspect raw TJS2 DATA + OBJS of system/Initialize.tjs
raw_init, _ = xp3.read_entry(
    data_xp3,
    entries["system/Initialize.tjs"],
)
# Known keys from earlier run: k1=0x78, k2=0x93, split=0x7a0
dec = bytes(raw_init[i] ^ (0x78 if i < 0x7a0 else 0x93) for i in range(len(raw_init)))
print("Initialize.tjs magic:", dec[:8], "size:", len(dec))

# Parse TJS2 DATA section
p = 8
file_sz = struct.unpack_from("<I", dec, p)[0]; p += 4
assert dec[p:p+4] == b"DATA"
dsz = struct.unpack_from("<I", dec, p+4)[0]; p += 8
dp = p
def skip_pad():
    global dp
    if dp & 3: dp = (dp + 3) & ~3

n_i8 = struct.unpack_from("<I", dec, dp)[0]; dp += 4 + n_i8; skip_pad()
n_i16 = struct.unpack_from("<I", dec, dp)[0]; dp += 4 + n_i16*2; skip_pad()
n_i32 = struct.unpack_from("<I", dec, dp)[0]; dp += 4 + n_i32*4; skip_pad()
n_i64 = struct.unpack_from("<I", dec, dp)[0]; dp += 4 + n_i64*8; skip_pad()
n_dbl = struct.unpack_from("<I", dec, dp)[0]; dp += 4 + n_dbl*8; skip_pad()
n_str = struct.unpack_from("<I", dec, dp)[0]; dp += 4
strs = []
for _ in range(n_str):
    slen = struct.unpack_from("<I", dec, dp)[0]; dp += 4
    strs.append(dec[dp:dp+slen*2].decode("utf-16-le", errors="replace"))
    dp += slen * 2
    skip_pad()
n_oct = struct.unpack_from("<I", dec, dp)[0]; dp += 4
print(f"DATA parsed cleanly: {n_str} strings, {n_oct} octets, ends at {p+dsz} (cur {dp})")

# Inspect OBJS header
p = dp
assert dec[p:p+4] == b"OBJS", dec[p-16:p+16]
opsz = struct.unpack_from("<I", dec, p+4)[0]
op = p + 8
top_lvl, obj_cnt = struct.unpack_from("<II", dec, op); op += 8
print(f"OBJS: top_lvl={top_lvl}, obj_cnt={obj_cnt}, strs={strs}")
# Scan top-level bytecode strings referenced near patch.xp3
for oid in range(obj_cnt):
    assert dec[op:op+4] == b"OBJC", (oid, dec[op:op+4])
    osz = struct.unpack_from("<I", dec, op+4)[0]
    obody = dec[op+8:op+8+osz]
    op += 8 + osz
    # In OBJC: parent(4), name(4=str_idx), ctx_type(4), max_var(4), max_arg(4), max_loc(4), max_tmp(4), code_sz(4)...
    parent, name_idx, ctype = struct.unpack_from("<iii", obody, 0)
    csz = struct.unpack_from("<i", obody, 28)[0]
    code_start = 32
    code_words = struct.unpack_from(f"<{csz}i", obody, code_start)
    # Check variants table after code:
    vpos = code_start + csz * 4
    vpos = (vpos + 3) & ~3
    vcnt = struct.unpack_from("<i", obody, vpos)[0]; vpos += 4
    # print objects that reference patch.xp3 or Storages or Override
    v_items = []
    for _ in range(vcnt):
        vt, vi = struct.unpack_from("<hh", obody, vpos); vpos += 4
        if vt == 5: # string
            v_items.append(strs[vi] if 0 <= vi < len(strs) else f"str#{vi}")
    nm = strs[name_idx] if 0 <= name_idx < len(strs) else str(name_idx)
    if any(w in str(v_items) for w in ["patch", "Override", "Storages", "AfterInit"]):
        print(f"  OBJC[{oid}] name={nm!r} strs={v_items}")
