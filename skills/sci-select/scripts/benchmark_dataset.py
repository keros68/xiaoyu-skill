"""Build reproducible, blinded sci-select benchmark datasets and annotation sheets."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import random
import re
import time
from pathlib import Path
from typing import Dict, Iterable, List, Sequence
from urllib.parse import quote

import requests


CROSSREF_WORKS_URL = "https://api.crossref.org/works"
MIN_CASES = 50
MAX_CASES = 100
FIT_LABELS = {"suitable", "borderline", "unsuitable"}
NON_ARTICLE_SIGNALS = re.compile(
    r"\b(conference|symposium|congress|workshop|meeting abstract)\b",
    re.IGNORECASE,
)
CONFERENCE_VENUE_SIGNALS = re.compile(
    r"\b(conference series|conference proceedings|proceedings of the .+ conference)\b",
    re.IGNORECASE,
)
# Corpus-only exclusion for a journal with disputed current index status. This
# does not affect journal discovery or recommendation.
BENCHMARK_EXCLUDED_JOURNALS = {"appliedmathematicsandnonlinearsciences"}
QUERY_STOPWORDS = {
    "and", "data", "for", "from", "in", "of", "on", "the", "to", "using", "with",
}

TOPIC_STRATA = [
    ("hydrogeology", "groundwater nitrate hydrochemistry"),
    ("medical-imaging", "cancer radiomics medical imaging"),
    ("photovoltaics", "perovskite solar cell stability"),
    ("ecology", "ecosystem services land use change"),
    ("agriculture", "smart agriculture crop production"),
    ("clinical-nlp", "clinical natural language processing"),
    ("work-sociology", "platform workers occupational health qualitative"),
    ("energy", "hybrid energy storage grid integration"),
    ("neuroscience", "Alzheimer MRI classification"),
    ("geochemistry", "sedimentary provenance geochemistry"),
    ("economics", "inflation monetary policy household"),
    ("education", "student assessment learning analytics"),
    ("law", "digital privacy data protection law"),
    ("linguistics", "multilingual discourse language acquisition"),
    ("catalysis", "heterogeneous catalysis materials"),
    ("epidemiology", "population epidemiology risk factors"),
    ("robotics", "autonomous robot navigation"),
    ("astronomy", "exoplanet stellar observation"),
    ("optimization", "combinatorial optimization algorithm"),
    ("psychology", "mental health psychological intervention"),
]


def sample_crossref_manifest(
    per_stratum: int = 3,
    seed: int = 20260711,
    timeout: int = 45,
) -> List[Dict]:
    """Return a deterministic 50-100 case DOI manifest without storing abstracts."""
    manifest: List[Dict] = []
    used_dois = set()
    used_journals = set()
    for stratum_index, (stratum, query) in enumerate(TOPIC_STRATA):
        response = _crossref_get(
            CROSSREF_WORKS_URL,
            params={
                "query": query,
                "filter": (
                    "from-pub-date:2023-01-01,until-pub-date:2025-12-31,"
                    "type:journal-article,has-abstract:true"
                ),
                "rows": 200,
                "sort": "relevance",
                "order": "desc",
            },
            timeout=timeout,
        )
        items = response.json().get("message", {}).get("items", [])
        eligible = []
        query_terms = {
            term
            for term in re.findall(r"[a-z0-9]+", query.lower())
            if len(term) >= 4 and term not in QUERY_STOPWORDS
        }
        for item in items:
            doi = str(item.get("DOI") or "").lower().strip()
            title = _first(item.get("title"))
            abstract = _clean_abstract(item.get("abstract", ""))
            journal = _first(item.get("container-title"))
            if not doi or doi in used_dois or not title or not journal or not item.get("ISSN"):
                continue
            journal_key = _normalize_journal(journal)
            if journal_key in used_journals or journal_key in BENCHMARK_EXCLUDED_JOURNALS:
                continue
            if not 800 <= len(abstract) <= 6000:
                continue
            if int(item.get("reference-count") or 0) < 8:
                continue
            if NON_ARTICLE_SIGNALS.search(title) or CONFERENCE_VENUE_SIGNALS.search(journal):
                continue
            searchable = f"{title} {abstract} {' '.join(item.get('subject') or [])}".lower()
            matched_terms = {
                term
                for term in query_terms
                if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", searchable)
            }
            if len(matched_terms) < min(2, len(query_terms)):
                continue
            eligible.append(item)
        eligible.sort(
            key=lambda item: (
                -float(item.get("score") or 0),
                -int(item.get("is-referenced-by-count") or 0),
                hashlib.sha256(
                    f"{seed}:{stratum_index}:{item.get('DOI', '')}".encode("utf-8")
                ).hexdigest(),
            )
        )
        selected_journals = set()
        for item in eligible:
            journal_key = _normalize_journal(_first(item.get("container-title")))
            if not journal_key or journal_key in selected_journals or journal_key in used_journals:
                continue
            doi = str(item["DOI"]).lower().strip()
            used_dois.add(doi)
            selected_journals.add(journal_key)
            used_journals.add(journal_key)
            manifest.append(
                {
                    "case_id": f"B{len(manifest) + 1:03d}",
                    "doi": doi,
                    "stratum": stratum,
                    "query": query,
                }
            )
            if len(selected_journals) >= per_stratum:
                break
        if len(selected_journals) < per_stratum:
            raise ValueError(
                f"Stratum {stratum} yielded {len(selected_journals)}/{per_stratum} eligible cases"
            )
    if not MIN_CASES <= len(manifest) <= MAX_CASES:
        raise ValueError(f"Benchmark must contain {MIN_CASES}-{MAX_CASES} cases; got {len(manifest)}")
    return manifest


def materialize_benchmark(
    manifest: Sequence[Dict],
    output_dir: str,
    seed: int = 20260711,
    holdout_fraction: float = 0.3,
    timeout: int = 30,
) -> Dict:
    """Fetch manuscript inputs while sealing original-journal metadata separately."""
    if not MIN_CASES <= len(manifest) <= MAX_CASES:
        raise ValueError(f"Benchmark must contain {MIN_CASES}-{MAX_CASES} cases")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    records = []
    truth = []
    for row in manifest:
        response = _crossref_get(
            f"{CROSSREF_WORKS_URL}/{quote(str(row['doi']), safe='')}",
            timeout=timeout,
        )
        item = response.json().get("message", {})
        abstract = _clean_abstract(item.get("abstract", ""))
        if not abstract:
            raise ValueError(f"Crossref record no longer exposes an abstract: {row['doi']}")
        records.append(
            {
                "case_id": row["case_id"],
                "title": _first(item.get("title")),
                "abstract": abstract,
                "keywords": list(item.get("subject") or [])[:8],
                "stratum": row.get("stratum", ""),
            }
        )
        truth.append(
            {
                "case_id": row["case_id"],
                "doi": row["doi"],
                "original_journal": _first(item.get("container-title")),
                "original_issns": list(item.get("ISSN") or []),
            }
        )

    by_stratum: Dict[str, List[str]] = {}
    for row in records:
        by_stratum.setdefault(row.get("stratum", "unstratified"), []).append(row["case_id"])
    holdout_ids = set()
    for stratum, case_ids in sorted(by_stratum.items()):
        random.Random(f"{seed}:{stratum}").shuffle(case_ids)
        stratum_holdout = max(1, round(len(case_ids) * holdout_fraction))
        holdout_ids.update(case_ids[:stratum_holdout])
    split = {
        row["case_id"]: ("holdout" if row["case_id"] in holdout_ids else "development")
        for row in records
    }
    dev = [row for row in records if split[row["case_id"]] == "development"]
    holdout = [row for row in records if split[row["case_id"]] == "holdout"]
    sealed = [{**row, "split": split[row["case_id"]]} for row in truth]

    paths = {
        "development_inputs": output / "development_inputs.json",
        "holdout_inputs": output / "holdout_inputs.json",
        "sealed_auxiliary_truth": output / "sealed_auxiliary_truth.json",
    }
    _write_json(paths["development_inputs"], dev)
    _write_json(paths["holdout_inputs"], holdout)
    _write_json(paths["sealed_auxiliary_truth"], sealed)
    metadata = {
        "schema": "sci-select-benchmark-v1",
        "cases": len(records),
        "development_cases": len(dev),
        "holdout_cases": len(holdout),
        "seed": seed,
        "holdout_fraction": holdout_fraction,
        "split_strategy": "stratified_by_topic",
        "hashes": {key: _sha256(path) for key, path in paths.items()},
        "rule": "Original journal is auxiliary metadata, not the primary relevance label.",
    }
    _write_json(output / "benchmark_manifest.json", metadata)
    return metadata


def build_annotation_sheet(
    predictions: Sequence[Dict],
    output_csv: str,
    rater_ids: Iterable[str] = ("rater_1", "rater_2"),
    max_candidates: int = 20,
    nominations: Sequence[Dict] = (),
) -> int:
    """Create a blinded sheet over pooled system candidates and expert nominations."""
    pool: Dict[str, Dict[str, Dict]] = {}
    for case in predictions:
        case_pool = pool.setdefault(str(case["case_id"]), {})
        for rank, candidate in enumerate(case.get("candidates", [])[:max_candidates], 1):
            journal = candidate.get("journal") or candidate.get("name") or ""
            key = _normalize_journal(journal)
            if key and key not in case_pool:
                case_pool[key] = {"journal": journal, "rank": rank}
    for nomination in nominations or []:
        case_id = str(nomination.get("case_id") or "").strip()
        journal = str(
            nomination.get("journal") or nomination.get("candidate_journal") or ""
        ).strip()
        key = _normalize_journal(journal)
        if case_id and key:
            pool.setdefault(case_id, {}).setdefault(
                key, {"journal": journal, "rank": ""}
            )

    rows = []
    for case_id, candidates in pool.items():
        blinded_candidates = sorted(
            candidates.values(),
            key=lambda candidate: hashlib.sha256(
                f"{case_id}:{_normalize_journal(candidate['journal'])}".encode("utf-8")
            ).hexdigest(),
        )
        for candidate in blinded_candidates:
            for rater_id in rater_ids:
                rows.append(
                    {
                        "case_id": case_id,
                        "candidate_journal": candidate["journal"],
                        "rater_id": rater_id,
                        "fit_label": "",
                        "community_match": "",
                        "journal_scope_type": "",
                        "scope_checked": "",
                        "notes": "",
                    }
                )
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)
    return len(rows)


def _normalize_journal(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _clean_abstract(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html.unescape(str(value or "")))
    return re.sub(r"\s+", " ", text).strip()


def _first(value) -> str:
    if isinstance(value, list):
        return str(value[0] if value else "").strip()
    return str(value or "").strip()


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _crossref_get(url: str, params: Dict | None = None, timeout: int = 30):
    retryable = {429, 500, 502, 503, 504}
    last_error = None
    for attempt in range(3):
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": "sci-select-benchmark/1.0"},
                timeout=timeout,
            )
            if response.status_code not in retryable:
                response.raise_for_status()
                return response
            last_error = requests.HTTPError(f"Crossref HTTP {response.status_code}")
        except requests.RequestException as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(2**attempt)
    raise last_error or requests.RequestException("Crossref request failed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a blinded sci-select benchmark dataset.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    sample = subparsers.add_parser("sample-manifest")
    sample.add_argument("--output", required=True)
    sample.add_argument("--per-stratum", type=int, default=3)
    sample.add_argument("--seed", type=int, default=20260711)
    materialize = subparsers.add_parser("materialize")
    materialize.add_argument("--manifest", required=True)
    materialize.add_argument("--output-dir", required=True)
    materialize.add_argument("--seed", type=int, default=20260711)
    annotation = subparsers.add_parser("annotation-sheet")
    annotation.add_argument("--predictions", required=True)
    annotation.add_argument("--output", required=True)
    annotation.add_argument("--nominations", default="")
    args = parser.parse_args()

    if args.command == "sample-manifest":
        _write_json(Path(args.output), sample_crossref_manifest(args.per_stratum, args.seed))
    elif args.command == "materialize":
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        print(json.dumps(materialize_benchmark(manifest, args.output_dir, args.seed), indent=2))
    else:
        predictions = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
        nominations = (
            json.loads(Path(args.nominations).read_text(encoding="utf-8"))
            if args.nominations
            else []
        )
        print(build_annotation_sheet(predictions, args.output, nominations=nominations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
