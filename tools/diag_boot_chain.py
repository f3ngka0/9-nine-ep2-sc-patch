import os
import struct
import sys
from collections import Counter

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"


def decrypt_tjs_and_parse(raw: bytes, name: str):
    # Check plaintext UTF-16LE or UTF-8 or TJS2100\0
    # TJS2100\x00 magic at offset 0: 54 4a 53 32 31 30 30 00
    k1 = Counter(raw[i] ^ b"TJS2100\x00"[i] for i in range(8)).most_common(1)[0][0]
    # Also check if byte 8..11 is total file size (little endian) -> gives info
    dec1 = bytes(b ^ k1 for b in raw)
    if dec1[:7] == b"TJS2100":
        # Find k2 and split via high bits of DATA / OBJS or known ASCII UTF-16LE patterns after split (~0x700..0x950)
        # Actually inspect raw[0x700:] XOR every byte 0..255 looking for b"OBJS" or b"DATA" or ASCII UTF-16LE (\x00 every 2nd byte)
        best = None
        for sp in range(min(len(raw), 0x700), min(len(raw), 0xA00)):
            pass
        # Faster: search k2 by finding ASCII/UTF-16LE or "OBJS"/"CODE" or \x00 density in second half
        if len(raw) <= 0x750:
            dec = dec1
            k2, sp = k1, len(raw)
        else:
            tail = raw[0xA00:]
            # In TJS2 bytecode, zero bytes are super common (padding, int32 high bytes, UTF-16LE ASCII high bytes)
            # Even better: check byte frequency at 0xA00..; most frequent byte is k2!
            if tail:
                k2 = Counter(tail).most_common(1)[0][0]
            else:
                k2 = Counter(raw[0x880:]).most_common(1)[0][0]
            # Find split around 0x750..0x950 where dec changes from k1-friendly to k2-friendly
            dec2 = bytes(b ^ k2 for b in raw)
            # Use simple boundary detection: compare matching TJS2 structure or UTF-16LE/zeros
            # Or try sp where OBJS/DATA appears or score neighboring bytes
            best_sp = len(raw)
            if b"OBJS" in dec1:
                best_sp = len(raw)
            else:
                # Score transition around 0x750..0x950 by counting 0x00 and printable ASCII in window
                scores = []
                for sp_cand in range(0x750, min(len(raw), 0x980)):
                    # Prefix [0x750..sp_cand] decoded with k1, [sp_cand..min(len,0x980)] decoded with k2
                    pass
                # Prefix sum of (b^k1 == 0 or 0x20<=b^k1<=0x7e) vs (b^k2 == 0 or 0x20<=b^k2<=0x7e)
                n = min(len(raw), 0xA00)
                s1 = [1 if ((raw[i] ^ k1) == 0) else 0 for i in range(n)]
                s2 = [1 if ((raw[i] ^ k2) == 0) else 0 for i in range(n)]
                # cumulative
                p1 = [0]
                for x in s1: p1.append(p1[-1] + x)
                best_val = -1
                for sp_cand in range(0x750, n):
                    # zeroes with k1 in [0..sp_cand) + zeroes with k2 in [sp_cand..n)
                    v = p1[sp_cand] + sum(s2[sp_cand:])
                    if v > best_val:
                        best_val = v
                        best_sp = sp_cand
            dec = dec1[:best_sp] + dec2[best_sp:]
            sp = best_sp
        print(f"TJS2 {name}: k1={hex(k1)} k2={hex(k2)} sp={hex(sp)} magic={dec[:8]!r} has_DATA={b'DATA' in dec} has_OBJS={b'OBJS' in dec}")
        # Extract DATA strings + inspect chunks
        pos = dec.find(b"DATA")
        strs = []
        if pos != -1:
            dsize = struct.unpack_from("<I", dec, pos + 4)[0]
            print(f"  DATA at {hex(pos)} size={dsize}")
            p = pos + 8
            # Header inside DATA: counts of byte, short, int, long, double, string, octet
            # Wait: let's read tjs2 DATA layout: 8 uint32s or counts? Let's print hex of DATA+8..DATA+48
            print("  DATA hdr:", dec[p:p+48].hex())
            counts = struct.unpack_from("<7I", dec, p)
            print("  counts (i8,i16,i32,i64,f64,str,oct?):", counts)
            # Let's parse byte/short/int/long/double/string!
            # Wait: let's just scan UTF-16LE strings inside [DATA..OBJS] too, OR find offsets:
        # Also dump all readable UTF-16LE strings >= 2 chars from dec[pos:dec.find(b'OBJS')] if present
        end_pos = dec.find(b"OBJS")
        chunk = dec[pos:end_pos if end_pos != -1 else len(dec)]
        # Parse TJS2 DATA exact format:
        if pos != -1:
            p = pos + 8
            c_byte, c_short, c_int, c_long, c_double, c_str, c_oct = struct.unpack_from("<7I", dec, p)
            p += 28
            # bytes (padded to 4? Let's check!)
            p += ((c_byte + 3) // 4) * 4
            p += ((c_short * 2 + 3) // 4) * 4
            p += c_int * 4
            p += c_long * 8
            p += c_double * 8
            print(f"  Estimated string table start at {hex(p)} (c_str={c_str})")
            # Each string in TJS2100 DATA: uint32 len_in_utf16_units + uint16[len] (+ pad to 4 bytes!)
            cur = p
            for idx in range(c_str):
                if cur + 4 > len(dec):
                    print(f"  OOB at string {idx}/{c_str}")
                    break
                slen = struct.unpack_from("<I", dec, cur)[0]
                cur += 4
                if slen > 100000 or cur + slen * 2 > len(dec):
                    print(f"  Bad slen={slen} at idx={idx}, cur={hex(cur)}, nearby={dec[cur-16:cur+32].hex()}")
                    break
                sbytes = dec[cur:cur + slen * 2]
                s = sbytes.decode("utf-16-le", errors="replace")
                strs.append(s)
                cur += slen * 2
                # align to 4? Wait let's check if aligned to 4
                if (slen * 2) % 4 != 0:
                    cur += 2
        return strs, dec
    else:
        # Check UTF-16LE text (e.g. startup.tjs)
        return None, raw


def main():
    print("=== Checking test_patch.xp3 ===")
    patch_path = r"d:\code\translate\build\test_patch.xp3"
    pentries = xp3.parse_xp3_entries(patch_path)
    for k, entry in pentries.items():
        data, orig_flags = xp3.read_entry(patch_path, entry)
        print(f"  entry={k!r} orig_flags={hex(orig_flags)} len={len(data)}")
        txt = xp3.decode_txtobf(data)
        print(f"  decode_txtobf={txt[:200]!r}" if txt else f"  raw={data[:100]!r}")

    print("\n=== Checking AppData files ===")
    appdata = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo")
    if os.path.exists(appdata):
        for fn in os.listdir(appdata):
            fp = os.path.join(appdata, fn)
            print(" ", fn, os.path.getsize(fp))

    print("\n=== Checking data.xp3 & steam.xp3 TJS ===")
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    steam_xp3 = os.path.join(GAME_DIR, "steam.xp3")
    d_entries = xp3.parse_xp3_entries(data_xp3)
    s_entries = xp3.parse_xp3_entries(steam_xp3)

    for arc, entries, name in [
        (data_xp3, d_entries, "system/Initialize.tjs"),
        (data_xp3, d_entries, "main/Storages.tjs"),
        (data_xp3, d_entries, "sysscn/syslangtext.tjs"),
        (data_xp3, d_entries, "sysscn/multilang.tjs"),
        (steam_xp3, s_entries, "steam.tjs"),
        (steam_xp3, s_entries, "achievement.ini"),
    ]:
        raw, fl = xp3.read_entry(arc, entries[name])
        print(f"\n--- {name} (len={len(raw)}, flags={hex(fl)}) ---")
        if name.endswith(".ini"):
            print("  first bytes:", raw[:40].hex())
        else:
            strs, dec = decrypt_tjs_and_parse(raw, name)
            if strs is not None:
                print(f"  Parsed {len(strs)} strings:")
                for i, s in enumerate(strs):
                    if any(w in s.lower() for w in ("patch", "xp3", "archive", "autopath", "title", "caption", "syslang", "lang", "steam", "sig", "ini", "font", "data", "storages", "config", "override", "afterinit")):
                        print(f"    [{i}] {s!r}")


if __name__ == "__main__":
    main()
