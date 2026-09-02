# Benchmarking sci-select

The committed corpus manifest contains 60 DOI-only cases across 20 strata. Abstracts and the original journal are materialized locally so the repository does not redistribute a bulk abstract corpus and the prediction input does not expose the auxiliary answer.

## Build the blinded dataset

```bash
python -m scripts.benchmark_dataset materialize \
  --manifest benchmarks/corpus_manifest.json \
  --output-dir benchmark_runs/run-001 \
  --seed 20260711
```

This creates a topic-stratified 40-case development split and 20-case holdout split, a separately sealed auxiliary-truth file, and SHA-256 hashes. With the committed 20 strata and three cases per stratum, one case per stratum is held out. Do not inspect holdout labels while changing retrieval or ranking.

The sampler applies generic quality checks (journal article, abstract length, ISSN, references, topic-term coverage, conference/proceedings signals, and unique journals across the corpus). It also keeps a corpus-only exclusion for venues with disputed current index status; this list never affects journal discovery or recommendation. A researcher must still inspect every case before the first scored release because metadata filters cannot establish venue legitimacy or scientific quality.

Run predictions without opening the auxiliary-truth file:

```bash
python -m scripts.benchmark_run \
  --inputs benchmark_runs/run-001/development_inputs.json \
  --profiles benchmark_runs/run-001/independent_profiles.json \
  --output benchmark_runs/run-001/predictions.json \
  --max-candidates 20
```

`--profiles` is optional for smoke testing only. Any cross-disciplinary benchmark result intended for publication must provide independently generated model-neutral profiles. Without them, the runner records `deterministic-fallback`; do not publish metrics from that condition because the fallback keyword rules intentionally cover only a limited set of fields.

## Expert annotation

Build a blinded pool from multiple systems or frozen sci-select versions, then add journals nominated independently by experts. A pool containing only the current system's own candidates will inflate Recall@K.

Create the sheet:

```bash
python -m scripts.benchmark_dataset annotation-sheet \
  --predictions benchmark_runs/run-001/predictions.json \
  --nominations benchmark_runs/run-001/expert_nominations.json \
  --output benchmark_runs/run-001/expert_labels.csv
```

`expert_nominations.json` contains records such as `{"case_id": "B001", "journal": "Journal Name"}`. Prepare it without revealing the original publication venue. The sheet deduplicates normalized journal names across pooled predictions and nominations.

At least two independent researchers must label every pooled candidate without seeing the original journal:

- `fit_label`: `suitable`, `borderline`, or `unsuitable`.
- `community_match`: whether the journal serves the manuscript's research community.
- `journal_scope_type`: `generalist` or `specialist`.
- `scope_checked`: whether the official aims-and-scope page was checked.
- `notes`: short evidence or disagreement notes.

The original journal is auxiliary metadata, not the unique correct label. Do not ask an AI model to impersonate expert raters.

## Score

```bash
python -m scripts.benchmark_score \
  --predictions benchmark_runs/run-001/predictions.json \
  --labels benchmark_runs/run-001/expert_labels.csv \
  --auxiliary-truth benchmark_runs/run-001/sealed_auxiliary_truth.json \
  --output benchmark_runs/run-001/score.json \
  --min-raters 2
```

Primary metrics are community Recall@K, expert-acceptable Recall@K, nDCG@K, and generalist-journal exposure. Exact original-journal Hit@K is reported only as an auxiliary diagnostic. Do not publish accuracy claims until the expert labels are complete and the holdout split has been scored once after model and threshold freeze.

The scorer exits nonzero and writes `ready=false` when any pooled candidate lacks complete labels from the required number of raters.
