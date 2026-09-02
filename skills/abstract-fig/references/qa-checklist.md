# QA Checklist

Use this before saying the draw.io figure is ready.

## Readability

- Main headings are readable at A4 page width.
- Small labels are still readable after expected scaling.
- Labels are short enough to fit comfortably.
- No label relies on tiny superscript/subscript that will disappear.

## Overlap

- No image covers text.
- No label covers an important image detail.
- No arrow passes through text.
- No icon touches a frame or other icon awkwardly.
- Pictorial elements of the same role have similar visual size.
- Bottom takeaway text, if present, is not clipped.

## Arrow Semantics

- Solid arrows mean process/evidence flow.
- Dashed arrows mean context/boundary conditions.
- If a legend is used, it is placed globally, not inside one panel where it could be misread.
- A group-level arrow points to the group, not a single output box.
- Remove decorative arrows that do not clarify reading order.

## Scientific Wording

- Avoid unsupported process certainty.
- Separate context/boundary conditions from source attribution.
- Do not label conceptual solute signals as mapped plumes unless the manuscript proves a plume.
- Use `Cl- vs NO3-/Cl-` wording, not a dash that looks like subtraction.
- Keep chemical notation consistent with the manuscript.
- Do not simplify Chinese, Greek letters, subscripts, superscripts, or chemical notation to ASCII just for platform convenience.

## Manuscript Visual Quality

- The figure does not look like a generic slide template.
- The figure does not look like a dashboard unless the user explicitly requested that style.
- White or near-white canvas dominates; large tinted section cards are avoided unless they are necessary for grouping.
- Editable boxed claims explain the scientific logic; image elements support those claims.
- Main subject elements are visible without zooming.
- The figure uses paper-specific visual elements rather than generic icons when presenting mechanisms or a graphical abstract.
- For graphical abstracts, mechanism diagrams, and body concept models, the main subject elements are embedded raster/image elements from image2 or a reused project element set.
- Draw.io primitive shapes are used mainly for frames, arrows, labels, highlights, and simple charts, not as the main landscape or mechanism illustrations.
- Repeated boxes are minimized unless the figure is explicitly a methods workflow.
- If it looks AI-like, rebuild the visual anchors with image2/project elements before calling it done.

## Editability

- Text remains editable.
- Boxes and arrows remain editable.
- Raster image elements are embedded in the `.drawio`.
- Follow the Required Gate in `image2-element-workflow.md`: multiple embedded image elements, never one full-canvas image.
- The original source figure remains untouched.

## Deliverable

- Return the `.drawio` path.
- Report the element source, split element folder path, split PNG count, and embedded image-cell count.
- Include the official draw.io editing link `https://app.diagrams.net/` and tell the user they can drag the `.drawio` file into the browser to continue editing.
- Do not produce final PNG/SVG/PDF unless requested.
- If a temporary preview was created for QA, say it is only a preview and not the default deliverable.
