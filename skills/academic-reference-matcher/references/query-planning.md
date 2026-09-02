# Query Planning

Use this for bounded Add or Replace work with multiple claims, Chinese text, long input, or a need for higher search quality. It does not authorize topic expansion.

## Segment IDs

For multi-claim input, split text into citable segments and assign stable IDs:

- `S001`, `S002`, ... for sentence-level or clause-level claims.
- Keep the original wording next to each ID.
- Merge only claims that can be supported by the same kind of source.
- Do not split so aggressively that every phrase becomes a claim.

## Claim Types

Label each segment before searching:

- empirical result
- causal or mechanistic claim
- comparison or trend
- method, dataset, software, or benchmark
- definition or taxonomy
- guideline, standard, regulation, or policy
- historical or bibliographic fact

The claim type determines the source type. For example, causal claims need direct empirical or mechanistic evidence; definitions may use standards, textbooks, reviews, or official docs.

## Query Families

Build 2-4 query families per important claim:

1. Exact phrase: distinctive terms from the claim in quotes.
2. Concept blocks: core entity + mechanism/method + outcome.
3. Study type: add review, randomized trial, benchmark, dataset, guideline, protocol, standard, or meta-analysis when relevant.
4. Known identifier: DOI, PMID, arXiv ID, author-year, dataset accession, or standard number.

For Chinese text, search both:

- original Chinese terms and institution/place names;
- English technical terms, Latin names, abbreviations, gene/protein/material names, disease names, and method names.

## Query Drift Checks

After finding candidates, compare each result against the original segment:

- Does the candidate answer the same claim, not just the same topic?
- Does it match population, species, geography, material, model, software version, or time period?
- Does it support the direction of the claim, not merely mention both variables?
- Is it an original source, review, guideline, dataset paper, or secondary summary?

If the query starts returning a neighboring topic, rewrite from the original segment instead of continuing down that path.

## Bounded Stop Rule

Stop a claim search when at least one direct supporting source is found and a different source route fails to produce a better match. Continue when:

- the best match is only metadata-only or abstract-only;
- the claim is central to the argument;
- the evidence is contested, clinical, legal, regulatory, or high-stakes;
- the user requested a defined date range or bounded source set.

Keep query families tied to the supplied segment. If a result exposes a neighboring research question, record it only as out of scope; do not pursue it.
