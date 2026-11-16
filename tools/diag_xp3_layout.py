import os
import struct
import zlib
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def read_xp3_raw_index(path):
    with open(path, "rb") as f:
        data = f.read()
    print(f"\n=== {os.path.basename(path)} size={len(data)} ===")
    print("  head[0:48]:", data[:48].hex())
    # Check where XP3 index starts according to XP3 spec (krkr2 minor_version==1 -> continue flag 0x80 at offset 23)
    off = struct.unpack_from("<Q", data, 11)[0]
    pos = off
    for step in range(4):
        fl = data[pos]
        print(f"  step {step} @ {pos} ({hex(pos)}): flag={hex(fl)} next32={data[pos:pos+32].hex()}")
        if fl & 0x80:
            # 1B flag + 8B real_offset
            pos = struct.unpack_from("<Q", data, pos + 1)[0]
            continue
        elif fl == 1:
            csz, usz = struct.unpack_from("<QQ", data, pos + 1)
            print(f"  zlib index @ {pos}: csz={csz} usz={usz}")
            idx = zlib.decompress(data[pos + 17: pos + 17 + csz])
            return idx
        elif fl == 0:
            usz = struct.unpack_from("<Q", data, pos + 1)[0]
            print(f"  raw index @ {pos}: usz={usz}")
            idx = data[pos + 9: pos + 9 + usz]
            return idx
        else:
            break
    # Fallback: check 23 -> maybe minor=1 has 8B size then flag?
    # Look at data[19:23] == 1 (minor_version=1), data[23]==0x80 (continue), data[24:32]==idx_size (0), data[32:40]==idx_off??
    # Check steam.xp3 header[24:40]!
    return b""


def dump_chunks(idx, max_n=10):
    p = 0
    i = 0
    while p < len(idx) and i < max_n:
        tag = idx[p:p+4]
        sz = struct.unpack_from("<Q", idx, p + 4)[0]
        body = idx[p+12:p+12+sz]
        p += 12 + sz
        print(f"  [{i}] tag={tag!r} sz={sz} hex={body[:48].hex()}")
        if tag == b"File":
            q = 0
            while q < len(body):
                st = body[q:q+4]
                ssz = struct.unpack_from("<Q", body, q+4)[0]
                sb = body[q+12:q+12+ssz]
                q += 12 + ssz
                print(f"      sub {st!r} ssz={ssz} hex={sb[:48].hex()}")
        i += 1


def main():
    sp = os.path.join(GAME_DIR, "steam.xp3")
    with open(sp, "rb") as f:
        sdata = f.read()
    print("steam.xp3 head[0:64]:", sdata[:64].hex())
    print("steam.xp3 tail[-256:]:", sdata[-256:].hex())
    # Find 0x78 0x9c or 0x78 0xda near tail
    for zsig in (b"\x78\x9c", b"\x78\xda", b"\x78\x01"):
        for idx_z in range(len(sdata) - 2000, len(sdata)):
            if idx_z > 0 and sdata[idx_z:idx_z+2] == zsig:
                try:
                    out = zlib.decompress(sdata[idx_z:])
                    print(f"zlib stream @ {idx_z} (prev9={sdata[idx_z-17:idx_z].hex()}) -> decomp={len(out)}")
                    dump_chunks(out, 12)
                    break
                except Exception:
                    pass

    test_xp3 = r"d:\code\translate\build\diag_sample.xp3"
    os.makedirs(os.path.dirname(test_xp3), exist_ok=True)
    xp3.pack_xp3(test_xp3, {"test.txt": b"hello", "main/a.ini": b"abc"}, compress=True)
    idx2 = read_xp3_raw_index(test_xp3)
    if idx2:
        dump_chunks(idx2, 12)
    os.remove(test_xp3)


if __name__ == "__main__":
    main()
