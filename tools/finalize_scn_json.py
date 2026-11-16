import json
import pathlib
import re

CORPUS_DIR = pathlib.Path(r"d:\code\translate\work\scn_corpus")
TR_DIR = pathlib.Path(r"d:\code\translate\work\scn_translated")
CHUNKS_DIR = pathlib.Path(r"d:\code\translate\work\scn_chunks")
TAG_RE = re.compile(r"%[^;]*;")
SINGLE_KANA_RE = re.compile(r"[\u3041-\u3096\u30a1-\u30fa]")


def normalize_disp(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\n", "\\n")
    while "\\\\n" in s:
        s = s.replace("\\\\n", "\\n")
    return s


# 1. Fix the 3 known hiragana slips in b07, b12a, b15b
fixes = [
    ("b07.txt.json", "0:87", "じゃん。", "嘛。"),
    ("b12a.txt.json", "0:106", "人渣かよ。", "真是个人渣啊。"),
    ("b15b.txt.json", "0:32", "「您好……って，咦？」", "「你好……哎，咦？」"),
    ("b10b.txt.json", "0:248", "诶～っ！", "诶～！"),
    ("b12c.txt.json", "0:2", "累死我了……っ」", "累死我了……」"),
    ("b12c.txt.json", "0:230", "可恶……っ」", "可恶……」"),
    ("b14.txt.json", "0:163", "「是ね。", "「是呢。"),
    ("b15b.txt.json", "0:102", "神社の传说", "神社的传说"),
]
for fn, key, old, new in fixes:
    p = TR_DIR / fn
    obj = json.loads(p.read_text(encoding="utf-8"))
    if old in obj["items"][key]:
        obj["items"][key] = obj["items"][key].replace(old, new)
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Fixed {fn} {key}: {obj['items'][key]!r}")

# 2. Assemble b20.txt.json (287 translated All-Ages lines + 160 checkAdult() R18 lines from cn)
b20_c = json.loads((CORPUS_DIR / "b20.txt.json").read_text(encoding="utf-8"))
b20_aa = json.loads((CHUNKS_DIR / "b20_allages.json").read_text(encoding="utf-8"))
b20_items = dict(b20_aa["items"])
for sc in b20_c["scenes"]:
    if sc["scene_idx"] == 3:
        for it in sc["texts"]:
            k = f"3:{it['i']}"
            b20_items[k] = normalize_disp(it["cn"][1])
(TR_DIR / "b20.txt.json").write_text(
    json.dumps(
        {
            "file": b20_c["file"],
            "name": b20_c["name"],
            "items": b20_items,
            "selects": b20_aa["selects"],
            "retained_r18_scenes": [3],
        },
        ensure_ascii=False,
        indent=1,
    ),
    encoding="utf-8",
)
print(f"Assembled b20.txt.json: {len(b20_items)} total lines (287 SC All-Ages + 160 retained R18)")

# 3. Assemble b19_1.txt.json (360 translated SC lines from c0+c1 + 149 retained R18 lines from cn)
b19_c = json.loads((CORPUS_DIR / "b19_1.txt.json").read_text(encoding="utf-8"))
c0 = json.loads((CHUNKS_DIR / "b19_1.txt.json.c0.json").read_text(encoding="utf-8"))
c1 = json.loads((CHUNKS_DIR / "b19_1.txt.json.c1.json").read_text(encoding="utf-8"))
b19_items = {}
for g in c0["items"] + c1["items"]:
    b19_items[f"{g['s']}:{g['i']}"] = normalize_disp(g["disp"])
retained_b19_keys = []
for sc in b19_c["scenes"]:
    s_idx = sc["scene_idx"]
    for it in sc["texts"]:
        k = f"{s_idx}:{it['i']}"
        if k not in b19_items:
            b19_items[k] = normalize_disp(it["cn"][1])
            retained_b19_keys.append(k)
(TR_DIR / "b19_1.txt.json").write_text(
    json.dumps(
        {
            "file": b19_c["file"],
            "name": b19_c["name"],
            "items": b19_items,
            "selects": {},
            "retained_r18_keys": retained_b19_keys,
        },
        ensure_ascii=False,
        indent=1,
    ),
    encoding="utf-8",
)
print(f"Assembled b19_1.txt.json: {len(b19_items)} total lines (360 SC + {len(retained_b19_keys)} retained R18)")

# 4. Assemble b18_2b.txt.json (300 checkAdult() R18 lines from cn)
b182b_c = json.loads((CORPUS_DIR / "b18_2b.txt.json").read_text(encoding="utf-8"))
b182b_items = {}
for sc in b182b_c["scenes"]:
    s_idx = sc["scene_idx"]
    for it in sc["texts"]:
        k = f"{s_idx}:{it['i']}"
        b182b_items[k] = normalize_disp(it["cn"][1])
(TR_DIR / "b18_2b.txt.json").write_text(
    json.dumps(
        {
            "file": b182b_c["file"],
            "name": b182b_c["name"],
            "items": b182b_items,
            "selects": {},
            "retained_r18_scenes": [1],
        },
        ensure_ascii=False,
        indent=1,
    ),
    encoding="utf-8",
)
print(f"Assembled b18_2b.txt.json: {len(b182b_items)} total lines (300 retained R18)")

# 5. Scan all 10,762 translated SC lines for ANY single hiragana/katakana character
print("\n--- Scanning all 10,762 SC lines for any single kana ---")
kana_hits = []
for p in sorted(TR_DIR.glob("*.json")):
    obj = json.loads(p.read_text(encoding="utf-8"))
    ret_scenes = set(obj.get("retained_r18_scenes", []))
    ret_keys = set(obj.get("retained_r18_keys", []))
    for k, v in obj["items"].items():
        s_idx = int(k.split(":")[0])
        if s_idx in ret_scenes or k in ret_keys:
            continue
        clean = TAG_RE.sub("", v)
        m = SINGLE_KANA_RE.findall(clean)
        if m:
            kana_hits.append((p.name, k, "".join(m), v))

print(f"Single-kana hits across 10,762 SC lines: {len(kana_hits)}")
for fn, k, chars, v in kana_hits[:30]:
    print(f"  {fn} {k} [{chars}]: {v!r}")
