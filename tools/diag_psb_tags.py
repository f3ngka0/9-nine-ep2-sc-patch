import os
import struct
import zlib

BASE = r"d:\code\translate\build\extracted\data"

# Write a minimal recursive walker that tracks every tag byte seen in all 88 PSB files!
def read_int_var(b, pos, w):
    return int.from_bytes(b[pos:pos+w], "little", signed=True), pos + w

def read_uint_var(b, pos, w):
    return int.from_bytes(b[pos:pos+w], "little", signed=False), pos + w

def read_int_array(b, pos):
    t = b[pos]; pos += 1
    assert 0x0d <= t <= 0x10, f"bad array count tag {t:#x} at {pos-1:#x}"
    cnt, pos = read_uint_var(b, pos, t - 0x0c)
    if cnt == 0:
        # Does empty IntArray still have elem_type byte?! Look at conf_lang or b01 earlier:
        # `20 0d 00 0d` -> YES! count=0 STILL has `0x0d` element-width byte!
        t2 = b[pos]; pos += 1
        assert 0x0d <= t2 <= 0x10, f"bad empty array elem tag {t2:#x} at {pos-1:#x}"
        return [], pos
    t2 = b[pos]; pos += 1
    assert 0x0d <= t2 <= 0x10, f"bad array elem tag {t2:#x} at {pos-1:#x}"
    ew = t2 - 0x0c
    vals = [int.from_bytes(b[pos+i*ew:pos+(i+1)*ew], "little") for i in range(cnt)]
    return vals, pos + cnt * ew

def decode_names_list(b, pos):
    # PSB B-tree names:
    # Actually: let's also verify exact name string reconstruction!
    # In PSB: names section has:
    #   value[] (v1), tree[] (v2), data[] / leaf_to_name_id?
    # Standard Emote/FreeMote trie:
    # Wait: let's check both v1/v2/v3 lengths on conf_lang.pimg and print reconstructed strings!
    v1, pos = read_int_array(b, pos)  # char / tail? Wait: v1 is offsets/charset, v2 is tree, v3 is tails?
    v2, pos = read_int_array(b, pos)
    v3, pos = read_int_array(b, pos)
    # Wait: in FreeMote PSB Names:
    #   `names.charset`? No: `names.value` (`v1`), `names.tree` (`v2`), `names.names` (`v3` = leaf node index for each name_id? Let's check!)
    # Check len(v1) == len(v2) on conf_lang earlier: 182 == 182! And len(v3) == 19!
    #Wait how do v1[node] & v2[node] reconstruct strings?
    # Node `c` has parent `p = v1[c]`, and char = `c - v2[p]`!!
    names = []
    for i, leaf in enumerate(v3):
        chars = []
        cur = leaf
        while cur > 0:
            parent = v2[cur]
            ch = cur - v1[parent]
            if ch != 0:
                chars.append(ch)
            cur = parent
        names.append(bytes(reversed(chars)).decode("utf-8"))
    return names, pos

tags_seen = set()

def walk_val(b, pos, names, strs, coffs, clens):
    t = b[pos]; pos += 1
    tags_seen.add(t)
    if t == 0x01:
        return None, pos
    elif t == 0x02:
        return True, pos   # Wait verify True vs False!
    elif t == 0x03:
        return False, pos
    elif t == 0x04:
        return 0, pos
    elif 0x05 <= t <= 0x0c:
        w = t - 0x04
        return read_int_var(b, pos, w)
    elif 0x0d <= t <= 0x10:
        w = t - 0x0c
        return read_uint_var(b, pos, w)
    elif 0x15 <= t <= 0x18:
        w = t - 0x14
        idx, pos = read_uint_var(b, pos, w)
        return ("STR", idx, strs[idx]), pos
    elif 0x19 <= t <= 0x1c:
        w = t - 0x18
        idx, pos = read_uint_var(b, pos, w)
        return ("RES", idx), pos
    elif t == 0x1d:
        return 0.0, pos
    elif t == 0x1e:
        return struct.unpack_from("<f", b, pos)[0], pos + 4
    elif t == 0x1f:
        return struct.unpack_from("<d", b, pos)[0], pos + 8
    elif t == 0x20:
        offs, p = read_int_array(b, pos)
        out = []
        for o in offs:
            v, _ = walk_val(b, p + o, names, strs, coffs, clens)
            out.append(v)
        return out, p # Note end pos of whole list is max end, caller only needs sub-element start
    elif t == 0x21:
        keys, p = read_int_array(b, pos)
        offs, p = read_int_array(b, p)
        out = {}
        for ki, o in zip(keys, offs):
            v, _ = walk_val(b, p + o, names, strs, coffs, clens)
            out[names[ki]] = v
        return out, p
    else:
        raise ValueError(f"Unknown PSB tag {t:#x} at {pos-1:#x}")

all_files = []
for sub in ("scn", "uipsd"):
    d = os.path.join(BASE, sub)
    for root, _, files in os.walk(d):
        for fn in sorted(files):
            if fn.endswith((".scn", ".pimg")):
                all_files.append(os.path.join(root, fn))

for fp in all_files:
    b = open(fp, "rb").read()
    hdr = struct.unpack_from("<4sHH9I", b, 0)
    _, ver, enc, u3, on, os_, osd, oco, ocl, ocd, oe, cksum = hdr
    assert cksum == (zlib.adler32(b[8:0x28], 1) & 0xFFFFFFFF), (fp, hex(cksum))
    names, np_ = decode_names_list(b, on)
    assert np_ == oe, (fp, np_, oe)
    soffs, _ = read_int_array(b, os_)
    strs = [b[osd+o:b.find(b"\x00", osd+o)].decode("utf-8") for o in soffs]
    coffs, _ = read_int_array(b, oco)
    clens, _ = read_int_array(b, ocl)
    root_val, _ = walk_val(b, oe, names, strs, coffs, clens)
    if os.path.basename(fp) == "conf_lang.pimg":
        print("conf_lang names:", names)
        print("conf_lang root:", root_val)
    elif os.path.basename(fp) == "b04.txt.scn":
        print("b04 root keys:", list(root_val.keys()), "scenes:", len(root_val["scenes"]))
        print("b04 scene[0] keys:", list(root_val["scenes"][0].keys()))

print(f"ALL {len(all_files)} PSB files parsed cleanly! Tags seen: {[hex(t) for t in sorted(tags_seen)]}")
