import os, struct

BASE = r"d:\code\translate\build\extracted\data"
b = open(os.path.join(BASE, "uipsd/conf_lang.pimg"), "rb").read()
on = struct.unpack_from("<I", b, 12)[0]

def read_int_array(b, pos):
    t = b[pos]; pos += 1
    cnt = int.from_bytes(b[pos:pos+(t-0x0c)], "little"); pos += t - 0x0c
    t2 = b[pos]; pos += 1
    ew = t2 - 0x0c
    return [int.from_bytes(b[pos+i*ew:pos+(i+1)*ew], "little") for i in range(cnt)], pos + cnt * ew

v1, p = read_int_array(b, on)
v2, p = read_int_array(b, p)
v3, p = read_int_array(b, p)
print("v1:", v1)
print("v2:", v2)
print("v3:", v3)
