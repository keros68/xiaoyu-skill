# Draw.io Element Workflow

Use this reference when creating or revising an editable draw.io figure with visual elements.

## Build Strategy

1. Create a new `.drawio` or copy the user's existing `.drawio`.
2. Keep labels, boxes, arrows, and layout editable.
3. Use embedded image2/generated or project image elements for the main scientific visuals.
4. Keep a consistent visual language across elements.
5. Do not export final PNG/SVG/PDF unless the user asks.

## Element Sources

Prefer, in order:

1. Existing clean project elements that match the figure.
2. Elements from a previous figure in the same manuscript, if style-compatible.
3. A newly generated image2 element sheet.

For graphical abstracts, mechanism diagrams, and body concept models, prefer an image2 element sheet over generic flowchart icons. See `image2-element-workflow.md` for the generation, splitting, and cleanup workflow.
For those figure types, this is a hard gate: do not make the main scene from draw.io primitive shapes unless the user explicitly requests a shape-only figure.

When generating elements, ask for or infer:

- target figure role
- scientific subjects
- style: clean scientific illustration, light watercolor, crisp edges, no text
- background: flat removable chroma-key or white

Common manuscript elements:

- study setting or landscape
- aquifer medium blocks
- fracture bedrock
- recharge/weather icon
- monitoring well
- solute-enrichment signal
- redox/reducing patches
- evidence icons
- output/status icons

Do not use decorative icons or hand-drawn draw.io primitives as a substitute for scientific subject matter. If the figure needs aquifer media, recharge, flow paths, solute signals, landscapes, sampling objects, model systems, or basin settings, those should be recognizable pictorial elements, not generic cards with small icons.

## Splitting Generated Elements

Follow the Required Gate in `image2-element-workflow.md`: multiple embedded image elements, never one full-canvas image.

If using an element sheet, crop each element into its own transparent PNG (remove the chroma-key background), check a preview sheet on white background, and fix any remaining edge artifacts or fragments from adjacent cells.

Array-safety note: when computing chroma-key color distance in Python, cast RGB arrays to `int32` before squaring.

## Embedding in Draw.io

Embed image data in the `.drawio` file so it is portable. In draw.io image style, this format is often safer:

```text
image=data:image/png,<base64 data>;
```

If the exported preview shows broken image icons, the data URI may be wrong. Try removing `;base64` from the image style.

After embedding, run the QA verification script from SKILL.md (or inspect the XML manually) to confirm the Required Gate in `image2-element-workflow.md`: multiple embedded image elements, never one full-canvas image.

## Layout Rules

- Make pictorial elements large enough to carry the subject.
- Put text beside or above the element, not on top of detailed image areas.
- Put the main scientific claim in editable text boxes, not only in image captions or icons.
- Align same-role boxes to the same size.
- Align similar image elements to a similar visual scale unless the concept needs a hierarchy.
- Use draw.io primitive shapes mainly for frames, arrows, labels, simple charts, and highlights, not for the main subject illustrations.
- Prefer white canvas, thin stroked frames, and light role-based fills over large tinted dashboard panels.
- For manuscript concept figures, use column or layer headings plus boxed claims rather than three oversized slide cards.
- Do not let arrows cross text.
- Prefer direct group-to-group arrows for graphical abstracts.
- Avoid arrows that make one output look like the only target of a group-level process.
- If the user intends manual edits, leave comfortable whitespace around key groups.
