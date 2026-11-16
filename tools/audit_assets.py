import pathlib
import re

DEC_ROOT = pathlib.Path(r"d:\code\translate\build\decoded\data")
EXT_ROOT = pathlib.Path(r"d:\code\translate\build\extracted\data")

print("=== 1. CJK STRING LITERALS IN DECODED TJS/KS (excluding comments) ===")
pat = re.compile(r'(["\'])(?:\\.|(?!\1).)*[\u3040-\u30ff\u4e00-\u9fff](?:\\.|(?!\1).)*\1')
for p in sorted(DEC_ROOT.rglob("*")):
    if p.is_file() and p.suffix in (".tjs", ".ks"):
        txt = p.read_text(encoding="utf-8", errors="replace")
        # strip // comments and /* */ comments roughly, plus ; comments in .ks
        no_cmt = re.sub(r'/\*.*?\*/', '', txt, flags=re.S)
        lines = []
        for idx, line in enumerate(no_cmt.splitlines(), 1):
            s = line.strip()
            if s.startswith("//") or (p.suffix == ".ks" and s.startswith(";")):
                continue
            line_nc = re.sub(r'//.*', '', line)
            matches = [m.group(0) for m in pat.finditer(line_nc)]
            if matches:
                lines.append((idx, matches))
        if lines:
            print(f"\n[{p.relative_to(DEC_ROOT)}] ({len(lines)} lines)")
            for idx, m in lines[:20]:
                print(f"  L{idx}: {m[:6]}")
            if len(lines) > 20:
                print(f"  ... ({len(lines) - 20} more lines)")

print("\n=== 2. UIPSD & IMAGE FILES IN EXTRACTED DATA ===")
for sub in ("uipsd", "image", "main", "font", "scn"):
    d = EXT_ROOT / sub
    if d.exists():
        files = sorted(f for f in d.rglob("*") if f.is_file())
        print(f"\n[{sub}] ({len(files)} files)")
        for f in files:
            print(f"  {f.relative_to(EXT_ROOT)} ({f.stat().st_size})")
