import os
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as d

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def read_text_or_tjs2(xp3_path, de, name):
    raw, adlr = xp3.read_entry(xp3_path, de[name])
    dec = xp3.decode_txtobf(raw)
    if dec is not None:
        return "TXT", dec
    tdec = d.decrypt_tjs2(raw)
    if tdec[:8] == b"TJS2100\x00":
        return "TJS2", tdec
    return "BIN", raw


def main():
    p = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(p)

    # Check txtobf roundtrip
    enc = xp3.encode_txtobf('System.inform("OK");\r\n')
    print("encode_txtobf head:", enc[:30].hex(), "decode back:", repr(xp3.decode_txtobf(enc)))

    # Print append_init.tjs and Config.tjs, first.ks
    for k in ("main/append_init.tjs", "sysscn/Config.tjs", "sysscn/first.ks", "main/ConfigEx.tjs", "main/syslangtext_cn.ini", "main/syslangtext_en.ini"):
        if k not in de:
            print(f"MISSING {k}")
            continue
        kind, val = read_text_or_tjs2(p, de, k)
        print(f"\n=== {k} ({kind}) ===")
        if kind == "TXT":
            print(val[:2500])
        elif kind == "TJS2":
            objs = d.parse_tjs2_objs(val)
            print("OBJs:", [o[1] for o in objs[:20]])
            print("OBJ[0]:\n" + d.disasm_tjs2(objs[0][2], objs[0][3], 0, min(300, len(objs[0][2]))))
        else:
            print("RAW head:", val[:64].hex())

    # Search all .tjs/.ks in data.xp3 for pkutil, checkSignature, patch, syslangtext, TitleCaption
    kws = ["pkutil", "Signature", "signature", ".sig", "syslangtext", "TitleCaption", "MultiLang", "Override", "ConfigEx"]
    print("\n=== Keyword search across data.xp3 scripts ===")
    for name in sorted(de):
        if not name.lower().endswith((".tjs", ".ks", ".ini")):
            continue
        kind, val = read_text_or_tjs2(p, de, name)
        if kind == "TXT":
            hits = [kw for kw in kws if kw.lower() in val.lower()]
            if hits:
                print(f"  {name} (TXT): {hits}")
        elif kind == "TJS2":
            # scan utf-16le strings in TJS2 bytecode
            hits = [kw for kw in kws if kw.encode("utf-16-le") in val or kw.lower().encode("utf-16-le") in val.lower()]
            if hits:
                print(f"  {name} (TJS2): {hits}")


if __name__ == "__main__":
    main()
