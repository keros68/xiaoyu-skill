# cugb-doctoral-thesis-format

检查中国地质大学（北京）博士学位论文 `.docx` 格式的 AI agent skill，附 Python 预检脚本。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)

脚本只读论文、输出报告，不改原文件。

## 环境要求

Python 3，依赖 `python-docx` 和 `lxml`（已验证 Python 3.12、python-docx 1.2.0、lxml 6.1.1）：

```bash
pip install python-docx lxml
```

只支持 `.docx`，`.doc` 需先转换。页眉的 Word COM 检查需要 Windows 和 Microsoft Word，其他系统自动跳过。

## 检查项

规则来自 `assets/` 中的模板与书写指南。结果分 ERROR、WARN、REMIND、INFO 四级：

- **页面与分节**：A4 尺寸、页边距、页眉页脚距离；横向页只提示。
- **页眉**：奇偶页页眉文字，其他学校模板的残留字样。
- **前置部分**：封面行距与缩进、目录字体、TOC/PAGE 域、中英文关键词分隔符。
- **正文与图表**：标题编号后的空格与缩进，图题表题的缩进、标点和字号，图表编号连续性。
- **标点与参考文献**：中文段落中的半角标点、括号混用，参考文献编号连续性和 GB/T 7714 常见缺项。

逐条规则和定稿顺序见 `references/`。

## 命令

一键预检，生成 Markdown 和 JSON 报告：

```bash
python scripts/precheck_cugb_doctoral_thesis.py path/to/thesis.docx
```

报告默认在论文同级的 `cugb-precheck/`，有 ERROR 时退出码为 1。可选参数：`--output-dir DIR`、`--detection-report report.html`（汇总学校检测报告）、`--no-word`（跳过 Word COM 检查）。

其余脚本：

```bash
python scripts/check_cugb_doctoral_docx.py thesis.docx --fail-on-error  # 检查结果打印到终端
python scripts/extract_cugb_docx_format.py thesis.docx                  # 导出分节、段落、样式明细
python scripts/summarize_cugb_detection_report.py report.html           # 汇总学校 HTML 检测报告
```

`.doc` 转 `.docx`（需要 Windows 和 Word，输出为新文件）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/convert_doc_to_docx_with_word.ps1 -InputPath input.doc -OutputPath output.docx
```

## 安装

任选一种，同一台电脑只装一份。

**skills.sh（推荐，需要 Node.js）**

```bash
npx skills add keros68/xiaoyu-skill --skill cugb-doctoral-thesis-format -g
```

用 `-a claude-code -a codex` 指定 Agent；更新用 `npx skills update -g`。

**交给 Agent 安装**：把下面这段发给正在用的 Agent：

```text
用 skills.sh 安装 keros68/xiaoyu-skill 里的 cugb-doctoral-thesis-format：运行
npx skills add keros68/xiaoyu-skill --skill cugb-doctoral-thesis-format -g -a <你自己对应的 agent 名，如 claude-code、codex、kimi-code-cli、pi>
不要手动复制文件。装完检查本机是否有 Python 3 和 python-docx、lxml，缺的用 pip install python-docx lxml 补上；再告诉我这台电脑是否为 Windows 且装了 Microsoft Word（转换 .doc 和页眉审计需要）。
装完提醒我新开会话。
```

**克隆后复制**（以 Codex 为例）：

```powershell
git clone https://github.com/keros68/xiaoyu-skill.git "$env:USERPROFILE\xiaoyu-skill"
Copy-Item -Recurse "$env:USERPROFILE\xiaoyu-skill\skills\cugb-doctoral-thesis-format" "$env:USERPROFILE\.codex\skills\cugb-doctoral-thesis-format"
```

## 使用

```text
使用 $cugb-doctoral-thesis-format 帮我预检这篇博士论文 DOCX。
```

正常工作时的表现：

- 要求预检：运行 `precheck_cugb_doctoral_thesis.py`，生成两份报告，不改论文。
- 要求按报告修改：先另存新文件，按分节页眉页码、封面摘要目录、正文标题与图表题、引用与参考文献的顺序修改，最后给改动清单。目录页码、域和交叉引用留到最后在 Word 中更新。
- 同时给出学校 HTML 检测报告：按严重、错误、提醒分层汇总后处理。

## 适用范围

仅适用于中国地质大学（北京）博士学位论文，不适用于硕士论文和其他学校。

`assets/` 中的书写指南和模板为学位办公室 2021 年 2 月版本。学校发布新版后以最新通知为准，并同步更新 `assets/`、`references/` 和检查脚本。

改用于其他学校：备齐官方模板、书写指南和一份真实检测报告，替换 `assets/`、`references/` 和 `SKILL.md`，再修改 `check_cugb_doctoral_docx.py` 中的常量和检查函数。

## 已知限制

- 本地预检不替代学校检测系统，只覆盖能从 Word XML 读出的项目。
- 目录页码、页末空白、图题与图片是否分离、横向页是否被接受，需在 Word 中更新域、导出 PDF 后人工核对。
- 封面个人信息、交叉引用、公式编号不宜批量处理。
- Word、WPS、PDF 和学校检测系统的渲染可能不一致，以更新域后的 PDF 和学校检测报告为准。
- 个人论文、学号和未公开的检测报告不要提交到公开仓库。

## 开发

```bash
pip install pytest && python -m pytest scripts/test_cugb_format_tools.py
```

## 许可与资产边界

keros68 编写的脚本、skill 说明和工作流笔记按 MIT License 发布；转载、fork 或二次分发须保留 `LICENSE`、`NOTICE.md` 和原仓库链接。

`assets/` 下的学校模板和书写指南仅用于格式检查，权属归原所有者，不在 MIT License 授权范围内。改为其他学校版本时，请换成有权使用的模板与规范文件。

## 致谢

组织思路参考了 [CTctikki/csu-thesis-format-Skill](https://github.com/CTctikki/csu-thesis-format-Skill)。本仓库不含该项目的模板或论文材料。

---

**同系列 Agent Skills**：[sci-select](../sci-select/)（选刊+投稿前审查） · [academic-reference-matcher](../academic-reference-matcher/)（文献引用） · [abstract-fig](../abstract-fig/)（图形摘要） · [ai-cross](../ai-cross/)（多模型交叉验证）｜[返回总览](../../)
