---
name: abstract-fig
description: Codex-native skill for editable draw.io manuscript figures using image2-generated or reused elements plus editable text, arrows, and frames. Use for a graphical abstract, concept model, mechanism diagram, workflow/synthesis figure, or research/technical roadmap (图形摘要、概念模型图、机制图、可编辑 draw.io、技术路线图、研究路线图); when revising from reviewer/GPT/Claude comments, converting a dense figure into element-based draw.io, or when a figure looks generic/templated/AI-like. Do not run the full workflow without an image-generation tool or a reusable element library - state the limitation instead of substituting plain shapes.
---

# Abstract-Fig

Build an editable draw.io manuscript figure that communicates the paper main scientific story with visual elements, short labels, and defensible arrows. The figure should be editable first: keep text, boxes, arrows, and layout as draw.io objects; use raster elements only for scientific illustrations or icons.

This skill is intended for Codex, because the complete workflow depends on image2 for generating subject-matter elements. Other agents may treat these instructions as a reference, but do not present the full workflow as agent-agnostic unless an equivalent image-generation and file-processing setup is available.

## Default Contract

- Deliver a `.drawio` file by default. Do not create final PNG, SVG, or PDF exports unless the user asks.
- Preserve the original file. Create a versioned copy or a clearly named new `.drawio`.
- Prefer fewer, larger labels over many small annotations.
- Keep scientific claims no stronger than the manuscript evidence supports.
- If the user provides review comments, convert them into visual constraints before editing.
- Use visual elements to carry subject matter, but keep labels and flow editable in draw.io.
- Default to a boxed manuscript style: white canvas, strong editable text boxes, restrained fills, thin borders, and pictorial elements as anchors rather than decoration.
- Confirm image-generation capability before building elements; see Workflow step 1.
- For graphical abstracts, mechanism diagrams, and body concept models, follow the Required Gate in `references/image2-element-workflow.md`: generate or reuse subject-matter elements, then split them into multiple embedded image elements, never one full-canvas image.
- Preserve the user's manuscript language and scientific notation in outputs. Do not downgrade Chinese labels, Greek letters, subscripts, superscripts, or chemical notation to ASCII solely for tool or platform convenience.

## Workflow

1. **Confirm image-generation capability.** Confirm an image-generation tool is available in this host. If none exists and no reusable element library is provided, stop and tell the user this workflow needs image generation - do not substitute plain draw.io primitives.
2. **Define the figure role.** Choose graphical abstract, body concept model, workflow figure (including research/technical roadmaps), or synthesis figure. If unclear, infer from the user's wording and manuscript context; ask only when the choice changes the layout substantially.
3. **Extract the scientific spine.** Reduce the paper to 3-5 blocks such as `setting -> aquifer media/process -> evidence -> status/output`.
4. **Set the canvas.** For A4-facing wide figures, use a wide canvas near 5:2 or A4-landscape proportions. Leave margins for manual edits.
5. **Run the style decision gate.** Load `references/style-decision-gate.md`. Before calling image2, show the user a compact figure design brief with figure role, core message, reading path, proposed elements, recommended element style, and recommended layout style. Ask the user to choose: A agent continues with the recommendation, B guided style menu, or C custom style instruction. Skip the wait only if the user explicitly asked you to proceed without a design check or already provided clear style and layout requirements.
6. **Pass the image-element gate.** For a graphical abstract, mechanism diagram, or body concept model, first generate an image2 element sheet or locate reusable project elements after the style decision is settled. Record the element source and chosen style. Shape-only fallback is allowed only for pure workflow figures or explicit user requests.
7. **Plan the boxed manuscript layout.** Load `references/boxed-manuscript-style.md` unless the user explicitly wants a modern infographic/dashboard style. Decide which claims belong in editable text boxes and which pictorial elements anchor them.
8. **Write short labels.** Use one heading line plus at most one supporting line per box. Put detailed explanation in the manuscript, not the figure.
9. **Build in draw.io.** Use editable text boxes, rounded rectangles, arrows, and embedded image elements. Avoid nested cards and dense legends.
10. **Run visual QA.** Check A4 readability, overlap, arrow meaning, chemical notation, unsupported process terms, and whether image2/project elements are actually embedded.
11. **Verify split-image embedding.** For graphical abstracts, mechanism diagrams, and body concept models, run `scripts/inspect_drawio_images.py <drawio> --elements-dir <elements_dir>` or perform an equivalent XML inspection. Do not call the figure done if it only embeds a whole element sheet or a single full-figure raster image.
12. **Report the `.drawio` path.** Also state whether image2 generated new elements or existing elements were reused, the chosen element style and layout style, the number of split PNG elements, and the number of embedded image cells. Include the final handoff note. Mention remaining manual drag suggestions only if they matter.

## Figure Role Selection

Load `references/figure-types.md` when choosing or changing figure type.

Quick guide:

- **Graphical abstract:** horizontal, fast, visual, 5-10 second reading. Use three broad panels and one bottom takeaway.
- **Body concept model:** more rigorous; can show context, process domains, evidence, and interpreted outputs.
- **Workflow figure:** shows method steps, data inputs, sensitivity checks, outputs, and objective.
- **Research/technical roadmap:** a workflow figure variant showing project phases, timeline, or milestones; structured as stages, not method steps. Defaults to shape-only and is exempt from the image2 Required Gate. Load `references/research-roadmap.md`.
- **Synthesis figure:** summarizes result logic or mechanism without all method details.

## Element-Based Draw.io Rules

Load `references/drawio-element-workflow.md` when generating, replacing, embedding, or arranging visual elements.

Load `references/image2-element-workflow.md` when creating graphical abstracts, mechanism diagrams, body concept models, or any figure where a plain box-and-icon workflow would look generic or AI-like.

Load `references/style-decision-gate.md` before image2 generation unless the user already gave clear style and layout requirements or explicitly asked you to proceed without a design check.

Load `references/boxed-manuscript-style.md` when the target is a paper graphical abstract, concept model, synthesis figure, or any figure that should resemble a journal manuscript figure rather than a slide dashboard.

Core rules:

- Keep all scientific text editable in draw.io.
- Use raster/image elements for things like aquifer media, rivers, villages, recharge, wells, redox patches, or evidence icons.
- Reuse existing clean elements when available; otherwise call image2 or the available image generation tool to create a consistent element sheet before splitting and embedding it.
- Do not default to 3D or isometric elements. Prefer clean 2D scientific vector, soft scientific illustration, or cross-section cutaway styles unless the user selects 3D/isometric or the figure clearly benefits from it.
- Follow the Required Gate in `references/image2-element-workflow.md`: multiple embedded image elements, never one full-canvas image.
- Do not settle for generic flowchart icons when the figure needs paper-specific subjects. Use image2/generated pictorial elements to carry the scientific scene, then keep text and arrows editable.
- Do not use hand-drawn draw.io mountains, clouds, rivers, trees, wells, or factories as the main subject elements for graphical abstracts or mechanism figures. Those are acceptable only as minor schematic marks inside a mostly element-based figure.
- If replacing old elements, replace all related elements from the same family so styles match.
- Embed image data in the `.drawio` so the file remains portable.
- Do not leave the final figure dependent on temporary image paths.

## Terminology Guardrails

Use conservative process language unless the manuscript directly proves the process.

Avoid over-strong terms:

- `rapid recharge` -> `recharge-linked dilution/mixing` or `valley recharge`
- `flushing` -> `dilution-mixing` unless seasonal flushing is measured
- `contaminant plume` -> `input-disturbance signal` or `conceptual solute-enrichment signal`
- `source attribution` -> `boundary conditions` or `context`
- `denitrification confirmed` -> `possible NO3 attenuation` or `redox-associated low-NO3 state`
- `diagnostic gain` / `accuracy gain` -> `rule-based separation`

Chemical notation:

- Use HTML notation such as `NO<sub>3</sub><sup>-</sup>` or consistent Unicode notation.
- Use `Cl<sup>-</sup> vs NO<sub>3</sub><sup>-</sup>/Cl<sup>-</sup>`, not a dash expression that looks like subtraction.
- Keep `Fe`, `Mn`, and `NH4` notation consistent with the manuscript.

Language and portability:

- The generated `.drawio` may contain Chinese, Unicode scientific symbols, Greek letters, and formatted chemical notation when appropriate.
- Write files in UTF-8-compatible ways and avoid assuming Windows-only paths or fonts.
- For maximum draw.io editability, prefer HTML subscript/superscript inside labels when chemical notation must survive cross-platform editing.

## A4/Journals QA

Load `references/qa-checklist.md` before calling the figure done.

Minimum QA:

- At A4 page width, all labels are readable.
- No image element covers a label, arrow, or frame.
- Arrows do not pass through text.
- Arrows point to a group when the meaning is group-level, not to one misleading output.
- Legends are optional; if used, they should not look like a note for one panel.
- The figure has a clear left-to-right or top-to-bottom reading path.
- The figure does not look like a generic slide template or AI workflow card. If it does, redesign with larger subject-matter elements and fewer boxes.
- The figure does not look like a dashboard or presentation slide. Text boxes carry the scientific claims, and images support those boxed claims.
- For graphical abstracts, mechanism diagrams, and body concept models, the file contains embedded raster subject elements generated by image2 or reused from a project element set.
- Split-image verification reports multiple embedded image cells and no single large full-figure or element-sheet image.
- The final `.drawio` is the deliverable.

## Output Naming

Use clear names:

- `graphical_abstract_<version>.drawio`
- `concept_model_<version>.drawio`
- `Fig10_ConceptualModel.drawio`
- `Graphical_Abstract.drawio`

When working in a manuscript package, place editable outputs in an `Editable_Figures` or `Graphical_Abstract` folder if present.

## Final Handoff Note

When returning the finished `.drawio`, include a short editing note in the user's language. Infer the language from the user's current request and conversation. If the user writes in Chinese, use Chinese. If the user writes in English, use English. If the conversation is mixed, use the dominant language or the language used in the latest request.

Chinese template:

```text
后续可以在 draw.io 官网继续编辑：https://app.diagrams.net/
打开网页后，如果提示选择存储位置，选本地/设备存储即可；然后把 `.drawio` 文件拖进浏览器窗口。图像元素可以继续移动、缩放和替换，文字框、箭头、分区框和标签也仍然可编辑。
```

English template:

```text
Continue editing in the official draw.io editor: https://app.diagrams.net/
Open the site, choose local/device storage if prompted, then drag the `.drawio` file into the browser window. The image elements can be moved/resized/replaced, and the text boxes, arrows, frames, and labels remain editable.
```
