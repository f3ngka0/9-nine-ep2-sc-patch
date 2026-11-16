import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, r"d:\code\translate\tools")
import psb

ROOT = pathlib.Path(r"d:\code\translate")
EXT_DATA = ROOT / "build" / "extracted" / "data"
DEC_DATA = ROOT / "build" / "decoded" / "data"
TR_SCN_DIR = ROOT / "work" / "scn_translated"
UI_TEXTS_DIR = ROOT / "work" / "ui_texts"
WIN_FONTS = pathlib.Path(r"C:\Windows\Fonts")
DIST_DIR = ROOT / "dist" / "9-nine-ep2-sc-patch"

TAG_RE = re.compile(r"%[^;]*;")

CN_SPEAKER_MAP = {
    None: None,
    "？？？": "？？？",
    "司令官": "司令官",
    "翔＆天": "翔＆天",
    "翔": "翔",
    "天": "天",
    "都": "都",
    "沙月": "沙月",
    "春風": "春风",
    "與一": "与一",
    "希亞": "希亚",
    "蓮夜": "莲夜",
    "幽靈": "幽灵",
    "蘇菲堤雅": "索菲蒂娅",
    "母": "妈妈",
}


def strip_for_plain(s: str) -> str:
    # Remove literal \n and Kirikiri inline %...; tags for speechtext/searchtext
    s = s.replace("\\n", "")
    s = TAG_RE.sub("", s)
    return s


def build_scn_files(out_scn_dir: pathlib.Path):
    out_scn_dir.mkdir(parents=True, exist_ok=True)
    src_files = sorted(EXT_DATA.glob("scn/*.scn"))
    assert len(src_files) == 36, f"Expected 36 .scn files, got {len(src_files)}"

    total_lines = 0
    total_selects = 0
    for src_path in src_files:
        tr_path = TR_SCN_DIR / f"{src_path.stem}.json"
        assert tr_path.exists(), f"Missing translated file: {tr_path}"
        tr = json.loads(tr_path.read_text(encoding="utf-8"))

        p = psb.PsbFile.parse(src_path.read_bytes())
        scenes = p.root.get("scenes", [])
        for s_idx, sc in enumerate(scenes):
            texts = sc.get("texts", [])
            for t_idx, t in enumerate(texts):
                key = f"{s_idx}:{t_idx}"
                assert key in tr["items"], f"Missing line {key} in {tr_path.name}"
                disp = tr["items"][key]
                disp = disp.replace("\r\n", "\n").replace("\n", "\\n")
                while "\\\\n" in disp:
                    disp = disp.replace("\\\\n", "\\n")

                cn = t[2][2]
                orig_sp = cn[0]
                assert orig_sp in CN_SPEAKER_MAP, f"Unmapped speaker {orig_sp!r} in {src_path.name} {key}"
                new_sp = CN_SPEAKER_MAP[orig_sp]
                plain = strip_for_plain(disp)

                if len(cn) == 4:
                    cn[0] = new_sp
                    cn[1] = disp
                    cn[2] = plain
                    cn[3] = plain
                elif len(cn) == 2:
                    if disp != plain:
                        t[2][2] = [new_sp, disp, plain, plain]
                    else:
                        cn[0] = new_sp
                        cn[1] = disp
                else:
                    raise ValueError(f"Unexpected cn length {len(cn)} in {src_path.name} {key}")
                total_lines += 1

            selects = sc.get("selects", [])
            for sel_idx, sel in enumerate(selects):
                skey = f"{s_idx}:{sel_idx}"
                assert skey in tr["selects"], f"Missing select {skey} in {tr_path.name}"
                sel_txt = tr["selects"][skey].strip()
                sel_plain = strip_for_plain(sel_txt)
                sel["language"][2]["text"] = sel_txt
                sel["language"][2]["speechtext"] = sel_plain
                sel["language"][2]["searchtext"] = sel_plain
                total_selects += 1

        p._names_raw = None
        out_bytes = p.to_bytes()
        # Re-parse roundtrip assertion
        psb.PsbFile.parse(out_bytes)
        (out_scn_dir / src_path.name).write_bytes(out_bytes)

    print(f"Built {len(src_files)} .scn files ({total_lines} lines, {total_selects} selects)")


def build_fonts(out_font_dir: pathlib.Path):
    out_font_dir.mkdir(parents=True, exist_ok=True)
    for fn in ("SourceHanSansCN-Medium.otf", "SourceHanSansCN-Bold.otf", "SourceHanSansCN-Heavy.otf"):
        src = WIN_FONTS / fn
        assert src.exists(), f"Font not found: {src}"
        shutil.copy2(src, out_font_dir / fn)

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
\t\t(const)%[ "name"=>"思源黑體M", "file"=>"SourceHanSansCN-Medium.otf", "face"=>"思源黑体 CN Medium,Source Han Sans CN Medium,Source Han Sans TC Medium" ],
\t\t(const)%[ "name"=>"思源黑體B", "file"=>"SourceHanSansCN-Bold.otf",   "face"=>"思源黑体 CN Bold,Source Han Sans CN Bold,Source Han Sans TC" ],
\t\t(const)%[ "name"=>"思源黑體H", "file"=>"SourceHanSansCN-Heavy.otf",  "face"=>"思源黑体 CN Heavy,Source Han Sans CN Heavy,Source Han Sans TC Heavy" ],
\t\t(const)%[ "name"=>"思源宋體B", "file"=>"SourceHanSerifTC-Bold.otf",  "face"=>"Source Han Serif TC" ],
\t\t(const)%[ "name"=>"思源宋體H", "file"=>"SourceHanSerifTC-Heavy.otf", "face"=>"Source Han Serif TC Heavy" ]
\t]
]
"""
    (out_font_dir / "embfontlist.tjs").write_bytes(emb_tjs.encode("utf-16"))
    print("Built font/ directory with SourceHanSansCN OTFs and embfontlist.tjs")


def build_main_scripts(out_main_dir: pathlib.Path):
    out_main_dir.mkdir(parents=True, exist_ok=True)
    orig_def = (DEC_DATA / "main" / "default.tjs").read_text(encoding="utf-8")
    patched_def = (
        orig_def
        .replace('.multiLangFirstTag = "en";', '.multiLangFirstTag = "cn";')
        .replace('cn:%[ "menu_caption" => "&Traditional Chinese" ]', 'cn:%[ "menu_caption" => "&Simplified Chinese" ]')
    )
    assert '.multiLangFirstTag = "cn";' in patched_def
    assert '"&Simplified Chinese"' in patched_def
    (out_main_dir / "default.tjs").write_bytes(patched_def.encode("utf-16"))

    for fn in ("syslangtext_cn.ini", "syslangtext_jp.ini", "syslangtext_en.ini", "help_conf_cn.txt", "help_exch_cn.txt"):
        p = UI_TEXTS_DIR / fn
        if p.exists():
            txt = p.read_text(encoding="utf-8")
            (out_main_dir / fn).write_bytes(txt.encode("utf-16"))
        else:
            print(f"WARNING: {p} not found yet!")
    print("Built main/ script & ini overrides")


def build_envscript(video_dir: pathlib.Path):
    env_tjs = r"""(function(){
  var st = global.Storages;
  var sy = global.System;
  var base = sy.exePath + "video/_patch/";
  st.addAutoPath(base);
  st.addAutoPath(base + "font/");
  st.addAutoPath(base + "main/");
  st.addAutoPath(base + "scn/");

  try {
    if (typeof sy.addFont == "Object") {
      try { sy.addFont("SourceHanSansCN-Medium.otf"); } catch (e) {}
      try { sy.addFont("SourceHanSansCN-Bold.otf"); } catch (e) {}
      try { sy.addFont("SourceHanSansCN-Heavy.otf"); } catch (e) {}
    }
  } catch (e) {}

  try {
    if (typeof global.PreRenderFontEx == "Object" && global.PreRenderFontEx.PreRenderFontInfo !== void) {
      var info = global.PreRenderFontEx.PreRenderFontInfo;
      if (info["思源黑體M"] !== void) {
        info["思源黑體M"].realFace = ",思源黑体 CN Medium,Source Han Sans CN Medium,Noto Sans SC Medium,Source Han Sans TC Medium,ＭＳ ゴシック";
      }
      if (info["思源黑體B"] !== void) {
        info["思源黑體B"].realFace = ",思源黑体 CN Bold,Source Han Sans CN Bold,Noto Sans SC,Source Han Sans TC,ＭＳ ゴシック";
      }
      if (info["思源黑體H"] !== void) {
        info["思源黑體H"].realFace = ",思源黑体 CN Heavy,Source Han Sans CN Heavy,Noto Sans SC Black,Source Han Sans TC Heavy,ＭＳ ゴシック";
      }
      if (info["源ノ明朝B"] !== void) {
        info["源ノ明朝B"].realFace = ",源ノ明朝 JP,思源黑体 CN Bold,Source Han Sans CN Bold,Source Han Serif TC,ＭＳ ゴシック";
      }
    }
  } catch (e) {}

  try {
    if (typeof global.SystemConfig == "Object" && global.SystemConfig.multiLangSetting !== void) {
      if (global.SystemConfig.multiLangSetting.cn !== void) {
        global.SystemConfig.multiLangSetting.cn.menu_caption = "&Simplified Chinese";
      }
    }
    (global.Dictionary.clear incontextof global.SystemLanguageText)();
    global.LoadSysLangText();
    if (typeof global.ResetAllMenuLangText == "Object") global.ResetAllMenuLangText(global.kag);
    if (typeof global.UpdateMultiLangTitleCaption == "Object") global.UpdateMultiLangTitleCaption(global.kag);
  } catch (e) {}

  try {
    if (typeof global.MyYesNoDialog == "Object" && global.MyYesNoDialog.ConfirmDialogMessages !== void) {
      if (global.CurrentLanguageUITag == "cn") {
        global.MyYesNoDialog.ConfirmDialogMessages.AskResetPos = "确定要将窗口恢复到初始位置吗？";
      }
    }
  } catch (e) {}

  return %[];
})()"""
    (video_dir / "envscript.tjs").write_bytes(env_tjs.encode("utf-16"))
    print("Built video/envscript.tjs")


def build_installers(dist_dir: pathlib.Path):
    install_bat = """@echo off
chcp 65001 >nul
setlocal
set "DEFAULT_DIR=C:\\Program Files (x86)\\Steam\\steamapps\\common\\9-nine-Episode 2"
set "GAME_DIR=%~dp0"
if exist "%GAME_DIR%nine_sorairo.exe" goto :found
if exist "%DEFAULT_DIR%\\nine_sorairo.exe" goto :found_default
echo 请将本补丁文件夹解压或复制到游戏根目录（含 nine_sorairo.exe 的目录）后运行，
echo 或直接手动把本目录下的 video 文件夹复制到游戏根目录。
pause
exit /b 1

:found_default
set "GAME_DIR=%DEFAULT_DIR%\\"

:found
echo 正在安装《9-nine-：天色天歌天籁音》简体中文补丁到：
echo "%GAME_DIR%"
xcopy /E /I /Y "%~dp0video" "%GAME_DIR%video" >nul
if not errorlevel 1 goto :ok
echo 复制失败！若游戏安装在 C:\\Program Files (x86) 下，请右键“以管理员身份运行”。
pause
exit /b 1

:ok
echo.
echo 安装完成！原版游戏文件未被修改。
echo 提示：若您此前在游戏内设置过英语/日语，启动后请在菜单或设置中选择 Simplified Chinese / 简体中文 即可。
pause
"""
    uninstall_bat = """@echo off
chcp 65001 >nul
setlocal
set "DEFAULT_DIR=C:\\Program Files (x86)\\Steam\\steamapps\\common\\9-nine-Episode 2"
set "GAME_DIR=%~dp0"
if exist "%GAME_DIR%nine_sorairo.exe" goto :found
if exist "%DEFAULT_DIR%\\nine_sorairo.exe" goto :found_default
echo 未找到 nine_sorairo.exe，请手动删除游戏目录下的 video 文件夹即可完全卸载补丁。
pause
exit /b 1

:found_default
set "GAME_DIR=%DEFAULT_DIR%\\"

:found
if not exist "%GAME_DIR%video" goto :not_found
rmdir /S /Q "%GAME_DIR%video"
echo 已卸载简体中文补丁，游戏已恢复纯原版状态。
pause
exit /b 0

:not_found
echo 未检测到已安装的补丁（video 目录不存在）。
pause
"""
    readme_txt = """《9-nine-：天色天歌天籁音》（9-nine- Episode 2）Steam 正版简体中文补丁
========================================================================

【补丁特性】
- 完全基于 Steam 正版原文件外挂加载（通过 video\\envscript.tjs + video\\_patch\\），
  不修改 nine_sorairo.exe、data.xp3 等任何官方文件，不破坏 SteamStub DRM 与校验。
- 全部 36 个剧本文件已重编译打包（其中 Steam 全年龄正版可达的全部 10,402 句正文对话/旁白 + b19_1 前 360 句共 10,762 句、全部 7 处选项、14 个说话人标签，以及菜单、帮助说明、存档提示等文本均以官方日语为主、交叉核对官方英文重新译校为地道简体中文；受 checkAdult() 门控、Steam 全年龄版不进入的 609 句成人向 H 文本保留官方原版中文）。
- 内置思源黑体简体中文（Source Han Sans CN）字库映射，简体字显示清晰完整。

【安装方法】
1. 运行“安装补丁.bat”，或直接将本目录下的 video 文件夹整个复制到游戏根目录
   （例如 C:\\Program Files (x86)\\Steam\\steamapps\\common\\9-nine-Episode 2\\）。
2. 如此前启动过游戏并保存过语言设置，进入游戏后右键或点击标题菜单「Language」->「Simplified Chinese」，
   或在 Config 设置中将语言切换为简体中文即可（新存档默认即为简体中文）。

【卸载方法】
- 运行“卸载补丁.bat”，或直接删除游戏目录下的 video 文件夹即可 100% 恢复原版。
"""
    # Batch files MUST NOT have UTF-8 BOM and must use CRLF line endings
    (dist_dir / "安装补丁.bat").write_bytes(install_bat.replace("\n", "\r\n").encode("utf-8"))
    (dist_dir / "卸载补丁.bat").write_bytes(uninstall_bat.replace("\n", "\r\n").encode("utf-8"))
    (dist_dir / "README.txt").write_bytes(readme_txt.replace("\n", "\r\n").encode("utf-8-sig"))


def main():
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    video_dir = DIST_DIR / "video"
    patch_dir = video_dir / "_patch"
    build_scn_files(patch_dir / "scn")
    build_fonts(patch_dir / "font")
    build_main_scripts(patch_dir / "main")
    build_envscript(video_dir)
    build_installers(DIST_DIR)
    print(f"Patch built cleanly at: {DIST_DIR}")


if __name__ == "__main__":
    main()
