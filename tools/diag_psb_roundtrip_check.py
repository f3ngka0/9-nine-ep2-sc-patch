import os
import struct

BASE = r"d:\code\translate\build\extracted\data"

def read_int_array(b, pos):
    t = b[pos]; pos += 1
    cnt = int.from_bytes(b[pos:pos+(t-0x0c)], "little"); pos += t - 0x0c
    t2 = b[pos]; pos += 1
    ew = t2 - 0x0c
    return [int.from_bytes(b[pos+i*ew:pos+(i+1)*ew], "little") for i in range(cnt)], pos + cnt * ew

def decode_names_list(b, pos):
    v1, pos = read_int_array(b, pos)
    v2, pos = read_int_array(b, pos)
    v3, pos = read_int_array(b, pos)
    # Verify mapping: for each leaf in v3, what is v1[leaf] and what is reconstructed string?
    n = len(v3)
    out = [None] * n
    for idx, leaf in enumerate(v3):
        name_id = v1[leaf]
        chars = []
        cur = leaf
        while cur > 0:
            parent = v2[cur]
            ch = cur - v1[parent]
            if ch != 0:
                chars.append(ch)
            cur = parent
        s = bytes(reversed(chars)).decode("utf-8")
        out[name_id] = s
    assert None not in out
    # Also check if v3 is sorted alphabetically or matches idx == name_id!
    return out, pos, (out == [out[v1[leaf]] for leaf in v3])

all_files = []
for sub in ("scn", "uipsd"):
    d = os.path.join(BASE, sub)
    for root, _, files in os.walk(d):
        for fn in sorted(files):
            if fn.endswith((".scn", ".pimg")):
                all_files.append(os.path.join(root, fn))

eq_count = 0
for fp in all_files:
    b = open(fp, "rb").read()
    on, os_, osd, oco, ocl, ocd, oe, cksum = struct.unpack_from("<8I", b, 12)
    names, np_, is_seq = decode_names_list(b, on)
    eq_count += int(is_seq)
    if os.path.basename(fp) in ("b01.txt.scn", "b02.txt.scn"):
        print(os.path.basename(fp), "names len=", len(names), "is_seq=", is_seq, "sorted=", names == sorted(names), "sample=", names[:15])
print(f"Checked all {len(all_files)} name tries: is_seq={eq_count}/{len(all_files)}")
