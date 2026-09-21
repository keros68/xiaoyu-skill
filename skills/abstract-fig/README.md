# Abstract-Fig

将论文内容组织成可编辑科研图件，支持图形摘要、方法框架、概念与机制图、研究路线图和综合示意图。先确定展示内容和模块关系，再选择真实项目素材、矢量示意或可选的生成插画。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent%20Skill-SKILL.md-green.svg)](SKILL.md)

## 适用场景

- 从论文主线和现有材料规划配图，区分核心内容与图注细节。
- 按用户提供的案例调整信息密度、模块组合、字号、配色和图例。
- 修改等大框堆叠、层级不清、内容空泛或字号过小的现有图件。
- 将方法或科学关系组织成可继续编辑的图形。

## 工作方式

1. 明确图件要回答的问题，选择必须展示的内容。
2. 根据先后、并行、比较、汇合或验证关系组合模块，分配主次面积。
3. 从案例提取版式原则，结合真实素材和目标版面选择表现方式。
4. 绘制并在实际使用尺寸下检查，交付可编辑源文件和预览。

默认使用 draw.io，也可按要求采用 PowerPoint 等可编辑格式。无需 image2 即可使用项目影像、数据生成的图表和矢量对象；只有需要生成概念插画时才调用相应工具。具体导出和原生渲染能力取决于运行环境。

观测影像、实验照片、地图边界和定量结果应来自可追溯来源。生成插画用于概念表达，不替代观测证据。文字、箭头和结构尽量保持可编辑；嵌入位图内部仍是像素内容。

## 使用

将 `skills/abstract-fig` 安装到 agent 的技能目录，在支持的环境中用 `$abstract-fig` 调用，例如：

```text
使用 $abstract-fig，结合正文和这个案例，先梳理展示内容与模块关系，再调整图1。优先使用已有影像和可编辑矢量元素，保留旧版，交付源文件和预览。
```

手动安装示例：

```bash
git clone https://github.com/keros68/xiaoyu-skill.git ~/xiaoyu-skill
cp -R ~/xiaoyu-skill/skills/abstract-fig ~/.codex/skills/abstract-fig
```

draw.io 文件可拖入 [官方编辑器](https://app.diagrams.net/) 继续修改。投稿用 PDF、SVG、PNG 按用户要求或既有工作流导出。

## 文件检查

```bash
python scripts/inspect_drawio_images.py figure.drawio
python -m unittest discover -s tests -v
```

脚本仅依赖 Python 3.10+ 标准库，支持未压缩、压缩和多页 draw.io。纯矢量图、单张图片图均可通过；外链图片会报告可移植性错误。大图片提示人工检查，不自动认定为整图栅格化。

`--min-images N` 仅用于某个设计确实需要指定数量图片时，默认值为 0。`--elements-dir` 可选，用于列出 PNG 素材。退出码：0 为结构检查通过（仍需查看警告），1 为读取错误，2 为未达到显式数量要求，3 为外链图片，6 为无效或不支持的图文件数据。

结构检查不能证明科学结论、视觉质量或完整可编辑性。应在目标编辑器中检查成品；只有其他程序生成的预览时，需要说明尚未核验原生渲染。

## 文件结构

- `SKILL.md`：任务定位、内容规划、素材选择与执行流程。
- `references/`：模块组合、案例分析、版式、可选生图、格式操作与验收。
- `scripts/inspect_drawio_images.py`：图片嵌入与尺寸诊断。
- `tests/`：纯矢量、单图、外链和压缩文件等行为检查。
- `agents/openai.yaml`：技能显示信息与默认提示词。

## Attribution and Redistribution

This project is the original Abstract-Fig skill by keros68:

https://github.com/keros68/abstract-fig

The project is released under the MIT License. Redistribution, forks, modified versions, and repackaged copies must preserve the copyright notice and license text. Please do not present modified copies as the original project or imply endorsement by the original author.

## English

Abstract-Fig plans and creates editable scientific figures from manuscript content. It selects essential information, organizes module relationships, and chooses project observations, native vector schematics, or optional generated illustrations. Image generation is not required.

Draw.io is the default; an explicitly requested editable format can be used instead. Deliver the editable source and a preview, with publication exports as requested. Check the intended output size and the actual editor rendering when available. The bundled inspector accepts vector-only, single-image, compressed, and multi-page draw.io files; large images require visual review rather than automatic rejection.

## License

MIT. See [LICENSE](LICENSE).
