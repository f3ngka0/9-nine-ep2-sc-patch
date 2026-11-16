import os
import re
import struct

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")

def parse_pe(data):
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    assert data[pe_off:pe_off+4] == b"PE\x00\x00"
    mach, nsec = struct.unpack_from("<HH", data, pe_off + 4)
    opt_sz = struct.unpack_from("<H", data, pe_off + 20)[0]
    opt_off = pe_off + 24
    img_base = struct.unpack_from("<I", data, opt_off + 28)[0]
    sec_off = opt_off + opt_sz
    secs = []
    for i in range(nsec):
        o = sec_off + i * 40
        name = data[o:o+8].rstrip(b"\x00").decode("ascii", errors="replace")
        vsz, va, rsz, ra, _, _, _, _, ch = struct.unpack_from("<9I", data, o + 8)
        secs.append((name, va, vsz, ra, rsz, ch))
    return img_base, secs, pe_off

def rva_to_off(rva, secs):
    for name, va, vsz, ra, rsz, ch in secs:
        if va <= rva < va + max(vsz, rsz):
            return ra + (rva - va)
    return None

def off_to_va(off, secs, img_base):
    for name, va, vsz, ra, rsz, ch in secs:
        if ra <= off < ra + rsz:
            return img_base + va + (off - ra)
    return None

def main():
    for pkg in ("capstone", "pefile"):
        try:
            __import__(pkg)
            print(f"pkg {pkg}: INSTALLED")
        except ImportError:
            print(f"pkg {pkg}: missing")

    with open(EXE_PATH, "rb") as f:
        data = f.read()
    img_base, secs, pe_off = parse_pe(data)
    print(f"ImageBase={hex(img_base)}, sections={[(s[0], hex(s[1]), hex(s[2]), hex(s[3]), hex(s[4]), hex(s[5])) for s in secs]}")

    # Check imports
    opt_off = pe_off + 24
    imp_rva, imp_sz = struct.unpack_from("<II", data, opt_off + 96 + 8)
    imp_off = rva_to_off(imp_rva, secs)
    print("\n=== Imports ===")
    while True:
        orig_first, ts, fwd, name_rva, first_thunk = struct.unpack_from("<5I", data, imp_off)
        if not name_rva:
            break
        noff = rva_to_off(name_rva, secs)
        end = data.find(b"\x00", noff)
        dll = data[noff:end].decode("ascii", errors="replace")
        print(" ", dll)
        imp_off += 20

    # Context around forcedataxp3 and TVPSystemSecurityOptions and TVPSetXP3ArchiveExtractionFilter etc.
    print("\n=== Interesting strings + xrefs ===")
    needles = [
        b"forcedataxp3",
        b"TVPSystemSecurityOptions",
        b"a\x00d\x00d\x00A\x00u\x00t\x00o\x00P\x00a\x00t\x00h\x00",
        b"g\x00e\x00t\x00P\x00l\x00a\x00c\x00e\x00d\x00P\x00a\x00t\x00h\x00",
        b"s\x00t\x00a\x00r\x00t\x00u\x00p\x00.\x00t\x00j\x00s\x00",
        b"d\x00a\x00t\x00a\x00.\x00x\x00p\x003\x00",
        b"d\x00a\x00t\x00a\x00.\x00e\x00x\x00e\x00",
        b".\x00x\x00p\x003\x00",
        b".\x00s\x00i\x00g\x00",
        b"TVPRebuildAutoPathTable",
    ]
    for nd in needles:
        idx = 0
        hits = []
        while True:
            pos = data.find(nd, idx)
            if pos < 0:
                break
            va = off_to_va(pos, secs, img_base)
            hits.append((pos, hex(va) if va else None))
            idx = pos + 1
        print(f"  {nd[:30]!r}: {hits[:5]}")
        # Find 4-byte LE VA references in .text/.bind/.rdata
        for pos, va_hex in hits[:3]:
            if va_hex:
                va_bytes = struct.pack("<I", int(va_hex, 16))
                xrefs = []
                xi = 0
                while True:
                    xp = data.find(va_bytes, xi)
                    if xp < 0:
                        break
                    xsec = next((s[0] for s in secs if s[3] <= xp < s[3] + s[4]), "?")
                    xrefs.append((xsec, hex(off_to_va(xp, secs, img_base) or xp)))
                    xi = xp + 1
                print(f"    VA {va_hex} xrefs: {xrefs[:8]}")

    # Dump nearby strings around forcedataxp3
    fp = data.find(b"forcedataxp3")
    if fp >= 0:
        print("\n=== Context around forcedataxp3 ===")
        print(repr(data[fp-120:fp+240]))

    # Dump exported functions of nine_sorairo.exe (plugins use GetProcAddress on TVP*)
    exp_rva, exp_sz = struct.unpack_from("<II", data, opt_off + 96)
    if exp_rva:
        eoff = rva_to_off(exp_rva, secs)
        if eoff:
            num_names, = struct.unpack_from("<I", data, eoff + 24)
            names_rva, = struct.unpack_from("<I", data, eoff + 32)
            noff = rva_to_off(names_rva, secs)
            print(f"\n=== Exports count={num_names} ===")
            matches = []
            for i in range(num_names):
                srva = struct.unpack_from("<I", data, noff + i * 4)[0]
                so = rva_to_off(srva, secs)
                if so:
                    end = data.find(b"\x00", so)
                    nm = data[so:end].decode("ascii", errors="replace")
                    if any(k in nm.lower() for k in ("xp3", "storage", "auto", "archive", "stream", "extract", "sig", "plugin")):
                        matches.append(nm)
            print("  Filtered exports:", matches)

if __name__ == "__main__":
    main()
