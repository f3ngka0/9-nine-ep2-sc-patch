import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
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
    f_diag = os.path.join(APPDATA_GAME, "_sp_probe6.txt")

    def clean():
        kill_game()
        if os.path.exists(f_diag):
            os.remove(f_diag)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        entries = xp3.parse_xp3_entries(DATA_XP3)
        raw_en, _ = xp3.read_entry(DATA_XP3, entries["main/syslangtext_en.ini"])
        ini_en = xp3.decode_txtobf(raw_en)
        # Replace TitleCaption line in en temporarily to verify live Win32 window title (current save uiLang=1)
        lines_en = []
        for ln in ini_en.splitlines():
            if ln.startswith("TitleCaption\t"):
                lines_en.append("TitleCaption\t\t9-nine-：Episode 2【测试】")
            else:
                lines_en.append(ln)
        mod_en = "\r\n".join(lines_en) + "\r\n"

        patch_main = os.path.join(video_dir, "_patch", "main")
        os.makedirs(patch_main, exist_ok=True)
        # Write plain UTF-16LE with BOM (verify Krkr Array.load loads plain UTF-16LE natively!)
        with open(os.path.join(patch_main, "syslangtext_en.ini"), "wb") as f:
            f.write(b"\xff\xfe" + mod_en.encode("utf-16-le"))

        # Check where LoadSysLangText / addAfterInitCallback run
        env_tjs = r"""(function(){
  var st = global.Storages;
  var sy = global.System;
  st.addAutoPath(sy.exePath + "video/_patch/");
  st.addAutoPath(sy.exePath + "video/_patch/main/");

  var info = [];
  var st = global.Storages;
  var sy = global.System;
  info.add("At envscript: placed ini_en=" + st.getPlacedPath("syslangtext_en.ini"));
  try {
    info.add("BEFORE TitleCaption.en=" + global.SystemLanguageText["TitleCaption"]["en"]);
    info.add("BEFORE EmbeddedFontList=" + (typeof global.SystemConfig.EmbeddedFontList));
    (global.Dictionary.clear incontextof global.SystemLanguageText)();
    global.LoadSysLangText();
    info.add("AFTER reload TitleCaption.en=" + global.SystemLanguageText["TitleCaption"]["en"]);
    info.add("System.title=" + sy.title + " kag.caption=" + global.kag.caption);
    if (typeof global.ResetAllMenuLangText == "Object") global.ResetAllMenuLangText(global.kag);
    if (typeof global.UpdateMultiLangTitleCaption == "Object") global.UpdateMultiLangTitleCaption(global.kag);
    info.add("AFTER UpdateCaption System.title=" + sy.title + " kag.caption=" + global.kag.caption);
  } catch(e) { info.add("At envscript: e=" + e.message); }

  info.save(sy.dataPath + "_sp_probe6.txt");
  return %[];
})()"""
        with open(os.path.join(video_dir, "envscript.tjs"), "wb") as f:
            f.write(env_tjs.encode("utf-16"))

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        for s in range(1, 20):
            time.sleep(1)
            tv = tasklist_v()
            if "nine_sorairo.exe" in tv and ("测试" in tv or s >= 5):
                print(f"@{s}s tasklist /V: {tv}")
                if os.path.exists(f_diag):
                    with open(f_diag, "rb") as f:
                        print("DIAG:", f.read().decode("utf-16"))
                break
        else:
            print("Timed out! tasklist:", tasklist_v())
            if os.path.exists(f_diag):
                with open(f_diag, "rb") as f:
                    print("DIAG:", f.read().decode("utf-16"))
    finally:
        clean()


if __name__ == "__main__":
    main()
