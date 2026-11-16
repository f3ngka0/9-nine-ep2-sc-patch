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
    data_xp3 = os.path.join(GAME_DIR, "data.xp3")
    de = xp3.parse_xp3_entries(data_xp3)
    raw_app, _ = xp3.read_entry(data_xp3, de["AppConfig.tjs"])
    app_orig = xp3.decode_txtobf(raw_app)

    video_dir = os.path.join(GAME_DIR, "video")
    patch_dst = os.path.join(GAME_DIR, "patch.xp3")
    f_diag = os.path.join(APPDATA_GAME, "_env_diag.txt")
    f_app = os.path.join(APPDATA_GAME, "_vid_app.txt")

    def clean():
        kill_game()
        for f in (patch_dst, f_diag, f_app):
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        # Put a test patch.xp3 so envscript can inspect whether engine can open patch.xp3>
        src_xp3 = r"d:\code\translate\build\p_diag.xp3"
        xp3.pack_xp3(src_xp3, {"_in_patch.txt": b"hello"}, compress=False)
        shutil.copy2(src_xp3, patch_dst)

        os.makedirs(video_dir, exist_ok=True)
        app_tjs = '["VID_APP"].save(System.dataPath + "_vid_app.txt");\r\n' + app_orig
        with open(os.path.join(video_dir, "AppConfig.tjs"), "wb") as f:
            f.write(app_tjs.encode("utf-16"))

        env_tjs = """(function(){
  var info = [];
  function gp(s) {
    try { return s + " => " + Storages.getFullPath(s); }
    catch(e) { return s + " => ERR:" + e.message; }
  }
  function ex(s) {
    try { return s + " => " + Storages.isExistentStorage(s); }
    catch(e) { return s + " => ERR:" + e.message; }
  }
  info.add("exePath=" + System.exePath);
  info.add("dataPath=" + System.dataPath);
  info.add("inXP3archivePacked=" + (typeof global.inXP3archivePacked != "undefined" ? inXP3archivePacked : "undef"));
  info.add(gp("AppConfig.tjs"));
  info.add(gp("syslangtext_cn.ini"));
  info.add(gp("main/syslangtext_cn.ini"));
  info.add(gp("b01.txt.scn"));
  info.add(gp("conf_lang.pimg"));
  info.add(gp("Override.tjs"));
  info.add(gp("AfterInit.tjs"));
  info.add(ex(System.exePath + "patch.xp3"));
  info.add(ex(System.exePath + "patch.xp3>_in_patch.txt"));
  info.add(gp("_in_patch.txt"));
  info.add("uiLang=" + (typeof global.SystemConfig != "undefined" ? SystemConfig.uiLanguageType : "undef"));
  info.add("msgLang=" + (typeof global.SystemConfig != "undefined" ? SystemConfig.messageLanguageType : "undef"));
  info.add("Title=" + System.title);
  info.save(System.dataPath + "_env_diag.txt");
  return %[];
})()"""
        with open(os.path.join(video_dir, "envscript.tjs"), "wb") as f:
            f.write(env_tjs.encode("utf-16"))

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        for s in range(1, 20):
            time.sleep(1)
            if os.path.exists(f_diag):
                time.sleep(0.5)
                print(f"@{s}s f_app exists={os.path.exists(f_app)}")
                with open(f_diag, "rb") as f:
                    print(f.read().decode("utf-16"))
                break
        else:
            print("Timed out! tasklist:", tasklist_v())
    finally:
        clean()


if __name__ == "__main__":
    main()
