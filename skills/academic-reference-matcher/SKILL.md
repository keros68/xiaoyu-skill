---
name: academic-reference-matcher
description: "Use only for user-provided academic text, explicit scholarly claims, existing citations, or known bibliographies needing citations added, verified, replaced, extracted, or formatted. Supports claim-to-source matching, citation-support checks, replacements, and common academic citation formats. Do not use for general fact-checking, legal/journalistic citation work, open-ended 'find literature about X', topic-level exhaustive discovery, systematic-review corpus construction, PRISMA searches, or creating new research claims. Chinese: 为已有段落补参考文献、核验已有引用、替换错误引用、提取需引文论断、GB/T 7714 格式化."
---

# Academic Reference Matcher

Match evidence to bounded, user-supplied academic claims. This is not an AutoResearch workflow: do not broaden the question, discover a topic-level corpus, or write extra claims.

## Scope gate

Proceed only when the user supplies at least one of: academic text, a discrete claim, citations attached to text, or a known reference list. Ask for the missing text, claim, or bibliography when needed.

Decline or redirect requests for open-ended research questions, comprehensive topic searches, systematic-review screening, PRISMA flow, or claims of complete coverage. Explain that this skill audits or matches citations for a bounded text; it does not build an exhaustive literature corpus.

Never invent bibliographic fields or claim support. Preserve the requested language and style; otherwise use author-year citations and a compact reference list. Report weak support, access limits, and unverified claims plainly.

## Mode shortcut

Choose one mode before work. Do not turn a narrow mode into a search task.

### Add

Match new scholarly evidence to specified uncited claims. Do not add claims or expand the topic.

### Verify

Resolve and assess citations already attached to claims first. Search only to resolve identity, version/status, or a necessary gap; do not proactively find replacements.

### Replace

Diagnose the supplied citation, then match a more direct, current, or valid source to the same claim. Do not change claim meaning or replace in bulk without confirmation.

### Format

Convert known, sufficiently identified references to the requested style. Do not search for new literature or assess relevance; mark missing fields.

### Extract

List citation-worthy claims from supplied text, then stop. Do not search or recommend sources.

## Workflow

1. Bound input: record mode, claims, field, language, date/source limits, style, and risk. For multi-claim work use `S001` IDs; read [query planning](references/query-planning.md) for multi-claim, Chinese, Add, or Replace work.
2. Apply the shortcut. In Verify, compare each citation to its attached claim before supplementary lookup. In Add/Replace, use [search sources](references/search-sources.md); read [source routing](references/source-routing.md) only for domain selection.
3. Check identity and direct support. Read [verification rubric](references/verification-rubric.md) for accepted matches in accuracy-sensitive, multi-candidate, Deep, or Audit work. Read [paywall-aware access](references/paywall-aware-access.md) only for limited access.
4. Insert or propose citations beside the supported claim, then format using [output formats](references/output-formats.md). Every processed claim must be accepted, rejected, or unverified.

## Depth and confirmation

Use the lightest bounded depth:

- Quick — 1–3 claims.
- Standard — a paragraph or short section.
- Deep — a defined long section or disputed claims.
- Audit — a bounded citation-evidence audit.

Depth increases checking and traceability, never topic scope.

For more than 10 citable claims, high-risk claims (clinical, safety, regulatory, or policy), or a requested bulk change, run a representative 3–5-claim sample first. Show the scope, evidence quality, and limitations, then obtain human confirmation before continuing.

Before applying a batch replacement to text, display a replacement table with claim ID, current citation, proposed citation, support rationale, evidence basis, confidence, and caveat. Wait for confirmation; until then label changes as proposals.

Audit is an evidence audit of the supplied, bounded claims—not a systematic-review or PRISMA completeness exercise. State this boundary when a user asks for PRISMA, comprehensive retrieval, or a systematic-review corpus.

## Evidence and source use

Prefer user-provided material and stable scholarly or official records. Search broadly enough to find a direct match, then stop when an alternate appropriate route adds no better evidence. Use two independent routes for important claims when practical; do not count duplicate metadata pages as independent evidence.

Capture bibliographic identity, stable locator, evidence basis, and a one-sentence claim-specific rationale. Evidence tiers, confidence labels, and rejection rules are defined only in [verification rubric](references/verification-rubric.md). Treat titles, keywords, metadata, and citation counts as discovery—not proof—except for bibliographic facts.

## Outputs and traceability

For small tasks, return cited text or the requested narrow result plus references. Use the file bundle and table contracts in [output formats](references/output-formats.md) for Standard+ or requested exports.

For Standard, Deep, or Audit work, read [search audit](references/search-audit.md) and include its compact source-status table. Record each route as `attempted`, `succeeded`, `partial`, or `skipped` with a reason.

Distinguish `no direct match found after a completed search` from `search failed` or `access/tool limited`; neither may be presented as the other.

## Reference map

- [query planning](references/query-planning.md) — segmenting and query families for multi-claim, Chinese, Add, or Replace work.
- [search sources](references/search-sources.md) — default source order and query patterns for Add or Replace.
- [source routing](references/source-routing.md) — domain-specific source selection after a search capability exists.
- [paywall-aware access](references/paywall-aware-access.md) — legal access and evidence limits for inaccessible records.
- [verification rubric](references/verification-rubric.md) — sole source for evidence tiers, scores, and confidence.
- [output formats](references/output-formats.md) — sole source for report, table, export, and style contracts.
- [search audit](references/search-audit.md) — audit scope, source status, rejection, and stopping records.

## Limits

The skill has no built-in database, paid access, or parser. Do not bypass paywalls, CAPTCHA, login walls, or authorization. If no search access exists, request user-provided PDFs, bibliography, DOI list, library export, or search results and verify only that material. Final journal-specific formatting and high-stakes manuscript decisions need human review.
