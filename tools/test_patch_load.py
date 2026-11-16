"""Create a minimal test patch.xp3 and verify XP3 roundtrip before live launch."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import xp3

game_dir = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
data_xp3 = os.path.join(game_dir, "data.xp3")
ents = xp3.parse_xp3_entries(data_xp3)

files = {}
for lang in ["jp", "en", "cn"]:
    path = f"main/syslangtext_{lang}.ini"
    r, a = xp3.read_entry(data_xp3, ents[path])
    txt = xp3.decode_txtobf(r)
    # Report any control chars other than \r \n \t
    bad = [(i, hex(ord(c)), 5 + i * 2) for i, c in enumerate(txt) if ord(c) < 32 and c not in "\r\n\t" or (0x7f <= ord(c) <= 0x9f)]
    print(f"{path}: adlr={a:#010x} len={len(r)} bad_ctrl={bad}")
    # Clean replace #... control anomaly if comment bar, and replace TitleCaption for smoke test
    lines = txt.splitlines(keepends=True)
    new_lines = []
    for ln in lines:
        if ln.startswith("TitleCaption\t"):
            new_lines.append("TitleCaption\t\t9-nine-:Episode2 [PATCH_TEST]\r\n")
        elif bad and "#" * 10 in ln and any(ord(c) == 0x89 for c in ln):
            new_lines.append(ln.replace("\x89", "#"))
        else:
            new_lines.append(ln)
    new_txt = "".join(new_lines)
    files[path] = xp3.encode_txtobf(new_txt)

out_xp3 = r"d:\code\translate\build\test_patch.xp3"
xp3.pack_xp3(out_xp3, files)
check_ents = xp3.parse_xp3_entries(out_xp3)
print("Packed test_patch.xp3 entries:", list(check_ents.keys()))
for k, ent in check_ents.items():
    raw_back, _ = xp3.read_entry(out_xp3, ent)
    dec_back = xp3.decode_txtobf(raw_back)
    print("  verified TitleCaption:", [l for l in dec_back.splitlines() if l.startswith("TitleCaption")])
