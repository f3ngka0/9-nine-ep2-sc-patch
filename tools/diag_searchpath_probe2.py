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
    f_diag = os.path.join(APPDATA_GAME, "_sp_probe2.txt")

    def clean():
        kill_game()
        for f in (patch_dst, f_diag):
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        src_xp3 = r"d:\code\translate\build\p_diag2.xp3"
        xp3.pack_xp3(src_xp3, {
            "_in_patch.txt": b"hello",
            "b01.txt.scn": b"dummy",
            "main/syslangtext_cn.ini": b"dummy",
            "syslangtext_cn.ini": b"dummy",
        }, compress=False)
        shutil.copy2(src_xp3, patch_dst)

        os.makedirs(video_dir, exist_ok=True)
        env_tjs = r"""(function(){
  var info = [];
  var st = global.Storages;
  var sy = global.System;
  try {
    info.add("typeof st.searchPath=" + (typeof st.searchPath));
    info.add("isArray=" + (st.searchPath instanceof "Array"));
    info.add("isDict=" + (st.searchPath instanceof "Dictionary"));
    info.add("isFunc=" + (st.searchPath instanceof "Function"));
    info.add("isProp=" + (st.searchPath instanceof "Property"));
    info.add("typeof st.ProxyStorageMap=" + (typeof st.ProxyStorageMap));
    info.add("typeof global.ProxyStorageMap=" + (typeof global.ProxyStorageMap));
  } catch(e) { info.add("e_type=" + e.message); }

  try {
    // Dump Scripts / Storages members via global.Scripts.getObjectNames or Dictionary? No, in TJS2 try known methods on st:
    var names = [
      "searchPath", "addAutoPath", "removeAutoPath", "getFullPath", "getPlacedPath",
      "isExistentStorage", "chopStorageExt", "extractStorageExt", "extractStorageName",
      "extractStoragePath", "getLocalName", "selectFile", "searchCD",
      "setProxyStorage", "addProxyStorage", "proxyStorageMap", "ProxyStorageMap",
      "clearAutoPath", "pushAutoPath"
    ];
    for (var i = 0; i < names.count; i++) {
      var n = names[i];
      info.add("st." + n + " => " + (typeof st[n]) + " / " + st[n]);
    }
  } catch(e) { info.add("e_names=" + e.message); }

  try {
    var p = sy.exePath + "patch.xp3>";
    info.add("BEFORE b01=" + st.getPlacedPath("b01.txt.scn"));
    info.add("BEFORE ini=" + st.getPlacedPath("syslangtext_cn.ini"));

    // Test 1: removeAutoPath(archive://data.xp3/scn/) etc, addAutoPath(patch.xp3>scn/)!
    st.removeAutoPath("archive://data.xp3/scn/");
    info.add("AFTER remove(data>scn/) b01=" + st.getPlacedPath("b01.txt.scn"));
    st.addAutoPath(p + "scn/");
    info.add("AFTER add(patch>scn/) b01=" + st.getPlacedPath("b01.txt.scn"));
    st.addAutoPath("archive://data.xp3/scn/");
    info.add("AFTER readd(data>scn/) b01=" + st.getPlacedPath("b01.txt.scn"));
    info.add("AFTER add(patch) _in_patch=" + st.getPlacedPath("_in_patch.txt"));
    st.addAutoPath(p);
    info.add("AFTER add(patch>) _in_patch=" + st.getPlacedPath("_in_patch.txt"));
    // Check if removing "archive://data.xp3/" works for subdirs like main/, uipsd/!
    st.removeAutoPath("archive://data.xp3/main/");
    st.addAutoPath(p + "main/");
    st.addAutoPath("archive://data.xp3/main/");
    info.add("AFTER swap(main/) syslangtext_cn.ini=" + st.getPlacedPath("syslangtext_cn.ini"));
    info.add("AFTER swap(main/) main/syslangtext_cn.ini=" + st.getPlacedPath("main/syslangtext_cn.ini"));
  } catch(e) { info.add("e_remadd=" + e.message); }

  info.save(sy.dataPath + "_sp_probe2.txt");
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
