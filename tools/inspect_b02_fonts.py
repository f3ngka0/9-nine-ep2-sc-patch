"""Inspect scene structure of a cleanly parsed .scn (b02.txt.scn) and check Windows SC fonts."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, r"C:\Users\fengkao\.gemini\antigravity\brain\4c347a84-c7e5-4806-8be9-1f2fe149f530\scratch")
import xp3
import test_psb

game_dir = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
data_xp3 = os.path.join(game_dir, "data.xp3")
ents = xp3.parse_xp3_entries(data_xp3)

# 1. Inspect b02.txt.scn (known clean: k1=0xf1, k2=0x4b, sp=0x79e)
r, a = xp3.read_entry(data_xp3, ents["scn/b02.txt.scn"])
dec = bytes(r[i] ^ (0xF1 if i < 0x79E else 0x4B) for i in range(len(r)))
root, names, strs = test_psb.parse_psb_full(dec)
print("b02 root keys:", list(root.keys()))
print("b02 name:", root.get("name"))
print("b02 outlines count:", len(root.get("outlines", [])))
if root.get("outlines"):
    print("b02 outlines[0]:", root["outlines"][0])
scenes = root.get("scenes", [])
print("b02 scenes count:", len(scenes))
for si, sc in enumerate(scenes):
    if isinstance(sc, dict):
        print(f"  scene[{si}] keys:", sorted(sc.keys()), "title:", sc.get("title"), "texts len:", len(sc.get("texts", [])), "selects len:", len(sc.get("selects", [])))
        if sc.get("texts"):
            for ti in range(min(3, len(sc["texts"]))):
                print(f"    texts[{ti}]:", sc["texts"][ti])
        if sc.get("selects"):
            print("    selects[0]:", sc["selects"][0])
        if sc.get("lines"):
            print("    lines[:2]:", sc["lines"][:2])

# 2. Check Windows Fonts directory for CJK fonts
win_fonts = r"C:\Windows\Fonts"
if os.path.isdir(win_fonts):
    hits = [f for f in sorted(os.listdir(win_fonts)) if any(k in f.lower() for k in ["sourcehan", "noto", "msyh", "simsun", "simhei", "deng", "sarasa", "pingfang"])]
    print("\nWindows Fonts matches:", hits[:40])
