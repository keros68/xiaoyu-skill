# sci-select Common Mistakes (Extended)

Read this file when triaging a candidate-journal report for subtle errors, doing a deeper QA pass on the pipeline, or investigating why a recommendation looks wrong. SKILL.md's "Common Mistakes" section keeps only the ten highest-frequency pitfalls; this file holds the rest.

- Do not equate `1区/2区/3区` with `冲刺/主投/稳妥/保底`; default output reports objective journal levels only.
- Do not silently treat a third-party static index as authoritative when it conflicts with LetPub, JCR, Clarivate, or known status overrides.
- Do not merge two records by ISSN alone when their normalized journal titles are incompatible. Prefer an exact title match and reject mismatched identity data.
- Do not describe the bundled sci-select SQLite as copied from ShowJCR. ShowJCR can be one possible local import source, but runtime uses sci-select's own schema.
- Do not commit raw Excel source files, ShowJCR `jcr.db`, ShowJCR source code, temporary generated JSON indexes, or cache files into the repository.
- Do not treat publisher Journal Finder suggestions as neutral quality judgments; use them only as optional manual cross-checks.
- Do not add automated login, account-state reuse, CAPTCHA bypass, or publisher-site scraping to the default workflow.
