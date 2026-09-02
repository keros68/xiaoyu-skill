# Research/Technical Roadmap (技术路线图)

Use this reference when the figure is a research or technical roadmap: a diagram of project phases, timeline, milestones, or per-stage methodology, typically for a thesis proposal, grant application, or project report.

A research roadmap is a variant of the **Workflow Figure** (see `figure-types.md`), not a mechanism diagram or a body concept model. It defaults to shape-only draw.io construction and is exempt from the image2 Required Gate in `image2-element-workflow.md` by default. Only pull in image2 elements if the user explicitly asks for a more pictorial, graphical-abstract-style treatment.

Trigger words: 技术路线图, 研究路线(图), 开题报告路线图, 课题路线图, technical roadmap, research roadmap.

## Stage Template Types

| Type | Characteristics | Best for |
|------|------------------|----------|
| Phase-progression (阶段递进型) | Top-to-bottom, each phase in a dashed frame | Theory-driven research, policy analysis |
| Parallel-branch (并行分支型) | Multiple paths advancing at the same time | Comparative experiments, multi-scheme designs |
| Loop/iterative (循环迭代型) | Includes feedback arrows | Algorithm optimization, iterative development |
| Hierarchical decomposition (层级分解型) | Tree-like expansion | System architecture, classification schemes |

## mxCell Style Reference

These are drawio XML style strings specific to roadmap figures. Use them as a starting point, adjusting colors/geometry to the manuscript.

Vertical stage label (left-side phase tag, blue):

```xml
<mxCell id="stage1_label" value="阶段名称"
        style="rounded=0;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;rotation=0;fontSize=12;verticalAlign=middle;"
        vertex="1" parent="1">
  <mxGeometry x="20" y="50" width="40" height="180" as="geometry"/>
</mxCell>
```

Dashed block frame (stage boundary):

```xml
<mxCell id="stage1_frame" value=""
        style="rounded=0;whiteSpace=wrap;html=1;dashed=1;strokeColor=#000000;fillColor=none;"
        vertex="1" parent="1">
  <mxGeometry x="80" y="20" width="760" height="210" as="geometry"/>
</mxCell>
```

Method label (purple, e.g. "literature review"):

```xml
<mxCell id="method1_label" value="文献研究法"
        style="rounded=0;whiteSpace=wrap;html=1;fillColor=#e1d5e7;strokeColor=#9673a6;rotation=0;fontSize=11;verticalAlign=middle;"
        vertex="1" parent="1">
  <mxGeometry x="100" y="340" width="30" height="120" as="geometry"/>
</mxCell>
```

Orange transition arrow (between stages):

```xml
<mxCell id="transition_1_2" value=""
        style="shape=flexArrow;endArrow=classic;html=1;fillColor=#ffe6cc;strokeColor=#d79b00;width=20;endSize=6;"
        edge="1" parent="1">
  <mxGeometry width="50" height="50" relative="1" as="geometry">
    <mxPoint x="460" y="240" as="sourcePoint"/>
    <mxPoint x="460" y="270" as="targetPoint"/>
  </mxGeometry>
</mxCell>
```

Connection point X/Y reference (for `exitX`/`exitY`/`entryX`/`entryY`):

| Position | X | Y |
|----------|---|---|
| left | 0 | 0.5 |
| right | 1 | 0.5 |
| top | 0.5 | 0 |
| bottom | 0.5 | 1 |
| top-left | 0 | 0 |
| bottom-right | 1 | 1 |

Color reference:

| Role | fillColor | strokeColor |
|------|-----------|--------------|
| Stage label (blue) | #dae8fc | #6c8ebf |
| Method label (purple) | #e1d5e7 | #9673a6 |
| Normal node | #ffffff | #000000 |
| Transition arrow (orange) | #ffe6cc | #d79b00 |
| Dashed frame | none | #000000 |

## Layout Heuristics

- Canvas width: 800-1000px, height scales with the number of stages.
- Three-column layout: left stage labels (x 20-60) | main content area (x 80-720) | right labels if needed (x 730-800).
- Per-stage frame height: 150-200px for a simple stage, 200-300px for a medium stage, 300-450px for a complex stage.

## Content Mapping (abstract/proposal text -> roadmap blocks)

| Source text element | Maps to roadmap block |
|----------------------|------------------------|
| Research background (问题/需求/缺口) | "Prior research" block (前期研究) |
| Research methods (理论/工具/技术) | "Theoretical foundation" block (理论基础) |
| Research process (步骤/阶段/流程) | "Research framework" block (研究框架) |
| Research conclusions (策略/建议/贡献) | "Response strategy" block (应对策略) |

Node text length: keep each node label to 4-12 characters. Add or remove nodes to match the source content's actual complexity — do not pad or trim to hit a fixed node count.

## QA

Follow the shared checklist in `qa-checklist.md`, plus these roadmap-specific checks:

- No `XXXX`-style placeholder text remains in any node.
- Every stage has both a vertical stage label and a matching dashed frame.
- Adjacent stages are connected by a transition arrow.
