import os
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def decrypt_utf16_cxdec(raw: bytes):
    k1 = raw[0] ^ 0xFF
    assert (raw[1] ^ k1) == 0xFE, (hex(raw[0] ^ k1), hex(raw[1] ^ k1))
    dec1 = bytes(b ^ k1 for b in raw)
    if len(raw) <= 0x750:
        return dec1.decode("utf-16"), k1, k1, len(raw)
    tail = raw[0xA00:] if len(raw) > 0xA00 else raw[0x880:]
    k2 = Counter(tail[1::2]).most_common(1)[0][0]
    dec2 = bytes(b ^ k2 for b in raw)
    n = min(len(raw), 0xA00)
    best_sp, best_sc = n, -1
    for sp in range(0x750, n):
        sc = sum(1 for i in range(0x751, sp, 2) if (raw[i] ^ k1) == 0) + sum(1 for i in range(sp | 1, n, 2) if (raw[i] ^ k2) == 0)
        if sc > best_sc:
            best_sc = sc
            best_sp = sp
    dec = dec1[:best_sp] + dec2[best_sp:]
    return dec.decode("utf-16", errors="replace"), k1, k2, best_sp


def main():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)

    for name in ("main/Config.tjs", "main/ConfigEx.tjs", "AppConfig.tjs", "system/Initialize.tjs"):
        raw, _ = xp3.read_entry(data_xp3, de[name])
        txt = xp3.decode_txtobf(raw)
        if txt is None and name == "main/Config.tjs":
            # decrypt TJS or check
            txt, k1, k2, sp = decrypt_utf16_cxdec(raw)
            print(f"=== {name} (decrypted k1={hex(k1)} k2={hex(k2)} sp={hex(sp)}) ===")
        elif txt is not None:
            print(f"=== {name} (txtobf) ===")
        else:
            print(f"=== {name} (binary {len(raw)} bytes, head={raw[:16].hex()}) ===")
            continue
        for idx, line in enumerate(txt.splitlines(), 1):
            low = line.lower()
            if any(w in low for w in ("title", "caption", "multilang", "lang", "font", "patch", "gamename", "gameid", "storages")):
                print(f"  L{idx:4d}: {line}")


if __name__ == "__main__":
    main()
