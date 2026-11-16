import os
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import psb

BASE = r"d:\code\translate\build\extracted\data"

files = []
for sub in ("scn", "uipsd"):
    d = os.path.join(BASE, sub)
    for root, _, fns in os.walk(d):
        for fn in sorted(fns):
            if fn.endswith((".scn", ".pimg")):
                files.append(os.path.join(root, fn))

byte_exact = 0
tree_exact = 0
rebuild_trie_ok = 0

for fp in files:
    orig = open(fp, "rb").read()
    p1 = psb.PsbFile.parse(orig)
    rebuilt = p1.to_bytes()
    if rebuilt == orig:
        byte_exact += 1
    p2 = psb.PsbFile.parse(rebuilt)
    assert p2.root == p1.root and p2.chunks == p1.chunks and p2.names == p1.names, fp
    tree_exact += 1

    # Also test full B-tree name trie encoder (setting _names_raw=None)!
    p1._names_raw = None
    rebuilt_trie = p1.to_bytes()
    p3 = psb.PsbFile.parse(rebuilt_trie)
    assert p3.root == p1.root and p3.chunks == p1.chunks and set(p3.names).issubset(p1.names), fp
    rebuild_trie_ok += 1

print(f"Tested {len(files)} PSB files: tree_exact={tree_exact}/{len(files)}, byte_exact={byte_exact}/{len(files)}, trie_rebuild_ok={rebuild_trie_ok}/{len(files)}")
