import pathlib
import re
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import psb

SCN_DIR = pathlib.Path(r"d:\code\translate\build\extracted\data\scn")

files = sorted(SCN_DIR.glob("*.txt.scn"))
print(f"Found {len(files)} .txt.scn files")

root_keys = Counter()
scene_keys = Counter()
outline_shapes = Counter()
select_shapes = Counter()
text_shapes = Counter()
lang_entry_lens = Counter()
speakers_jp = Counter()
speakers_en = Counter()
speakers_cn = Counter()
tags_jp = Counter()
tags_cn = Counter()
titles = []

total_scenes = 0
total_texts = 0
total_selects = 0
total_outlines = 0

sample_select = None
sample_outline = None
sample_speaker_text = None

tag_re = re.compile(r'%[^;]*;')
bracket_re = re.compile(r'\[[^\[\]]*\]')
ruby_samples = []

for fp in files:
    p = psb.PsbFile.parse(fp.read_bytes())
    r = p.root
    root_keys[tuple(sorted(r.keys()))] += 1
    outlines = r.get("outlines")
    if outlines is not None:
        total_outlines += len(outlines)
        for o in outlines:
            if isinstance(o, dict):
                outline_shapes[("dict", tuple(sorted(o.keys())))] += 1
                if sample_outline is None:
                    sample_outline = (fp.name, o)
            elif isinstance(o, list):
                outline_shapes[("list", len(o))] += 1
                if sample_outline is None:
                    sample_outline = (fp.name, o)
            else:
                outline_shapes[(type(o).__name__,)] += 1

    scenes = r.get("scenes", [])
    total_scenes += len(scenes)
    for si, sc in enumerate(scenes):
        scene_keys[tuple(sorted(sc.keys()))] += 1
        t = sc.get("title")
        if t:
            titles.append((fp.name, si, t))
        selects = sc.get("selects") or []
        total_selects += len(selects)
        for sel in selects:
            if isinstance(sel, dict):
                select_shapes[("dict", tuple(sorted(sel.keys())))] += 1
                if sample_select is None:
                    sample_select = (fp.name, si, sel)
            elif isinstance(sel, list):
                select_shapes[("list", len(sel))] += 1
                if sample_select is None:
                    sample_select = (fp.name, si, sel)

        texts = sc.get("texts") or []
        total_texts += len(texts)
        for ti, item in enumerate(texts):
            # item = [speaker?, voice?, lang_list, ...]
            shape = (
                len(item),
                type(item[0]).__name__ if len(item) > 0 else None,
                type(item[1]).__name__ if len(item) > 1 else None,
                len(item[2]) if len(item) > 2 and isinstance(item[2], list) else type(item[2]).__name__,
            )
            text_shapes[shape] += 1
            if item[0] is not None and sample_speaker_text is None:
                sample_speaker_text = (fp.name, si, ti, item[:4])
            langs = item[2]
            if isinstance(langs, list):
                for li, le in enumerate(langs):
                    if isinstance(le, list):
                        lang_entry_lens[(li, len(le))] += 1
                        if li == 0 and le[0] is not None:
                            speakers_jp[le[0]] += 1
                        elif li == 1 and le[0] is not None:
                            speakers_en[le[0]] += 1
                        elif li == 2 and le[0] is not None:
                            speakers_cn[le[0]] += 1
                        if len(le) > 1 and isinstance(le[1], str):
                            for m in tag_re.findall(le[1]):
                                (tags_jp if li == 0 else tags_cn if li == 2 else Counter())[m] += 1
                            if li == 0 and "[" in le[1] and len(ruby_samples) < 10:
                                ruby_samples.append((fp.name, le[1][:120]))

print(f"Total scenes={total_scenes}, texts={total_texts}, selects={total_selects}, outlines={total_outlines}, titles={len(titles)}")
print("root_keys:", dict(root_keys))
print("scene_keys:", dict(scene_keys))
print("outline_shapes:", dict(outline_shapes))
print("select_shapes:", dict(select_shapes))
print("text_shapes (top 10):", text_shapes.most_common(10))
print("lang_entry_lens:", dict(lang_entry_lens))
print("sample_outline:", repr(sample_outline))
print("sample_select:", repr(sample_select))
print("sample_speaker_text:", repr(sample_speaker_text))
print("sample_titles:", titles[:15])
print("speakers_jp:", speakers_jp.most_common(40))
print("speakers_en:", speakers_en.most_common(40))
print("speakers_cn:", speakers_cn.most_common(40))
print("top tags_jp:", tags_jp.most_common(25))
print("top tags_cn:", tags_cn.most_common(25))
print("bracket/ruby samples:", ruby_samples[:10])
