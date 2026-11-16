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
    f_diag = os.path.join(APPDATA_GAME, "_sp_probe3.txt")

    def clean():
        kill_game()
        for f in (patch_dst, f_diag):
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        src_xp3 = r"d:\code\translate\build\p_diag3.xp3"
        xp3.pack_xp3(src_xp3, {
            "_in_patch.txt": b"hello",
            "scn/b01.txt.scn": b"dummy",
            "b01.txt.scn": b"dummy2",
            "main/syslangtext_cn.ini": b"dummy3",
            "syslangtext_cn.ini": b"dummy4",
        }, compress=False)
        shutil.copy2(src_xp3, patch_dst)

        os.makedirs(os.path.join(video_dir, "_patch"), exist_ok=True)
        with open(os.path.join(video_dir, "_patch", "_in_folder.txt"), "w") as f:
            f.write("ok")
        with open(os.path.join(video_dir, "_patch", "b01.txt.scn"), "w") as f:
            f.write("dummy_folder")

        env_tjs = r"""(function(){
  var info = [];
  var st = global.Storages;
  var sy = global.System;

  // Test 1: direct addAutoPath archive://patch.xp3/ vs sy.exePath + "video/_patch/"
  try {
    st.addAutoPath("archive://patch.xp3/");
    st.addAutoPath("archive://patch.xp3/scn/");
    st.addAutoPath("archive://patch.xp3/main/");
    info.add("isEx(archive://patch.xp3/_in_patch.txt)=" + st.isExistentStorage("archive://patch.xp3/_in_patch.txt"));
    info.add("isEx(archive://./patch.xp3/_in_patch.txt)=" + st.isExistentStorage("archive://./patch.xp3/_in_patch.txt"));
    info.add("getPlaced(_in_patch via archive://)=" + st.getPlacedPath("_in_patch.txt"));
  } catch(e) { info.add("e1=" + e.message); }

  try {
    st.addAutoPath(sy.exePath + "video/_patch/");
    info.add("getPlaced(_in_folder.txt)=" + st.getPlacedPath("_in_folder.txt"));
    // Check removing data>scn/ and data>main/ and data>/
    st.removeAutoPath("archive://data.xp3/scn/");
    st.addAutoPath("archive://patch.xp3/scn/");
    st.addAutoPath(sy.exePath + "video/_patch/");
    st.addAutoPath("archive://data.xp3/scn/");
    info.add("b01 after swap=" + st.getPlacedPath("b01.txt.scn"));

    // Why did syslangtext_cn.ini still resolve to data.xp3/main/ earlier? Test removing data.xp3/ too!
    st.removeAutoPath("archive://data.xp3/");
    info.add("ini after rm data.xp3/ =" + st.getPlacedPath("syslangtext_cn.ini"));
    st.removeAutoPath("archive://data.xp3/main/");
    info.add("ini after rm main/ =" + st.getPlacedPath("syslangtext_cn.ini"));
    st.removeAutoPath("archive://data.xp3/main");
    st.removeAutoPath(sy.exePath + "data.xp3>main/");
    st.removeAutoPath(sy.exePath + "data.xp3>");
    info.add("ini after all rm =" + st.getPlacedPath("syslangtext_cn.ini"));
  } catch(e) { info.add("e2=" + e.message); }

  // Also test reading a binary/string from archive://patch.xp3/ vs sy.exePath+"patch.xp3>"
  try {
    var a = new global.Array();
    a.load(sy.exePath + "patch.xp3>_in_patch.txt");
    info.add("Array.load(exePath+patch.xp3>)=count:" + a.count + " [0]:" + a[0]);
  } catch(e) { info.add("e_arr=" + e.message); }

  try {
    // Wait: what does Storages.searchPath(filename, path) do?!
    info.add("searchPath(b01, patch)=" + st.searchPath("b01.txt.scn", sy.exePath + "patch.xp3>;" + sy.exePath + "video/_patch/"));
  } catch(e) { info.add("e_sp=" + e.message); }

  info.save(sy.dataPath + "_sp_probe3.txt");
  return %[];
})()"""
        with open(os.path.join(video_dir, "envscript.tjs"), "wb") as f:
            f.write(env_tjs.encode("utf-16"))

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        for s in range(1, 20):
            time.sleep(1)
            if os.path.exists(f_diag):
                time.sleep(0.3)
                print(f"@{s}s HIT:")
                with open(f_diag, "rb") as f:
                    print(f.read().decode("utf-16"))
                break
        else:
            print("Timed out! tasklist:", tasklist_v())
    finally:
        clean()


if __name__ == "__main__":
    main()
