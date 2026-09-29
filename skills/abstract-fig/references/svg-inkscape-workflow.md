# Script-Generated SVG with Inkscape

Use when the figure is built by a script (Python, R) as SVG, or when the user edits figures in Inkscape. Draw.io remains the default when no route is established.

## Build

- Generate the SVG from a versioned script that reads archived results and existing assets. Write run metadata: script and output checksums, input files, parameters, and time. Support an output-directory switch so candidates do not overwrite the current figure.
- Group objects into named Inkscape layers (`inkscape:groupmode="layer"`, `inkscape:label`) by module, and give editable objects stable ids. Later revisions can then modify specific elements.
- Reuse existing vector paths such as a map outline extracted from a published figure PDF instead of redrawing geographic shapes by hand.
- Embed photographs as original bytes with editable clipping; do not resample them into the SVG. Remove EXIF before embedding when the data are not public.
- Write subscripts and superscripts as `<tspan baseline-shift="sub">` (or `super`) with a reduced font size. Do not use Unicode subscript characters such as ₂ and ₃: some PDF readers show them as boxes and text extraction breaks.
- Set one font family for the whole figure and check that it is installed on the machine that exports.

## Revise

- When the user supplies a hand-edited SVG, parse that file and modify elements by id. Preserve untouched elements byte for byte where possible.
- Keep each version in its own folder; move superseded scripts to an archive with a note of what the new version changes.

## Export and check

- Export with Inkscape itself (`inkscape in.svg --export-type=pdf,png --export-dpi=600`), not only with a browser or another renderer.
- Re-render the exported PDF to PNG and inspect it at the target width. Check page size, text extraction of key numbers (`pdftotext`), and that vector parts contain no unintended bitmaps.
- Deliver the SVG as the editable source together with PDF and PNG.
