import os
import shutil
import subprocess
import time

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
SRC_PATCH = r"d:\code\translate\build\test_patch.xp3"
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


def main():
    existing = get_tasklist_csv("IMAGENAME eq nine_sorairo.exe")
    print("Initial nine_sorairo.exe:", repr(existing))
    if "nine_sorairo.exe" in existing:
        subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
        time.sleep(1)

    if os.path.exists(DST_PATCH):
        raise RuntimeError(f"Unexpected existing file: {DST_PATCH}")

    shutil.copy2(SRC_PATCH, DST_PATCH)
    print(f"Copied {SRC_PATCH} -> {DST_PATCH} ({os.path.getsize(DST_PATCH)} bytes)")

    try:
        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        found_title = None
        for sec in range(1, 16):
            time.sleep(1)
            out = get_tasklist_csv("IMAGENAME eq nine_sorairo.exe")
            print(f"[{sec:2d}s] {out}")
            if "[PATCH_TEST]" in out:
                found_title = out
                if sec >= 10:
                    break
        print("Result found_title:", repr(found_title))
    finally:
        subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
        time.sleep(0.5)
        if os.path.exists(DST_PATCH):
            os.remove(DST_PATCH)
            print("Cleaned up", DST_PATCH)


if __name__ == "__main__":
    main()
