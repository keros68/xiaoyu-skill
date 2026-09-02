# Output Formats

Follow the user's requested style. If no style is requested, use author-year inline citations and a compact reference list.

## Copy-Ready File Bundle

When the runtime can write files, create file outputs for Standard, Deep, or Audit tasks if the user asks for copy/paste, export, a citation package, or explicit citation formats. Format mode converts supplied references only and does not add search results.

Default file:

- `reference-match-report.md`

Optional files when requested:

- `references-apa.md`
- `references-gbt7714.md`
- `references-vancouver.md`
- `references-ieee.md`
- `references.bib`
- `references.ris`

Keep chat output short: list the created files, summarize the strongest matches, and mention unverified claims or access limits. Do not paste the whole report in chat when the file exists.

Use this `reference-match-report.md` order:

````markdown
# Reference Match Report

## Citation Style

Requested style: ...

## Copy-Ready Cited Text

...

## Claim-Reference Table

| Segment | Claim | Accepted reference | Evidence basis | Confidence | Notes |
|---|---|---|---|---|---|

## References

### APA

...

### GB/T 7714

...

### BibTeX

```bibtex
...
```

## Could Not Verify

...

## Search Audit

...
````

Omit unused style sections unless the user asked for multiple styles. Put BibTeX/RIS in separate files when there are more than 5 references or when the user asks for manager import.

## Multi-Claim Table

| Claim | Mode | Best reference | Support | Evidence basis | Confidence | Notes |
|---|---|---|---|---|---|---|
| Short claim text | Add/Verify/Replace | Author et al., year, title, DOI/URL | One-sentence support rationale | Discovery-only / Abstract-supported / Snippet-supported / Fulltext-supported / Bibliographic-only | High/Medium/Low | Access limits or caveats |

Use `Discovery-only` in the Evidence basis column when a paywalled paper looks relevant from title, keywords, or metadata but has not been verified through abstract, official snippet, full text, user PDF, or another adequate source; add the access limitation in the Notes column.

## Reference Fields

Capture these fields when available:

- Authors
- Year
- Title
- Venue
- DOI
- Stable URL
- PMID, arXiv ID, ISBN, standard number, or dataset accession when relevant

## Style Notes

- APA: author-year inline citations; reference list with DOI URL when available.
- GB/T 7714: numeric or author-year form based on user request; preserve Chinese punctuation if the surrounding text is Chinese.
- Vancouver: numbered citations in order of appearance.
- IEEE: bracketed numbered citations in order of appearance.
- BibTeX/RIS: output machine-readable entries only when requested, and avoid placeholder fields.

## Unverified Claims

Use this section when no reliable match is found:

```text
Could not verify:
- Claim: ...
  Checked: source and query summary
  Best candidates rejected: title/year/why rejected
  Reason: no direct scholarly support found / access unavailable / candidates only weakly related
  Next step: ask user for bibliography/PDF/corpus or revise the claim
```

## Verification Summary

For larger tasks, end with:

```text
Mode and depth: ...
Bounded scope: ...
Source status: see the compact table from `search-audit.md`
Query intent: ...
Accepted references: N
Weak or partial matches: N
Unverified claims: N
Access limits: ...
```

For Deep or Audit tasks, include segment IDs. The sole source for search-audit structure and statuses is `search-audit.md`:

| Segment | Claim | Query families | Accepted reference | Evidence basis | Confidence | Notes |
|---|---|---|---|---|---|---|
