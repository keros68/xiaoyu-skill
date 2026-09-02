# Source Routing

Use this after a usable search route exists and the claim type is known. Choose the smallest route set that can supply direct evidence; this table does not define evidence strength or search logging.

| Claim need | First route | Useful second route |
|---|---|---|
| DOI/title/author-year check | DOI.org, Crossref, publisher | OpenAlex or Semantic Scholar |
| Biomedical result | PubMed, Europe PMC, publisher | Crossref or OpenAlex |
| Clinical guidance | Issuing guideline body, PubMed | Government or publisher |
| Computer science / AI | Conference/publisher, arXiv, ACM/IEEE | Semantic Scholar or OpenAlex |
| Physics / mathematics | arXiv, ADS when available, publisher | Crossref |
| Dataset / benchmark | Dataset repository, dataset paper, official docs | OpenAlex or Semantic Scholar |
| Standard / regulation / policy | Issuing body or regulator | Scholarly commentary for context only |
| Social science | Field journal, Crossref, OpenAlex, SSRN as appropriate | Official report |
| Chinese policy, standard, local dataset | Official Chinese record or repository | Scholarly index for context |

## Version And Freshness

Prefer a peer-reviewed record over its preprint when final results matter; label a retained preprint. Check recent routes for emerging claims and foundational routes for historical claims. Note conflicting title, author, or year metadata as a possible version mismatch.

## Diversity And Stop

For important claims, use two independent routes when practical (for example, PubMed plus a journal page), not two copies of the same metadata. Stop when additional routes return duplicates, adjacent-topic papers, or lower-quality support; record that reason in `search-audit.md` when an audit is required.
