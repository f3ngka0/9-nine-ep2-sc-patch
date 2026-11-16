import json, pathlib

corpus = pathlib.Path(r"d:\code\translate\work\scn_corpus")
tr_dir = pathlib.Path(r"d:\code\translate\work\scn_translated")

for p in sorted(corpus.glob("*.json")):
    if p.name.startswith("_"): continue
    c_obj = json.loads(p.read_text(encoding="utf-8"))
    t_obj = json.loads((tr_dir / p.name).read_text(encoding="utf-8"))
    for sc in c_obj["scenes"]:
        for it in sc["texts"]:
            jp = it["jp"][1] if it["jp"] else ""
            if "モック" in jp:
                k = f"{sc['scene_idx']}:{it['i']}"
                print(f"{p.name} {k}:\n  JP: {jp}\n  EN: {it['en'][1]}\n  TR: {t_obj['items'][k]}")
