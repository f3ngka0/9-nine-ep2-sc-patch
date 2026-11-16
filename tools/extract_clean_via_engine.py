import json
import os
import shutil
import struct
import subprocess
import sys
import time
import zlib

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
APPDATA_GAME = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo")
OUT_BASE = r"d:\code\translate\build\extracted"


def tasklist_v():
    return subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq nine_sorairo.exe", "/V", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, errors="replace"
    ).stdout.strip()


def kill_game():
    subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
    for _ in range(20):
        if "nine_sorairo.exe" not in tasklist_v():
            break
        time.sleep(0.3)
    time.sleep(0.5)


def select_entries(xp3_name: str, entries: dict) -> list[str]:
    selected = []
    for k in sorted(entries):
        kl = k.lower()
        if "$$$ this is a protected archive" in kl:
            continue
        if kl.endswith((".ogg", ".amv", ".sli")):
            continue
        if xp3_name == "data.xp3":
            if kl.startswith(("bgm/", "sound/", "rule/", "thum/", "bgimage/")):
                continue
            if kl.startswith("image/particle") or kl.startswith("image/emotion/") or kl.startswith("image/cutin/"):
                continue
        else:
            # From steam.xp3 & adult.xp3 take scripts/scn/uipsd/ui/text/ini/csv/png(non-cg)
            if not kl.endswith((".tjs", ".ks", ".ini", ".csv", ".txt", ".scn", ".pimg", ".func", ".asd")):
                continue
        selected.append(k)
    return selected


def decode_clean_txtobf(raw: bytes) -> str | None:
    """Exact bit-unswap for cxdec-free \xfe\xfe\x01\xff\xfe files (no heuristics)."""
    if len(raw) >= 5 and raw[:5] == b"\xfe\xfe\x01\xff\xfe":
        out = bytearray()
        for i in range(5, len(raw) - ((len(raw) - 5) % 2), 2):
            c = raw[i] | (raw[i + 1] << 8)
            c = ((c & 0x5555) << 1) | ((c & 0xAAAA) >> 1)
            out.extend((c & 0xFF, c >> 8))
        return out.decode("utf-16-le")
    # Also check mode-2 (\xfe\xfe\x02\xff\xfe) just in case
    if raw[:2] == b"\xff\xfe":
        return raw[2:].decode("utf-16-le")
    return None


def main():
    kill_game()
    tasks = []
    for xname in ("data.xp3", "steam.xp3", "adult.xp3"):
        xp = os.path.join(GAME_DIR, xname)
        if not os.path.exists(xp):
            continue
        e = xp3.parse_xp3_entries(xp)
        sel = select_entries(xname, e)
        print(f"{xname}: total={len(e)}, selected={len(sel)}")
        if xname == "adult.xp3":
            print("  adult.xp3 selected:", sel[:30])
        sub = xname.replace(".xp3", "")
        for k in sel:
            src = f"archive://{xname}/{k}"
            # Convert '#' to '_hash_' only if needed? Windows allows '#', so keep exact relpath
            dst = os.path.join(OUT_BASE, sub, k.replace("/", os.sep))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            tasks.append((src, dst.replace("\\", "/")))

    print(f"Total files to extract via game engine: {len(tasks)}")
    manifest_path = os.path.join(OUT_BASE, "_extract_list.txt")
    # Write tab-separated lines in UTF-16LE BOM for Kirikiri Array.load!
    with open(manifest_path, "wb") as f:
        lines = "\r\n".join(f"{src}\t{dst}" for src, dst in tasks) + "\r\n"
        f.write(b"\xff\xfe" + lines.encode("utf-16-le"))

    video_dir = os.path.join(GAME_DIR, "video")
    f_diag = os.path.join(APPDATA_GAME, "_sp_extract.txt")

    def clean():
        kill_game()
        if os.path.exists(f_diag):
            os.remove(f_diag)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        os.makedirs(video_dir, exist_ok=True)
        m_tjs = manifest_path.replace("\\", "/")
        env_tjs = rf"""(function(){{
  var info = [];
  var st = global.Storages;
  var sy = global.System;
  var lines = new global.Array();
  lines.load("{m_tjs}");
  var ok = 0, fail = 0;
  for (var i = 0; i < lines.count; i++) {{
    var row = lines[i];
    if (row == "") continue;
    var parts = row.split("\t");
    if (parts.count < 2) continue;
    var src = parts[0], dst = parts[1];
    try {{
      var oct = st.loadOctet(src);
      st.saveOctet(dst, oct);
      ok++;
    }} catch(e) {{
      fail++;
      if (fail <= 10) info.add("FAIL " + src + ": " + e.message);
    }}
  }}
  info.add("DONE ok=" + ok + " fail=" + fail);
  info.save(sy.dataPath + "_sp_extract.txt");
  return %[];
}})()"""
        with open(os.path.join(video_dir, "envscript.tjs"), "wb") as f:
            f.write(env_tjs.encode("utf-16"))

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        for s in range(1, 30):
            time.sleep(1)
            if os.path.exists(f_diag):
                time.sleep(0.5)
                print(f"@{s}s HIT:")
                with open(f_diag, "rb") as f:
                    print(f.read().decode("utf-16"))
                break
        else:
            print("Timed out! tasklist:", tasklist_v())
    finally:
        clean()

    # Verify extracted assets!
    print("\n=== Verifying extracted assets ===")
    dec_dir = r"d:\code\translate\build\decoded"
    tjs2_bad, psb_bad, png_bad, txt_bad = [], [], [], []
    tjs2_ok, psb_ok, png_ok, txt_ok = 0, 0, 0, 0

    for sub in ("data", "steam", "adult"):
        base = os.path.join(OUT_BASE, sub)
        if not os.path.exists(base):
            continue
        for root_dir, _, files in os.walk(base):
            for fn in files:
                fp = os.path.join(root_dir, fn)
                rel = os.path.relpath(fp, base).replace("\\", "/")
                raw = open(fp, "rb").read()
                rl = rel.lower()
                if rl.endswith((".scn", ".pimg")):
                    if raw[:8] == b"PSB\x00\x03\x00\x00\x00":
                        psb_ok += 1
                    else:
                        psb_bad.append((sub, rel, raw[:8]))
                elif rl.endswith(".png"):
                    # Verify full PNG chunks + zlib!
                    if raw[:8] != b"\x89PNG\r\n\x1a\n":
                        png_bad.append((sub, rel, "sig"))
                        continue
                    pos = 8
                    crc_ok = True
                    z_chunks = []
                    while pos + 12 <= len(raw):
                        clen = struct.unpack_from(">I", raw, pos)[0]
                        ctype = raw[pos+4:pos+8]
                        cdata = raw[pos+8:pos+8+clen]
                        ccrc = struct.unpack_from(">I", raw, pos+8+clen)[0]
                        if (zlib.crc32(ctype + cdata) & 0xFFFFFFFF) != ccrc:
                            crc_ok = False
                            break
                        if ctype == b"IDAT":
                            z_chunks.append(cdata)
                        pos += 12 + clen
                    if not crc_ok or pos != len(raw):
                        png_bad.append((sub, rel, f"crc_ok={crc_ok} pos={pos}/{len(raw)}"))
                    else:
                        try:
                            zlib.decompress(b"".join(z_chunks))
                            png_ok += 1
                        except Exception as e:
                            png_bad.append((sub, rel, f"zlib:{e}"))
                elif raw[:8] == b"TJS2100\x00":
                    tjs2_ok += 1
                elif raw[:5] == b"\xfe\xfe\x01\xff\xfe":
                    try:
                        txt = decode_clean_txtobf(raw)
                        # Write clean UTF-8 copy for easy reading!
                        out_txt = os.path.join(dec_dir, sub, rel.replace("/", os.sep))
                        os.makedirs(os.path.dirname(out_txt), exist_ok=True)
                        with open(out_txt, "w", encoding="utf-8", newline="") as f:
                            f.write(txt)
                        txt_ok += 1
                    except Exception as e:
                        txt_bad.append((sub, rel, str(e)))
                elif rl.endswith((".tjs", ".ks", ".ini", ".csv", ".txt", ".func", ".asd")):
                    # Might be plain UTF-16LE or Shift-JIS or UTF-8
                    txt_ok += 1
                    out_txt = os.path.join(dec_dir, sub, rel.replace("/", os.sep))
                    os.makedirs(os.path.dirname(out_txt), exist_ok=True)
                    if raw[:2] == b"\xff\xfe":
                        t = raw[2:].decode("utf-16-le")
                    elif raw[:3] == b"\xef\xbb\xbf":
                        t = raw[3:].decode("utf-8")
                    else:
                        try:
                            t = raw.decode("utf-8")
                        except UnicodeDecodeError:
                            t = raw.decode("cp932", errors="replace")
                    with open(out_txt, "w", encoding="utf-8", newline="") as f:
                        f.write(t)

    print(f"TJS2: ok={tjs2_ok} bad={tjs2_bad}")
    print(f"PSB : ok={psb_ok} bad={psb_bad}")
    print(f"PNG : ok={png_ok} bad={png_bad}")
    print(f"TXT : ok={txt_ok} bad={txt_bad}")


if __name__ == "__main__":
    main()
