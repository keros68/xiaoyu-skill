# Example Requests

These requests supply a bounded text, claim, citation, or bibliography. They do not ask the skill to build a topic-level corpus.

## Add References To An English Paragraph

```text
Use $academic-reference-matcher in Add mode. Match 2–4 scholarly references to the citation-worthy claims in this paragraph, use APA style, and include a claim-reference table with confidence labels:

[paste paragraph]
```

Expected behavior:

- extract only claims that need citation;
- search for direct scholarly support without adding claims or topics;
- insert citations next to supported claims and mark the rest unverified.

## Verify Existing Citations

```text
Use $academic-reference-matcher in Verify mode. Check whether each citation already attached to this paragraph supports its claim. Keep the output as a table; do not search for replacements unless identity or status cannot be resolved.

[paste paragraph with citations]
```

Expected behavior:

- assess the supplied citations before supplementary lookup;
- keep correct citations and flag weak, wrong, inaccessible, or unverifiable ones;
- offer Replace as a separate next step rather than silently substituting sources.

## Replace Weak Citations

```text
Use $academic-reference-matcher in Replace mode. For these three marked claims, find a more direct replacement for the existing citation. Show a replacement table and wait for my confirmation before rewriting the paragraph.

[paste bounded claims and citations]
```

Expected behavior:

- preserve each claim's meaning;
- show current and proposed citations, evidence basis, rationale, confidence, and caveats;
- make no batch text change before confirmation.

## Format A Known Bibliography

```text
Use $academic-reference-matcher in Format mode. Convert these known references to GB/T 7714 and return BibTeX. Do not search for new papers; flag records with missing fields.

[paste references]
```

## Extract Claims Only

```text
Use $academic-reference-matcher in Extract mode. List the citation-worthy claims in this introduction with stable segment IDs. Do not search for or recommend references.

[paste text]
```

## Long Or High-Risk Text

```text
Use $academic-reference-matcher in Add mode for this clinical guideline section. It has 14 citable claims. First trial 3–5 representative claims, show evidence quality and source-status limits, then wait for my confirmation before processing the rest.

[paste bounded section]
```

## Source Status And No Reliable Match

```text
Use $academic-reference-matcher in Add mode. If no paper directly supports a claim, do not invent one. Include source status with attempted/succeeded/partial/skipped and distinguish a completed no-match search from a search failure.

[paste claim or paragraph]
```

## Outside This Skill's Scope

```text
I need every paper on [broad topic], PRISMA screening, and a systematic-review corpus.
```

Expected behavior: explain that this skill does not perform topic-level comprehensive retrieval or PRISMA/systematic-review corpus construction; request a bounded text or claim for citation matching instead.
