# Abstract-Fig

Abstract-Fig 是一个 Codex agent skill，用于把论文内容做成可继续编辑的 draw.io 图件：图形摘要、正文概念模型、机制图、方法流程图、研究/技术路线图和综合示意图。

科学场景由 image2 生成的主题元素承担：元素表拆成独立透明 PNG 逐个嵌入，文字框、箭头、边框和标签保留为 draw.io 对象，拿到文件后仍可拖拽、改字、换元素、调版面。

> 中文为主，English version below.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)
[![draw.io](https://img.shields.io/badge/draw.io-editable%20.drawio-orange.svg)](https://app.diagrams.net/)

## 运行要求

完整流程依赖 Codex 里的 image2 生图能力，所以这个 skill 面向 Codex。其他 agent 可以把 `SKILL.md` 和 `references/` 当流程参考，但缺少生图与图片处理能力时，「生成元素 → 拆分元素 → 嵌入 draw.io」这条链跑不下来。

## 使用场景

- 已有论文主线、审稿意见或修改建议，要转成正文概念图或 graphical abstract。
- 普通流程图太像模板，想加入含水层介质、河流、田块、监测井、仪器、地貌等论文主题元素。
- 把已有草图或 draw.io 文件改成适合期刊正文的 boxed manuscript style。

## 功能

**图件类型选型**：判断图件类型并套用对应的版式和箭头用法。路线图按纯图形构建，默认不走 image2 元素流程。

**生图前的方案确认**：调用 image2 之前先给出一版绘制方案（核心信息、阅读路径、拟生成元素、推荐风格），再让你选择按方案继续、展开风格菜单还是自己写要求。元素风格、版式和角色配色都有预置选项，见 `references/`。

**元素生成与拆分**：先列 6-12 个可复用元素，元素表拆出的透明 PNG 放进 `elements` 文件夹，已有的干净元素优先复用。图片以 data URI 内嵌，`.drawio` 不依赖本地图片路径。

**论文风格与措辞约束**：默认 boxed manuscript style，白底、细描边、克制填色。过强的过程判断会降级为证据支持得住的说法；中文、希腊字母和化学式上下标不降级成 ASCII。

**交付前自检**：按 `references/qa-checklist.md` 检查 A4 页宽下的标签可读性、压盖、箭头指向和术语强度。

交付物是一个 `.drawio` 文件加一个透明 PNG 元素文件夹。默认不导出 PNG、SVG、PDF；先在 draw.io 里调到满意，再按期刊要求导出。

## 快速开始

在 Codex 里发送：

```text
请从 GitHub 安装这个 skill，并在之后需要制作论文 graphical abstract、概念模型图或可编辑 draw.io 投稿图时优先使用它：
https://github.com/keros68/xiaoyu-skill/tree/main/skills/abstract-fig
```

装完重启或新开窗口，用 `$abstract-fig` 触发，例如「使用 $abstract-fig 根据这篇论文主线做一张可编辑 draw.io 图形摘要」。

手动安装：

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/abstract-fig ~/.codex/skills/abstract-fig
```

做好的 `.drawio` 文件拖进 [draw.io 官方编辑器](https://app.diagrams.net/) 即可继续编辑；网页询问保存位置时选本地存储。

## 校验脚本

```bash
python scripts/inspect_drawio_images.py <figure.drawio> --elements-dir <elements_dir>
```

确认拆出来的 PNG 真的变成了多个内嵌图片单元。少于 `--min-images`（默认 3）、有外链图片或整页大图时以非零退出码报告失败，各码含义见 `--help`。只用 Python 3 标准库。

## 文件结构

- `SKILL.md` - 主说明、默认约定和工作流。
- `references/` - 图件类型、方案与风格菜单、元素生成与拆分、嵌入与布局、论文图风格与配色、路线图模板、交付检查清单。
- `scripts/inspect_drawio_images.py` - 检查 `.drawio` 是否嵌入了多个独立图片元素。
- `agents/openai.yaml` - 显示名与默认提示词。

## 边界

- 嵌入的是 PNG 元素，元素内部不能像矢量图那样逐笔修改；可编辑的是它的位置、大小和替换关系。
- 元素质量取决于 image2 的生成和拆分效果，复杂背景、阴影和细线可能要手动清理边缘和色晕。
- 图形摘要、机制图和概念模型在没有生图能力时不会降级成纯图形版本，而是直接告知无法满足。
- 措辞约束只做过强表述的降级提示，不判断结论是否成立。科学术语、图注和投稿格式仍需作者复核。

## Attribution and Redistribution

This project is the original Abstract-Fig skill by keros68:

https://github.com/keros68/abstract-fig

The project is released under the MIT License. Redistribution, forks, modified versions, and repackaged copies must preserve the copyright notice and license text. Please do not present modified copies as the original project or imply endorsement by the original author.

## English

Abstract-Fig is a Codex agent skill that turns manuscript content into editable draw.io figures: graphical abstracts, concept models, mechanism diagrams, workflow figures, research roadmaps, and synthesis figures. It proposes a design brief and a style first, then generates an image2 element sheet, splits it into separate transparent PNGs, and embeds each as its own draw.io image object, while text boxes, arrows, frames, and labels stay editable. The deliverable is a `.drawio` file plus an elements folder; PNG/SVG/PDF exports are not produced unless you ask. The full pipeline needs image2 or an equivalent image-generation setup.

Copy `skills/abstract-fig` from the `xiaoyu-skill` repository into `~/.codex/skills/abstract-fig`, then trigger it with `$abstract-fig`. Open finished files in the official draw.io editor: https://app.diagrams.net/

## License

MIT. See [LICENSE](LICENSE).

---

**同系列 Agent Skills**：[sci-select](../sci-select/)（选刊+投稿前审查） · [academic-reference-matcher](../academic-reference-matcher/)（文献引用） · [cugb-doctoral-thesis-format](../cugb-doctoral-thesis-format/)（学位论文格式） · [ai-cross](../ai-cross/)（多模型交叉验证）｜[返回总览](../../)
