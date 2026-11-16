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
    time.sleep(0.5)


def main():
    kill_game()
    video_dir = os.path.join(GAME_DIR, "video")
    patch_dst = os.path.join(GAME_DIR, "patch.xp3")
    f_diag = os.path.join(APPDATA_GAME, "_env_diag2.txt")

    def clean():
        kill_game()
        for f in (patch_dst, f_diag):
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        src_xp3 = r"d:\code\translate\build\p_diag.xp3"
        xp3.pack_xp3(src_xp3, {"_in_patch.txt": b"hello"}, compress=False)
        shutil.copy2(src_xp3, patch_dst)

        os.makedirs(video_dir, exist_ok=True)
        env_tjs = r"""(function(){
  var info = [];
  var st = global.Storages;
  var sy = global.System;
  try { info.add("exePath=" + sy.exePath); } catch(e) { info.add("e0=" + e.message); }
  try { info.add("AppConfig=" + st.getFullPath("AppConfig.tjs")); } catch(e) { info.add("e1=" + e.message); }
  try { info.add("syslang_cn=" + st.getFullPath("syslangtext_cn.ini")); } catch(e) { info.add("e2=" + e.message); }
  try { info.add("main_syslang_cn=" + st.getFullPath("main/syslangtext_cn.ini")); } catch(e) { info.add("e3=" + e.message); }
  try { info.add("b01=" + st.getFullPath("b01.txt.scn")); } catch(e) { info.add("e4=" + e.message); }
  try { info.add("conf_lang=" + st.getFullPath("conf_lang.pimg")); } catch(e) { info.add("e5=" + e.message); }
  try { info.add("Override=" + st.getFullPath("Override.tjs")); } catch(e) { info.add("e6=" + e.message); }
  try { info.add("patch_xp3_ex=" + st.isExistentStorage(sy.exePath + "patch.xp3")); } catch(e) { info.add("e7=" + e.message); }
  try { info.add("patch_file_ex=" + st.isExistentStorage(sy.exePath + "patch.xp3>_in_patch.txt")); } catch(e) { info.add("e8=" + e.message); }
  try { info.add("auto_in_patch=" + st.getFullPath("_in_patch.txt")); } catch(e) { info.add("e9=" + e.message); }
  try { info.add("uiLang=" + global.SystemConfig.uiLanguageType); } catch(e) { info.add("e10=" + e.message); }
  try { info.add("msgLang=" + global.SystemConfig.messageLanguageType); } catch(e) { info.add("e11=" + e.message); }
  try { info.add("Title=" + sy.title); } catch(e) { info.add("e12=" + e.message); }
  info.save(sy.dataPath + "_env_diag2.txt");
  return %[];
})()"""
        with open(os.path.join(video_dir, "envscript.tjs"), "wb") as f:
            f.write(env_tjs.encode("utf-16"))

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        for s in range(1, 20):
            time.sleep(1)
            if os.path.exists(f_diag):
                time.sleep(0.3)
                print(f"@{s}s DIAG HIT:")
                with open(f_diag, "rb") as f:
                    print(f.read().decode("utf-16"))
                break
        else:
            print("Timed out! tasklist:", tasklist_v())
    finally:
        clean()


if __name__ == "__main__":
    main()
