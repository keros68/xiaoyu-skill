# Pre-Submission Evidence Safeguards

Read this file when a guideline retrieval is weak, a same-journal benchmark is sparse, or a proposed finding could overstate the evidence.

## Guidelines

- Never substitute an Elsevier, Wiley, ACS, Springer Nature, or Taylor & Francis publisher-wide default for the target journal's requirements. That can reverse a requirement such as graphical abstract, reference style, abstract limit, or keyword range.
- Do not treat security checks, cookie pages, access-denied output, or a generic journal-information page as guideline text. Use the fallback sequence and report `Unable to assess` if current official requirements cannot be established.
- Third-party aggregators and search results are fallback evidence only. They cannot produce a confirmed P0; identify the source and ask for official confirmation before submission.
- Do not use OpenAlex to locate Author Guidelines. Use it for journal identity and same-journal article discovery.

## Same-journal benchmarks

- Search by journal ISSN **and** topic keywords. ISSN alone overweights unrelated, highly cited papers.
- Prefer recent research articles and report the usable sample. Fewer than five exemplars is low confidence; fewer than three cannot support a convention claim.
- Exclude papers with no usable abstract from abstract-length and language statistics. Try Semantic Scholar, then OpenAlex inverted abstracts, then clean Crossref abstracts; record the usable count.
- Do not estimate Elsevier article length from Crossref `page`: article numbers are common. Parse an OA full text only when length matters.
- Use median and IQR for small, skewed samples. Treat style alignment as P1/P2 evidence, never a hard journal requirement.
- Require at least three usable OA full texts before making language-style observations; otherwise mark the analysis insufficient.

## Scope and reporting

- Do not benchmark by a famous article, citation count, or venue identity alone. Topic match and article type matter.
- Do not combine discovery labels with pre-submission P0/P1/P2/Pass/Unable-to-assess statuses.
- Keep every recommendation diagnostic: issue, evidence, risk, revision direction, and source status. Do not rewrite the manuscript or simulate a reviewer unless the user explicitly switches tasks.
