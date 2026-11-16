import os
import re
import struct
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as dt
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
entries = xp3.parse_xp3_entries(DATA_XP3)

# 1. Inspect main/syslangtext_cn.ini, _en.ini, _jp.ini anomalies (non-ASCII/unexpected chars in ASCII lines)
for k in ("main/syslangtext_cn.ini", "main/syslangtext_en.ini", "main/syslangtext_jp.ini", "font/embfontlist.tjs"):
    raw, adlr = xp3.read_entry(DATA_XP3, entries[k])
    dec = xp3.decode_txtobf(raw)
    print(f"=== {k} (len={len(raw)}, adlr={adlr:#010x}) ===")
    for ln_no, line in enumerate(dec.splitlines(), 1):
        # Flag any unexpected chars (Hangul, control, replacement, broken ASCII comment)
        weird = [c for c in line if ord(c) > 0xFFFF or (0xAC00 <= ord(c) <= 0xD7AF) or c in "`\x89‰" or (c == '\ufffd')]
        if weird or (line.startswith("####") and not all(ch == "#" for ch in line)) or ("`" in line):
            print(f"  L{ln_no}: {line[:100]!r} (weird={weird})")
    # Also check specifically line with ttsdata_DictEnabled
    for ln_no, line in enumerate(dec.splitlines(), 1):
        if "DictEnabled" in line or 'Source Han Sans TC"' in line:
            print(f"  CHK L{ln_no}: {line!r}")

# 2. Check all system/*.tjs and sysscn/*.tjs for addArchive, setupSubFolders, embFontLoader, multilang, syslangtext
print("\n=== Searching system/ and sysscn/ for archive/searchpath/lang ===")
out = []
for k in sorted(entries):
    if not (k.startswith(("system/", "sysscn/", "k2compat/")) and k.endswith(".tjs")):
        continue
    raw, adlr = xp3.read_entry(DATA_XP3, entries[k])
    txt = xp3.decode_txtobf(raw)
    if txt is not None:
        if any(w in txt for w in ("addArchive", "setupSubFolders", "addAutoPath", "LoadSysLangText", "TitleCaption", "embfontlist")):
            out.append(f"\n===== TXT {k} =====\n{txt}")
        continue
    dec = safe_decrypt_tjs2(raw)
    if dec[:4] != b"TJS2":
        print(f"  {k}: not TJS2 after safe_decrypt (magic={dec[:8]!r})")
        continue
    # Parse TJS2 DATA section safely! Notice dt.parse_tjs2_objs failed on negative/bad code_words due to 1-byte cxdec mismatch
    try:
        objs = dt.parse_tjs2_objs(dec)
    except Exception as e:
        print(f"  {k}: parse_tjs2_objs failed: {e}")
        continue
    hit_objs = []
    for idx, oname, code, consts in objs:
        cs = repr(consts)
        if any(w in cs for w in ("addArchive", "setupSubFolders", "addAutoPath", "LoadSysLangText", "TitleCaption", "UpdateMultiLang", "embfontlist", "addFont", "multiLang", "syslangtext", "uipsd")):
            hit_objs.append((idx, oname, code, consts))
    if hit_objs or k in ("sysscn/syslangtext.tjs", "sysscn/embFontLoader.tjs", "system/StorageData.tjs"):
        out.append(f"\n===== TJS2 {k} (objs={len(objs)}, hits={len(hit_objs)}) adlr={adlr:#010x} len={len(raw)} =====")
        targets_to_dump = objs if k in ("sysscn/syslangtext.tjs", "sysscn/embFontLoader.tjs", "system/StorageData.tjs") else hit_objs
        for idx, oname, code, consts in targets_to_dump:
            out.append(f"  -- OBJ[{idx}] {oname} code_len={len(code)} consts={consts!r} --")
            try:
                out.append(dt.disasm_tjs2(code, consts))
            except Exception as e:
                out.append(f"    [disasm err: {e}]")

with open(r"d:\code\translate\tools\sys_lang_disasm_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Wrote tools/sys_lang_disasm_out.txt lines:", len(out))
