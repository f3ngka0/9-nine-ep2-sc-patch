import os
import re
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as d
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def main():
    # 1. Verify xp3.pack_xp3 roundtrip
    tmp = r"d:\code\translate\build\verify_pack.xp3"
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    xp3.pack_xp3(tmp, {"AppConfig.tjs": b"\xff\xfeA\x00", "main/a.ini": b"123"}, compress=False)
    e1 = xp3.parse_xp3_entries(tmp)
    print("pack_xp3(compress=False) entries:", list(e1.keys()), {k: xp3.read_entry(tmp, v) for k, v in e1.items()})
    xp3.pack_xp3(tmp, {"AppConfig.tjs": b"\xff\xfeA\x00", "main/a.ini": b"123"}, compress=True)
    e2 = xp3.parse_xp3_entries(tmp)
    print("pack_xp3(compress=True)  entries:", list(e2.keys()), {k: xp3.read_entry(tmp, v) for k, v in e2.items()})
    os.remove(tmp)

    # 2. Search ALL scripts in data.xp3 and steam.xp3 for '.dll' or 'link' or 'autoPath' or 'xp3'
    print("\n=== DLL links and XP3 references in data.xp3 + steam.xp3 ===")
    for arc in ("data.xp3", "steam.xp3"):
        p = os.path.join(GAME_DIR, arc)
        de = xp3.parse_xp3_entries(p)
        for name in sorted(de):
            if not name.lower().endswith((".tjs", ".ks")):
                continue
            raw, _ = xp3.read_entry(p, de[name])
            dec = xp3.decode_txtobf(raw)
            if dec is not None:
                hits = re.findall(r"[^\r\n]{0,40}(?:\.dll|\.xp3|addAutoPath|Override|AfterInit|custom\.tjs|custom\.ks)[^\r\n]{0,40}", dec, re.I)
                if hits:
                    print(f"  {arc}::{name} (TXT): {hits[:8]}")
            else:
                tdec = safe_decrypt_tjs2(raw)
                u16 = re.findall(rb"(?:[\x20-\x7e]\x00){3,}", tdec)
                strs = [s.decode("utf-16-le") for s in u16]
                shits = [s for s in strs if any(k in s.lower() for k in (".dll", ".xp3", "autopath", "override", "afterinit", "custom.", "syslang", "pkutil"))]
                if shits:
                    print(f"  {arc}::{name} (TJS2): {shits[:12]}")

    # 3. Check custom.tjs and version.ks and custom.ks
    p = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(p)
    for k in ("main/custom.tjs", "main/custom.ks", "sysscn/version.ks", "main/macro.ks"):
        if k in de:
            raw, _ = xp3.read_entry(p, de[k])
            txt = xp3.decode_txtobf(raw)
            print(f"\n=== {k} ({'TXT' if txt else 'BIN'}) ===")
            print(txt[:1500] if txt else raw[:64].hex())


if __name__ == "__main__":
    main()
