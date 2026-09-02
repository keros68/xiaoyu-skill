# Runtime Data Sources

Use this file only while retrieving or interpreting live journal data. For index construction, input formats, and release auditing, read `index-maintenance.md` instead.

## Source authority and lookup order

Runtime lookup order is user override SQLite (`SCI_SELECT_JOURNAL_INDEX_DB`), local/static JSON (`SCI_SELECT_JOURNAL_INDEX_PATH` or `_URL`), bundled `assets/sci_select_journals.sqlite`, then live public sources. Keep a source-status entry for every material lookup. A returned field is evidence from that source, not a guarantee that all other fields were checked.

| Source | Use for | Do not use as final authority for |
|---|---|---|
| Bundled/user SQLite or JSON index | title-keyed `2025中科院`, `2026新锐`, Nature Index flags; user-verified JCR fields when present | unverified identity or current coverage |
| OpenAlex | similar-work recall, output-normalized precedents, h-index, citedness, OA/APC | JIF, JCR quartile, or current WoS coverage |
| LetPub | public IF, partitions, coverage hints, review-speed text, warning hints, recall fallback | current Clarivate coverage or official scope |
| XinRui WebAPI | optional 2026 XinRui/status fallback with `XINRUI_API_KEY` | scope, quality, or acceptance fit |
| Clarivate Master Journal List / JCR | current SCI/SCIE/SSCI/ESCI coverage and JCR data | scope or manuscript fit |
| Official journal/publisher pages | aims, scope, accepted article types | journal-level or acceptance prediction |

## Runtime rules

- The bundled index intentionally omits unverified ISSN/eISSN, JIF/JCR quartile, and coverage fields. Keep them missing unless a verified override or live source provides them. Accept an ISSN match only when titles are compatible.
- Report CAS only as `2025中科院`: the CAS Documentation and Information Center stopped updating/releasing its table from 2026. Report the newer scheme as `2026新锐`; never write “2026 中科院分区.”
- LetPub's `新锐期刊分区表` is stored only as `xinrui_partition_2026`. Prefer its detail page when public; use the optional XinRui API only as fallback. If neither returns data, retain `未获取` with status/reason.
- OpenAlex requires `OPENALEX_API_KEY`; without it, mark the live check `skipped` and preserve the local specialist-title path. Do not call missing OpenAlex evidence “no similar papers.”
- LetPub and OpenAlex may lag behind Web of Science. If Clarivate coverage was not checked, write `收录需复核`.
- Nature Index is a selective venue flag, not a substitute for IF, JCR, partitions, or scope fit. Show its year when available.
- `Science of the Total Environment` has a known reported WoS/SCIE removal. Do not restore normal SCIE status from stale third-party/cached data; mark `WoS已移除/不推荐` and require Clarivate verification before a submission decision.
- If a local/static partition conflicts with LetPub, retain the local/static field and add `分区来源冲突需复核`. Do not silently merge incompatible identities.

## Missing and partial evidence

`succeeded` with `no matching record` means a completed search found no match. `attempted` means a request failed or yielded unusable material. `partial` means a usable but incomplete page/record. `skipped` means the source was not needed, not configured, or outside scope. Never turn any of these into a guessed field value.
