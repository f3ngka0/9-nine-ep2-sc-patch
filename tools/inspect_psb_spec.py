import os
import struct
import sys

BASE = r"d:\code\translate\build\extracted\data"

# PSB v3 header layout (44 bytes = 11 uint32? Let's verify across all 88!)
# 0..4: "PSB\0"
# 4..6: version (3), 6..8: encrypt (0)
# 8..12: off_encrypt? Wait why was vals[2] == 0x2c AND vals[3] == 0x2c?!
# Wait: in PSB v3:
#   off_names      (0x0c? Wait: why 0x2c at +8 AND 0x2c at +12?)
#   In PSB v3: +0x08 = index_offset (44 = 0x2c), +0x0c = off_names (44 = 0x2c)!
#   +0x10 = off_strings, +0x14 = off_strings_data,
#   +0x18 = off_chunk_offsets, +0x1c = off_chunk_lengths, +0x20 = off_chunk_data,
#   +0x24 = off_entries, +0x28 = checksum!

for sub in ("scn", "uipsd"):
    d = os.path.join(BASE, sub)
    for root, _, files in os.walk(d):
        for fn in sorted(files):
            if not fn.endswith((".scn", ".pimg")):
                continue
            p = os.path.join(root, fn)
            b = open(p, "rb").read()
            hdr = struct.unpack_from("<4sHH9I", b, 0)
            magic, ver, enc = hdr[0], hdr[1], hdr[2]
            u3, o_names, o_strs, o_sdata, o_coffs, o_clens, o_cdata, o_entries, cksum = hdr[3:]
            if sub == "scn" and fn in ("b01.txt.scn", "b02.txt.scn") or fn in ("conf_lang.pimg", "conf_cn.pimg"):
                print(f"{fn:22s} ver={ver} enc={enc} u3={u3:#x} names={o_names:#x} strs={o_strs:#x} sdata={o_sdata:#x} coffs={o_coffs:#x} clens={o_clens:#x} cdata={o_cdata:#x} entries={o_entries:#x} cksum={cksum:#x} len={len(b):#x}")
                print("  names[:32]:", b[o_names:o_names+32].hex())
                print("  strs[:32]:", b[o_strs:o_strs+32].hex())
                print("  coffs[:16]:", b[o_coffs:o_coffs+16].hex())
                print("  clens[:16]:", b[o_clens:o_clens+16].hex())
                print("  entries[:32]:", b[o_entries:o_entries+32].hex())
            assert u3 == 0x2c and o_names == 0x2c, (fn, hdr)
            assert o_names < o_entries < o_strs < o_sdata <= o_coffs <= o_clens <= o_cdata <= len(b), (fn, hdr)
print("All 88 PSB headers satisfy exact v3 layout bounds!")
