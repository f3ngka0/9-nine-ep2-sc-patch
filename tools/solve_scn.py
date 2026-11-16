"""Inspect all 36 .scn files: find exact k1, k2, split, and isolate any single-byte cxdec differences."""

import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, r"C:\Users\fengkao\.gemini\antigravity\brain\4c347a84-c7e5-4806-8be9-1f2fe149f530\scratch")
import xp3
import test_psb

game_dir = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
data_xp3 = os.path.join(game_dir, "data.xp3")
ents = xp3.parse_xp3_entries(data_xp3)

def find_k1_psb(r):
    return Counter([r[1]^ord('S'), r[2]^ord('B'), r[3]^0, r[5]^0, r[6]^0, r[7]^0]).most_common(1)[0][0]

def find_k2_psb(r, hdr):
    for k in range(256):
        t0 = r[hdr[4]] ^ k
        if t0 in (0x0d, 0x0e, 0x0f, 0x10):
            csz = t0 - 0x0c
            if hdr[4] + 1 + csz < hdr[5]:
                t1 = r[hdr[4]+1+csz] ^ k
                if t1 in (0x0d, 0x0e, 0x0f, 0x10):
                    esz = t1 - 0x0c
                    cnt = int.from_bytes(bytes(b^k for b in r[hdr[4]+1:hdr[4]+1+csz]), 'little')
                    if hdr[4] + 2 + csz + cnt * esz == hdr[5]:
                        return k
    return None

def rd_ia_len(b, off):
    t = b[off]
    if not (0x0d <= t <= 0x10): raise ValueError
    cs = t - 0x0c; c = int.from_bytes(b[off+1:off+1+cs], 'little')
    t2 = b[off+1+cs]
    if not (0x0d <= t2 <= 0x10): raise ValueError
    es = t2 - 0x0c
    return off + 2 + cs + c * es

scns = sorted(k for k in ents if k.startswith("scn/") and k.endswith(".scn"))
for fn in scns:
    r, a = xp3.read_entry(data_xp3, ents[fn])
    k1 = find_k1_psb(r)
    hdr_b = bytearray(r[i]^k1 for i in range(40))
    # Fix any byte in hdr[:40] if needed (we know hdr[0..3]=PSB\0, hdr[3]=44, hdr[1]=3, hdr[2]=0)
    b0_anom = [i for i, b in enumerate(b"PSB\x00\x03\x00\x00\x00\x2c\x00\x00\x00") if hdr_b[i] != b]
    hdr_b[:12] = b"PSB\x00\x03\x00\x00\x00\x2c\x00\x00\x00"
    hdr = struct.unpack_from("<10I", hdr_b, 0)
    k2 = find_k2_psb(r, hdr)
    # Check where name_trie arrays sit! Note name_trie ends BEFORE hdr[9] (entry) OR hdr[9] is AFTER split!
    # Wait: test_psb parses name_trie = 3 int_arrays starting at 44, ending at p; let's see what best_s gives!
    lo_s, hi_s = 0x700, 0x920
    if k1 != k2:
        best_s = max(range(lo_s, hi_s), key=lambda s: sum(1 for i in range(lo_s, s) if r[i]==k1) + sum(1 for i in range(s, hi_s) if r[i]==k2))
    else:
        best_s = len(r)
    # Also check ALL splits in 0x700..0x920 where name_trie ends at hdr[9] AND dec[hdr[9]] == 0x21 (with full 3-array check)
    # Wait: in 3rd array, elements can cross 0x800, ONLY tag bytes must be valid, and p == hdr[9]!
    # Why did task-256 skip b16? Because best_s was 0x8b0 while split was ~0x8c0!
    ok_sp = None
    err_best = None
    # Try best_s, then +-20 ONLY checking fast header+names+root FIRST (<0.01ms per split)!
    cands = [best_s] + [best_s + d for k in range(1, 25) for d in (k, -k)]
    # Also add full 0x790..0x8e0 for anything failing
    for sp in cands:
        if not (0x700 <= sp <= 0x950): continue
        dec = bytearray(r[i] ^ (k1 if i < sp else k2) for i in range(hdr[9] + 32))
        dec[:12] = b"PSB\x00\x03\x00\x00\x00\x2c\x00\x00\x00"
        try:
            p = rd_ia_len(dec, 44)
            p = rd_ia_len(dec, p)
            p = rd_ia_len(dec, p)
            if p != hdr[9] or dec[p] != 0x21:
                continue
            # Also check root keys int_array at hdr[9]+1!
            p2 = rd_ia_len(dec, p + 1)
        except Exception:
            continue
        # Candidate passed name_trie & root dict keys! Run full parse!
        full_dec = bytearray(r[i] ^ (k1 if i < sp else k2) for i in range(len(r)))
        full_dec[:12] = b"PSB\x00\x03\x00\x00\x00\x2c\x00\x00\x00"
        try:
            root, names, strs = test_psb.parse_psb_full(bytes(full_dec))
            ok_sp = (sp, len(strs), sum(1 for s in strs if "\ufffd" in s))
            break
        except Exception as e:
            if err_best is None: err_best = (sp, f"{type(e).__name__}: {e}")
    if ok_sp:
        print(f"OK  {fn:18s} adlr={a:#010x} k1={k1:#04x} k2={k2:#04x} sp={ok_sp[0]:#x} strs={ok_sp[1]:4d} bad_u8={ok_sp[2]} hdr_anom={b0_anom}")
    else:
        print(f"ERR {fn:18s} adlr={a:#010x} k1={k1:#04x} k2={k2:#04x} best_s={best_s:#x} hdr_anom={b0_anom} err={err_best}")
