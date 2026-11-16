import os
import sys
sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as d

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"

def dump_tjs(name, xp3_name="data.xp3"):
    p = os.path.join(GAME_DIR, xp3_name)
    entries = xp3.parse_xp3_entries(p)
    if name not in entries:
        print(f"MISSING {name} in {xp3_name}")
        return
    raw, adlr = xp3.read_entry(p, entries[name])
    print(f"=== {xp3_name}::{name} len={len(raw)} adlr={hex(adlr)} head={raw[:16].hex()} ===")
    if raw[:8] == b"TJS2100\x00":
        dec = raw
    else:
        dec = d.decrypt_tjs2(raw)
    objs = d.parse_tjs2_objs(dec)
    for idx, oname, code, consts in objs:
        print(f"--- OBJ[{idx}] {oname} (code={len(code)}, consts={len(consts)}) ---")
        if name == "system/Initialize.tjs" and idx == 0:
            print(d.disasm_tjs2(code, consts, 0, len(code)))
        elif name != "system/Initialize.tjs":
            print(d.disasm_tjs2(code, consts, 0, min(len(code), 350)))

def main():
    print("=== GAME_DIR files ===")
    for f in sorted(os.listdir(GAME_DIR)):
        fp = os.path.join(GAME_DIR, f)
        sz = os.path.getsize(fp) if os.path.isfile(fp) else -1
        print(f"  {f:30s} {sz}")

    cf = os.path.join(GAME_DIR, "nine_sorairo.cf")
    if os.path.exists(cf):
        print("\n=== nine_sorairo.cf ===")
        with open(cf, "rb") as f:
            b = f.read()
        print(b.decode("utf-16", errors="replace") if b[:2] in (b"\xff\xfe", b"\xfe\xff") else b.decode("utf-8", errors="replace"))

    dump_tjs("startup.tjs")
    dump_tjs("startup.tjs#1")
    dump_tjs("system/Initialize.tjs")

if __name__ == "__main__":
    main()
