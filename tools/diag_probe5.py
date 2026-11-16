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
    patch_zh_xp3 = os.path.join(GAME_DIR, "patch_zh.xp3")
    f_diag = os.path.join(APPDATA_GAME, "_sp_probe5.txt")

    def clean():
        kill_game()
        for f in (patch_zh_xp3, f_diag):
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        src_xp3 = r"d:\code\translate\build\p_diag5.xp3"
        xp3.pack_xp3(src_xp3, {
            "_in_zh.txt": b"hello",
            "scn/b01.txt.scn": b"dummy_xp3",
            "b01.txt.scn": b"dummy_xp3_root",
        }, compress=False)
        shutil.copy2(src_xp3, patch_zh_xp3)

        os.makedirs(os.path.join(video_dir, "_patch", "scn"), exist_ok=True)
        with open(os.path.join(video_dir, "_patch", "scn", "b01.txt.scn"), "w") as f:
            f.write("dummy_folder")

        env_tjs = r"""(function(){
  var info = [];
  var st = global.Storages;
  var sy = global.System;
  var p = sy.dataPath + "_sp_probe5.txt";

  info.add("steam.tjs placed=" + st.getPlacedPath("steam.tjs"));
  info.add("patch.xp3 in archive_exists=" + global.archive_exists["patch"]);

  // Test 1: patch_zh.xp3> BEFORE removing anything
  st.addAutoPath(sy.exePath + "patch_zh.xp3>");
  st.addAutoPath(sy.exePath + "patch_zh.xp3>scn/");
  info.add("after add patch_zh.xp3>: _in_zh=" + st.getPlacedPath("_in_zh.txt"));
  info.add("after add patch_zh.xp3>scn/: b01=" + st.getPlacedPath("b01.txt.scn"));
  info.add("isEx(patch_zh.xp3>_in_zh)=" + st.isExistentStorage(sy.exePath + "patch_zh.xp3>_in_zh.txt"));

  // Test 2: video/_patch/scn/ WITHOUT removeAutoPath!
  st.addAutoPath(sy.exePath + "video/_patch/scn/");
  info.add("after add _patch/scn/ (NO rm): b01=" + st.getPlacedPath("b01.txt.scn"));

  // Test 3: state of SystemLanguageText & TitleCaption test!
  try {
    info.add("uiLang=" + global.SystemConfig.uiLanguageType);
    info.add("LoadSysLangText=" + (typeof global.LoadSysLangText));
    info.add("LoadEmbeddedFontList=" + (typeof global.LoadEmbeddedFontList));
    info.add("EmbeddedFontList.count=" + global.EmbeddedFontList.count);
    info.add("old cn TitleCaption=" + global.SystemLanguageText["!system"]["TitleCaption"]["cn"]);
    global.SystemLanguageText["!system"]["TitleCaption"]["cn"] = "9-nine-:Episode2 [SC-TEST]";
    global.SystemLanguageText["!system"]["TitleCaption"]["en"] = "9-nine-:Episode2 [SC-TEST]";
    global.SystemLanguageText["!system"]["TitleCaption"]["jp"] = "9-nine-:Episode2 [SC-TEST]";
  } catch(e) { info.add("e_slt=" + e.message); }

  info.save(p);
  return %[];
})()"""
        with open(os.path.join(video_dir, "envscript.tjs"), "wb") as f:
            f.write(env_tjs.encode("utf-16"))

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        for s in range(1, 20):
            time.sleep(1)
            if os.path.exists(f_diag):
                time.sleep(1.5) # let AfterInit + window caption settle
                print(f"@{s}s HIT:")
                with open(f_diag, "rb") as f:
                    print(f.read().decode("utf-16"))
                print("LIVE tasklist /V:", tasklist_v())
                break
        else:
            print("Timed out! tasklist:", tasklist_v())
    finally:
        clean()


if __name__ == "__main__":
    main()
