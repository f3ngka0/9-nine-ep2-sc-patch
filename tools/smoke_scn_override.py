import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"d:\code\translate\tools")
import psb

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
APPDATA_GAME = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo")
SCN_SRC = r"d:\code\translate\build\extracted\data\scn\b04.txt.scn"


def kill_game():
    subprocess.run(["taskkill", "/F", "/IM", "nine_sorairo.exe"], capture_output=True)
    for _ in range(20):
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq nine_sorairo.exe", "/NH"],
            capture_output=True, text=True, errors="replace"
        ).stdout
        if "nine_sorairo.exe" not in out:
            break
        time.sleep(0.3)
    time.sleep(0.4)


def main():
    kill_game()
    video_dir = os.path.join(GAME_DIR, "video")
    f_diag = os.path.join(APPDATA_GAME, "_sp_scn_smoke.txt")

    def clean():
        kill_game()
        if os.path.exists(f_diag):
            os.remove(f_diag)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        raw = open(SCN_SRC, "rb").read()
        p = psb.PsbFile.parse(raw)
        test_disp = r"【冒烟测试】昨天已经把九条做的菜吃光了，\n早上只有吐司，中午则是便利商店便当，\n凑合着吃了顿寒酸至极的饭。"
        test_plain = "【冒烟测试】昨天已经把九条做的菜吃光了，早上只有吐司，中午则是便利商店便当，凑合着吃了顿寒酸至极的饭。"
        cn_entry = p.root["scenes"][0]["texts"][0][2][2]
        cn_entry[1] = test_disp
        cn_entry[2] = test_plain
        cn_entry[3] = test_plain
        p.root["scenes"][0]["title"] = "【测试标题】第四天"
        p._names_raw = None
        patched_bytes = p.to_bytes()

        patch_scn = os.path.join(video_dir, "_patch", "scn")
        os.makedirs(patch_scn, exist_ok=True)
        with open(os.path.join(patch_scn, "b04.txt.scn"), "wb") as f:
            f.write(patched_bytes)

        env_tjs = r"""(function(){
  var st = global.Storages;
  var sy = global.System;
  st.addAutoPath(sy.exePath + "video/_patch/");
  st.addAutoPath(sy.exePath + "video/_patch/scn/");

  var info = [];
  info.add("placed_scn=" + st.getPlacedPath("scn/b04.txt.scn"));
  info.add("placed_bare=" + st.getPlacedPath("b04.txt.scn"));
  info.add("placed_patch_scn=" + st.getPlacedPath(sy.exePath + "video/_patch/scn/b04.txt.scn"));
  info.add("placed_uipsd=" + st.getPlacedPath("conf_lang.pimg"));
  info.add("placed_uipsd_sub=" + st.getPlacedPath("uipsd/conf_lang.pimg"));
  info.add("placed_font=" + st.getPlacedPath("embfontlist.tjs"));
  info.add("placed_btn_cn=" + st.getPlacedPath("btn_conf_cn.pimg"));
  try {
    if (typeof global.PSBFile == "undefined") {
      global.Plugins.link("psbfile.dll");
    }
    var psb = new global.PSBFile();
    var ok = psb.load("b04.txt.scn");
    info.add("psb.load_bare=" + ok);
    var r = psb.root;
    info.add("root.name=" + r.name);
    var s0 = r.scenes[0];
    info.add("s0.title=" + s0.title);
    info.add("s0.texts[0][2][2][1]=" + s0.texts[0][2][2][1]);
    info.add("s0.texts[0][2][2][2]=" + s0.texts[0][2][2][2]);
  } catch (e) {
    info.add("EXC_psb=" + e.message);
  }
  try {
    var sd = new global.StorageData("b04");
    info.add("sd.typeof=" + (typeof sd));
    var t0 = sd.getText(0, 2);
    info.add("sd.getText(0,2)=" + (typeof t0) + " disp=" + (t0 !== void ? t0.disp : "void"));
  } catch (e) {
    info.add("EXC_sd1=" + e.message);
  }
  try {
    var sd2 = new global.StorageData("b04.txt.scn");
    var t2 = sd2.getText(0, 2);
    info.add("sd2.getText(0,2)=" + (typeof t2) + " disp=" + (t2 !== void ? t2.disp : "void"));
  } catch (e) {
    info.add("EXC_sd2=" + e.message);
  }
  info.save(sy.dataPath + "_sp_scn_smoke.txt");
  return %[];
})()"""
        with open(os.path.join(video_dir, "envscript.tjs"), "wb") as f:
            f.write(env_tjs.encode("utf-16"))

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        for s in range(1, 20):
            time.sleep(1)
            if os.path.exists(f_diag):
                time.sleep(0.3)
                with open(f_diag, "rb") as f:
                    print(f.read().decode("utf-16"))
                break
        else:
            print("TIMEOUT waiting for _sp_scn_smoke.txt")
    finally:
        clean()


if __name__ == "__main__":
    main()
