import os
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as dt
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
entries = xp3.parse_xp3_entries(DATA_XP3)

out = []

# 1. Initialize.tjs OBJ[9..12]
raw, _ = xp3.read_entry(DATA_XP3, entries["system/Initialize.tjs"])
objs = dt.parse_tjs2_objs(safe_decrypt_tjs2(raw))
for idx in (8, 9, 10, 11, 12):
    _, oname, code, consts = objs[idx]
    out.append(f"=== Initialize.tjs OBJ[{idx}] {oname} consts={consts} ===")
    out.append(dt.disasm_tjs2(code, consts))

# 2. sysscn/syslangtext.tjs ALL objs
raw, _ = xp3.read_entry(DATA_XP3, entries["sysscn/syslangtext.tjs"])
objs = dt.parse_tjs2_objs(safe_decrypt_tjs2(raw))
out.append(f"\n=== sysscn/syslangtext.tjs (objs={len(objs)}) ===")
for idx, oname, code, consts in objs:
    out.append(f"  -- OBJ[{idx}] {oname} consts={consts} --")
    out.append(dt.disasm_tjs2(code, consts))

# 3. sysscn/multilang.tjs OBJ[0] + key functions
raw, _ = xp3.read_entry(DATA_XP3, entries["sysscn/multilang.tjs"])
dec_ml = safe_decrypt_tjs2(raw)
objs = dt.parse_tjs2_objs(dec_ml)
out.append(f"\n=== sysscn/multilang.tjs (objs={len(objs)}) ===")
# List all objs first
for idx, oname, code, consts in objs:
    out.append(f"  OBJ[{idx:3d}] {oname:30s} code={len(code):4d} consts={consts[:12]}")

target_kws = ("LoadSysLangText", "TitleCaption", "GetSystemLang", "onSystemLangChanged", "onKAGSetupMenu", "LanguageFont", "syslangtext", "embfont", "uipsd", "CurrentLanguage")
for idx, oname, code, consts in objs:
    cs = repr(consts)
    if idx == 0 or any(kw in cs or kw in oname for kw in target_kws):
        out.append(f"\n  -- multilang OBJ[{idx}] {oname} consts={consts} --")
        try:
            out.append(dt.disasm_tjs2(code, consts))
        except Exception as e:
            out.append(f"  [disasm err: {e}]")

with open(r"d:\code\translate\tools\init_and_multilang_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Wrote tools/init_and_multilang_out.txt lines:", sum(x.count("\n") + 1 for x in out))

# 4. Check all 88 scn & uipsd PSB/MDF headers
psb_ok, psb_anoms = 0, []
for k in sorted(entries):
    if not k.endswith((".scn", ".pimg")):
        continue
    r, adlr = xp3.read_entry(DATA_XP3, entries[k])
    votes = Counter(r[i] ^ b"PSB\x00\x03\x00\x00\x00"[i] for i in range(8))
    k1, cnt = votes.most_common(1)[0]
    if cnt == 8:
        psb_ok += 1
    else:
        diffs = [i for i in range(8) if (r[i] ^ k1) != b"PSB\x00\x03\x00\x00\x00"[i]]
        psb_anoms.append((k, f"cnt={cnt}", diffs, hex(adlr)))
print(f"PSB v3 header check: 8/8 exact={psb_ok}, partial/other={len(psb_anoms)}: {psb_anoms[:15]}")
