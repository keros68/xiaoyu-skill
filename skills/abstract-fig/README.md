# Abstract-Fig

把论文内容做成可编辑科研图件的 AI agent skill：图形摘要、方法框架、概念与机制图、研究路线图、综合示意图。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)

## 适用场景

- 根据论文主线和现有材料规划配图。
- 参照用户给的案例调整信息密度、模块、字号、配色和图例。
- 修改层级不清、内容空泛或字号过小的现有图件。
- 制作期刊图形摘要：先查期刊规格和生成式 AI 政策，以真实地图、照片和数据图为主体，数字与正文逐条核对。

## 工作方式

1. 明确图件要回答的问题和必须展示的内容。
2. 按先后、并行、比较、汇合或验证关系组合模块，分配主次面积。
3. 参照案例和真实素材选择表现方式。
4. 绘制后在实际尺寸下检查，交付可编辑源文件和预览。

默认用 draw.io，也可用脚本生成 SVG（Inkscape 编辑）或 PowerPoint。用户手改过的版本作为底稿，只改指出的元素。生成插画只在需要概念示意时使用，不替代观测影像、实验照片、地图和定量结果。

## 安装

任选一种，同一台电脑只装一份。

**skills.sh（推荐，需要 Node.js）**

```bash
npx skills add keros68/xiaoyu-skill --skill abstract-fig -g
```

用 `-a claude-code -a codex` 指定 Agent；更新用 `npx skills update -g`。

**交给 Agent 安装**：把下面这段发给正在用的 Agent：

```text
用 skills.sh 安装 keros68/xiaoyu-skill 里的 abstract-fig：运行
npx skills add keros68/xiaoyu-skill --skill abstract-fig -g -a <你自己对应的 agent 名，如 claude-code、codex、kimi-code-cli、pi>
不要手动复制文件。装完检查本机是否有 Python 3.10+（draw.io 文件检查脚本要用），再告诉我本机有没有能打开和导出 .drawio 的 draw.io 编辑器；没有时我用 https://app.diagrams.net/ 打开，你交付时要写明未在编辑器里核验渲染。
装完提醒我新开会话。
```

**克隆后复制**

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/abstract-fig ~/.codex/skills/abstract-fig
```

## 使用

```text
使用 $abstract-fig，结合正文和这个案例，先梳理展示内容与模块关系，再调整图1。优先使用已有影像和可编辑矢量元素，保留旧版，交付源文件和预览。
```

正常工作时的表现：

- 新做或大改一张图：动手前简要说明展示内容、阅读顺序、模块分组和视觉处理；信息足够时直接继续。
- 改现有图：保留旧版，只改指出的元素。
- 交付可编辑源文件（默认 `.drawio`）和预览图，说明改动和检查结果；未在目标编辑器里核验的渲染会写明。

`.drawio` 文件可在 [draw.io 编辑器](https://app.diagrams.net/) 中继续修改。

## 文件检查

```bash
python scripts/inspect_drawio_images.py figure.drawio
python -m unittest discover -s tests -v
```

脚本只依赖 Python 3.10+ 标准库，支持未压缩、压缩和多页 draw.io。外链图片报错；大图片提示人工检查。

可选参数：`--min-images N` 要求最少图片数（默认 0）；`--elements-dir` 列出 PNG 素材。

退出码：0 通过（仍需看警告），1 读取错误，2 图片数不足，3 外链图片，6 文件数据无效。

结构检查不代表科学结论、视觉质量或可编辑性合格，成品需在目标编辑器中查看。

## 文件结构

- `SKILL.md`：任务定位、内容规划、素材选择与执行流程。
- `references/`：模块组合、案例分析、版式、图形摘要、生图、draw.io 与 SVG/Inkscape 操作、验收。
- `scripts/inspect_drawio_images.py`：图片嵌入与尺寸检查。
- `tests/`：行为测试。
- `agents/openai.yaml`：显示信息与默认提示词。

## Attribution and Redistribution

This project is the original Abstract-Fig skill by keros68: https://github.com/keros68/abstract-fig

Released under the MIT License. Redistributions, forks and modified versions must keep the copyright notice and license text, and must not be presented as the original project or imply endorsement by the original author.

## English

Abstract-Fig is an AI-agent skill that turns manuscript content into editable scientific figures: graphical abstracts, method frameworks, concept and mechanism diagrams, and research roadmaps. It plans content and module layout first, then uses real project materials, vector schematics, or optional generated illustrations. Image generation is not required.

draw.io is the default; SVG (Inkscape) or PowerPoint can be used instead. For graphical abstracts it checks the journal's requirements and generative-AI policy and builds around real maps, photos, and data plots. It delivers an editable source plus a preview, keeps previous versions, and edits only the elements you name in a hand-edited file.

```bash
npx skills add keros68/xiaoyu-skill --skill abstract-fig -g
```

The draw.io inspector needs Python 3.10+.

## License

MIT. See [LICENSE](LICENSE).

---

**同系列 Agent Skills**：[sci-select](../sci-select/)（选刊+投稿前审查） · [academic-reference-matcher](../academic-reference-matcher/)（文献引用） · [cugb-doctoral-thesis-format](../cugb-doctoral-thesis-format/)（学位论文格式） · [study-area-map](../study-area-map/)（研究区区位图） · [ai-cross](../ai-cross/)（多模型交叉验证）｜[返回总览](../../)
