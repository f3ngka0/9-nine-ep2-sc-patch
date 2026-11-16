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
    f_diag = os.path.join(APPDATA_GAME, "_sp_arr.txt")

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
        xp3.pack_xp3(src_xp3, {
            "_in_patch.txt": b"hello",
            "b01.txt.scn": b"dummy",
            "syslangtext_cn.ini": b"dummy",
            "main/syslangtext_cn.ini": b"dummy",
        }, compress=False)
        shutil.copy2(src_xp3, patch_dst)

        os.makedirs(video_dir, exist_ok=True)
        env_tjs = r"""(function(){
  var info = [];
  var st = global.Storages;
  var sy = global.System;
  try {
    info.add("=== ORIG searchPath (count=" + st.searchPath.count + ") ===");
    for (var i = 0; i < st.searchPath.count; i++) {
      info.add("  [" + i + "] " + st.searchPath[i]);
    }
  } catch(e) { info.add("e_dump=" + e.message); }

  try {
    // Test addAutoPath & removeAutoPath & insert
    st.addAutoPath(sy.exePath + "video/_sub/");
    info.add("after addAutoPath count=" + st.searchPath.count + " last=" + st.searchPath[st.searchPath.count-1]);
  } catch(e) { info.add("e_add=" + e.message); }

  try {
    // Test removing data.xp3>scn/ and re-adding or searchPath.insert(0, ...)
    var orig = [];
    orig.assign(st.searchPath);
    var p = sy.exePath + "patch.xp3>";
    st.searchPath.insert(0, p + "scn/");
    st.searchPath.insert(0, p + "main/");
    st.searchPath.insert(0, p);
    info.add("after insert(0) len=" + st.searchPath.count + " [0]=" + st.searchPath[0]);
    info.add("getPlacedPath(_in_patch.txt)=" + st.getPlacedPath("_in_patch.txt"));
    info.add("getPlacedPath(b01.txt.scn)=" + st.getPlacedPath("b01.txt.scn"));
    info.add("getPlacedPath(syslangtext_cn.ini)=" + st.getPlacedPath("syslangtext_cn.ini"));
  } catch(e) { info.add("e_ins=" + e.message); }

  try {
    // Wait: what if searchPath returns a COPY? Check st.searchPath[0]!
    info.add("recheck st.searchPath[0]=" + st.searchPath[0]);
    // Try assigning array to st.searchPath or removeAutoPath!
    var arr = [];
    var p = sy.exePath + "patch.xp3>";
    arr.add(p, p + "main/", p + "scn/");
    for (var i = 0; i < st.searchPath.count; i++) arr.add(st.searchPath[i]);
    st.searchPath = arr;
    info.add("after assign st.searchPath[0]=" + st.searchPath[0] + " count=" + st.searchPath.count);
    info.add("ASSIGN getPlacedPath(_in_patch.txt)=" + st.getPlacedPath("_in_patch.txt"));
    info.add("ASSIGN getPlacedPath(b01.txt.scn)=" + st.getPlacedPath("b01.txt.scn"));
    info.add("ASSIGN getPlacedPath(syslangtext_cn.ini)=" + st.getPlacedPath("syslangtext_cn.ini"));
  } catch(e) { info.add("e_ass=" + e.message); }

  try {
    // Test removeAutoPath on archive://data.xp3/scn/ then addAutoPath!
    st.removeAutoPath("archive://data.xp3/scn/");
    info.add("after remove(scn) count=" + st.searchPath.count + " getPlaced(b01)=" + st.getPlacedPath("b01.txt.scn"));
    st.addAutoPath(sy.exePath + "patch.xp3>scn/");
    info.add("after add(patch>scn) getPlaced(b01)=" + st.getPlacedPath("b01.txt.scn"));
  } catch(e) { info.add("e_rem=" + e.message); }

  info.save(sy.dataPath + "_sp_arr.txt");
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
