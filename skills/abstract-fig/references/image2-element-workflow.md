# Image2 Element Workflow

Use this reference when a manuscript figure needs pictorial subject matter rather than a plain flowchart. This is the default path for graphical abstracts, mechanism diagrams, and body concept models unless the user asks for a shape-only method workflow.

## Required Gate

For graphical abstracts, mechanism diagrams, and body concept models, do one of these before constructing the draw.io figure:

1. Call image2 or the available image generation tool to create a new element sheet.
2. Reuse an existing project element set that already has publication-style raster elements.

If neither is possible, do not continue with a hand-drawn draw.io substitute. Tell the user that the image-element requirement cannot be met in the current run.

The final response must state the element source: `image2-generated element sheet`, `reused project elements`, or a clear skip reason.

Research/technical roadmaps (技术路线图) — diagrams showing project phases, timelines, milestones, or per-stage methodology — are classified as a Workflow Figure variant, not a mechanism diagram or concept model. They are exempt from this Required Gate by default. Only apply the image2 element gate to a roadmap if the user explicitly asks for a more pictorial, graphical-abstract-style treatment. See `research-roadmap.md`.

The element sheet is only an intermediate file. It must not be used as the main image in the final draw.io figure. Split it into separate PNGs and embed each element as its own draw.io image object: multiple embedded image elements, never one full-canvas image.

Before calling image2, run the style decision gate in `style-decision-gate.md` unless the user already provided clear style and layout requirements or explicitly asked you to proceed without a design check. Carry the selected element style and layout style into the image2 prompt and final report.

## When to Use Image2 Elements

Use image2 or the available image generation tool when:

- the figure needs a visible scientific scene, object, medium, process, or status
- a generic icon set would make the figure look like a template slide
- the user says the figure is too plain, AI-like, repeated, or hard to understand
- a graphical abstract must look manuscript-ready but remain editable in draw.io

Skip image2 only when the user explicitly wants a pure vector/shape workflow, or when the figure is a simple methods flowchart where pictorial elements would distract.

Do not skip image2 merely because draw.io shapes can approximate the scene. Hand-drawn mountains, clouds, rivers, factories, trees, wells, or charts are not a substitute for required subject-matter elements in a graphical abstract or mechanism figure.

## Element Plan First

Before calling image generation, list 6-12 reusable elements:

- setting elements: field, village, river, wetland, slope, basin, coast, sampling site
- medium/process elements: porous sediment, fractured rock, soil layer, recharge, flow path, plume-like signal, redox patch
- method/evidence elements: sample bottle, well, isotope pair, ion-ratio symbol, bootstrap chart, map tile
- output/status elements: reference state, disturbance, risk, uncertainty, stable group

Keep the plan tied to the manuscript terms. Do not generate unrelated decorative art.

## Style Selection

Use the selected or recommended element style from `style-decision-gate.md`.

Important: avoiding 3D/isometric styling must not collapse the result into generic flat icons. Preserve the selected style's visual richness. If the selected style is watercolor, cutaway, or semi-realistic object, the prompt must include positive texture/detail words and must explicitly avoid `flat icon style`.

Default behavior:

- Do not default to `3D / isometric scientific blocks`.
- Use `clean scientific vector` for biomedical, lab, general conceptual, and experimental workflow figures.
- Use `soft watercolor scientific illustration` or `cross-section cutaway illustration` first for earth, water, soil, ecology, landscape, hydrogeology, and environmental-process figures.
- Use `flat schematic vector` for method, model, and data workflow figures.
- Use `technical line art` when the user wants a restrained or black-and-white body concept model.
- Use `3D / isometric scientific blocks` only when the user selects it or when spatial block structure is central to the figure.
- Never choose `flat schematic vector` merely because the prompt says not to use 3D/isometric.

Avoid using branded terms such as BioRender or Mind the Graph inside the image2 prompt. Use neutral visual descriptions such as `clean scientific vector illustration`, `consistent scientific icon style`, or `publication-style scientific illustration`.

## Image Prompt Pattern

Generate a single element sheet, not a finished figure. Ask for no text in the image.
The prompt may use the user's manuscript language, but the generated element sheet should normally contain no baked-in text. Add Chinese, Unicode symbols, and chemical notation later as editable draw.io labels.

Template:

```text
Create a publication-style scientific illustration element sheet for an editable manuscript figure. 
White or flat chroma-key background, no text, no labels, no numbers, no watermark.
Consistent [selected element style], crisp edges, publication-ready, not cartoonish.
Preserve enough scientific and material detail for manuscript use; do not simplify into generic low-detail icons unless the selected style is flat schematic vector or minimal pictogram.
Not 3D, not isometric, no glossy plastic render, no mockup lighting, unless the user selected 3D/isometric.
Arrange the following separate elements with generous white space between them:
1. [element]
2. [element]
...
Each element must be isolated, complete, and easy to crop into a transparent PNG.
```

For hydrogeology or environmental geochemistry, useful style words are:

```text
clean scientific cross-section, cutaway aquifer block, soft watercolor texture, crisp ink edge, muted colors, white background, no text, not 3D, not isometric
```

For hydrogeology, environmental geochemistry, soil, ecology, and natural-process figures, prefer a textured watercolor/cutaway prompt over a flat schematic prompt unless the user explicitly selected `flat schematic vector`.

Style-specific positive tokens:

- `clean scientific vector`: clean scientific vector illustration, consistent icon family, crisp outlines, moderate detail, not low-detail clipart
- `soft watercolor scientific illustration`: soft watercolor texture, crisp ink outlines, natural material detail, subtle paper-like shading, not flat vector icons
- `flat schematic vector`: flat vector schematic, minimal shadows, simple geometric forms, clear blocks, low visual complexity
- `technical line art`: precise technical line drawing, monochrome or low-saturation lines, minimal fill, clear contours
- `semi-realistic scientific object`: semi-realistic scientific object rendering, clean white background, accurate object shape, subtle material texture
- `cross-section cutaway illustration`: cutaway scientific illustration, visible internal layers, soil/rock/water texture, granular material detail, not flat icon style
- `minimal pictogram / visual abstract icon`: minimal pictogram, high legibility, simple icon set, very low detail
- `3D / isometric scientific blocks`: isometric scientific block, controlled 3D structure, no glossy plastic look

Avoid:

- text baked into the image
- one big combined scene that cannot be rearranged
- emoji-like icons
- hyper-realistic stock photos
- default glossy 3D or isometric styling
- unwanted flat-icon simplification when watercolor, cutaway, or semi-realistic styles were selected
- brand-specific style names in the prompt
- complex backgrounds
- tiny elements that will blur at A4 width

## Splitting and Cleaning

After generation:

1. Save the image in the manuscript figure working folder.
2. Split or crop each element into its own PNG. Keep these PNGs in an `elements` folder or clearly named equivalent.
3. Remove the white/chroma-key background and save transparent PNGs.
4. Create a quick preview sheet on white background to inspect all elements.
5. Fix cropped edges, colored halos, clipped arrows, or fragments from neighboring cells.

Hard requirements:

- Keep the original element sheet as provenance only.
- Keep separate cropped PNG files for the elements actually used.
- Do not embed the whole element sheet into the draw.io canvas.
- Do not render a complete final figure as one image and place it into draw.io.
- Insert each main pictorial element as a separate image object so it can be moved, resized, replaced, or deleted independently.

If using a script for chroma-key removal, cast RGB arrays to `int32` before squaring color distances.

## Draw.io Assembly

In draw.io:

- embed element PNGs as image objects
- keep all text as editable draw.io text
- keep arrows, frames, and boxes editable
- use large pictorial elements as anchors, with short labels beside them
- avoid placing text directly over detailed illustrations
- align same-role elements to a similar visual size, but allow important mechanism elements to be larger
- embed image data so the `.drawio` file is portable and does not depend on local image paths
- avoid using draw.io primitive shapes as the main visual subjects after the image-element gate has been triggered
- after assembly, run the QA verification script from SKILL.md (or inspect the draw.io XML) to confirm that split PNGs became multiple embedded image cells

## Quality Bar

The output should read as a manuscript figure, not a generic presentation slide. If the figure could be mistaken for a template workflow with pasted icons, redesign it with larger subject-matter elements, fewer boxes, and a clearer scientific scene.

Use the user's previous high-quality figures or element folders as style anchors when available. Reuse those elements before generating new ones.

Completion evidence to report:

- element source
- chosen element style
- chosen layout style
- element sheet path, if generated
- split element folder path
- number of split PNG files used
- number of embedded image cells in the draw.io file
