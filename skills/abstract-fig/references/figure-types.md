# Figure Types

Use this reference when deciding how a manuscript idea should become a draw.io figure.

## Graphical Abstract

Purpose: make the paper's core contribution understandable in 5-10 seconds.

Use when the user says graphical abstract, GA, visual summary, ScienceDirect preview, or wants a striking overview figure.

Design:

- Prefer horizontal three-panel flow.
- Use large pictorial elements and very short text.
- Use image2/project pictorial elements as the main visual anchors; avoid a plain box-only workflow. Follow the Required Gate in `image2-element-workflow.md`: multiple embedded image elements, never one full-canvas image.
- Prefer boxed manuscript style: column headings, editable claim boxes, restrained borders, and image elements inside or beside the claims.
- Keep one bottom takeaway sentence at most.
- Do not include detailed methods, data source names, long captions, or caveats.
- Use 2-3 main arrows. Too many arrows makes it look like a method workflow.
- Avoid slide-dashboard structure with oversized tinted cards, subtitle-heavy title bars, and decorative metric widgets unless the user asks for an infographic.

Useful structure:

```text
Surface input + recharge -> Aquifer-media filtering/evidence -> NO3 status
```

## Body Concept Model

Purpose: support the Discussion or mechanism interpretation.

Use when the figure must defend a process interpretation, distinguish contextual constraints from evidence, or explain how outputs are interpreted.

Design:

- Can use 3-4 layers.
- Can show contextual constraints, process domains, evidence, and interpreted states.
- Use dashed arrows for context/boundary constraints and solid arrows for process/evidence flow.
- Use pictorial elements for the main media/process domains, but keep evidence labels and interpretations editable.
- Use boxed claims as the main explanation layer; figures should not rely on images alone to carry the mechanism.
- Keep visual elements subordinate to the conceptual logic.

Useful structure:

```text
Setting -> aquifer media/process -> hydrochemical evidence -> interpreted status
```

## Workflow Figure

Purpose: explain method sequence.

Use when the figure is about data preparation, screening, sensitivity checks, and outputs.

Design:

- Use steps.
- Separate input data, prior grouping, method/sensitivity checks, outputs, and objective.
- Avoid making the workflow look like a management-priority tool unless the manuscript is explicitly about management.

### Research/Technical Roadmap Variant (技术路线图)

Purpose: lay out project phases, timeline, milestones, or per-stage methodology for a thesis proposal, grant application, or project report, rather than a data-processing method sequence.

Use when the user says 技术路线图, 研究路线(图), 开题报告路线图, 课题路线图, research roadmap, or technical roadmap.

Design:

- Defaults to shape-only draw.io construction and is exempt from the image2 Required Gate in `image2-element-workflow.md` by default; only add image2 elements if the user explicitly asks for a more pictorial, graphical-abstract-style treatment.
- See `research-roadmap.md` for stage template types, mxCell style examples, layout heuristics, and content-mapping guidance.

## Synthesis Figure

Purpose: summarize results or mechanism without full method detail.

Use when the manuscript already has method figures but needs one integrative figure.

Design:

- Focus on 2-4 key findings.
- Avoid repeating every result panel.
- Use a small number of visual anchors and larger labels.
