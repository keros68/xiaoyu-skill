---
name: cugb-doctoral-thesis-format
description: Use when editing, auditing, or finalizing CUGB doctoral thesis DOC/DOCX files, especially thesis templates, format detection reports, cover pages, declarations, abstracts, TOC, section breaks, odd/even headers, page numbers, headings, captions, formulas, punctuation, GB7714 references, and final Word submission. Covers China University of Geosciences (Beijing) (中国地质大学（北京）) doctoral dissertations (博士学位论文格式预检). Not for master's theses or other universities' templates.
---

# CUGB 博士论文排版

## Overview

把博士论文排版当成 `Word 结构 + 检测系统` 问题处理，不只是刷字体。封面缩进、摘要关键词、目录域、分节页眉、图表题、参考文献和全半角标点都会影响检测结论。

## Version Scope

本 skill 的资产来自 `2021年修订` 博士学位论文书写指南和模板。后续如果学校或学院发布新版模板、归档通知或检测规则，必须优先采用最新文件，并同步更新 `assets/`、`references/` 和检查脚本。

## Required Workflow

1. 先确认用户要做的是预检、局部修复，还是最终定稿。提示中已经指定本 skill 时，不要求用户重复学校全称。
2. 先读 `references/cugb-doctoral-format-rules.md`，锁定模板和书写指南中的硬规则。
3. 如果用户给了格式检测报告，继续读 `references/cugb-detection-failure-modes.md`，按严重/错误/提醒分层处理。
4. 编辑前复制出新文件版本，不覆盖原论文；修改后输出改动清单。
5. 如果输入是旧版 `.doc`，先转成 `.docx`。Windows + Word 环境优先用 `scripts/convert_doc_to_docx_with_word.ps1`。
6. 默认只跑一键预检入口（内部已调用 `check_cugb_doctoral_docx` 和 `extract_cugb_docx_format` 并生成合并报告）：
```bash
python scripts/precheck_cugb_doctoral_thesis.py path/to/thesis.docx
```
   按需补充：`extract_cugb_docx_format.py` 仅用于人工核对原始 section/样式明细；`check_cugb_doctoral_docx.py --fail-on-error` 仅用于门禁式判定；`summarize_cugb_detection_report.py path/to/format-report.html` 仅在用户提供学校检测报告 HTML 时运行。
   如果用户只要求预检，跑完本步、输出报告后即可结束，不进入第 7-9 步的修改与定稿流程。
7. 按固定顺序修：
   - `section / 分页 / 页码 / 奇偶页页眉`
   - `封面 / 英文封面 / 声明 / 中文摘要 / 英文摘要 / 目录`
   - `正文标题 / 正文段落 / 图题 / 表题 / 公式编号`
   - `正文引用 / 参考文献 / 标点数字 / 量和单位`
8. 自动目录、页码域、页眉页脚、交叉引用和字段更新放到最后一轮，在 Word 中完成。
9. 进入最终定稿排版阶段前，完整阅读 `references/cugb-revision-playbook.md`。最终导出 PDF 或截图复核关键页：封面、声明、摘要、目录、第 1 章首页、每章首页、图表密集页、参考文献页、致谢/个人简历页。

## Hard Rules

- 以当年学校/学院最新通知为准；不要把 2021 版资产当成永久有效的规范。
- 模板页面为 A4 纵向，页边距上 2.5 cm、下 2.0 cm、左 2.5 cm、右 2.0 cm，页眉/页脚距边界 1.5 cm。
- 页眉从第 1 章开始：奇数页为 `中国地质大学（北京）博士学位论文`，偶数页为当前章题；宋体五号，居中。检测报告会把偶数页章题错误列为严重问题。
- 页码位于页面底端居中；前置部分单独编号，正文从引言开始连续编号。
- 封面字段按模板保留缩进和行距。检测系统会检查 `学号 / 研究生 / 专业 / 研究方向 / 指导教师` 等行的首行缩进。
- 中文摘要 1000 字以内，关键词 3-5 个；中文关键词用中文逗号 `，` 分隔。英文关键词标记必须为 `Key words:`，英文关键词用半角逗号 `,` 分隔。
- 目录项应使用宋体，不要把正文标题的黑体直接带入目录；目录页码必须在最后更新。
- 正文一级标题形如 `1 引言`，编号和标题之间保留 1 个空格；二级/三级标题同理，如 `1.1 标题`、`1.1.1 标题`。标题段落不要保留正文首行缩进。
- 图题在图下方，表题在表上方；图、表、公式可按章编号，如 `图2-5`、`表3-2`、`(5-1)`，编号必须连续。图题/表题末尾通常不加标点。
- 正文引用使用方括号数字右上角标注；参考文献按正文引用顺序编号，并遵循 GB/T 7714-2015。
- 中文段落使用中文标点和全角括号；英文段落和英文参考文献按英文标点规则处理，不要机械全替换。
- Word 预览、WPS、PDF 和检测系统可能不一致；最终以 Word 更新字段后的 PDF 和学校检测报告共同验收。

## Modification Boundaries

- 当前脚本以检查、汇总和定位问题为主；修改由 agent 基于报告另存新文件后执行，不直接覆盖原稿。
- 适合自动或半自动修改：页边距、页眉页脚文本、常规段落样式、标题样式、图题表题样式、参考文献段落格式、明显空段、部分全角/半角标点。
- 必须谨慎修改：封面个人信息、目录页码、交叉引用、公式编号、图片位置、横向页、页末大空白、图题是否与图片分离。
- 不要承诺“一键通过”。学校检测系统的隐藏规则、Word/WPS/PDF 渲染差异、人工审美问题，只能通过最终 PDF 和学校检测报告复核。

## Quick Commands

这些脚本主要用于预检，不会直接改写论文文件。

旧版 `.doc` 转 `.docx`：
```powershell
powershell -ExecutionPolicy Bypass -File scripts/convert_doc_to_docx_with_word.ps1 -InputPath path/to/input.doc -OutputPath path/to/output.docx
```

提取结构和样式：
```bash
python scripts/extract_cugb_docx_format.py path/to/thesis.docx
```

启发式格式检查：
```bash
python scripts/check_cugb_doctoral_docx.py path/to/thesis.docx
```

一键本地预检报告：
```bash
python scripts/precheck_cugb_doctoral_thesis.py path/to/thesis.docx --output-dir output_dir
```

带学校 HTML 检测报告一起汇总：
```bash
python scripts/precheck_cugb_doctoral_thesis.py path/to/thesis.docx --detection-report path/to/format-report.html
```

## Resources

- `references/cugb-doctoral-format-rules.md`：学校博士论文结构、页面、封面、摘要、目录、正文、图表公式和参考文献规则。
- `references/cugb-detection-failure-modes.md`：根据真实格式检测报告匿名提炼出的高频扣分点和修复顺序。
- `references/cugb-revision-playbook.md`：从草稿到检测合格的推荐处理流程。
- `assets/cugb-doctoral-writing-guide-2021.doc` / `.docx`：2021 年修订版博士学位论文书写指南。
- `assets/cugb-doctoral-thesis-template-2021.doc` / `.docx`：2021 年修订版博士学位论文模板。
- 以上两项资产只读取 `.docx` 版本；`.doc` 是二进制遗留格式、无法直接解析，仅作模板溯源保留，不要尝试读取或解析。
- `scripts/extract_cugb_docx_format.py`：提取 section、页眉页脚、段落、表格和样式概览。
- `scripts/check_cugb_doctoral_docx.py`：按 CUGB 博士模板和检测报告高频项做启发式检查。
- `scripts/test_cugb_format_tools.py`：脚本自身的 pytest 单元测试，用于验证检查逻辑，不用于检查用户论文。
- `scripts/summarize_cugb_detection_report.py`：汇总学校格式检测 HTML 报告中的严重/错误/提醒和问题类别。
- `scripts/precheck_cugb_doctoral_thesis.py`：一键生成 Markdown/JSON 本地预检报告，合并脚本检查、Word COM 页眉审计、隐藏页眉残留和人工复核清单。
- `scripts/convert_doc_to_docx_with_word.ps1`：使用 Microsoft Word COM 将旧 `.doc` 转成 `.docx`。
