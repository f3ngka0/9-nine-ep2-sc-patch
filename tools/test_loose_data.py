import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
DATA_DIR = os.path.join(GAME_DIR, "data")


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
    if "nine_sorairo.exe" in get_tasklist_csv("IMAGENAME eq nine_sorairo.exe"):
        subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
        time.sleep(1)
    assert not os.path.exists(DATA_DIR), f"Unexpected {DATA_DIR}"
    assert not os.path.exists(os.path.join(GAME_DIR, "patch.xp3"))

    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    os.makedirs(os.path.join(DATA_DIR, "main"), exist_ok=True)
    try:
        for lang in ("jp", "en", "cn"):
            key = f"main/syslangtext_{lang}.ini"
            raw, _ = xp3.read_entry(data_xp3, de[key])
            txt = xp3.decode_txtobf(raw)
            new_lines = []
            for line in txt.splitlines(keepends=True):
                if line.startswith("TitleCaption"):
                    new_lines.append(f"TitleCaption\t\t9-nine-:Episode2 [LOOSE_{lang.upper()}]\r\n")
                else:
                    new_lines.append(line)
            enc = xp3.encode_txtobf("".join(new_lines))
            with open(os.path.join(DATA_DIR, f"syslangtext_{lang}.ini"), "wb") as f:
                f.write(enc)
            with open(os.path.join(DATA_DIR, "main", f"syslangtext_{lang}.ini"), "wb") as f:
                f.write(enc)
        print("Wrote loose data/*.ini")

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        found = None
        for sec in range(1, 14):
            time.sleep(1)
            out = get_tasklist_csv("IMAGENAME eq nine_sorairo.exe")
            print(f"[{sec:2d}s] {out}")
            if "LOOSE" in out:
                found = out
                break
        print("Result found:", repr(found))
    finally:
        subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
        time.sleep(0.5)
        if os.path.exists(DATA_DIR):
            shutil.rmtree(DATA_DIR)
            print("Cleaned up", DATA_DIR)


if __name__ == "__main__":
    main()
