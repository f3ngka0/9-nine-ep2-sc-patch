import os
import re
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def dump_exe_strings():
    exe = os.path.join(GAME_DIR, "nine_sorairo.exe")
    with open(exe, "rb") as f:
        data = f.read()

    # Extract UTF-16LE strings >= 4 chars
    u16 = re.findall(rb"(?:[\x20-\x7e]\x00){4,}", data)
    strs = [s.decode("utf-16-le") for s in u16]
    kws = [".sig", "signature", "rsa", "sha", "verify", "xp3", "patch", "data", "cf", "override", "datapath", "userconf", "wait", "steam", "startup", "archive", "public", "key"]
    print("=== UTF-16 strings in nine_sorairo.exe matching keywords ===")
    seen = set()
    for s in strs:
        sl = s.lower()
        if any(k in sl for k in kws):
            if s not in seen:
                seen.add(s)
                print("  U16:", repr(s))

    # Extract ASCII strings around Signature / .sig / pkutil / xp3 / BEGIN PUBLIC
    a8 = re.findall(rb"[\x20-\x7e]{6,}", data)
    print("\n=== ASCII strings in nine_sorairo.exe matching sig/rsa/xp3/patch/crypt/cf ===")
    kws_a = [".sig", "signature", "public key", "xp3", "patch", "crypt", "rsa", "pss", "sha256", "steam", "pkutil", "verify"]
    seen_a = set()
    for b in a8:
        s = b.decode("ascii")
        sl = s.lower()
        if any(k in sl for k in kws_a):
            if s not in seen_a and not s.startswith((".?A", "?$", "??")):
                seen_a.add(s)
                print("  A8 :", repr(s))


def list_entries():
    de = xp3.parse_xp3_entries(os.path.join(GAME_DIR, "data.xp3"))
    print("\n=== Config/Append/Override/First/Syslang entries in data.xp3 ===")
    for k in sorted(de):
        kl = k.lower()
        if any(x in kl for x in ("append", "config", "override", "first", "syslang", "storages", "afterinit", "startup", "custom", "default")):
            print(f"  {k:40s} flags={hex(de[k][0]['flags'])} adlr={hex(de[k][2])}")


if __name__ == "__main__":
    dump_exe_strings()
    list_entries()
