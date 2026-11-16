import os
import pathlib
import shutil
import subprocess
import sys
import time

sys.path.insert(0, r"d:\code\translate\tools")
import psb

GAME_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\9-nine-Episode 2"
EXE_PATH = os.path.join(GAME_DIR, "nine_sorairo.exe")
APPDATA_GAME = os.path.expandvars(r"%APPDATA%\PALETTE\nine_sorairo")
WIN_FONTS = pathlib.Path(r"C:\Windows\Fonts")
DECODED_DATA = pathlib.Path(r"d:\code\translate\build\decoded\data")
EXTRACTED_DATA = pathlib.Path(r"d:\code\translate\build\extracted\data")


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
    time.sleep(0.3)


def main():
    kill_game()
    video_dir = os.path.join(GAME_DIR, "video")
    f_diag = os.path.join(APPDATA_GAME, "_sp_full_smoke.txt")

    f_font = os.path.join(APPDATA_GAME, "_sp_font1.bmp")

    def clean():
        kill_game()
        for fp in (f_diag, f_font):
            if os.path.exists(fp):
                os.remove(fp)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

    clean()
    try:
        patch_dir = pathlib.Path(video_dir) / "_patch"
        (patch_dir / "font").mkdir(parents=True, exist_ok=True)
        (patch_dir / "main").mkdir(parents=True, exist_ok=True)
        (patch_dir / "scn").mkdir(parents=True, exist_ok=True)

        for fn in ("SourceHanSansCN-Medium.otf", "SourceHanSansCN-Bold.otf", "SourceHanSansCN-Heavy.otf"):
            shutil.copy2(WIN_FONTS / fn, patch_dir / "font" / fn)

        emb_tjs = """(const)[
\t"MTL_NOTICE.txt", (const)[
\t\t(const)%[ "name"=>"シーダ",   "file"=>"MTLc3m.ttf",  "face"=>"モトヤLシータ゛3等幅", "capname"=>"モトヤLシーダ3"   ],
\t\t(const)%[ "name"=>"マルベリ", "file"=>"MTLmr3m.ttf", "face"=>"モトヤLマルベリ3等幅", "capname"=>"モトヤLマルベリ3" ]
\t],
\t"SourceHanSansAndSerifJP-LICENSE.txt", (const)[
\t\t(const)%[ "name"=>"源ノ角ゴシックM", "file"=>"SourceHanSansJP-Medium.otf", "face"=>"源ノ角ゴシック JP Medium" ],
\t\t(const)%[ "name"=>"源ノ角ゴシックB", "file"=>"SourceHanSansJP-Bold.otf",   "face"=>"源ノ角ゴシック JP"        ],
\t\t(const)%[ "name"=>"源ノ角ゴシックH", "file"=>"SourceHanSansJP-Heavy.otf",  "face"=>"源ノ角ゴシック JP Heavy"  ],
\t\t(const)%[ "name"=>"源ノ明朝B",       "file"=>"SourceHanSerifJP-Bold.otf",  "face"=>"源ノ明朝 JP"              ],
\t\t(const)%[ "name"=>"源ノ明朝H",       "file"=>"SourceHanSerifJP-Heavy.otf", "face"=>"源ノ明朝 JP Heavy"        ]
\t],
\t"sourcehansansandseriftc-license.txt", (const)[
\t\t(const)%[ "name"=>"思源黑體M", "file"=>"SourceHanSansCN-Medium.otf", "face"=>"Source Han Sans CN Medium" ],
\t\t(const)%[ "name"=>"思源黑體B", "file"=>"SourceHanSansCN-Bold.otf",   "face"=>"Source Han Sans CN Bold"   ],
\t\t(const)%[ "name"=>"思源黑體H", "file"=>"SourceHanSansCN-Heavy.otf",  "face"=>"Source Han Sans CN Heavy"  ],
\t\t(const)%[ "name"=>"思源宋體B", "file"=>"SourceHanSerifTC-Bold.otf",  "face"=>"Source Han Serif TC"       ],
\t\t(const)%[ "name"=>"思源宋體H", "file"=>"SourceHanSerifTC-Heavy.otf", "face"=>"Source Han Serif TC Heavy" ]
\t]
]
"""
        (patch_dir / "font" / "embfontlist.tjs").write_bytes(emb_tjs.encode("utf-16"))

        # Test default.tjs override + syslangtext_cn.ini
        orig_def = (DECODED_DATA / "main" / "default.tjs").read_text(encoding="utf-8")
        test_def = orig_def.replace('.multiLangFirstTag = "en"', '.multiLangFirstTag = "cn"').replace('"&Traditional Chinese"', '"&Simplified Chinese"')
        (patch_dir / "main" / "default.tjs").write_bytes(test_def.encode("utf-16"))

        orig_ini = (DECODED_DATA / "main" / "syslangtext_cn.ini").read_text(encoding="utf-8")
        test_ini = orig_ini.replace("繁體中文(&T)", "简体中文(&C)").replace("文字顯示測試", "简体文字显示测试")
        (patch_dir / "main" / "syslangtext_cn.ini").write_bytes(test_ini.encode("utf-16"))

        # Modified b04.txt.scn
        p = psb.PsbFile.parse((EXTRACTED_DATA / "scn" / "b04.txt.scn").read_bytes())
        p.root["scenes"][0]["texts"][0][2][2][1] = "【简中字体与路径测试】"
        p.root["scenes"][0]["texts"][0][2][2][2] = "【简中字体与路径测试】"
        p.root["scenes"][0]["texts"][0][2][2][3] = "【简中字体与路径测试】"
        p._names_raw = None
        (patch_dir / "scn" / "b04.txt.scn").write_bytes(p.to_bytes())

        env_tjs = r"""(function(){
  var st = global.Storages;
  var sy = global.System;
  global._sp_prfn = (typeof global.PreRenderFontEx == "Object" && global.PreRenderFontEx.PreRenderFontNames !== void) ? global.PreRenderFontEx.PreRenderFontNames.join(",") : "NONE";
  var base = sy.exePath + "video/_patch/";
  st.addAutoPath(base);
  st.addAutoPath(base + "font/");
  st.addAutoPath(base + "main/");
  st.addAutoPath(base + "scn/");

  if (typeof global.addAfterInitCallback == "Object") {
    global.addAfterInitCallback(function() {
      var a = [];
      try {
        a.add("AFTER_INIT_CALLED=1");
        a.add("at_env_prfn=" + global._sp_prfn);
        a.add("placed_bare_emb=" + global.Storages.getPlacedPath("embfontlist.tjs"));
        a.add("placed_sub_emb=" + global.Storages.getPlacedPath("font/embfontlist.tjs"));
        try { global.SetLanguageType(2); global.SetUILanguageType(2); } catch (e) { a.add("setlang_exc=" + e.message); }
        a.add("curLang=" + global.CurrentLanguageTag + " msgFace=" + global.MessageDefaultFontFace);
        var infoB = global.PreRenderFontEx.PreRenderFontInfo["思源黑體B"];
        a.add("infoB_realFace=" + infoB.realFace + " infoB_ttf=" + infoB.ttf);
        var lay = new global.KAGLayer(global.kag, global.kag.primaryLayer);
        lay.setSize(680, 220);
        lay.fillRect(0, 0, 680, 220, 0xFF102030);
        var faces = ["思源黑體B", "思源黑体 CN Bold", "Source Han Sans CN Bold", "Noto Sans SC", "SimSun"];
        for (var i = 0; i < faces.count; i++) {
          lay.font.face = faces[i];
          lay.font.height = 24;
          lay.drawText(10, 10 + i * 40, faces[i] + ": 简骨边体门复发龙爱天翔都", 0xFFFFFFFF);
        }
        lay.saveLayerImage(global.System.dataPath + "_sp_font1.bmp");
        invalidate lay;
      } catch (e) {
        a.add("TOP_EXC=" + e.message);
      }
      a.save(global.System.dataPath + "_sp_full_smoke.txt");
    });
  }
  return %[];
})();
"""
        (pathlib.Path(video_dir) / "envscript.tjs").write_bytes(env_tjs.encode("utf-16"))

        subprocess.Popen([EXE_PATH], cwd=GAME_DIR)
        t0 = time.time()
        while time.time() - t0 < 12.0:
            time.sleep(0.5)
            if os.path.exists(f_diag):
                break
        time.sleep(0.4)
        if os.path.exists(f_font):
            shutil.copy2(f_font, r"d:\code\translate\work\test_font1.bmp")
        if os.path.exists(f_diag):
            print(open(f_diag, encoding="utf-16-le", errors="replace").read())
        else:
            print("NO OUTPUT WRITTEN")
    finally:
        clean()


if __name__ == "__main__":
    main()
