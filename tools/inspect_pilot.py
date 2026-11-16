import json, pathlib, re

tr_dir = pathlib.Path(r"d:\code\translate\work\scn_translated")
src_dir = pathlib.Path(r"d:\code\translate\work\scn_corpus")

for fn in ("b04.txt.json", "b01.txt.json"):
    tr = json.loads((tr_dir / fn).read_text(encoding="utf-8"))
    src = json.loads((src_dir / fn).read_text(encoding="utf-8"))
    print(f"=== {fn} selects={tr['selects']} ===")
    dbl_bs = sum(1 for v in tr["items"].values() if "\\\\n" in v)
    ascii_sp_after_nl = sum(1 for v in tr["items"].values() if "\\n " in v)
    print(f"stats: total={len(tr['items'])} double_backslash_n={dbl_bs} ascii_space_after_n={ascii_sp_after_nl}")
    shown = 0
    for sc in src["scenes"]:
        for it in sc["texts"]:
            k = f"{sc['scene_idx']}:{it['i']}"
            val = tr["items"][k]
            if (sc["scene_idx"] == 0 and it["i"] < 8) or ("%p-1" in it["jp"][1]) or ("%D$" in it["jp"][1] and shown < 18) or it["i"] in (301, 401, 440, 491):
                print(f"  [{k}] ({it['t0']}) repr={val!r}")
                print(f"     JP: {it['jp'][1]}")
                print(f"     TC: {it['cn'][1]}")
                shown += 1
