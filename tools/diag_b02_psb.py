import os
import struct
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def read_int_array(buf: bytes, pos: int):
    # PSB array of unsigned ints: header byte 0x0d..0x10 (type = 0x0c + elem_bytes? or 0x0d..0x10?)
    t = buf[pos]
    # 0x0d: 1 byte count? In PSB: t = 0x0c + size_of_count (1..4) -> count, then 0x0c + size_of_elem -> elems
    # Wait let's check hex first!
    return t


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    raw, adlr = xp3.read_entry(data_xp3, de["scn/b02.txt.scn"])
    k1, k2, sp = 0xF1, 0x4B, 0x79E
    dec = bytes(b ^ k1 for b in raw[:sp]) + bytes(b ^ k2 for b in raw[sp:])
    hdr = struct.unpack_from("<4sHH10I", dec, 0)
    print("b02 hdr (<4sHH10I):", hdr)
    # Print chunks at offsets in hdr
    for label, off in zip(["o1(8)", "o2(12)", "o3(16)", "o4(20)", "o5(24)", "o6(28)", "o7(32)", "o8(36)", "o9(40)"], hdr[3:]):
        if 0 <= off < len(dec):
            print(f"  {label}={off}: hex={dec[off:off+24].hex()}")
        else:
            print(f"  {label}={off}: OOB (len={len(dec)})")
    # Also test finding k2 cleanly without hardcoding: score XOR keys on dec[5000:15000] (which is text/str_data!)
    # Wait: where is str_data in b02? Print dec[hdr[9]:hdr[9]+120] and dec[hdr[9]-120:hdr[9]]!
    print("around off=2319:", repr(dec[2300:2450]))
    print("around off=44:", dec[40:100].hex())
    print("around off=sp(0x79e):", dec[0x790:0x7c0].hex())
    print("around off=1479934:", dec[1479930:1479970].hex())


if __name__ == "__main__":
    main()
