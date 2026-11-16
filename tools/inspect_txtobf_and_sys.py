import inspect
import os
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as dt
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
entries = xp3.parse_xp3_entries(DATA_XP3)

print("=== xp3.decode_txtobf source ===")
print(inspect.getsource(xp3.decode_txtobf))
print("=== xp3.encode_txtobf source ===")
print(inspect.getsource(xp3.encode_txtobf))

# Check raw bytes around `"face"=`"` in font/embfontlist.tjs and `#` / `t` glitches in main/syslangtext_cn.ini
for target, needle in [
    ("font/embfontlist.tjs", "Source Han Sans TC"),
    ("main/syslangtext_cn.ini", "Windowsダイアログ"),
    ("main/syslangtext_cn.ini", "tsdata_DictEnabled"),
]:
    raw, adlr = xp3.read_entry(DATA_XP3, entries[target])
    dec = xp3.decode_txtobf(raw)
    idx = dec.find(needle)
    print(f"\n--- {target} around {needle!r} (idx={idx}) ---")
    print("  decoded slice:", repr(dec[max(0, idx-80):idx+60]))
    # Also inspect raw UTF-16 bytes in raw around that offset (byte offset ~ 2 + idx*2 or inspect header)
    print("  raw[:24]:", raw[:24].hex())
    # Note txtobf byte mapping around position!
    b_start = max(0, (idx - 40) * 2)
    b_end = min(len(raw), (idx + 30) * 2)
    print(f"  raw[{b_start}:{b_end}]:", raw[b_start:b_end].hex())

print("\n=== system/ & sysscn/ key scripts ===")
# Search for addArchive, setupSubFolders in system/ files
sys_targets = [
    k for k in sorted(entries)
    if k.startswith(("system/", "sysscn/", "main/")) and k.endswith(".tjs")
]
out = []
for k in sys_targets:
    raw, _ = xp3.read_entry(DATA_XP3, entries[k])
    txt = xp3.decode_txtobf(raw)
    if txt is not None:
        if any(w in txt for w in ("addArchive", "setupSubFolders", "LoadSysLangText", "UpdateMultiLangTitleCaption", "embfontlist", "addFont")):
            out.append(f"\n===== TXT {k} (len={len(txt)}) =====\n{txt}")
    else:
        dec = safe_decrypt_tjs2(raw)
        if dec[:4] == b"TJS2":
            objs = dt.parse_tjs2_objs(dec)
            interesting = False
            for idx, oname, code, consts in objs:
                for c in consts:
                    if isinstance(c, str) and any(w in c for w in ("addArchive", "setupSubFolders", "LoadSysLangText", "UpdateMultiLangTitleCaption", "embfontlist", "addFont", "multiLang", "syslangtext", "uipsd")):
                        interesting = True
                        break
            if interesting or k in ("sysscn/syslangtext.tjs", "sysscn/multilang.tjs", "sysscn/embFontLoader.tjs"):
                out.append(f"\n===== TJS2 {k} (objs={len(objs)}) =====")
                for idx, oname, code, consts in objs:
                    cstr = repr(consts)
                    if k in ("sysscn/syslangtext.tjs", "sysscn/embFontLoader.tjs") or any(w in cstr for w in ("addArchive", "setupSubFolders", "LoadSysLangText", "UpdateMultiLangTitleCaption", "embfontlist", "addFont", "multiLang", "syslangtext", "TitleCaption", "FontFace", "uipsd", "envscript", "AfterInit")):
                        out.append(f"  -- OBJ[{idx}] {oname} code_len={len(code)} consts={consts!r} --")
                        dis = dt.disasm_tjs2(code, consts)
                        if isinstance(dis, str):
                            out.append(dis)
                        else:
                            out.extend(dis)

with open(r"d:\code\translate\tools\sys_lang_disasm_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("Wrote tools/sys_lang_disasm_out.txt bytes:", os.path.getsize(r"d:\code\translate\tools\sys_lang_disasm_out.txt"))
