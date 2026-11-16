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
APPDATA_PAL = os.path.expandvars(r"%APPDATA%\PALETTE")


def tasklist_v():
    return subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq nine_sorairo.exe", "/V", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, errors="replace"
    ).stdout.strip()


def kill_game():
    subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
    for _ in range(15):
        if "nine_sorairo.exe" not in tasklist_v():
            break
        time.sleep(0.3)


def run_case(label, check_files, max_sec=10):
    print(f"\n=== {label} ===")
    subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
    last = ""
    for s in range(1, max_sec + 1):
        time.sleep(1)
        out = tasklist_v()
        hits = [p for p in check_files if os.path.exists(p)]
        if out != last:
            print(f"  [{s:2d}s] {out} | hits={hits}")
            last = out
        if hits:
            print(f"  >>> FILE HIT @ {s}s: {hits}")
            for h in hits:
                with open(h, "rb") as f:
                    print("      content:", repr(f.read()[:200]))
            break
        if "9-nine-:Episode2" in out and s >= 5:
            break


def main():
    kill_game()
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    raw_app, _ = xp3.read_entry(data_xp3, de["AppConfig.tjs"])
    app_orig = xp3.decode_txtobf(raw_app)

    patch_dst = os.path.join(GAME_DIR, "patch.xp3")
    patch2_dst = os.path.join(GAME_DIR, "patch2.xp3")
    data_dir = os.path.join(GAME_DIR, "data")
    root_app = os.path.join(GAME_DIR, "AppConfig.tjs")
    probes = [
        os.path.join(APPDATA_GAME, "_p_probe.txt"),
        os.path.join(APPDATA_PAL, "nine_sorairo_p_probe.txt"),
    ]

    def clean():
        kill_game()
        for f in [patch_dst, patch2_dst, root_app] + probes:
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)

    clean()
    try:
        # Prepare probe TJS
        def make_tjs(tag):
            return (
                f'try {{ ["{tag}", System.dataPath].save(System.dataPath + "_p_probe.txt"); }} '
                f'catch(e) {{ System.inform("SAVE_ERR_{tag}: " + e.message); }}\r\n'
                + app_orig
            ).encode("utf-16")

        # 1. patch.xp3
        src = r"d:\code\translate\build\p_test.xp3"
        xp3.pack_xp3(src, {"AppConfig.tjs": make_tjs("XP3")}, compress=False)
        shutil.copy2(src, patch_dst)
        run_case("1_patch_xp3_AppConfig", probes)
        clean()

        # 2. loose data/AppConfig.tjs
        os.makedirs(data_dir, exist_ok=True)
        with open(os.path.join(data_dir, "AppConfig.tjs"), "wb") as f:
            f.write(make_tjs("LOOSE_DATA"))
        run_case("2_loose_data_AppConfig", probes)
        clean()

        # 3. loose GAME_DIR/AppConfig.tjs
        with open(root_app, "wb") as f:
            f.write(make_tjs("LOOSE_ROOT"))
        run_case("3_loose_root_AppConfig", probes)
        clean()

        # 4. patch.xp3 with BOTH plain AppConfig.tjs AND txtobf AppConfig.tjs AND startup.tjs? Wait test patch2.xp3 too
        xp3.pack_xp3(src, {"AppConfig.tjs": xp3.encode_txtobf(
            '["XP3_OBF", System.dataPath].save(System.dataPath + "_p_probe.txt");\r\n' + app_orig
        )}, compress=True)
        shutil.copy2(src, patch2_dst)
        run_case("4_patch2_xp3_txtobf", probes)
        clean()
    finally:
        clean()


if __name__ == "__main__":
    main()
