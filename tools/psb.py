"""PSB v3 parser and lossless serializer for Kirikiri2/KrkrZ (.scn and .pimg)."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PsbResource:
    """Reference to an embedded binary chunk in PSB chunk_data."""

    index: int


def _min_signed_bytes(v: int) -> bytes:
    if v == 0:
        return b""
    for w in range(1, 9):
        lo = -(1 << (8 * w - 1))
        hi = (1 << (8 * w - 1)) - 1
        if lo <= v <= hi:
            return v.to_bytes(w, "little", signed=True)
    raise OverflowError(f"Integer out of 64-bit signed range: {v}")


def _min_uint_bytes(v: int) -> bytes:
    if v < 0:
        raise ValueError(f"Expected non-negative int: {v}")
    if v == 0:
        return b"\x00"
    w = (v.bit_length() + 7) // 8
    return v.to_bytes(w, "little", signed=False)


def _read_uint(buf: bytes, pos: int, w: int) -> tuple[int, int]:
    return int.from_bytes(buf[pos : pos + w], "little", signed=False), pos + w


def _read_int(buf: bytes, pos: int, w: int) -> tuple[int, int]:
    return int.from_bytes(buf[pos : pos + w], "little", signed=True), pos + w


def read_int_array(buf: bytes, pos: int) -> tuple[list[int], int]:
    t = buf[pos]
    pos += 1
    if not (0x0D <= t <= 0x10):
        raise ValueError(f"Invalid PSB IntArray count tag {t:#x} at {pos - 1:#x}")
    cnt, pos = _read_uint(buf, pos, t - 0x0C)
    t2 = buf[pos]
    pos += 1
    if not (0x0D <= t2 <= 0x10):
        raise ValueError(f"Invalid PSB IntArray elem tag {t2:#x} at {pos - 1:#x}")
    ew = t2 - 0x0C
    vals = [
        int.from_bytes(buf[pos + i * ew : pos + (i + 1) * ew], "little", signed=False)
        for i in range(cnt)
    ]
    return vals, pos + cnt * ew


def encode_int_array(vals: list[int]) -> bytes:
    cnt = len(vals)
    cnt_b = _min_uint_bytes(cnt)
    out = bytearray([0x0C + len(cnt_b)])
    out.extend(cnt_b)
    if cnt == 0:
        out.append(0x0D)
        return bytes(out)
    mx = max(vals)
    if mx < 0:
        raise ValueError("PSB IntArray cannot contain negative values")
    ew = 1 if mx == 0 else (mx.bit_length() + 7) // 8
    if ew > 4:
        raise ValueError(f"PSB IntArray element too large: {mx}")
    out.append(0x0C + ew)
    for v in vals:
        out.extend(v.to_bytes(ew, "little", signed=False))
    return bytes(out)


def _decode_names(buf: bytes, pos: int) -> tuple[list[str], int]:
    v1, pos = read_int_array(buf, pos)
    v2, pos = read_int_array(buf, pos)
    v3, pos = read_int_array(buf, pos)
    out = [""] * len(v3)
    for leaf in v3:
        name_id = v1[leaf]
        chars = []
        cur = leaf
        while cur > 0:
            parent = v2[cur]
            ch = cur - v1[parent]
            if ch != 0:
                chars.append(ch)
            cur = parent
        out[name_id] = bytes(reversed(chars)).decode("utf-8")
    return out, pos


def _encode_names(names: list[str]) -> bytes:
    """Build PSB v3 B-tree name lookup tables (v1, v2, v3) for sorted/arbitrary names."""
    # Note: for standard PSB compatibility, assign leaf IDs matching `names` order (name_id = index)
    # Build byte trie first, then allocate double-array slots cleanly!
    root: dict[int, Any] = {}
    for nid, s in enumerate(names):
        node = root
        for b in s.encode("utf-8"):
            node = node.setdefault(b, {})
        node[0] = nid  # null terminator -> leaf name_id

    # Allocate base offsets greedily
    v1: list[int] = [0]
    v2: list[int] = [0]
    used: set[int] = {0}
    leaf_indices: list[int] = [-1] * len(names)

    def place_children(parent_idx: int, children: dict[int, Any]) -> None:
        keys = sorted(children.keys())
        if not keys:
            return
        # Find smallest base >= 1 such that (base + k) not in used for all k in keys
        base = 1
        while True:
            if all((base + k) not in used for k in keys):
                break
            base += 1
        v1[parent_idx] = base
        needed_max = base + keys[-1]
        if needed_max >= len(v1):
            grow = needed_max + 1 - len(v1)
            v1.extend([0] * grow)
            v2.extend([0] * grow)
        for k in keys:
            idx = base + k
            used.add(idx)
            v2[idx] = parent_idx
        for k in keys:
            idx = base + k
            sub = children[k]
            if k == 0:
                v1[idx] = sub  # name_id stored at leaf
                leaf_indices[sub] = idx
            else:
                place_children(idx, sub)

    place_children(0, root)
    return encode_int_array(v1) + encode_int_array(v2) + encode_int_array(leaf_indices)


class PsbFile:
    """Parsed PSB v3 container."""

    def __init__(
        self,
        root: Any,
        names: list[str],
        chunks: list[bytes],
        names_raw: bytes | None = None,
        strings_orig: list[str] | None = None,
    ) -> None:
        self.root = root
        self.names = names
        self.chunks = chunks
        self._names_raw = names_raw
        self._strings_orig = strings_orig

    @classmethod
    def parse(cls, data: bytes) -> "PsbFile":
        if len(data) < 0x2C or data[:4] != b"PSB\x00":
            raise ValueError(f"Not a PSB file: {data[:8]!r}")
        ver, enc = struct.unpack_from("<HH", data, 4)
        if ver != 3 or enc != 0:
            raise ValueError(f"Unsupported PSB ver={ver} enc={enc}")
        u3, on, os_, osd, oco, ocl, ocd, oe, cksum = struct.unpack_from("<9I", data, 8)
        if (zlib.adler32(data[8:0x28], 1) & 0xFFFFFFFF) != cksum:
            raise ValueError(f"PSB header adler32 mismatch: {cksum:#x}")

        names, np_ = _decode_names(data, on)
        names_raw = data[on:np_]

        soffs, _ = read_int_array(data, os_)
        strs = []
        for o in soffs:
            start = osd + o
            end = data.find(b"\x00", start)
            if end == -1:
                raise ValueError(f"Unterminated PSB string at {start:#x}")
            strs.append(data[start:end].decode("utf-8"))

        coffs, _ = read_int_array(data, oco)
        clens, _ = read_int_array(data, ocl)
        chunks = [data[ocd + co : ocd + co + cl] for co, cl in zip(coffs, clens)]

        def read_val(pos: int) -> Any:
            t = data[pos]
            pos += 1
            if t == 0x01:
                return None
            if t == 0x02:
                return True
            if t == 0x03:
                return False
            if t == 0x04:
                return 0
            if 0x05 <= t <= 0x0C:
                val, _ = _read_int(data, pos, t - 0x04)
                return val
            if 0x0D <= t <= 0x10:
                val, _ = _read_uint(data, pos, t - 0x0C)
                return val
            if 0x15 <= t <= 0x18:
                idx, _ = _read_uint(data, pos, t - 0x14)
                return strs[idx]
            if 0x19 <= t <= 0x1C:
                idx, _ = _read_uint(data, pos, t - 0x18)
                return PsbResource(idx)
            if t == 0x1D:
                return 0.0
            if t == 0x1E:
                return struct.unpack_from("<f", data, pos)[0]
            if t == 0x1F:
                return struct.unpack_from("<d", data, pos)[0]
            if t == 0x20:
                offs, body = read_int_array(data, pos)
                return [read_val(body + o) for o in offs]
            if t == 0x21:
                keys, p2 = read_int_array(data, pos)
                offs, body = read_int_array(data, p2)
                return {names[k]: read_val(body + o) for k, o in zip(keys, offs)}
            raise ValueError(f"Unsupported PSB value tag {t:#x} at {pos - 1:#x}")

        root = read_val(oe)
        return cls(root=root, names=names, chunks=chunks, names_raw=names_raw, strings_orig=strs)

    def to_bytes(self) -> bytes:
        # Collect all dictionary keys & strings from self.root
        used_names: set[str] = set()
        used_strs: dict[str, int] = {}

        def scan(v: Any) -> None:
            if isinstance(v, dict):
                for k, val in v.items():
                    used_names.add(k)
                    scan(val)
            elif isinstance(v, list):
                for item in v:
                    scan(item)
            elif isinstance(v, str):
                if v not in used_strs:
                    used_strs[v] = len(used_strs)

        scan(self.root)

        # Keep existing names table if all keys fit in self.names, else rebuild trie
        if self._names_raw is not None and used_names.issubset(self.names):
            name_to_id = {n: i for i, n in enumerate(self.names)}
            names_bytes = self._names_raw
        else:
            all_names = sorted(used_names)
            name_to_id = {n: i for i, n in enumerate(all_names)}
            names_bytes = _encode_names(all_names)

        # Preserve original string ordering for unchanged strings (faster + minimal diff),
        # append new strings in encounter order
        str_list: list[str] = []
        str_to_id: dict[str, int] = {}
        if self._strings_orig:
            for s in self._strings_orig:
                if s in used_strs and s not in str_to_id:
                    str_to_id[s] = len(str_list)
                    str_list.append(s)
        for s in used_strs:
            if s not in str_to_id:
                str_to_id[s] = len(str_list)
                str_list.append(s)

        # Build strings data & offsets
        sdata = bytearray()
        soffs = []
        for s in str_list:
            soffs.append(len(sdata))
            sdata.extend(s.encode("utf-8"))
            sdata.append(0)
        strs_bytes = encode_int_array(soffs)

        # Serialize root value tree
        def ser_val(v: Any) -> bytes:
            if v is None:
                return b"\x01"
            if isinstance(v, bool):
                # Note: 0x02/0x03 never appeared in the 88 game PSBs, ints are used for visible/flags
                return b"\x02" if v else b"\x03"
            if isinstance(v, int):
                if v == 0:
                    return b"\x04"
                ib = _min_signed_bytes(v)
                return bytes([0x04 + len(ib)]) + ib
            if isinstance(v, float):
                # Preserve -0.0 or 0.0 -> check struct sign bit
                if v == 0.0 and struct.pack("<d", v) == b"\x00" * 8:
                    return b"\x1d"
                return b"\x1f" + struct.pack("<d", v)
            if isinstance(v, str):
                idx = str_to_id[v]
                ib = _min_uint_bytes(idx)
                return bytes([0x14 + len(ib)]) + ib
            if isinstance(v, PsbResource):
                ib = _min_uint_bytes(v.index)
                return bytes([0x18 + len(ib)]) + ib
            if isinstance(v, list):
                encoded_items = [ser_val(x) for x in v]
                offs = []
                body = bytearray()
                for item_b in encoded_items:
                    offs.append(len(body))
                    body.extend(item_b)
                return b"\x20" + encode_int_array(offs) + bytes(body)
            if isinstance(v, dict):
                # Sort keys by name_id (standard PSB dictionary invariant for binary search!)
                items = sorted(((name_to_id[k], val) for k, val in v.items()), key=lambda kv: kv[0])
                keys = [k for k, _ in items]
                offs = []
                body = bytearray()
                for _, val in items:
                    offs.append(len(body))
                    body.extend(ser_val(val))
                return b"\x21" + encode_int_array(keys) + encode_int_array(offs) + bytes(body)
            raise TypeError(f"Unsupported PSB value type: {type(v)}")

        entries_bytes = ser_val(self.root)

        # Chunks (4-byte aligned offsets)
        coffs = []
        clens = []
        cdata = bytearray()
        for ch in self.chunks:
            while len(cdata) % 4 != 0:
                cdata.append(0)
            coffs.append(len(cdata))
            clens.append(len(ch))
            cdata.extend(ch)
        coffs_bytes = encode_int_array(coffs)
        clens_bytes = encode_int_array(clens)

        # Assemble sections in exact v3 order: names -> entries -> strings -> sdata -> coffs -> clens -> cdata
        hdr_len = 0x2C
        off_names = hdr_len
        off_entries = off_names + len(names_bytes)
        off_strs = off_entries + len(entries_bytes)
        off_sdata = off_strs + len(strs_bytes)
        off_coffs = off_sdata + len(sdata)
        off_clens = off_coffs + len(coffs_bytes)
        off_cdata = off_clens + len(clens_bytes)

        hdr_body = struct.pack(
            "<8I",
            hdr_len,
            off_names,
            off_strs,
            off_sdata,
            off_coffs,
            off_clens,
            off_cdata,
            off_entries,
        )
        cksum = zlib.adler32(hdr_body, 1) & 0xFFFFFFFF
        header = b"PSB\x00" + struct.pack("<HH", 3, 0) + hdr_body + struct.pack("<I", cksum)
        return (
            header
            + names_bytes
            + entries_bytes
            + strs_bytes
            + bytes(sdata)
            + coffs_bytes
            + clens_bytes
            + bytes(cdata)
        )
