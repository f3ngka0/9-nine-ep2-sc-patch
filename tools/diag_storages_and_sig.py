import os
import re
import struct
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as d

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def dump_all_objs(xp3_file, entry_name):
    p = os.path.join(GAME_DIR, xp3_file)
    de = xp3.parse_xp3_entries(p)
    if entry_name not in de:
        print(f"MISSING {xp3_file}::{entry_name}")
        return
    raw, adlr = xp3.read_entry(p, de[entry_name])
    print(f"\n================ {xp3_file}::{entry_name} (len={len(raw)}, adlr={hex(adlr)}) ================")
    if raw[:8] == b"TJS2100\x00":
        dec = raw
    elif raw[:5] == b"\xfe\xfe\x01\xff\xfe" or raw[:5] == b"\xfe\xfe\x02\xff\xfe":
        print("TEXT/OBF:", xp3.decode_txtobf(raw))
        return
    else:
        # check if UTF-16 text
        dec = d.decrypt_tjs2(raw)
        if dec[:8] != b"TJS2100\x00":
            print("NOT TJS2100, head:", raw[:32].hex(), "dec head:", dec[:32].hex())
            return
    objs = d.parse_tjs2_objs(dec)
    for idx, name, code, consts in objs:
        print(f"--- OBJ[{idx}] {name} (code={len(code)}, consts={len(consts)}) ---")
        print(d.disasm_tjs2(code, consts, 0, len(code)))


def search_bin_strings(path, patterns):
    with open(path, "rb") as f:
        data = f.read()
    print(f"\n=== Binary scan: {os.path.basename(path)} ({len(data)} bytes) ===")
    for pat in patterns:
        # ascii
        hits_a = [m.start() for m in re.finditer(pat.encode("ascii"), data, re.I)]
        hits_u = [m.start() for m in re.finditer(pat.encode("utf-16-le"), data, re.I)]
        samples = []
        for off in hits_a[:4]:
            s = data[max(0, off-24):off+48]
            samples.append("A:" + repr(s))
        for off in hits_u[:4]:
            s = data[max(0, off-24):off+64]
            try:
                samples.append("U:" + repr(s.decode("utf-16-le", errors="ignore")))
            except Exception:
                pass
        if hits_a or hits_u:
            print(f"  '{pat}': ascii={len(hits_a)}, utf16={len(hits_u)} -> {samples[:4]}")


def main():
    # 1. Initialize.tjs helper functions
    p = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(p)
    raw, _ = xp3.read_entry(p, de["system/Initialize.tjs"])
    objs = d.parse_tjs2_objs(d.decrypt_tjs2(raw))
    print("=== Initialize.tjs OBJ[6..12] ===")
    for idx in range(6, 13):
        _, name, code, consts = objs[idx]
        print(f"--- OBJ[{idx}] {name} ---")
        print(d.disasm_tjs2(code, consts, 0, len(code)))

    # 2. Storages.tjs, AfterInit, Override, steam
    for xp3n, en in [
        ("data.xp3", "main/Storages.tjs"),
        ("data.xp3", "sysscn/Override.tjs"),
        ("data.xp3", "sysscn/AfterInit.tjs"),
        ("steam.xp3", "steam.tjs"),
        ("steam.xp3", "steam_r18hack.tjs"),
    ]:
        dump_all_objs(xp3n, en)

    # 3. plugin/ listing
    pdir = os.path.join(GAME_DIR, "plugin")
    print("\n=== plugin/ directory ===")
    if os.path.isdir(pdir):
        for fn in sorted(os.listdir(pdir)):
            print(f"  {fn:35s} {os.path.getsize(os.path.join(pdir, fn))}")

    # 4. .sig files content & scan exe / plugin dlls
    print("\n=== .sig files sample ===")
    for sfn in ("data.xp3.sig", "steam.xp3.sig", "nine_sorairo.exe.sig"):
        sp = os.path.join(GAME_DIR, sfn)
        with open(sp, "rb") as f:
            sb = f.read()
        print(f"  {sfn} ({len(sb)}B): {sb[:80]!r}")

    pats = [r"\.sig", r"SIGNATURE", r"patch", r"patch2", r"\.xp3", r"Override", r"AutoPath", r"RSA", r"SHA256", r"Verify"]
    search_bin_strings(os.path.join(GAME_DIR, "nine_sorairo.exe"), pats)
    if os.path.isdir(pdir):
        for fn in sorted(os.listdir(pdir)):
            if fn.lower().endswith((".dll", ".tpm")):
                search_bin_strings(os.path.join(pdir, fn), pats)


if __name__ == "__main__":
    main()
