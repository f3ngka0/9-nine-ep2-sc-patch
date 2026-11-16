import json, pathlib

tr_dir = pathlib.Path(r"d:\code\translate\work\scn_translated")
changed_files = 0
repl_nineball = 0
repl_mock = 0

for p in sorted(tr_dir.glob("*.json")):
    obj = json.loads(p.read_text(encoding="utf-8"))
    modified = False
    for k, v in obj["items"].items():
        nv = v
        if "九号球" in nv:
            nv = nv.replace("九号球咖啡厅", "Nine Ball 咖啡厅")
            nv = nv.replace("九号球", "Nine Ball")
            repl_nineball += 1
        if p.name == "b01.txt.json" and "莫克" in nv:
            nv = nv.replace("莫克", "MockDonald's")
            repl_mock += 1
        # Clean up any double spaces introduced
        while "  " in nv:
            nv = nv.replace("  ", " ")
        if nv != v:
            obj["items"][k] = nv
            modified = True
    if modified:
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        changed_files += 1

print(f"Updated {changed_files} files: Nine Ball={repl_nineball} lines, MockDonald's={repl_mock} lines")
