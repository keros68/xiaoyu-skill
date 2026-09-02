# Journal Index Maintenance

Read this file only when building, refreshing, auditing, or packaging a local journal index. It does not change normal lookup behavior.

## Inputs and build

Use a user SQLite override before the bundled index with `SCI_SELECT_JOURNAL_INDEX_DB`. Build a generated sci-select SQLite file from verified local inputs:

```bash
python -m scripts.build_journal_index \
  --cas-2025-xlsx /path/to/cas_2025.xlsx \
  --xinrui-2026-xlsx /path/to/xinrui_2026.xlsx \
  --jcr-file /path/to/jcr_2025.xlsx \
  --nature-index-url https://www.nature.com/nature-index/faq \
  --sqlite-output /path/to/sci_select_journals.sqlite
```

ShowJCR may be a user-supplied database or public CSV input, but do not vendor its code, `jcr.db`, raw CSV, or raw Excel files:

```bash
python -m scripts.build_journal_index \
  --showjcr-db /path/to/jcr.db \
  --sqlite-output /path/to/sci_select_journals.sqlite
```

Lightweight deployments may instead use `SCI_SELECT_JOURNAL_INDEX_PATH` or `_URL` for either `{"meta": {...}, "journals": [...]}` or a bare journal array. Recognized fields include title/ISSN identity, `jif_2025`, `jcr_release_year`, `jcr_data_year`, `jcr_quartile_2025`, `cas_2025`, `xuankan_2026`, Nature Index fields, warning fields, and tags.

## Integrity rules

- Store normalized title keys and JSON payloads in sci-select's schema; it is not a ShowJCR database.
- Prefer compatible ISSN/eISSN identity, then normalized title; reject an ISSN hit with an incompatible title.
- Preserve provenance and release/data years. The 2026 JCR release contains 2025 JIF/JCR data; use fields such as `jif_2025`, `jcr_quartile_2025`, `jcr_release_year=2026`, and `jcr_data_year=2025`.
- Do not commit raw source workbooks, ShowJCR assets, generated temporary JSON, or runtime cache files.
- Before releasing an index, run `python -m scripts.audit_journal_index assets/sci_select_journals.sqlite --sample-size 20 --max-severe-mismatch-rate 0.02` and investigate identity, provenance, duplicate-title, ISSN, and partition-format failures.
