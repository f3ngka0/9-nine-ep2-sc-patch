import os
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as d

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def safe_decrypt_tjs2(raw: bytes):
    if raw[:8] == b"TJS2100\x00":
        return raw
    k1 = Counter(raw[i] ^ b"TJS2100\x00"[i] for i in range(min(8, len(raw)))).most_common(1)[0][0]
    dec1 = bytes(b ^ k1 for b in raw)
    if len(raw) <= 0x750:
        return dec1
    tail = raw[0xA00:] if len(raw) > 0xA00 else raw[0x880:]
    if not tail:
        return dec1
    k2 = Counter(tail).most_common(1)[0][0]
    dec2 = bytes(b ^ k2 for b in raw)
    n = min(len(raw), 0xA00)
    s1 = [1 if ((raw[i] ^ k1) == 0) else 0 for i in range(n)]
    s2 = [1 if ((raw[i] ^ k2) == 0) else 0 for i in range(n)]
    p1 = [0]
    for x in s1:
        p1.append(p1[-1] + x)
    best_sp, best_sc, suf = n, -1, 0
    for sp_c in range(n - 1, 0x750 - 1, -1):
        suf += s2[sp_c]
        if p1[sp_c] + suf > best_sc:
            best_sc = p1[sp_c] + suf
            best_sp = sp_c
    return dec1[:best_sp] + dec2[best_sp:]


def main():
    p = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(p)

    print("=== Boot/Append/Config entries in data.xp3 ===")
    for k in sorted(de):
        kl = k.lower()
        if any(x in kl for x in ("append", "config", "override", "first", "syslang", "storages", "afterinit", "startup", "custom", "default")):
            print(f"  {k:40s} adlr={hex(de[k][2])}")

    print("\n=== Search all scripts in data.xp3 & steam.xp3 for pkutil / sig / verify / patch ===")
    kws = ["pkutil", ".sig", "signature", "verify", "checksig", "rsa", "override", "patch"]
    for xp3n in ("data.xp3", "steam.xp3"):
        xp = os.path.join(GAME_DIR, xp3n)
        entries = xp3.parse_xp3_entries(xp)
        for name in sorted(entries):
            if not name.lower().endswith((".tjs", ".ks", ".ini")):
                continue
            raw, _ = xp3.read_entry(xp, entries[name])
            dec = xp3.decode_txtobf(raw)
            if dec is not None:
                hits = [kw for kw in kws if kw in dec.lower()]
                if hits:
                    print(f"  {xp3n}::{name} (TXT): {hits}")
            else:
                tdec = safe_decrypt_tjs2(raw)
                hits = [kw for kw in kws if kw.encode("utf-16-le") in tdec or kw.lower().encode("utf-16-le") in tdec.lower()]
                if hits:
                    print(f"  {xp3n}::{name} (TJS2): {hits}")

    # Check if pkutil appears in append_init.tjs or Config.tjs
    for target in ("sysscn/append_init.tjs", "sysscn/Config.tjs", "main/Config.tjs", "AppConfig.tjs", "sysscn/Override.tjs"):
        if target in de:
            raw, _ = xp3.read_entry(p, de[target])
            dec = xp3.decode_txtobf(raw)
            print(f"\n=== {target} ({'TXT' if dec is not None else 'TJS2'}) ===")
            if dec is not None:
                print(dec[:2000])
            else:
                tdec = safe_decrypt_tjs2(raw)
                objs = d.parse_tjs2_objs(tdec)
                print("  OBJs:", [(i, o[1]) for i, o in enumerate(objs[:30])])
                if target == "sysscn/append_init.tjs":
                    for i, o in enumerate(objs):
                        print(f"--- append_init OBJ[{i}] {o[1]} ---")
                        print(d.disasm_tjs2(o[2], o[3], 0, len(o[2])))


if __name__ == "__main__":
    main()
