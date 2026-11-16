import json, pathlib

d = pathlib.Path(r"d:\code\translate\work\scn_corpus")
terms = ["オーバーロード", "イーヴィル", "スレイヴ", "アダム", "イヴ", "ブランチ", "ゲート", "アルター", "九つの星", "ペルソナ", "インビジブル", "スティール", "エクスチェンジ", "ペトリファクション"]
for t in terms:
    hits = []
    for p in sorted(d.glob("*.json")):
        if p.name.startswith("_"): continue
        obj = json.loads(p.read_text(encoding="utf-8"))
        for sc in obj["scenes"]:
            for it in sc["texts"]:
                jp = it["jp"][1] if it["jp"] else ""
                if t in jp:
                    hits.append((f"{p.stem}#{it['i']}({it['t0']})", jp, it["en"][1] if it["en"] else "", it["cn"][1] if it["cn"] else ""))
    if hits:
        print(f"=== {t} ({len(hits)}) ===")
        for h in hits[:3]:
            print(" ", h)
