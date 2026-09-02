# cugb-doctoral-thesis-format

cugb-doctoral-thesis-format 是一个 AI agent skill 及配套 Python 脚本，用于检查中国地质大学（北京）博士学位论文 `.docx` 的 Word 格式，并生成本地预检报告。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)

脚本只读取论文、输出报告，不会写回论文文件。修改由你自己或 AI agent 依据报告完成。

## 环境要求

Python 3，依赖 `python-docx` 和 `lxml`（已验证 Python 3.12、python-docx 1.2.0、lxml 6.1.1）：

```bash
pip install python-docx lxml
```

只能解析 `.docx`，旧版 `.doc` 需先转换。Word COM 页眉审计需要 Windows 加 Microsoft Word，其他系统自动跳过。

## 检查项

规则来自 `assets/` 中的模板与书写指南，写在 `scripts/check_cugb_doctoral_docx.py` 里。结果分 ERROR、WARN、REMIND、INFO 四级：

- **页面与分节**：A4 纵向尺寸、四边页边距、页眉页脚距边界；横向 A4 只提示不判错。
- **页眉**：奇偶页页眉文字，以及 `header*.xml`、`footer*.xml` 中其他学校模板的残留字样。
- **前置部分**：封面行距与缩进、目录项字体、TOC/PAGE 域、中英文关键词的标记与分隔符。
- **正文与图表**：标题编号后的空格与缩进、图题表题的缩进和末尾标点与字号、图表编号连续性。
- **标点与参考文献**：中文段落里的半角标点和全半角括号混用、参考文献编号连续性和 GB/T 7714 常见缺项。

逐条规则、高频扣分点和定稿顺序见 `references/`。

## 命令

一键预检，生成 Markdown 和 JSON 两份报告：

```bash
python scripts/precheck_cugb_doctoral_thesis.py path/to/thesis.docx
```

默认输出到论文同级目录的 `cugb-precheck/`，存在 ERROR 时退出码为 1。可选 `--output-dir DIR`、`--detection-report report.html`（汇总学校检测报告）、`--no-word`（跳过 Word COM 页眉审计）。

其余脚本：

```bash
python scripts/check_cugb_doctoral_docx.py thesis.docx --fail-on-error  # 检查结果打印到终端
python scripts/extract_cugb_docx_format.py thesis.docx                  # 导出 section/段落/样式明细
python scripts/summarize_cugb_detection_report.py report.html           # 汇总学校 HTML 检测报告
```

旧版 `.doc` 转 `.docx`，需要 Windows 加 Word，输出为新文件：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/convert_doc_to_docx_with_word.ps1 -InputPath input.doc -OutputPath output.docx
```

## 作为 skill 使用

项目由 `SKILL.md`、`assets/`、`references/`、`scripts/` 组成，可交给支持 skill 的 AI agent。从 `xiaoyu-skill` 仓库复制到 Codex 的 skills 目录：

```powershell
git clone https://github.com/keros68/xiaoyu-skill.git "$env:USERPROFILE\xiaoyu-skill"
Copy-Item -Recurse "$env:USERPROFILE\xiaoyu-skill\skills\cugb-doctoral-thesis-format" "$env:USERPROFILE\.codex\skills\cugb-doctoral-thesis-format"
```

调用方式见 `agents/openai.yaml`：

```text
使用 $cugb-doctoral-thesis-format 帮我预检这篇博士论文 DOCX。
```

`SKILL.md` 为 agent 规定了修改顺序：先预检，改前另存新文件，字段和目录页码最后在 Word 中更新。

## 适用范围

中国地质大学（北京）博士学位论文。硕士学位论文和其他学校的模板不适用。

`assets/` 中的书写指南落款为学位办公室 2021 年 2 月，模板同期。学校发布新版模板或检测规则后，以最新通知为准，并同步更新 `assets/`、`references/` 和检查脚本。

改成别的学校：先备齐官方模板、书写指南和一份真实检测报告，替换 `assets/`、`references/` 和 `SKILL.md`，再改写 `check_cugb_doctoral_docx.py` 中的常量和检查函数。

## 已知限制

- 本地预检不替代学校检测系统，脚本覆盖的是能从 Word XML 静态读出的项目。
- 目录实际页码、页末大片空白、图题是否与图片分离、横向页是否被接受，需要在 Word 中更新域并导出 PDF 后人工复核。
- 封面个人信息、交叉引用、公式编号不适合批量处理。
- Word、WPS、PDF 和学校检测系统的渲染结果可能不一致，最终以更新字段后的 PDF 和学校检测报告为准。
- 不要把个人论文、学号、未公开的检测报告提交到公开仓库。

## 开发

```bash
pip install pytest && python -m pytest scripts/test_cugb_format_tools.py
```

## 许可与资产边界

由 keros68 编写的脚本、skill 说明和派生工作流笔记按 MIT License 发布；转载、fork、改名分发或二次打包时必须保留 `LICENSE`、`NOTICE.md` 和原始仓库链接。

`assets/` 下的学校模板和书写指南仅作为格式检查与规则校准材料保留，仍受其原始权属和使用条款约束。仓库的 MIT License 不额外授予这些第三方或学校模板材料的再授权权利。改造成其他学校版本时，请替换为你有权使用的模板与规范文件，并保留资产说明。

## 致谢

本项目的组织思路参考了 [CTctikki/csu-thesis-format-Skill](https://github.com/CTctikki/csu-thesis-format-Skill)。本仓库不包含原项目的学校模板或个人论文材料。

---

**同系列 Agent Skills**：[sci-select](../sci-select/)（选刊+投稿前审查） · [academic-reference-matcher](../academic-reference-matcher/)（文献引用） · [abstract-fig](../abstract-fig/)（图形摘要） · [ai-cross](../ai-cross/)（多模型交叉验证）｜[返回总览](../../)
