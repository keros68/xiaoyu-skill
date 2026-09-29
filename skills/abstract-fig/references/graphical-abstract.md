# Graphical Abstracts

Read when the figure is a journal graphical abstract. General module planning remains in `style-decision-gate.md`.

## Before drawing

- **Check the journal page first.** Record whether the graphical abstract is required or optional, the size and aspect ratio, the file formats, and the policy on generative AI. Separate hard requirements from recommendations: a suggested pixel size or aspect ratio is not a reason to force a layout the author prefers. If the author guidelines cannot be accessed, say so rather than claiming compliance.
- **Generative AI policy decides whether generated elements are usable.** Some publishers (for example Elsevier) do not accept general-purpose generative-AI imagery in graphical abstracts. A draft containing generated elements is then a design sketch only; every generated element must be replaced before submission. Where generated content is allowed, it still needs to be listed in the manuscript's AI declaration.
- **Do not duplicate the conceptual figure.** A graphical abstract shows what was done and what was found: the study setting, the evidence, and the key result. A mechanism or concept figure already in the manuscript should not be repeated.
- **A main-text framework figure is rarely usable as is.** Reduced to the target height, its labels usually become illegible. Rearrange it for the target width.
- **Look at the user's reference collection before choosing a layout.** Classify the references by layout family (below) and follow the family the user collects. A layout chosen on design theory alone, even a well-argued one, is often rejected when it departs from the user's examples.

## Layout families

| Family | Structure | Suits |
|---|---|---|
| Partitioned roadmap | Titled parts (Part 1/2/3 or a/b/c) with tinted or dashed group frames; real maps and small result plots embedded in the frames; arrows between parts | Field and data studies with several lines of evidence; the most common choice for earth-science graphical abstracts |
| Overview plus details | One large map or scene with linked insets or a row of small panels | Spatial results with representative sites |
| Block diagram with magnified callouts | Cutaway or block diagram; circles or boxes enlarge local processes | Mechanisms and process models |
| Stepped narrative | a → b → c panels along one reading direction | Short causal or temporal stories with few results |

Families can be combined. Borrow area allocation, grouping, frame style, and reading path from the references; do not copy their subject matter, software logos, or panel count.

## Content

- **Real data carry the figure.** Use real maps, photographs, and plots generated from the data, plus the key numbers set large. Schematic icons and illustrations support them; they do not replace them. A draft built mainly from illustrations tends to be judged as "the data are missing".
- **One message sentence.** Put it as a title band or a bottom line, matching the manuscript title and evidence strength. Calibrate the wording: "no detected step", "approximated criteria", "partly overlapping sample sets" when those are the facts.
- **Relationships, not section lists.** Show how the evidence is organized: a shared input branching into parallel tests, a comparison, a convergence. Do not draw one box per manuscript section.
- **Sub-panels from different data subsets on one shared axis need a short note.** Otherwise readers take them as one continuous series.
- **Private data stay private.** Do not show sample points, coordinates, site codes, or raw file names when the data are not public. Strip EXIF from photographs and renumber them.

## Consistency with the manuscript

- Read every number from archived result tables by script, and assert each numeric value against the manuscript text. When the brief and the manuscript disagree, the manuscript wins; report the difference.
- Category labels mean the same thing as in the main figures (for example, a grey class is labelled exactly as the main figure defines it).
- Round from counts in the same way as the manuscript.
- When the manuscript changes, regenerate the graphical abstract and update the submission package list that names its version.

## Iteration

- **When the user has edited a version by hand, that file is the base.** Make minimal changes to identified elements (by id or layer) and keep the user's font, proportions, alignment, and wording. Do not re-lay-out the figure.
- **Over-regularization reads as machine-made.** Forcing strict symmetry, equal module sizes, uniform centring, a grid for every object, a recommended aspect ratio, or a new font can turn an accepted draft into one the author rejects. Fix specific problems rather than normalizing everything.
- **Give the core module more area.** Equal three-column and equal 2×2 layouts flatten the hierarchy; the module that carries the main result should be visibly larger.
- Keep every candidate in its own versioned folder with its script and run metadata. Record why a version was rejected so the next version does not repeat it.
