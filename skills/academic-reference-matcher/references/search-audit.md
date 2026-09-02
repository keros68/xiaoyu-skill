# Search Audit

Use for Standard, Deep, or Audit work. This records a bounded citation-evidence audit, not systematic-review retrieval or PRISMA completeness.

## Compact Audit

```text
Mode and depth: ...
Bounded scope: supplied text/claims, language, date/source limits
Segments: S001–S00N
Source status:
| Route | Status | Reason / result |
| ... | attempted/succeeded/partial/skipped | ... |
Query intent: S001: ...; S002: ...
Accepted evidence: N high, N medium, N low
Rejected candidates: title/year/reason
Stopping reason: ...
```

## Source Status

- `succeeded`: the query completed. Record its outcome, including an accepted/usable candidate or `no direct match found after completed search`.
- `partial`: some results or checking were usable, but access, missing content, rate limits, or another limitation prevented completion; state the precise limitation.
- `attempted`: a query was tried but failed or its results were unusable; state `search failed` or the specific unusable-result reason.
- `skipped`: deliberately not queried because it was unsuitable, duplicate, unavailable before use, or outside the bounded scope; state why.

Never write “not found” when a search failed or was limited, and never describe a completed no-match route as a tool failure.

## Rejection And Integrity

Use specific rejection reasons: wrong claim or scope; background only; superseded preprint; retraction/concern/outdated guidance; metadata-only evidence; or inaccessible content that does not establish support. List only routes actually checked. If tool syntax is hidden, summarize query intent and route. Do not imply exhaustive coverage unless the user supplied a bounded corpus and reproducible strategy; even then, this skill does not conduct PRISMA screening or construct a systematic-review corpus.
