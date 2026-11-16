"""XP3 v2 archive reader/writer and KiriKiri text obfuscation utilities."""

from __future__ import annotations

import os
import struct
import zlib
from collections import Counter

XP3_MAGIC = b"XP3\r\n \n\x1a\x8bg\x01"
TXTOBF_MAGIC = b"\xfe\xfe\x01\xff\xfe"


def parse_xp3_entries(xp3_path: str) -> dict[str, tuple]:
    """Return mapping {internal_path: (info_tuple, segm_list, adlr_uint32)}."""
    with open(xp3_path, "rb") as f:
        hdr = f.read(40)
        if hdr[:11] != XP3_MAGIC:
            raise ValueError(f"Not an XP3 archive: {xp3_path}")
        idx_off = struct.unpack_from("<Q", hdr, 11)[0]
        if idx_off == 0x17:
            idx_off = struct.unpack_from("<Q", hdr, 32)[0]
        f.seek(idx_off)
        zflag = f.read(1)[0]
        if zflag & 1:
            comp_sz, orig_sz = struct.unpack("<QQ", f.read(16))
            idx = zlib.decompress(f.read(comp_sz))
        else:
            orig_sz = struct.unpack("<Q", f.read(8))[0]
            idx = f.read(orig_sz)

    hnfn_map: dict[int, str] = {}
    entries: dict[str, tuple] = {}
    p = 0
    while p + 12 <= len(idx):
        tag = idx[p : p + 4]
        sz = struct.unpack_from("<Q", idx, p + 4)[0]
        body = idx[p + 12 : p + 12 + sz]
        p += 12 + sz
        if tag == b"hnfn":
            ahash, fn_len = struct.unpack_from("<IH", body, 0)
            hnfn_map[ahash] = body[6 : 6 + fn_len * 2].decode("utf-16-le", errors="replace")
        elif tag == b"File":
            q = 0
            info = None
            segms = []
            adlr = 0
            while q + 12 <= len(body):
                ct = body[q : q + 4]
                csz = struct.unpack_from("<Q", body, q + 4)[0]
                cb = body[q + 12 : q + 12 + csz]
                q += 12 + csz
                if ct == b"info":
                    fl, usz, csz2, fnl = struct.unpack_from("<IQQH", cb, 0)
                    fn = cb[22 : 22 + fnl * 2].decode("utf-16-le", errors="replace")
                    info = (fl, usz, csz2, fn)
                elif ct == b"segm":
                    for off_s in range(0, len(cb), 28):
                        segms.append(struct.unpack_from("<IQQQ", cb, off_s))
                elif ct == b"adlr":
                    adlr = struct.unpack_from("<I", cb, 0)[0]
            if info is None:
                continue
            real_fn = hnfn_map.get(adlr, info[3])
            if real_fn in entries:
                real_fn = f"{real_fn}#1"
            entries[real_fn] = (info, segms, adlr)
    return entries


def read_entry(xp3_path: str, entry: tuple) -> tuple[bytes, int]:
    """Read and decompress segments of an XP3 entry -> (raw_bytes, adlr)."""
    _info, segms, adlr = entry
    out = bytearray()
    with open(xp3_path, "rb") as f:
        for sfl, off, usz, csz in segms:
            f.seek(off)
            chunk = f.read(csz)
            if sfl & 7:
                chunk = zlib.decompress(chunk)
            out.extend(chunk)
    return bytes(out), adlr


def _chunk(tag: bytes, payload: bytes) -> bytes:
    return tag + struct.pack("<Q", len(payload)) + payload


def pack_xp3(out_path: str, files: dict[str, bytes], compress: bool = True) -> None:
    """Write an unencrypted XP3 v2 archive from {archive_path: plain_bytes}."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    # 40-byte XP3 v2 header: magic(11) + info_off(8=0x17) + minor_ver(4=1) + flag(1=0x80) + idx_size(8=0) + tbl_off(8)
    with open(out_path, "wb") as f:
        f.write(b"\x00" * 40)
        index_chunks = bytearray()
        for arc_name, data in sorted(files.items()):
            norm_name = arc_name.replace("\\", "/")
            usz = len(data)
            adlr = zlib.adler32(data) & 0xFFFFFFFF
            off = f.tell()
            if compress and usz > 64:
                cdata = zlib.compress(data, 6)
                if len(cdata) < usz:
                    seg_flag = 1
                    stored = cdata
                else:
                    seg_flag = 0
                    stored = data
            else:
                seg_flag = 0
                stored = data
            f.write(stored)
            csz = len(stored)
            fn_u16 = norm_name.encode("utf-16-le")
            info_b = struct.pack("<IQQH", 0, usz, csz, len(norm_name)) + fn_u16
            segm_b = struct.pack("<IQQQ", seg_flag, off, usz, csz)
            adlr_b = struct.pack("<I", adlr)
            file_body = _chunk(b"info", info_b) + _chunk(b"segm", segm_b) + _chunk(b"adlr", adlr_b)
            index_chunks.extend(_chunk(b"File", file_body))

        tbl_off = f.tell()
        comp_idx = zlib.compress(bytes(index_chunks), 6)
        f.write(struct.pack("<BQQ", 1, len(comp_idx), len(index_chunks)))
        f.write(comp_idx)

        f.seek(0)
        f.write(XP3_MAGIC)
        f.write(struct.pack("<QIBQQ", 0x17, 1, 0x80, 0, tbl_off))


def decode_txtobf(r: bytes) -> str | None:
    """Decode cxdec-encrypted KiriKiri mode-1 obfuscated text (\xfe\xfe\x01\xff\xfe)."""
    if len(r) < 7:
        return None
    votes = Counter([r[0] ^ 0xFE, r[1] ^ 0xFE, r[2] ^ 0x01, r[3] ^ 0xFF, r[4] ^ 0xFE])
    k1, cnt = votes.most_common(1)[0]
    if cnt < 4:
        return None
    tail_evens = [r[i] for i in range(max(6, (len(r) - 400) & ~1), len(r), 2)]
    k2 = Counter(tail_evens).most_common(1)[0][0] if tail_evens else k1
    if len(r) <= 0x680 or k1 == k2:
        sp = len(r)
    else:
        lo_s, hi_s = 0x680, min(len(r), 0x980)
        sp = max(
            range(lo_s, hi_s),
            key=lambda s: sum(1 for i in range(lo_s & ~1, s, 2) if r[i] == k1)
            + sum(1 for i in range((s + 1) & ~1, hi_s, 2) if r[i] == k2),
        )
    out = bytearray()
    for i in range(5, len(r) - ((len(r) - 5) % 2), 2):
        b0 = r[i] ^ (k1 if i < sp else k2)
        b1 = r[i + 1] ^ (k1 if i + 1 < sp else k2)
        c = b0 | (b1 << 8)
        c = ((c & 0x5555) << 1) | ((c & 0xAAAA) >> 1)
        out.extend((c & 0xFF, c >> 8))
    return out.decode("utf-16-le", errors="replace")


def encode_txtobf(text: str) -> bytes:
    """Encode text into KiriKiri mode-1 obfuscated UTF-16LE format."""
    raw = text.encode("utf-16-le")
    out = bytearray(TXTOBF_MAGIC)
    for i in range(0, len(raw), 2):
        c = raw[i] | (raw[i + 1] << 8)
        c = ((c & 0x5555) << 1) | ((c & 0xAAAA) >> 1)
        out.extend((c & 0xFF, c >> 8))
    return bytes(out)
