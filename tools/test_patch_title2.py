import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
PATCH_BUILD = r"d:\code\translate\build\test_patch2.xp3"
DST_PATCH = os.path.join(GAME_DIR, "patch.xp3")


def get_tasklist_csv(filter_expr: str) -> str:
    res = subprocess.run(
        ["tasklist", "/FI", filter_expr, "/V", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return res.stdout.strip()


def build_test_patch2():
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    files = {}
    for lang in ("jp", "en", "cn"):
        key = f"main/syslangtext_{lang}.ini"
        raw, _ = xp3.read_entry(data_xp3, de[key])
        txt = xp3.decode_txtobf(raw)
        assert txt is not None, key
        new_lines = []
        for line in txt.splitlines(keepends=True):
            if line.startswith("TitleCaption"):
                new_lines.append(f"TitleCaption\t\t9-nine-:Episode2 [PATCH2_{lang.upper()}]\r\n")
            else:
                new_lines.append(line)
        enc = xp3.encode_txtobf("".join(new_lines))
        # Put at BOTH root and main/!
        files[f"syslangtext_{lang}.ini"] = enc
        files[key] = enc
    xp3.pack_xp3(PATCH_BUILD, files, compress=True)
    print(f"Built {PATCH_BUILD}: {os.path.getsize(PATCH_BUILD)} bytes, keys={list(files.keys())}")


def main():
    build_test_patch2()
    if "nine_sorairo.exe" in get_tasklist_csv("IMAGENAME eq nine_sorairo.exe"):
        subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
        time.sleep(1)
    if os.path.exists(DST_PATCH):
        raise RuntimeError(f"Unexpected existing file: {DST_PATCH}")

    shutil.copy2(PATCH_BUILD, DST_PATCH)
    try:
        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        found = None
        for sec in range(1, 14):
            time.sleep(1)
            out = get_tasklist_csv("IMAGENAME eq nine_sorairo.exe")
            print(f"[{sec:2d}s] {out}")
            if "PATCH2" in out:
                found = out
                break
        print("Result found:", repr(found))
    finally:
        subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
        time.sleep(0.5)
        if os.path.exists(DST_PATCH):
            os.remove(DST_PATCH)
            print("Cleaned up", DST_PATCH)


if __name__ == "__main__":
    main()
