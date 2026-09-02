# Search Sources

Use this only for Add or Replace after the claim is bounded. It chooses discovery routes; `verification-rubric.md` decides whether a result supports the claim.

## Default Source Order

1. User-provided PDFs, bibliography, DOI list, library export, or manuscript references.
2. Open records: OpenAlex, Crossref, PubMed, Europe PMC, arXiv, Semantic Scholar.
3. Publisher, society, repository, standards-body, government, guideline, trial-registry, or dataset pages.
4. General web search only to find a stable scholarly or official record.

Do not scrape Google Scholar, bypass CAPTCHA, or treat copied search metadata as independent evidence. If the host has no search or browsing capability, request user-provided material instead of simulating a search.

## Query Patterns

Try 2–4 claim-specific query shapes:

- exact phrase or distinctive result terms;
- entity + mechanism/method + outcome;
- source-type term such as `review`, `trial`, `benchmark`, `dataset`, `guideline`, or `standard`;
- known DOI, title, author-year, accession, or standard number.

Use domain-limited queries when only general web search exists: `site:pubmed.ncbi.nlm.nih.gov`, `site:doi.org`, `site:arxiv.org`, or the relevant official/publisher domain. For Chinese source text, search the original terms plus accurate English technical terms and abbreviations.

## Bounded Stop Rule

Stop a claim route after a direct match is verified and one appropriate alternate route produces no better evidence. Continue only when the claim is central, contested, high-risk, or supported only by weak visible evidence. Do not extend a claim search into an open-ended topic scan.
