import json, pathlib, re
from collections import Counter

d = pathlib.Path(r"d:\code\translate\work\scn_corpus")
kat = Counter()
for p in sorted(d.glob("*.json")):
    if p.name.startswith("_"): continue
    obj = json.loads(p.read_text(encoding="utf-8"))
    for sc in obj["scenes"]:
        for it in sc["texts"]:
            jp = it["jp"][1] if it["jp"] else ""
            for m in re.findall(r"[ァ-ヶー]{3,}", jp):
                kat[m] += 1

print("Top 80 katakana terms:")
for k, v in kat.most_common(80):
    print(f"  {k}: {v}")
