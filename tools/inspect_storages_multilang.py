import os
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as dt
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")

entries = xp3.parse_xp3_entries(DATA_XP3)
print("Total data.xp3 entries:", len(entries))

targets = {
    "main/storages.tjs",
    "sysscn/multilang.tjs",
    "sysscn/syslangtext.tjs",
    "font/embfontlist.tjs",
    "sysscn/option.tjs",
    "sysscn/myhistorylayer.tjs",
    "main/syslangtext_jp.ini",
    "main/syslangtext_en.ini",
    "main/syslangtext_cn.ini",
}

out = []
for name in sorted(entries):
    nl = name.lower()
    if any(x in nl for x in ("lang", "font", "storage", "proxy", "uipsd", "history", "option", ".scn")):
        out.append(f"ENTRY: {name} adlr={entries[name][2]:#010x}")

for name in sorted(entries):
    if name.lower() in targets:
        raw, adlr = xp3.read_entry(DATA_XP3, entries[name])
        out.append("\n" + "=" * 70)
        out.append(f"FILE: {name} len={len(raw)} magic={raw[:8]!r}")
        txt = xp3.decode_txtobf(raw)
        if txt is not None:
            out.append(txt)
        else:
            dec = safe_decrypt_tjs2(raw)
            if dec[:4] == b"TJS2":
                objs = dt.parse_tjs2_objs(dec)
                for idx, oname, code, consts in objs:
                    out.append(f"  -- OBJ[{idx}] {oname} code_len={len(code)} consts={consts!r} --")
                    try:
                        for line in dt.disasm_tjs2(code, consts):
                            out.append("    " + line)
                    except Exception as e:
                        out.append(f"    [disasm err: {e}]")
            else:
                out.append(f"Cannot decode! dec_magic={dec[:16]!r}")

# Also list steam.xp3 entries
STEAM_XP3 = os.path.join(GAME_DIR, "steam.xp3")
if os.path.exists(STEAM_XP3):
    se = xp3.parse_xp3_entries(STEAM_XP3)
    out.append(f"\n=== steam.xp3 entries ({len(se)}) ===")
    for name in sorted(se):
        out.append(f"  STEAM: {name}")

with open(r"d:\code\translate\tools\storages_multilang_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Wrote tools/storages_multilang_out.txt lines:", len(out))
