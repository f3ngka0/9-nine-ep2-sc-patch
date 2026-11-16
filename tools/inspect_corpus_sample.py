import json, pathlib

def dump_scene(fname, max_lines=80):
    obj = json.loads((pathlib.Path(r"d:\code\translate\work\scn_corpus") / fname).read_text(encoding="utf-8"))
    for sc in obj["scenes"]:
        print(f"=== {fname} SCENE {sc['scene_idx']} ({len(sc['texts'])} lines) ===")
        for it in sc["texts"][:max_lines]:
            sp = f"{it['t0']}" + (f"({it['cn'][0]})" if it["cn"] and it["cn"][0] else "")
            print(f"#{it['i']:03d} [{sp}]")
            print("  JP:", it["jp"][1] if it["jp"] else "")
            print("  EN:", it["en"][1] if it["en"] else "")
            print("  CN:", it["cn"][1] if it["cn"] else "")

if __name__ == "__main__":
    o = json.loads((pathlib.Path(r"d:\code\translate\work\scn_corpus") / "b02.txt.json").read_text(encoding="utf-8"))
    for sc in o["scenes"]:
        for it in sc["texts"]:
            if sc["scene_idx"] == 2 and 344 <= it["i"] <= 368:
                print(f"b02.s2#{it['i']} [{it['t0']}] JP:{it['jp'][1]} || EN:{it['en'][1]} || CN:{it['cn'][1]}")
            elif sc["scene_idx"] == 0 and 344 <= it["i"] <= 368:
                print(f"b02.s0#{it['i']} [{it['t0']}] JP:{it['jp'][1]} || EN:{it['en'][1]} || CN:{it['cn'][1]}")
