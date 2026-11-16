import json
import pathlib
import re

CORPUS_DIR = pathlib.Path(r"d:\code\translate\work\scn_corpus")
OUT_DIR = pathlib.Path(r"d:\code\translate\work\scn_translated")
CHUNKS_DIR = pathlib.Path(r"d:\code\translate\work\scn_chunks")
ERRORS_DIR = pathlib.Path(r"d:\code\translate\work\scn_errors")
GLOSSARY_PATH = pathlib.Path(r"d:\code\translate\work\glossary.md")
OUT_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
ERRORS_DIR.mkdir(parents=True, exist_ok=True)

GLOSSARY_TEXT = GLOSSARY_PATH.read_text(encoding="utf-8")
TAG_RE = re.compile(r"%[^;]*;")
SINGLE_KANA_RE = re.compile(r"[\u3041-\u3096\u30a1-\u30fa]")
BANNED_LORE_CN = ("圣遗物", "圣痕", "仙馔密酒", "萨菲罗斯", "歌咏明论", "瓦尔哈拉")

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


TC_STRICT = set(
    "這為說裡個們會來時學問國動無應將總覺聲聽話經讓該請識變過進連還選錯鏡難離頭顏風飛飯館點開關門體廣張寫對愛認氣場機歡樂從條與畫書見現觀視電腦網線結統給紅綠藍黃嗎"
)


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
        missing = sorted(set(exp_keys) - set(got_map.keys()))[:10]
        extra = sorted(set(got_map.keys()) - set(exp_keys))[:10]
        errors.append(f"Key mismatch missing={missing} extra={extra}")
        return errors

    for it in chunk_items:
        k = (it["s"], it["i"])
        tr = got_map[k]
        if it["jp"].strip() and not tr.strip():
            errors.append(f"{k}: empty translation for non-empty JP")
        jp_tags = extract_tags(it["jp"])
        tr_tags = extract_tags(tr)
        for t in jp_tags:
            if t.startswith("%D$") or t == "%d;" or t.startswith("%p") or t.startswith("%f"):
                if tr_tags.count(t) != jp_tags.count(t):
                    errors.append(f"{k}: tag {t!r} count mismatch jp={jp_tags} tr={tr_tags}")
                    break
        clean_tr = TAG_RE.sub("", tr)
        tc_chars = [c for c in clean_tr if c in TC_STRICT]
        if tc_chars:
            errors.append(f"{k}: Traditional Chinese character(s) found: {''.join(tc_chars)}")
        kana_chars = SINGLE_KANA_RE.findall(clean_tr)
        if kana_chars:
            errors.append(f"{k}: Untranslated Japanese kana found: {''.join(kana_chars)} in {tr!r}")
        for banned in BANNED_LORE_CN:
            if banned in clean_tr:
                errors.append(
                    f"{k}: Forbidden translated lore term {banned!r} found; must keep English proper noun (Artifact / Stigma / Ambrosia / Sephirot / Rig Veda / Valhalla Society)"
                )

    exp_sel = [(sel["s"], sel["i"]) for sel in chunk_selects]
    got_sel_map = {(g["s"], g["i"]): g["text"] for g in got_selects}
    if set(got_sel_map.keys()) != set(exp_sel):
        errors.append(f"Select mismatch expected={exp_sel} got={sorted(got_sel_map.keys())}")
    else:
        for k, v in got_sel_map.items():
            if not v.strip():
                errors.append(f"Select {k}: empty")

    return errors


async def translate_file(fname: str):
    src_path = CORPUS_DIR / fname
    out_path = OUT_DIR / fname
    if out_path.exists():
        log(f"Skip {fname} (already exists)")
        return {"file": fname, "status": "cached"}

    obj = json.loads(src_path.read_text(encoding="utf-8"))

    # Pure checkAdult() R18 file b18_2b.txt.json
    if fname == "b18_2b.txt.json":
        items_out = {}
        for sc in obj["scenes"]:
            s_idx = sc["scene_idx"]
            for it in sc["texts"]:
                k = f"{s_idx}:{it['i']}"
                raw = normalize_disp(it["cn"][1])
                raw = raw.replace("聖遺物", "Artifact").replace("聖痕", "Stigma")
                items_out[k] = raw
        out_obj = {
            "file": obj["file"],
            "name": obj["name"],
            "items": items_out,
            "selects": {},
            "retained_r18_scenes": [1],
        }
        out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"file": fname, "lines": len(items_out), "selects": 0, "status": "ok"}

    flat_items = []
    flat_selects = []
    retained_r18_items = {}
    retained_r18_scenes = []
    retained_r18_keys = []

    for sc in obj["scenes"]:
        s_idx = sc["scene_idx"]
        # b20 scene 3 is checkAdult()-gated R18 H-scene
        if fname == "b20.txt.json" and s_idx == 3:
            retained_r18_scenes.append(3)
            for it in sc["texts"]:
                k = (s_idx, it["i"])
                raw = normalize_disp(it["cn"][1])
                raw = raw.replace("聖遺物", "Artifact").replace("聖痕", "Stigma")
                retained_r18_items[k] = raw
            continue

        for it in sc["texts"]:
            # b19_1 chunk 2 (s==1 and i>=360, or s==2) is checkAdult()-gated explicit R18 H-scene
            if fname == "b19_1.txt.json" and ((s_idx == 1 and it["i"] >= 360) or s_idx == 2):
                k = (s_idx, it["i"])
                raw = normalize_disp(it["cn"][1])
                raw = raw.replace("聖遺物", "Artifact").replace("聖痕", "Stigma")
                retained_r18_items[k] = raw
                retained_r18_keys.append(f"{s_idx}:{it['i']}")
                continue

            sp_jp = (it["jp"][0] if it["jp"] and it["jp"][0] else it["t0"]) or "旁白"
            flat_items.append({
                "s": s_idx,
                "i": it["i"],
                "sp": sp_jp,
                "jp": it["jp"][1] if it["jp"] else "",
                "en": it["en"][1] if it["en"] else "",
            })
        for sel in sc["selects"]:
            d = sel["data"]
            lang = d.get("language") or []
            en_s = lang[1]["text"] if len(lang) > 1 and lang[1] else ""
            flat_selects.append({
                "s": s_idx,
                "i": sel["i"],
                "jp": d.get("text", ""),
                "en": en_s,
            })

    system_prompt = (
        f"你是顶尖的中文轻小说与视觉小说《9-nine-：天色天歌天籁音》（Episode 2）母语级本土化译者。\n"
        f"你正在翻译并深度润色剧本文件 `{fname}`。\n"
        f"不要调用任何读/写/命令工具，直接翻译输入的 JSON 数据并通过 `finish` 工具返回严格符合 schema 的 JSON 对象。\n\n"
        f"{GLOSSARY_TEXT}\n\n"
        f"核心要求（务必严格执行）：\n"
        f"1. **彻底消除日式翻译腔，贴近中文母语者的语序和用词**：\n"
        f"   - 严禁顺着日语语序逐字硬翻！遇到日语倒装补语（如『……ない。俺に。』）、超长前置定语（『……した犯人が。』）、形式体言（『……したのは昨日のこと』）或日式套话（『一応』『視線に負けて』『実際、いる』『二度見である』），必须结合 `jp` 的准确原意与 `en` 的自然叙事逻辑，用自然、地道、流畅的现代中文重新组织语序和词汇（意译）！\n"
        f"   - 连续几条短句如果是同一段心理活动或动作拆分，请先通读上下文，让拆开后的每一行在中文里顺畅衔接。\n"
        f"2. **世界观专有名词直接保留英文**：\n"
        f"   - `Artifact`（及 `AF`）、`Stigma`、`Ambrosia`、`Sephirot`、`Rig Veda`、`Valhalla Society`、`Gate` 必须直接保留英文（严禁译为圣遗物、圣痕、仙馔密酒、萨菲罗斯、歌咏明论、瓦尔哈拉）！\n"
        f"3. **格式与标签铁律**：\n"
        f"   - 必须原封不动保留每一条目的 `s` 和 `i`，不得漏行、合并或增删条目。\n"
        f"   - 若 `jp` 含引擎控制符 `%D$vl1;`..`%D$vl5;`、`%d;`、`%p-1;%fＭＳ ゴシック;`、`%p;%fuser;`，务必严格保留相同次数与精确拼写。\n"
        f"   - 对话保持 `「……」` 与适当的换行对齐（对话内 `\\n` 换行后的下一行行首加全角空格 `\\u3000`；换行写单个 `\\n`）。\n"
        f"   - 严禁残留任何日语假名（如 `っ`、`ね`、`じゃん`）或繁体字。\n"
    )

    tr = None
    try:
        CHUNK_SIZE = 180
        all_trans_items = dict(retained_r18_items)
        all_trans_selects = {}

        chunks = [flat_items[k : k + CHUNK_SIZE] for k in range(0, len(flat_items), CHUNK_SIZE)]
        if not chunks:
            chunks = [[]]

        for c_idx, ch in enumerate(chunks):
            ch_selects = flat_selects if c_idx == len(chunks) - 1 else []
            chunk_path = CHUNKS_DIR / f"{fname}.c{c_idx}.json"
            res = None
            if chunk_path.exists():
                try:
                    cached = json.loads(chunk_path.read_text(encoding="utf-8"))
                    if not validate_chunk(ch, ch_selects, cached):
                        res = cached
                        log(f"Loaded cached chunk {chunk_path.name}")
                except Exception:
                    res = None

            if res is None:
                if tr is None:
                    tr = agent(prompt=system_prompt, schema=CHUNK_SCHEMA, role=f"TL2 {fname}", type_name="self")
                payload = json.dumps({"items": ch, "selects": ch_selects}, ensure_ascii=False)
                prompt = (
                    f"请将 `{fname}` 的第 {c_idx + 1}/{len(chunks)} 段翻译为符合中文母语者说话与阅读习惯的地道简体中文。\n"
                    f"注意：以 `jp` 核对准确原意与引擎标签，参考 `en` 的自然句式与英文专有名词（`Artifact`、`Stigma`、`Ambrosia`、`Sephirot`、`Rig Veda`、`Valhalla Society`、`Gate` 直接保留英文），大胆调整日语语序并意译，彻底消除翻译腔：\n{payload}"
                )
                res = await tr(prompt, CHUNK_SCHEMA)
                errs = validate_chunk(ch, ch_selects, res)
                if errs:
                    fix_prompt = (
                        f"刚才返回结果存在以下校验错误，请修复并重新通过 `finish` 提交本段完整 `{len(ch)}` 条译文与 `{len(ch_selects)}` 条选项：\n"
                        + "\n".join(errs[:20])
                    )
                    res = await tr(fix_prompt, CHUNK_SCHEMA)
                    errs = validate_chunk(ch, ch_selects, res)
                    if errs:
                        raise RuntimeError(f"{fname} chunk {c_idx} failed validation after retry: {errs[:10]}")
                chunk_path.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")

            for g in res["items"]:
                all_trans_items[(g["s"], g["i"])] = normalize_disp(g["disp"])
            for g in res["selects"]:
                all_trans_selects[(g["s"], g["i"])] = g["text"]

        out_obj = {
            "file": obj["file"],
            "name": obj["name"],
            "items": {f"{s}:{i}": v for (s, i), v in sorted(all_trans_items.items())},
            "selects": {f"{s}:{i}": v for (s, i), v in sorted(all_trans_selects.items())},
        }
        if retained_r18_scenes:
            out_obj["retained_r18_scenes"] = retained_r18_scenes
        if retained_r18_keys:
            out_obj["retained_r18_keys"] = retained_r18_keys

        out_path.write_text(json.dumps(out_obj, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"Finished {fname}: {len(all_trans_items)} lines, {len(all_trans_selects)} selects")
        return {"file": fname, "lines": len(all_trans_items), "selects": len(all_trans_selects), "status": "ok"}
    except Exception as exc:
        err_path = ERRORS_DIR / f"{fname}.txt"
        err_path.write_text(str(exc), encoding="utf-8")
        log(f"ERROR in {fname}: {exc}")
        return {"file": fname, "status": "error", "error": str(exc)}
    finally:
        if tr is not None:
            del tr


target_files = args.get("files") or sorted(
    (p.name for p in CORPUS_DIR.glob("*.json") if not p.name.startswith("_")),
    key=lambda fn: -(CORPUS_DIR / fn).stat().st_size,
)
todo_files = [fn for fn in target_files if not (OUT_DIR / fn).exists()]
batch_size = int(args.get("batch_size", 12))

results = []
for b_idx in range(0, len(todo_files), batch_size):
    batch = todo_files[b_idx : b_idx + batch_size]
    phase(f"Batch {b_idx // batch_size + 1}: {', '.join(batch)}")
    res = await parallel(batch, translate_file)
    results.extend(res)

print(json.dumps(results, ensure_ascii=False))
