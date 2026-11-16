"""Inspect exact byte-level errors in b12c (at 2219), b05c, b07 (at 38582), b15a (at 38582)."""
import os, struct, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
import xp3

data_xp3 = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2\data.xp3"
ents = xp3.parse_xp3_entries(data_xp3)

def dump_info(fn, k1, k2, guess_sp):
    r, a = xp3.read_entry(data_xp3, ents[fn])
    hdr_b = bytearray(r[i]^k1 for i in range(40))
    hdr_b[:12] = b"PSB\x00\x03\x00\x00\x00\x2c\x00\x00\x00"
    hdr = struct.unpack_from("<10I", hdr_b, 0)
    print(f"\n=== {fn}: len={len(r)} adlr={a:#010x} k1={k1:#04x} k2={k2:#04x} hdr={hdr} ===")
    print("  raw[0x880:0x8e0]:", r[0x880:0x8e0].hex(" "))
    print("  dec_k1[hdr[9]:hdr[9]+24]:", bytes(b^k1 for b in r[hdr[9]:hdr[9]+24]).hex(" "))
    print("  dec_k2[hdr[9]:hdr[9]+24]:", bytes(b^k2 for b in r[hdr[9]:hdr[9]+24]).hex(" "))
    # check r[guess_sp-8 : guess_sp+24] XOR k1 and k2
    print(f"  around {guess_sp:#x} ({guess_sp}):")
    print("    ^k1:", bytes(b^k1 for b in r[guess_sp-8:guess_sp+24]).hex(" "))
    print("    ^k2:", bytes(b^k2 for b in r[guess_sp-8:guess_sp+24]).hex(" "))

dump_info("scn/b12c.txt.scn", 0xf4, 0x07, 2219)
dump_info("scn/b16.txt.scn", 0x17, 0x38, 2227)
dump_info("scn/b05c.txt.scn", 0x93, 0x93, 2000)
# Check k2 candidates for b05c using chunk_offs & str_offs!
r5c, _ = xp3.read_entry(data_xp3, ents["scn/b05c.txt.scn"])
h5c = struct.unpack_from("<10I", bytes(b^0x93 for b in r5c[:40]), 0)
print("b05c str_offs raw:", r5c[h5c[4]:h5c[4]+30].hex(" "))
for k in range(256):
    d = bytes(b^k for b in r5c[h5c[4]:h5c[4]+16])
    if d[0] in (0x0d, 0x0e, 0x0f) and d[3] in (0x0d, 0x0e, 0x0f) and d[4] == 0:
        print(f"  b05c cand k2={k:#04x}: {d.hex(' ')}")
# Inspect b07 and b15a at 38582!
for fn, k1, k2 in [("scn/b07.txt.scn", 0xef, 0x8d), ("scn/b15a.txt.scn", 0x0b, 0x8d)]:
    r, a = xp3.read_entry(data_xp3, ents[fn])
    print(f"\n{fn} dec^k2[38570:38600]:", bytes(b^k2 for b in r[38570:38600]).hex(" "))
