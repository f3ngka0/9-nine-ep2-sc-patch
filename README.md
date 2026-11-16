# 9-nine- Episode 2 简体中文补丁

适用于 Steam 正版《9-nine-：天色天歌天籁音》（*9-nine- Episode 2*）的外挂式简体中文补丁。


## 补丁内容

使用Argon和Hydrogen进行翻译，以官方日语（jp）为唯一主准，交叉核对官方英文（en）与官方繁中（cn），译校了 Steam 全年龄版全部 10,402 行正文及全部 7 处选项
修正了官方繁中多处误译、漏标控制符与台式用语（如 b14.txt.json 0:131 将否定句 契約の解除はできないのか 误译为肯定的问题、b02.txt.json 0:347 将陈述句 そうなの 误译为疑问句的问题、b18_2a.txt.json 10:90 诀别台词漏掉 %d; 控制符及误用“葛格”的问题）。
注：R18内容没有翻译

菜单、提示与帮助文本（5 个纯文本配置文件 + 默认语言设置）：

default.tjs：将首次启动默认语言标签设为 "cn"，菜单标题改为 "&Simplified Chinese"。
syslangtext_cn.ini、syslangtext_jp.ini、syslangtext_en.ini、help_conf_cn.txt、help_exch_cn.txt：全部译为简体中文，并补齐了官方原版遗留的所有 [CN-STUB] 日文未译占位符与 (CN)←Drop to Load,Click to Save 简易存取提示。

## 安装与卸载

- **安装**：运行 `dist/9-nine-ep2-sc-patch/安装补丁.bat`，或将 `video` 文件夹复制到游戏根目录。若此前保存过其他语言设置，可在菜单 `Language -> Simplified Chinese` 或 Config 中切换。**安装脚本默认游戏安装在C盘，如果安装在其他盘符请先将其复制到游戏根目录**
- **卸载**：运行 `卸载补丁.bat`，或删除游戏目录下的 `video` 文件夹。

