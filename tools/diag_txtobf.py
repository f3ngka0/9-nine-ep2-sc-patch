import os
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    for k in ("main/syslangtext_cn.ini", "main/ConfigEx.tjs", "main/Config.tjs", "main/custom.ks"):
        raw, adlr = xp3.read_entry(data_xp3, de[k])
        txt = xp3.decode_txtobf(raw)
        print(f"{k}: len={len(raw)} adlr={hex(adlr)} head={raw[:16].hex()} tail={raw[-16:].hex()}")
        if txt:
            enc = xp3.encode_txtobf(txt)
            # Check cxdec differences cleanly
            diffs = [i for i in range(min(len(raw), len(enc))) if raw[i] != enc[i]]
            print(f"  txt_len={len(txt)} enc_len={len(enc)} diffs_count={len(diffs)} first_diffs={diffs[:10]}")
            for idx, l in enumerate(txt.splitlines()):
                if any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in l):
                    print(f"  HANGUL-like anom at line {idx+1}: {l!r}")

    # Also read ConfigEx.tjs in full
    r_ce, _ = xp3.read_entry(data_xp3, de["main/ConfigEx.tjs"])
    print("\n=== main/ConfigEx.tjs FULL ===")
    print(xp3.decode_txtobf(r_ce))


if __name__ == "__main__":
    main()
