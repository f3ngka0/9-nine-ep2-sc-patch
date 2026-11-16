import json
import pathlib
import re

CORPUS_DIR = pathlib.Path(r"d:\code\translate\work\scn_corpus")
CHUNKS_DIR = pathlib.Path(r"d:\code\translate\work\scn_chunks")
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
GLOSSARY_TEXT = pathlib.Path(r"d:\code\translate\work\glossary.md").read_text(encoding="utf-8")
TAG_RE = re.compile(r"%[^;]*;")
TC_STRICT = set(
    "這為說裡個們會來時學問國動無應將總覺聲聽話經讓該請識變過進連還選錯鏡難離頭顏風飛飯館點開關門體廣張寫對愛認氣場機歡樂從條與畫書見現觀視電腦網線結統給紅綠藍黃嗎"
)
CHUNK_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "s": {"type": "integer"},
                    "i": {"type": "integer"},
                    "disp": {"type": "string"},
                },
                "required": ["s", "i", "disp"],
            },
        },
        "selects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "s": {"type": "integer"},
                    "i": {"type": "integer"},
                    "text": {"type": "string"},
                },
                "required": ["s", "i", "text"],
            },
        },
    },
    "required": ["items", "selects"],
}


def extract_tags(s: str) -> list[str]:
    return TAG_RE.findall(s or "")


def normalize_disp(s: str) -> str:
    s = s.replace("\r\n", "\n").replace("\n", "\\n")
    while "\\\\n" in s:
        s = s.replace("\\\\n", "\\n")
    return s


def validate_chunk(chunk_items, chunk_selects, res):
    errors = []
    if not isinstance(res, dict):
        return ["Response is not an object"]
    got_items = res.get("items") or []
    got_selects = res.get("selects") or []
    exp_keys = [(it["s"], it["i"]) for it in chunk_items]
    got_map = {}
    for g in got_items:
        k = (g["s"], g["i"])
        if k in got_map:
            errors.append(f"Duplicate key {k}")
        got_map[k] = normalize_disp(g["disp"])
    if set(got_map.keys()) != set(exp_keys):
        errors.append("Key mismatch")
        return errors
    for it in chunk_items:
        k = (it["s"], it["i"])
        tr = got_map[k]
        if it["jp"].strip() and not tr.strip():
            errors.append(f"{k}: empty translation")
        jp_tags = extract_tags(it["jp"])
        tr_tags = extract_tags(tr)
        for t in jp_tags:
            if t.startswith("%D$") or t == "%d;" or t.startswith("%p") or t.startswith("%f"):
                if tr_tags.count(t) != jp_tags.count(t):
                    errors.append(f"{k}: tag {t!r} count mismatch")
                    break
        tc_chars = [c for c in TAG_RE.sub("", tr) if c in TC_STRICT]
        if tc_chars:
            errors.append(f"{k}: TC chars {''.join(tc_chars)}")
    return errors


obj = json.loads((CORPUS_DIR / "b20.txt.json").read_text(encoding="utf-8"))
flat_items = []
flat_selects = []
for sc in obj["scenes"]:
    s_idx = sc["scene_idx"]
    if s_idx == 3:
        continue
    for it in sc["texts"]:
        sp_jp = (it["jp"][0] if it["jp"] and it["jp"][0] else it["t0"]) or "旁白"
        flat_items.append({
            "s": s_idx,
            "i": it["i"],
            "sp": sp_jp,
            "jp": it["jp"][1] if it["jp"] else "",
            "en": it["en"][1] if it["en"] else "",
            "tc": it["cn"][1] if it["cn"] else "",
        })
    for sel in sc["selects"]:
        d = sel["data"]
        lang = d.get("language") or []
        en_s = lang[1]["text"] if len(lang) > 1 and lang[1] else ""
        tc_s = lang[2]["text"] if len(lang) > 2 and lang[2] else ""
        flat_selects.append({
            "s": s_idx,
            "i": sel["i"],
            "jp": d.get("text", ""),
            "en": en_s,
            "tc": tc_s,
        })

system_prompt = (
    "你是专业轻小说与 Galgame《9-nine-：天色天歌天籁音》（Episode 2）的资深简体中文译者。\n"
    "你正在翻译终章剧情文件 `b20.txt.json`（全年龄路线场景 1、2、4）。\n"
    "不要调用任何读/写/命令工具，直接翻译输入的 JSON 数据并通过 `finish` 工具返回严格符合 schema 的 JSON 对象。\n\n"
    f"{GLOSSARY_TEXT}\n\n"
    "输出要求：\n"
    "- 必须原封不动保留每一条目的 `s` 和 `i`，不得漏行、合并或增删条目。\n"
    "- 若原文含引擎控制符 `%D$vl1;`..`%D$vl5;`、`%d;`、`%p-1;%fＭＳ ゴシック;`、`%p;%fuser;`，务必严格保留相同次数与精确拼写（尤其不要漏 `%d;` 和 `%D$vlN;`）。\n"
    "- 对话保持 `「……」` 与适当的换行对齐（换行后的对白接全角空格 `\\u3000`；换行只需写单个 `\\n`，不要双写反斜杠）。\n"
    "- 零繁体字或台式惯用语残留。\n"
)

tr = None
try:
    chunks = [flat_items[k : k + 150] for k in range(0, len(flat_items), 150)]
    all_items = {}
    all_sels = {}
    for c_idx, ch in enumerate(chunks):
        ch_sel = flat_selects if c_idx == len(chunks) - 1 else []
        cpath = CHUNKS_DIR / f"b20_allages.c{c_idx}.json"
        res = None
        if cpath.exists():
            try:
                cached = json.loads(cpath.read_text(encoding="utf-8"))
                if not validate_chunk(ch, ch_sel, cached):
                    res = cached
                    log(f"Loaded cached {cpath.name}")
            except Exception:
                res = None
        if res is None:
            if tr is None:
                tr = agent(prompt=system_prompt, schema=CHUNK_SCHEMA, role="TL b20 allages", type_name="self")
            payload = json.dumps({"items": ch, "selects": ch_sel}, ensure_ascii=False)
            prompt = f"请将 `b20.txt.json` 全年龄第 {c_idx + 1}/{len(chunks)} 段逐条自然翻译成简体中文（以 `jp` 为主，`en` 和 `tc` 作辅助参考并纠正误译）：\n{payload}"
            res = await tr(prompt, CHUNK_SCHEMA)
            errs = validate_chunk(ch, ch_sel, res)
            if errs:
                res = await tr("请修复以下校验错误并重新调用 `finish`：\n" + "\n".join(errs[:20]), CHUNK_SCHEMA)
                errs = validate_chunk(ch, ch_sel, res)
                if errs:
                    raise RuntimeError(f"b20 allages chunk {c_idx} failed: {errs[:10]}")
            cpath.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        for g in res["items"]:
            all_items[(g["s"], g["i"])] = normalize_disp(g["disp"])
        for g in res["selects"]:
            all_sels[(g["s"], g["i"])] = g["text"]
finally:
    if tr is not None:
        del tr

out_path = pathlib.Path(r"d:\code\translate\work\scn_chunks\b20_allages.json")
out_obj = {
    "file": obj["file"],
    "name": obj["name"],
    "items": {f"{s}:{i}": v for (s, i), v in sorted(all_items.items())},
    "selects": {f"{s}:{i}": v for (s, i), v in sorted(all_sels.items())},
}
out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=1), encoding="utf-8")
log(f"Finished b20_allages: {len(all_items)} lines")
print(f"Finished b20_allages: {len(all_items)} lines")
