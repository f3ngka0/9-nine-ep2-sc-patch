import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
APPDATA_GAME = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo")


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
    time.sleep(1.0)


def make_env_tjs(tag: str) -> bytes:
    code = (
        f'(function(){{ '
        f'["{tag}", System.dataPath].save(System.dataPath + "_env_{tag}.txt"); '
        f'return %[]; }})()'
    )
    return code.encode("utf-16")


def wait_run(label, watch_files, max_sec=20):
    print(f"\n=== {label} ===")
    subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
    last = ""
    seen_win_at = None
    for s in range(1, max_sec + 1):
        time.sleep(1)
        out = tasklist_v()
        hits = [p for p in watch_files if os.path.exists(p)]
        if out != last:
            print(f"  [{s:2d}s] {out} | hits={hits}")
            last = out
        if hits:
            for h in hits:
                with open(h, "rb") as f:
                    print(f"  >>> HIT {h}: {f.read(300)!r}")
            return True
        if "9-nine-" in out and seen_win_at is None:
            seen_win_at = s
        if seen_win_at is not None and s >= seen_win_at + 4:
            print(f"  (window settled at +{s - seen_win_at}s, no hit)")
            return False
    print(f"  (ended {max_sec}s, last={last})")
    return False


def main():
    kill_game()
    patch_dst = os.path.join(GAME_DIR, "patch.xp3")
    pa_dst = os.path.join(GAME_DIR, "patch_adult.xp3")
    video_dir = os.path.join(GAME_DIR, "video")
    data_dir = os.path.join(GAME_DIR, "data")
    root_env = os.path.join(GAME_DIR, "envscript.tjs")

    tags = ["XP3", "PA", "VIDEO", "DATA", "ROOT"]
    watch = [os.path.join(APPDATA_GAME, f"_env_{t}.txt") for t in tags]

    def clean():
        kill_game()
        for f in [patch_dst, pa_dst, root_env] + watch:
            if os.path.exists(f):
                os.remove(f)
        for d in (video_dir, data_dir):
            if os.path.exists(d):
                shutil.rmtree(d)

    clean()
    try:
        s1 = r"d:\code\translate\build\p_env1.xp3"
        s2 = r"d:\code\translate\build\p_env2.xp3"
        xp3.pack_xp3(s1, {"envscript.tjs": make_env_tjs("XP3")}, compress=False)
        xp3.pack_xp3(s2, {"envscript.tjs": make_env_tjs("PA")}, compress=False)
        shutil.copy2(s1, patch_dst)
        shutil.copy2(s2, pa_dst)
        wait_run("Case1_patch_and_patch_adult_envscript", watch)
        clean()

        os.makedirs(video_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(video_dir, "envscript.tjs"), "wb") as f:
            f.write(make_env_tjs("VIDEO"))
        with open(os.path.join(data_dir, "envscript.tjs"), "wb") as f:
            f.write(make_env_tjs("DATA"))
        with open(root_env, "wb") as f:
            f.write(make_env_tjs("ROOT"))
        wait_run("Case2_loose_video_data_root_envscript", watch)
        clean()
    finally:
        clean()


if __name__ == "__main__":
    main()
