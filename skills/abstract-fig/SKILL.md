---
name: abstract-fig
description: Plan, create, or revise editable scientific graphical abstracts, concept and mechanism diagrams, method frameworks, research roadmaps, and synthesis figures. Organize manuscript content and module relationships before choosing real project assets, vector schematics, or optional generated illustrations. Use for dense, generic, or poorly structured manuscript figures and reference-guided redesigns.
---

# Abstract-Fig

Turn manuscript content into a figure whose scientific message, module relationships, and visual hierarchy are clear at its intended publication size. Keep the source editable. Draw.io is the default; follow an explicit request for PowerPoint or another suitable editable format.

## Working contract

- Preserve the previous figure and edit a versioned copy or keep a recoverable backup.
- Use manuscript evidence and actual project materials. Preserve scientific meaning, numerical values, uncertainty, and the distinction between observations and schematics.
- Keep text, connectors, and structural objects editable. Embed reused images; explain that pixels within a raster remain raster content.
- Deliver the editable source and a rendered preview. Export submission PDF/SVG/PNG when requested or part of the established manuscript workflow.
- Image generation is optional. Neither image count nor use of a particular tool is a completion criterion.
- Apply user instructions and existing design decisions before defaults. A local adjustment does not require redesigning the whole figure.

## Workflow

### 1. Define the communication task

Identify the figure's role, the research question it supports, and what readers should understand from it. Consult [figure-types.md](references/figure-types.md) when the role is unclear. Distinguish a method framework from a graphical abstract or a results synthesis; they need different information density.

Read the relevant manuscript passages, captions, existing figure, and available assets. For each proposed module, identify its purpose, essential content, supporting source, and connection to other modules. Omit implementation inventories and details better carried by the caption. Do not reproduce the section list as a row of boxes.

### 2. Choose the content and module arrangement

Use [style-decision-gate.md](references/style-decision-gate.md) for content planning, reference comparison, and module combinations. Define sequence, comparison, shared input, parallel analysis, convergence, or validation relationships before placing boxes.

Allocate area according to importance and the space needed to read the evidence. Align comparable objects, but do not force unrelated modules to equal sizes. Choose canvas proportions and density from the content and target display width, not a fixed panel count or aspect ratio.

For a new or substantially redesigned figure, briefly state the content, reading path, grouping, and intended visual treatment. Continue when the request, references, or existing decisions provide enough direction. Ask only about missing information or materially different interpretations; do not impose an approval menu.

### 3. Select representations and sources

| Content | Preferred representation |
|---|---|
| Observations and results | Traceable project imagery, maps, photographs, or plots generated from actual data |
| Methods and relationships | Editable vector diagrams, timelines, partitions, model structures, and concise labels |
| Conceptual objects or scenes | Existing suitable illustrations; optional image generation when it adds explanatory value |

Use as many elements as the content requires, including zero raster images. Never generate or retouch an illustration to stand in for measured imagery, a geographic boundary, an experimental photograph, or a quantitative result. Label illustrative examples and hypothetical states when readers could mistake them for observations.

Only when generating illustrations, read [image2-element-workflow.md](references/image2-element-workflow.md). Missing image2 does not block vector construction or use of existing assets. If an essential source is unavailable, identify that specific gap without inventing a replacement observation.

### 4. Build the figure

Use [boxed-manuscript-style.md](references/boxed-manuscript-style.md) for hierarchy, typography, lines, and legends. For draw.io assembly, read [drawio-element-workflow.md](references/drawio-element-workflow.md). For proposal or project roadmaps, consult [research-roadmap.md](references/research-roadmap.md).

Shorten text before reducing font size. Put detail in the caption where appropriate. Preserve Chinese, Greek letters, subscripts, superscripts, units, and other scientific notation. Calibrate wording and arrows to the evidence; a process relationship is not automatically a demonstrated causal mechanism.

### 5. Inspect the actual deliverable

Follow [qa-checklist.md](references/qa-checklist.md). Render the editable file in its intended editor/exporter when available, then inspect the expected publication width. A separately generated preview can aid development but does not prove that the editable file renders identically. State any unverified rendering limitation.

For draw.io, use `python scripts/inspect_drawio_images.py <figure.drawio>` to check image embedding and identify images needing review. This supports vector-only, uncompressed, and compressed files. Large image warnings require visual judgment; a large map is not automatically a flattened diagram. Use `--min-images` only when the particular design requires a known number of images.

### 6. Hand off

Link the editable source and preview; briefly report the substantive change, validation, and any material limitation. Identify reused or generated assets where relevant. Avoid reporting image counts as evidence of scientific or visual quality.

For draw.io, explain once when useful: open https://app.diagrams.net/ and drag in the `.drawio` file. Text and structural objects remain editable; embedded images can be moved, resized, or replaced. Other formats should have equivalent handoff instructions.
