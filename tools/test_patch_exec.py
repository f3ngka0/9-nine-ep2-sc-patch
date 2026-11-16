import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
PROOF1 = r"d:\code\translate\build\proof_app.txt"
PROOF2 = r"d:\code\translate\build\proof_cfg.txt"
PROOF3 = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo\proof_app.txt")
PROOF4 = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo\proof_cfg.txt")


def kill_game():
    subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
    time.sleep(0.5)


def clear_proofs():
    for p in (PROOF1, PROOF2, PROOF3, PROOF4):
        if os.path.exists(p):
            os.remove(p)


def make_probe_files(tag: str):
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    raw_app, _ = xp3.read_entry(data_xp3, de["AppConfig.tjs"])
    app_txt = xp3.decode_txtobf(raw_app)
    app_probe = app_txt + (
        f'\r\ntry {{ ["{tag}_APP"].save("file://./d/code/translate/build/proof_app.txt"); }} catch(e) {{}}\r\n'
        f'try {{ ["{tag}_APP"].save(System.dataPath + "proof_app.txt"); }} catch(e) {{}}\r\n'
    )
    # Minimal ConfigEx.tjs preserving IsTrial=false
    cfg_probe = (
        'global.IsTrial = false;\r\n'
        f'try {{ ["{tag}_CFG"].save("file://./d/code/translate/build/proof_cfg.txt"); }} catch(e) {{}}\r\n'
        f'try {{ ["{tag}_CFG"].save(System.dataPath + "proof_cfg.txt"); }} catch(e) {{}}\r\n'
    )
    # Test plain UTF-16LE BOM for AppConfig and txtobf for ConfigEx (or encode_txtobf for both)
    return {
        "AppConfig.tjs": app_probe.encode("utf-16"),
        "ConfigEx.tjs": xp3.encode_txtobf(cfg_probe),
        "main/ConfigEx.tjs": xp3.encode_txtobf(cfg_probe),
    }


def launch_and_wait(label: str):
    subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
    for s in range(1, 12):
        time.sleep(1)
        hits = [p for p in (PROOF1, PROOF2, PROOF3, PROOF4) if os.path.exists(p)]
        if hits:
            print(f"[{label}] @{s}s PROOF FOUND:", hits)
            for h in hits:
                with open(h, "rb") as f:
                    print("  content:", f.read()[:120])
            return True
    print(f"[{label}] No proof files created after 11s.")
    return False


def main():
    kill_game()
    clear_proofs()
    patch_dst = os.path.join(GAME_DIR, "patch.xp3")
    patch_src = r"d:\code\translate\build\test_exec_patch.xp3"
    data_dir = os.path.join(GAME_DIR, "data")
    assert not os.path.exists(patch_dst)
    assert not os.path.exists(data_dir)

    try:
        # 1. Test patch.xp3
        xp3.pack_xp3(patch_src, make_probe_files("XP3"), compress=True)
        shutil.copy2(patch_src, patch_dst)
        ok_xp3 = launch_and_wait("XP3")
        kill_game()
        os.remove(patch_dst)
        clear_proofs()

        # 2. Test loose data/
        files = make_probe_files("LOOSE")
        os.makedirs(os.path.join(data_dir, "main"), exist_ok=True)
        for k, v in files.items():
            with open(os.path.join(data_dir, k), "wb") as f:
                f.write(v)
        ok_loose = launch_and_wait("LOOSE")
        print(f"Summary: ok_xp3={ok_xp3}, ok_loose={ok_loose}")
    finally:
        kill_game()
        if os.path.exists(patch_dst):
            os.remove(patch_dst)
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)
        clear_proofs()


if __name__ == "__main__":
    main()
