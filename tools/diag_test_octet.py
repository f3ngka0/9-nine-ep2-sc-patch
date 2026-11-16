import os
import shutil
import subprocess
import sys
import time
import zlib

sys.path.insert(0, r"d:\code\translate\tools")
import xp3

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
APPDATA_GAME = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo")
OUT_DIR = r"d:\code\translate\build\diag_dec"


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
    os.makedirs(OUT_DIR, exist_ok=True)
    video_dir = os.path.join(GAME_DIR, "video")
    f_diag = os.path.join(APPDATA_GAME, "_sp_oct.txt")

    def clean():
        kill_game()
        for f in (f_diag,):
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        os.makedirs(video_dir, exist_ok=True)
        out_tjs_path = OUT_DIR.replace("\\", "/") + "/"
        env_tjs = rf"""(function(){{
  var info = [];
  var st = global.Storages;
  var sy = global.System;
  info.add("loadOctet=" + (typeof st.loadOctet));
  info.add("saveOctet=" + (typeof st.saveOctet));
  info.add("exportFile=" + (typeof st.exportFile));
  try {{
    var files = ["syslangtext_cn.ini", "PreRenderFontEx.tjs", "attention_cn.png", "attention2_cn.png", "b07.txt.scn", "conf_lang.pimg"];
    for (var i = 0; i < files.count; i++) {{
      var fn = files[i];
      var oct = st.loadOctet(fn);
      var dst = "{out_tjs_path}" + fn;
      st.saveOctet(dst, oct);
      info.add("saved " + fn + " len=" + oct.length);
    }}
  }} catch(e) {{ info.add("err=" + e.message); }}
  info.save(sy.dataPath + "_sp_oct.txt");
  return %[];
}})()"""
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

    # Now compare decrypted bytes vs data.xp3 raw encrypted bytes!
    entries = xp3.parse_xp3_entries(DATA_XP3)
    map_names = {
        "syslangtext_cn.ini": "main/syslangtext_cn.ini",
        "PreRenderFontEx.tjs": "sysscn/PreRenderFontEx.tjs",
        "attention_cn.png": "image/attention_cn.png",
        "attention2_cn.png": "image/attention2_cn.png",
        "b07.txt.scn": "scn/b07.txt.scn",
        "conf_lang.pimg": "uipsd/conf_lang.pimg",
    }
    for fn, xp_name in map_names.items():
        p = os.path.join(OUT_DIR, fn)
        if not os.path.exists(p):
            print(fn, "MISSING!")
            continue
        dec = open(p, "rb").read()
        raw, adlr = xp3.read_entry(DATA_XP3, entries[xp_name])
        xor_stream = bytes(a ^ b for a, b in zip(raw, dec))
        from collections import Counter
        top = Counter(xor_stream).most_common(3)
        k1, k2 = xor_stream[1], xor_stream[-1]
        # Find where xor_stream differs from k1 (< split) and k2 (>= split)!
        # First find runs!
        runs = []
        cur_v, cur_s = xor_stream[0], 0
        for i, v in enumerate(xor_stream):
            if v != cur_v:
                runs.append((cur_s, i, cur_v))
                cur_v, cur_s = v, i
        runs.append((cur_s, len(xor_stream), cur_v))
        print(f"FILE {xp_name:30s} adlr={adlr:#010x} len={len(raw):#x} num_runs={len(runs)}")
        for r in runs[:12]:
            print(f"   [{r[0]:#x}..{r[1]:#x}) len={r[1]-r[0]} key={r[2]:#04x}")
        if len(runs) > 12:
            print(f"   ... tail runs: {[(hex(x[0]), hex(x[1]), hex(x[2])) for x in runs[-4:]]}")


if __name__ == "__main__":
    main()
