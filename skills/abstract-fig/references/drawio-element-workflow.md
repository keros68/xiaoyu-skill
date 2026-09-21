# Editable Figure Assembly

Use when constructing or revising a draw.io figure. Follow the user's requested alternative format when applicable.

## Source and object structure

Copy or version the original. Keep scientific labels, arrows, group boundaries, and simple schematics as native editable objects. Use real project images and plots for observations, and suitable illustrations for conceptual content; source selection is defined in SKILL.md.

Use native vector primitives for diagrams they express clearly, including subject-specific cross-sections and model structures. Do not force those objects into raster form. Generated illustration handling is optional and described in `image2-element-workflow.md`.

An embedded photograph or map can be one large image object with editable annotations. Avoid flattening a complete multi-module diagram into one bitmap and calling the result editable. Image quantity alone cannot distinguish those cases.

## Image embedding

Embed assets so the file remains portable. A draw.io PNG style commonly uses:

```text
image=data:image/png,<base64 data>;
```

Check the saved file in the actual editor: data-URI handling and font metrics may differ from another renderer. Keep source files and provenance when needed for regeneration. Preserve observation metadata, aspect ratio, and scientific content; record display transformations that matter to interpretation.

Crop generated element sheets into independently movable assets only when that generation method was used. Existing images and vector objects do not need to pass through an element sheet.

## Assembly and preview

Lay out modules and compare their relative sizes before polishing. Give images enough room for meaningful detail, place legends near their subjects, and route group-level connectors to the correct group. Share encodings for comparable panels.

Preserve Chinese, Unicode symbols, and chemical notation. Use appropriate HTML subscript/superscript when needed by the editor. Keep mathematical labels editable to the extent supported by the chosen format, and disclose limitations.

Run `scripts/inspect_drawio_images.py` for structural diagnostics, then render the actual editable file when a compatible editor/exporter is available. The helper accepts compressed and uncompressed draw.io files, including vector-only files. It checks embedded versus external images and flags large images for review; it cannot certify rendering, scientific accuracy, or full editability.

If a script creates both a preview and editable XML, inspect the XML export in the target application as well. When that is unavailable, deliver the useful preview and source with the rendering limitation stated explicitly. Do not equate a successful XML parse with a successful editor rendering.

Deliver the editable source and preview together. Export final publication files according to the request or established workflow.
