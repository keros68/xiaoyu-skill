# Style Decision Gate

Use this reference after reading the user's manuscript content and before calling image2. The goal is to prevent image2 from defaulting to a fixed 3D/isometric look, without forcing every element into a simplified flat-icon style. Let the user approve the visual direction before generation.

## Core Rule

Do not call image2 immediately after receiving manuscript content unless the user explicitly says to proceed without a design check.

First provide a compact figure design brief, then ask the user to choose one of three paths:

```text
A. Agent decides based on the recommended plan and continues
B. Show style options for the user to choose
C. User provides a custom style instruction
```

If the user already specified the style and layout clearly, show a brief confirmation and proceed. If the user says "you decide", "按你判断", "直接做", or similar, choose the style yourself and continue after the brief design summary.

## Figure Design Brief

The brief should be short and in the user's language. Include:

- figure role: graphical abstract, body concept model, workflow figure, synthesis figure, or other
- core message: one sentence that states what the figure should communicate
- reading path: left-to-right, top-to-bottom, layered, comparison, cross-section, or workflow
- proposed elements: 6-12 image2 elements to generate or reuse
- recommended element style: one item from the element style menu
- recommended layout style: one item from the layout menu
- avoid list: no full-figure raster, no baked-in text, no default 3D/isometric unless selected, no unwanted flat-icon simplification, no tiny unreadable labels

Chinese compact template:

```text
我先不直接生图，先给你一版绘制方案。

图件类型：...
核心信息：...
阅读路径：...
拟生成元素：...
推荐元素风格：...
推荐版式：...
我会避免：整张 AI 大图、文字烘焙进图片、默认 3D/isometric、不必要的扁平简化、小字号。

下一步你选一个：
A. 按这个方案继续
B. 展开风格菜单让我选
C. 我自己输入风格要求
```

English compact template:

```text
Before generating images, here is the proposed figure plan.

Figure role: ...
Core message: ...
Reading path: ...
Planned elements: ...
Recommended element style: ...
Recommended layout style: ...
I will avoid: full-figure raster output, baked-in text, default 3D/isometric styling, unwanted flat-icon simplification, and tiny unreadable labels.

Choose one:
A. Continue with this recommended plan
B. Show style options
C. I will provide a custom style instruction
```

## Element Style Menu

Use these options for image2 element generation. These describe visual language, not copyrighted platform assets. Do not say "BioRender style" in the image2 prompt. Use neutral descriptions such as "clean scientific vector illustration".

1. `clean scientific vector`
   - Default general option.
   - White background, clean scientific icons, consistent line weight, restrained colors.
   - Not the same as low-detail flat icons; keep enough domain detail for manuscript use.
   - Good for graphical abstracts, experimental workflows, environmental mechanisms, and biomedical-style schematic figures.

2. `soft watercolor scientific illustration`
   - Soft texture, crisp ink edge, muted natural colors.
   - Preserve hand-painted texture, soil/rock/water/material detail, and natural-process richness.
   - Do not flatten into simple vector icons.
   - Good for geology, hydrology, ecology, soil, landscape, and natural-process figures.

3. `flat schematic vector`
   - Flat vector forms, minimal shadows, clear blocks and arrows.
   - This is the deliberately simplified option.
   - Good for method workflows, model frameworks, data pipelines, and machine-learning figures.

4. `technical line art`
   - Monochrome or low-saturation line drawing, precise outlines, minimal fill.
   - Good for serious body concept models, mechanism diagrams, and figures that should print well in grayscale.

5. `semi-realistic scientific object`
   - More concrete object rendering while keeping a white background and clean edges.
   - Good for instruments, wells, reactors, cores, bottles, field devices, and lab equipment.

6. `cross-section cutaway illustration`
   - Sectional blocks, visible internal layers, process arrows can be added later in draw.io.
   - Preserve layer texture, particle/rock/soil detail, and readable cutaway structure.
   - Good for groundwater, soil, rock, river valleys, aquifers, roots, sediment layers, and subsurface processes.

7. `minimal pictogram / visual abstract icon`
   - Simple icons, low detail, high legibility.
   - Good for medical/public-health visual abstracts, 1-3 panel summaries, and social-media-facing result summaries.

8. `3D / isometric scientific blocks`
   - Optional only; do not choose by default.
   - Good for modular devices, model components, spatial blocks, and physical setups where 3D structure matters.
   - Risk: may look fixed, AI-like, or overly glossy.

Default selection:

- Use `clean scientific vector` for biomedical, lab, general conceptual, and experimental workflow figures.
- Use `soft watercolor scientific illustration` or `cross-section cutaway illustration` first for earth, water, soil, ecology, landscape, hydrogeology, and environmental-process topics.
- Use `flat schematic vector` for data/model/method-heavy figures.
- Use `technical line art` when the user wants a restrained, serious, or black-and-white body figure.
- Use `3D / isometric scientific blocks` only when selected by the user or strongly justified by the object.
- Never choose `flat schematic vector` merely because the workflow says not to default to 3D/isometric.

## Layout Style Menu

Call this "layout" rather than "overall style". It controls reading order and information architecture.

1. `three-panel graphical abstract`
   - Left-center-right story.
   - Good for journal graphical abstracts.

2. `boxed manuscript layout`
   - White canvas, claim boxes, pictorial anchors, restrained borders.
   - Good for body concept models and discussion figures.

3. `layered conceptual model`
   - Top-to-bottom layers such as setting, process, evidence, output.
   - Good for mechanism interpretation and synthesis.

4. `method workflow`
   - Inputs, processing steps, sensitivity checks, outputs, objective.
   - Good for Fig. 2-style study framework figures.

5. `comparison / contrast layout`
   - Parallel panels with same-role elements aligned.
   - Good for treatment vs control, medium A vs medium B, known vs new, before vs after.

6. `cross-section mechanism model`
   - Sectional scene plus process arrows and evidence boxes.
   - Good for hydrogeology, soil, ecology, contaminant transport, and subsurface processes.

7. `visual abstract panels`
   - One to three result panels with concise claims.
   - Good for medical, public-health, and policy-facing visual abstracts.

Default layout selection:

- Use `three-panel graphical abstract` for graphical abstracts.
- Use `boxed manuscript layout` or `layered conceptual model` for body concept models.
- Use `method workflow` for explicit method figures.
- Use `cross-section mechanism model` when the scientific object is spatially layered.
- Use `comparison / contrast layout` when the manuscript's main claim is a contrast.

## Guided Style Menu Reply

When the user chooses B, reply with a compact menu and ask for a combination such as `2 + 6`.

Chinese:

```text
可以。你选“元素风格 + 版式”即可，比如 `2 + 6`。
每个选项后面的英文是给 image2 prompt 用的，你看中文解释选择就行。

元素风格：
1 干净科学矢量图（clean scientific vector）：白底、统一描边、颜色克制，最通用
2 柔和水彩科学插图（soft watercolor scientific illustration）：适合地学、水文、生态、土壤和自然过程
3 扁平流程示意图（flat schematic vector）：适合方法流程、模型框架、数据管线
4 技术线稿/黑白线图（technical line art）：适合严肃正文图、黑白打印、机制示意
5 半写实科学对象（semi-realistic scientific object）：适合仪器、井、反应器、岩芯、样品瓶
6 剖面/切块示意图（cross-section cutaway illustration）：适合地下水、土壤、岩体、河谷、含水层
7 极简图标/视觉摘要图标（minimal pictogram / visual abstract icon）：适合医学、公卫、结果摘要
8 3D/等距科学模块（3D / isometric scientific blocks）：只在需要立体模块时选，容易有固定 AI 味

版式：
1 三段式图形摘要（three-panel graphical abstract）：左-中-右讲清楚一个故事
2 论文正文框架图（boxed manuscript layout）：白底、文字框、元素锚点，适合正文概念图
3 分层概念模型（layered conceptual model）：背景-过程-证据-结论，上下分层
4 方法流程图（method workflow）：数据输入、处理步骤、敏感性检查、输出
5 对比式版式（comparison / contrast layout）：A vs B、处理组 vs 对照组、前后对比
6 剖面机制模型（cross-section mechanism model）：剖面场景 + 过程箭头 + 证据框
7 视觉摘要面板（visual abstract panels）：1-3 个结果面板，适合医学/公卫类摘要图
```

English:

```text
Choose an element style plus a layout style, for example `2 + 6`.

Element styles:
1 clean scientific vector
2 soft watercolor scientific illustration
3 flat schematic vector
4 technical line art
5 semi-realistic scientific object
6 cross-section cutaway illustration
7 minimal pictogram / visual abstract icon
8 3D / isometric scientific blocks

Layout styles:
1 three-panel graphical abstract
2 boxed manuscript layout
3 layered conceptual model
4 method workflow
5 comparison / contrast layout
6 cross-section mechanism model
7 visual abstract panels
```

## Prompt Translation

After the user chooses or accepts a style, translate it into the image2 prompt. The image2 prompt must request an element sheet, not a finished figure.

Style fidelity rule:

- `not 3D` does not mean `simple`, `flat`, or `minimal`.
- Preserve the selected style's visual richness. For watercolor and cutaway styles, keep material textures, internal layers, and natural forms.
- Use words like `simple icon`, `flat icon`, `minimal pictogram`, or `low-detail` only when the user selected `flat schematic vector` or `minimal pictogram / visual abstract icon`.
- If the generated result becomes too simple compared with the selected style, regenerate with stronger positive style tokens before assembling draw.io.

Always include:

- white or transparent-friendly background
- no text, labels, numbers, legends, watermark, or title
- separate elements with generous spacing
- consistent style across all elements
- isolated complete objects, easy to crop

Unless the user selected 3D/isometric, include:

```text
not 3D, not isometric, no glossy plastic render, no mockup lighting
```

For `soft watercolor scientific illustration`, add:

```text
soft watercolor texture, crisp ink outlines, natural material detail, subtle paper-like shading, not flat vector icons
```

For `cross-section cutaway illustration`, add:

```text
cutaway scientific illustration, visible internal layers, soil/rock/water texture, granular material detail, not flat icon style
```

Do not ask another style question after the user has selected A, B, or C unless generation fails or the result clearly violates the selected style.
