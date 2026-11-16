# 9-nine- Episode 2 简体中文补丁

适用于 Steam 正版《9-nine-：天色天歌天籁音》（*9-nine- Episode 2*）的外挂式简体中文补丁。

## 改动内容

- **外挂加载**：通过 `video/envscript.tjs` 与 `video/_patch/` 挂载补丁资源，不修改 `nine_sorairo.exe` 与 `data.xp3`。
- **字体与界面文本**：内置思源黑体 CN（`SourceHanSansCN`）字库映射，替换菜单、设置说明与系统提示为简体中文，并在 `envscript.tjs` 中重载 `SystemLanguageText`。
- **全剧本重译与润色**：
  - 重新编译全部 36 个 `.scn` 剧本文件（11,371 行正文与 7 处选项），其中 Steam 全年龄版可达的 10,402 行与 `b19_1` 前 360 行（共 10,762 行）、全部选项与说话人标签均以官方日语为基准、交叉核对官方英文重新译校为现代简体中文。
  - 世界观专有名词与店名保留英文：`Artifact` / `AF`、`Stigma`、`Ambrosia`、`Sephirot`、`Rig Veda`、`Valhalla Society`、`Gate`、`Nine Ball`、`MockDonald's`。
  - `checkAdult()` 门控的 609 行成人向文本保留官方原版中文。

## 安装与卸载

- **安装**：运行 `dist/9-nine-ep2-sc-patch/安装补丁.bat`，或将 `video` 文件夹复制到游戏根目录。若此前保存过其他语言设置，可在菜单 `Language -> Simplified Chinese` 或 Config 中切换。
- **卸载**：运行 `卸载补丁.bat`，或删除游戏目录下的 `video` 文件夹。

## 目录结构

- `tools/`：PSB 解析/编译、翻译、QA 校验与补丁打包脚本（`build_patch.py`）。
- `work/glossary.md`：术语与翻译规范。
- `work/scn_translated/`：36 个剧本的简体中文译文 JSON。
- `work/ui_texts/`：菜单、设置与帮助文本。
- `dist/9-nine-ep2-sc-patch/`：可直接安装的补丁包。
