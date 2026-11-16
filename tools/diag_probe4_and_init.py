import os
import shutil
import subprocess
import sys
import time
import zlib

sys.path.insert(0, r"d:\code\translate\tools")
import xp3
import diag_init_full_trace as dt
from diag_find_pkutil_and_auto import safe_decrypt_tjs2

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
DATA_XP3 = os.path.join(GAME_DIR, "data.xp3")
APPDATA_GAME = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo")


def inspect_init_funcs():
    de = xp3.parse_xp3_entries(DATA_XP3)
    raw, _ = xp3.read_entry(DATA_XP3, de["system/Initialize.tjs"])
    dec = safe_decrypt_tjs2(raw)
    objs = dt.parse_tjs2_objs(dec)
    print(f"Initialize.tjs objs={len(objs)}")
    for idx in range(1, min(15, len(objs))):
        _, oname, code, consts = objs[idx]
        print(f"\n-- Init OBJ[{idx}] {oname} consts={consts} --")
        print(dt.disasm_tjs2(code, consts))

    # Also test scn/*.txt.scn & uipsd/*.pimg MDF headers!
    print("\n=== Checking scn & uipsd PSB/MDF headers ===")
    bad_mdf = []
    good_mdf = 0
    for k in sorted(de):
        if not (k.endswith(".scn") or k.endswith(".pimg")):
            continue
        r, adlr = xp3.read_entry(DATA_XP3, de[k])
        # Test guessing k1 from b"MDF\x00" and k2 from zlib / tail
        votes = [r[i] ^ b"MDF\x00"[i] for i in range(4)]
        k1 = max(set(votes), key=votes.count)
        if votes.count(k1) < 3:
            bad_mdf.append((k, "magic", r[:8].hex()))
            continue
        # Test XOR with k1 on first 16 bytes -> if dec[0:4]==MDF\x00, try simple split vs zlib decompress!
        # Find k2 where last bytes or zlib header (0x78) matches
        # Wait: MDF has uint32 uncomp_size at [4:8], zlib header (78 9c or 78 da or 78 01) at [8:10]
        # Let's see how many match votes==4
        if votes.count(k1) < 4:
            bad_mdf.append((k, f"partial_magic(cnt={votes.count(k1)})", bytes(b^k1 for b in r[:8]).hex()))
        else:
            good_mdf += 1
    print(f"MDF magic: good={good_mdf}, bad={len(bad_mdf)}: {bad_mdf[:10]}")


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


def test_probe4():
    kill_game()
    video_dir = os.path.join(GAME_DIR, "video")
    patch_dst = os.path.join(GAME_DIR, "patch.xp3")
    f_diag = os.path.join(APPDATA_GAME, "_sp_probe4.txt")

    def clean():
        kill_game()
        for f in (patch_dst, f_diag):
            if os.path.exists(f):
                os.remove(f)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        # Step 1: ONLY video/_patch folder + valid utf16 patch.xp3 without breaking anything!
        src_xp3 = r"d:\code\translate\build\p_diag4.xp3"
        xp3.pack_xp3(src_xp3, {
            "_in_patch.txt": b"hello",
            "scn/b01.txt.scn": b"dummy",
        }, compress=False)
        shutil.copy2(src_xp3, patch_dst)

        os.makedirs(os.path.join(video_dir, "_patch", "scn"), exist_ok=True)
        with open(os.path.join(video_dir, "_patch", "_in_folder.txt"), "w") as f:
            f.write("ok")
        with open(os.path.join(video_dir, "_patch", "scn", "b01.txt.scn"), "w") as f:
            f.write("dummy_folder")

        env_tjs = r"""(function(){
  var info = [];
  var st = global.Storages;
  var sy = global.System;
  var p = sy.dataPath + "_sp_probe4.txt";
  info.add("start");
  info.save(p);

  try {
    info.add("isEx(archive://patch.xp3/_in_patch.txt)=" + st.isExistentStorage("archive://patch.xp3/_in_patch.txt"));
    info.add("isEx(exe+patch.xp3>_in_patch)=" + st.isExistentStorage(sy.exePath + "patch.xp3>_in_patch.txt"));
    info.add("getPlaced(_in_patch)=" + st.getPlacedPath("_in_patch.txt"));
    info.add("getFull(archive://data.xp3/scn/b01.txt.scn)=" + st.getFullPath("b01.txt.scn"));
    info.add("getFull(syslangtext_cn.ini)=" + st.getFullPath("syslangtext_cn.ini"));
    info.save(p);
  } catch(e) { info.add("e1=" + e.message); info.save(p); }

  try {
    st.addAutoPath(sy.exePath + "video/_patch/");
    st.addAutoPath(sy.exePath + "video/_patch/scn/");
    info.add("added _patch/: _in_folder=" + st.getPlacedPath("_in_folder.txt"));
    // Now test removeAutoPath + addAutoPath on video/_patch/scn/
    st.removeAutoPath("archive://data.xp3/scn/");
    info.add("removed scn/: b01=" + st.getPlacedPath("b01.txt.scn"));
    st.addAutoPath(sy.exePath + "video/_patch/scn/");
    info.add("added _patch/scn/: b01=" + st.getPlacedPath("b01.txt.scn"));
    st.addAutoPath("archive://data.xp3/scn/");
    info.add("readded data/scn/: b01=" + st.getPlacedPath("b01.txt.scn"));
    info.save(p);
  } catch(e) { info.add("e2=" + e.message); info.save(p); }

  return %[];
})()"""
        with open(os.path.join(video_dir, "envscript.tjs"), "wb") as f:
            f.write(env_tjs.encode("utf-16"))

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        for s in range(1, 20):
            time.sleep(1)
            if os.path.exists(f_diag):
                time.sleep(0.5)
                print(f"\n=== LIVE @{s}s HIT ===")
                with open(f_diag, "rb") as f:
                    print(f.read().decode("utf-16"))
                break
        else:
            print("Timed out! tasklist:", tasklist_v())
    finally:
        clean()


if __name__ == "__main__":
    inspect_init_funcs()
    test_probe4()
