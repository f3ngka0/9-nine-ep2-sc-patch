from __future__ import annotations

import struct
from typing import Tuple
from PIL import Image


def _lzss_decompress(src: bytes, out_len: int, text: bytearray | None = None, r: int = 0) -> tuple[bytes, int]:
    """Kirikiri/M2 TLG5 LZSS decompression with persistent ring buffer and 0xF length extension."""
    if text is None:
        text = bytearray(4096)
    flags = 0
    si = 0
    slen = len(src)
    out = bytearray(out_len)
    oi = 0

    while oi < out_len and si < slen:
        flags >>= 1
        if (flags & 0x100) == 0:
            if si >= slen:
                break
            flags = src[si] | 0xFF00
            si += 1
        if flags & 1:
            if si + 1 >= slen:
                break
            lo = src[si]
            hi = src[si + 1]
            si += 2
            mpos = lo | ((hi & 0x0F) << 8)
            mlen = (hi >> 4) + 3
            if (hi >> 4) == 0xF:
                mlen += src[si]
                si += 1
            for _ in range(mlen):
                if oi >= out_len:
                    break
                c = text[mpos]
                mpos = (mpos + 1) & 0xFFF
                out[oi] = c
                oi += 1
                text[r] = c
                r = (r + 1) & 0xFFF
        else:
            c = src[si]
            si += 1
            out[oi] = c
            oi += 1
            text[r] = c
            r = (r + 1) & 0xFFF
    return bytes(out), r


def _lzss_compress_uncompressed_stream(raw: bytes) -> bytes:
    """Valid TLG5 LZSS stream emitting literal bytes (flag=0 per 8 literals)."""
    out = bytearray()
    n = len(raw)
    i = 0
    while i < n:
        out.append(0x00)
        chunk = raw[i : i + 8]
        out.extend(chunk)
        i += 8
    return bytes(out)


def decode_tlg5(data: bytes) -> Image.Image:
    """Decode TLG5.0\\x00raw\\x1a bytes into a PIL Image ('RGB' or 'RGBA')."""
    if len(data) < 24 or data[:11] != b"TLG5.0\x00raw\x1a":
        raise ValueError(f"Not TLG5.0 raw header: {data[:16]!r}")
    colors = data[11]
    if colors not in (3, 4):
        raise ValueError(f"Unsupported TLG5 colors={colors}")
    w, h, bh = struct.unpack_from("<III", data, 12)
    nb = (h + bh - 1) // bh
    off = 24 + 4 * nb

    # Kirikiri TLG5 channel storage order is [B, G, R (, A)]
    buf = bytearray(w * h * colors)
    prevline = bytearray(w * colors)
    y_base = 0
    text = bytearray(4096)
    r_pos = 0

    for _b in range(nb):
        blk_h = min(bh, h - y_base)
        n_pix_blk = w * blk_h
        planes = []
        for _c in range(colors):
            mark = data[off]
            size = struct.unpack_from("<I", data, off + 1)[0]
            off += 5
            comp = data[off : off + size]
            off += size
            if mark == 0:
                plane, r_pos = _lzss_decompress(comp, n_pix_blk, text, r_pos)
                planes.append(plane)
            elif mark == 1:
                planes.append(comp)
            else:
                raise ValueError(f"Unsupported TLG5 channel mark={mark}")

        for yy in range(blk_h):
            y = y_base + yy
            row_start = yy * w
            dst_off = y * w * colors
            if colors == 4:
                pb, pg, pr, pa = planes
                sb = sg = sr = sa = 0
                for x in range(w):
                    idx = row_start + x
                    b = sb = (sb + pb[idx]) & 0xFF
                    g = sg = (sg + pg[idx]) & 0xFF
                    r = sr = (sr + pr[idx]) & 0xFF
                    a = sa = (sa + pa[idx]) & 0xFF
                    # Undo Kirikiri TLG5 green-centered color correlation: planes = [B-G, G, R-G]
                    b = (b + g) & 0xFF
                    r = (r + g) & 0xFF
                    poff = x * 4
                    rb = (prevline[poff] + b) & 0xFF
                    rg = (prevline[poff + 1] + g) & 0xFF
                    rr = (prevline[poff + 2] + r) & 0xFF
                    ra = (prevline[poff + 3] + a) & 0xFF
                    prevline[poff] = rb
                    prevline[poff + 1] = rg
                    prevline[poff + 2] = rr
                    prevline[poff + 3] = ra
                    # Store RGBA for PIL
                    buf[dst_off + poff] = rr
                    buf[dst_off + poff + 1] = rg
                    buf[dst_off + poff + 2] = rb
                    buf[dst_off + poff + 3] = ra
            else:
                pb, pg, pr = planes
                sb = sg = sr = 0
                for x in range(w):
                    idx = row_start + x
                    b = sb = (sb + pb[idx]) & 0xFF
                    g = sg = (sg + pg[idx]) & 0xFF
                    r = sr = (sr + pr[idx]) & 0xFF
                    b = (b + g) & 0xFF
                    r = (r + g) & 0xFF
                    poff = x * 3
                    rb = (prevline[poff] + b) & 0xFF
                    rg = (prevline[poff + 1] + g) & 0xFF
                    rr = (prevline[poff + 2] + r) & 0xFF
                    prevline[poff] = rb
                    prevline[poff + 1] = rg
                    prevline[poff + 2] = rr
                    buf[dst_off + poff] = rr
                    buf[dst_off + poff + 1] = rg
                    buf[dst_off + poff + 2] = rb
        y_base += blk_h

    mode = "RGBA" if colors == 4 else "RGB"
    return Image.frombytes(mode, (w, h), bytes(buf))


def encode_tlg5(img: Image.Image, block_height: int = 4) -> bytes:
    """Encode a PIL Image into Kirikiri TLG5.0\\x00raw\\x1a bytes."""
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    colors = 4 if img.mode == "RGBA" else 3
    w, h = img.size
    raw = img.tobytes()

    nb = (h + block_height - 1) // block_height
    header = bytearray(b"TLG5.0\x00raw\x1a")
    header.append(colors)
    header.extend(struct.pack("<III", w, h, block_height))
    block_sizes = []
    block_blobs = []

    prevline = bytearray(w * colors)
    y_base = 0
    for _b in range(nb):
        blk_h = min(block_height, h - y_base)
        planes = [bytearray(w * blk_h) for _ in range(colors)]
        for yy in range(blk_h):
            y = y_base + yy
            src_off = y * w * colors
            dst_row = yy * w
            prev_b = prev_g = prev_r = prev_a = 0
            for x in range(w):
                soff = src_off + x * colors
                poff = x * colors
                rr = raw[soff]
                rg = raw[soff + 1]
                rb = raw[soff + 2]
                db = (rb - prevline[poff]) & 0xFF
                dg = (rg - prevline[poff + 1]) & 0xFF
                dr = (rr - prevline[poff + 2]) & 0xFF
                prevline[poff] = rb
                prevline[poff + 1] = rg
                prevline[poff + 2] = rr
                # Apply Kirikiri TLG5 green-centered correlation: [B-G, G, R-G]
                dr_c = (dr - dg) & 0xFF
                dg_c = dg
                db_c = (db - dg) & 0xFF
                planes[0][dst_row + x] = (db_c - prev_b) & 0xFF
                planes[1][dst_row + x] = (dg_c - prev_g) & 0xFF
                planes[2][dst_row + x] = (dr_c - prev_r) & 0xFF
                prev_b, prev_g, prev_r = db_c, dg_c, dr_c
                if colors == 4:
                    ra = raw[soff + 3]
                    da = (ra - prevline[poff + 3]) & 0xFF
                    prevline[poff + 3] = ra
                    planes[3][dst_row + x] = (da - prev_a) & 0xFF
                    prev_a = da

        blk_out = bytearray()
        for c in range(colors):
            comp = _lzss_compress_uncompressed_stream(bytes(planes[c]))
            blk_out.append(0)  # compressed mark=0
            blk_out.extend(struct.pack("<I", len(comp)))
            blk_out.extend(comp)
        block_sizes.append(len(blk_out))
        block_blobs.append(bytes(blk_out))
        y_base += blk_h

    header.extend(struct.pack(f"<{nb}I", *block_sizes))
    return bytes(header) + b"".join(block_blobs)
