import json, pathlib, re

d = pathlib.Path(r"d:\code\translate\work\scn_corpus")
files = sorted(p for p in d.glob("*.json") if not p.name.startswith("_"))

terms = [
    "スティグマ", "ヴェーダ", "アンブロシア", "アガスティア", "セフィロト", "ヴァルハラ"
]
counts = {t: {"count": 0, "samples": []} for t in terms}

for p in files:
    obj = json.loads(p.read_text(encoding="utf-8"))
    for sc in obj["scenes"]:
        for it in sc["texts"]:
            jp = it["jp"][1] if it["jp"] else ""
            en = it["en"][1] if it["en"] else ""
            cn = it["cn"][1] if it["cn"] else ""
            sp = it["t0"] or "Narr"
            for t in terms:
                if t in jp:
                    counts[t]["count"] += 1
                    if len(counts[t]["samples"]) < 3:
                        counts[t]["samples"].append((f"{p.stem}#{it['i']}({sp})", jp, en, cn))

for t, info in sorted(counts.items(), key=lambda kv: -kv[1]["count"]):
    if info["count"] == 0:
        continue
    print(f"=== {t} ({info['count']}) ===")
    for loc, jp, en, cn in info["samples"]:
        print(f"  [{loc}]\n    JP: {jp}\n    EN: {en}\n    CN: {cn}")
