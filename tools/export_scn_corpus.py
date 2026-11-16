import json
import pathlib
import re
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import psb

EXT_SCN = pathlib.Path(r"d:\code\translate\build\extracted\data\scn")
OUT_DIR = pathlib.Path(r"d:\code\translate\work\scn_corpus")
OUT_DIR.mkdir(parents=True, exist_ok=True)

TAG_RE = re.compile(r"%[^;]*;")


def norm_speaker(sp):
    if isinstance(sp, str):
        return sp
    return sp


def main():
    summary = {
        "files": [],
        "total_scenes": 0,
        "total_texts": 0,
        "total_selects": 0,
        "speakers": {},
        "tags": {},
        "len4_jp": 0,
        "len4_en": 0,
        "len4_cn": 0,
        "extra_len_items": [],
        "tc_anomalies": [],
    }

    for scn_path in sorted(EXT_SCN.glob("*.scn")):
        raw = scn_path.read_bytes()
        p = psb.PsbFile.parse(raw)
        root = p.root
        scenes = root.get("scenes", [])
        file_rec = {
            "file": scn_path.name,
            "name": root.get("name"),
            "scene_count": len(scenes),
            "text_count": 0,
            "select_count": 0,
            "scenes": [],
        }

        for s_idx, sc in enumerate(scenes):
            sp_jp = sc.get("sp_jp") or sc.get("speakers_jp")
            sp_en = sc.get("sp_en") or sc.get("speakers_en")
            sp_cn = sc.get("sp_cn") or sc.get("speakers_cn")
            texts = sc.get("texts", [])
            selects = sc.get("selects", [])
            lines_out = sc.get("lines", [])
            outlines = sc.get("outlines")

            sc_rec = {
                "scene_idx": s_idx,
                "title": sc.get("title"),
                "sp_jp": sp_jp,
                "sp_en": sp_en,
                "sp_cn": sp_cn,
                "lines_meta": [
                    # preserve speaker name if stored on texts rather than scene, inspect keys!
                ],
                "texts": [],
                "selects": [],
            }

            for t_idx, t in enumerate(texts):
                # Inspect t structure: [speaker_name_id/disp?, line_idx?, [jp, en, cn], ...]
                speaker_id = t[0] if len(t) > 0 else None
                speaker_jp_slot = t[1] if len(t) > 1 else None
                langs = t[2] if len(t) > 2 else None
                extra = t[3:] if len(t) > 3 else []
                if len(t) != 6:
                    summary["extra_len_items"].append({
                        "file": scn_path.name,
                        "scene": s_idx,
                        "idx": t_idx,
                        "len": len(t),
                        "extra": extra,
                    })

                jp = langs[0] if isinstance(langs, list) and len(langs) > 0 else None
                en = langs[1] if isinstance(langs, list) and len(langs) > 1 else None
                cn = langs[2] if isinstance(langs, list) and len(langs) > 2 else None

                if isinstance(jp, list) and len(jp) == 4:
                    summary["len4_jp"] += 1
                if isinstance(en, list) and len(en) == 4:
                    summary["len4_en"] += 1
                if isinstance(cn, list) and len(cn) == 4:
                    summary["len4_cn"] += 1

                # Track speakers
                sp_key = json.dumps([speaker_id, jp[0] if jp else None, en[0] if en else None, cn[0] if cn else None], ensure_ascii=False)
                summary["speakers"][sp_key] = summary["speakers"].get(sp_key, 0) + 1

                # Track inline tags across jp, en, cn
                jp_disp = jp[1] if isinstance(jp, list) and len(jp) > 1 else ""
                en_disp = en[1] if isinstance(en, list) and len(en) > 1 else ""
                cn_disp = cn[1] if isinstance(cn, list) and len(cn) > 1 else ""
                for lang_code, s in (("jp", jp_disp), ("en", en_disp), ("cn", cn_disp)):
                    if isinstance(s, str):
                        for m in TAG_RE.findall(s):
                            summary["tags"][m] = summary["tags"].get(m, 0) + 1

                # Detect possible missing text in TC vs JP
                if isinstance(jp_disp, str) and isinstance(cn_disp, str):
                    if ("%p-1;" in jp_disp or len(jp_disp) > 5) and len(cn_disp) == 0:
                        summary["tc_anomalies"].append({
                            "file": scn_path.name,
                            "scene": s_idx,
                            "idx": t_idx,
                            "jp": jp_disp,
                            "en": en_disp,
                            "cn": cn_disp,
                        })
                    elif jp_disp.count("%") != cn_disp.count("%"):
                        summary["tc_anomalies"].append({
                            "file": scn_path.name,
                            "scene": s_idx,
                            "idx": t_idx,
                            "jp": jp_disp,
                            "en": en_disp,
                            "cn": cn_disp,
                        })

                item = {
                    "i": t_idx,
                    "t0": speaker_id,
                    "t1": speaker_jp_slot,
                    "jp": jp,
                    "en": en,
                    "cn": cn,
                    "t_rest": extra,
                }
                sc_rec["texts"].append(item)
                file_rec["text_count"] += 1

            for sel_idx, sel in enumerate(selects):
                sc_rec["selects"].append({"i": sel_idx, "data": sel})
                file_rec["select_count"] += 1

            file_rec["scenes"].append(sc_rec)

        out_file = OUT_DIR / f"{scn_path.stem}.json"
        out_file.write_text(json.dumps(file_rec, ensure_ascii=False, indent=1), encoding="utf-8")

        summary["files"].append({
            "file": scn_path.name,
            "scenes": file_rec["scene_count"],
            "texts": file_rec["text_count"],
            "selects": file_rec["select_count"],
        })
        summary["total_scenes"] += file_rec["scene_count"]
        summary["total_texts"] += file_rec["text_count"]
        summary["total_selects"] += file_rec["select_count"]

    (OUT_DIR / "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(summary['files'])} files: {summary['total_scenes']} scenes, {summary['total_texts']} texts, {summary['total_selects']} selects")
    print("len4:", summary["len4_jp"], summary["len4_en"], summary["len4_cn"])
    print("tags:", summary["tags"])
    print("tc_anomalies:", len(summary["tc_anomalies"]))


if __name__ == "__main__":
    main()
