"""Score expert-labeled sci-select candidate rankings."""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


FIT_RELEVANCE = {"unsuitable": 0, "borderline": 1, "suitable": 2}
TRUE_VALUES = {"1", "true", "yes", "y", "是"}
FALSE_VALUES = {"0", "false", "no", "n", "否"}


def score_benchmark(
    predictions: Sequence[Dict],
    label_rows: Iterable[Dict],
    cutoffs: Sequence[int] = (3, 5, 10),
    min_raters: int = 2,
) -> Dict:
    """Compute expert relevance metrics; original-journal matching is intentionally separate."""
    label_rows = list(label_rows)
    readiness = _label_readiness(predictions, label_rows, min_raters=min_raters)
    labels = _aggregate_labels(label_rows, min_raters=min_raters)
    per_case = []
    for case in predictions:
        case_id = case["case_id"]
        candidates = [
            _normalize(row.get("journal") or row.get("name") or "")
            for row in case.get("candidates", [])
        ]
        candidates = [name for name in candidates if name]
        pool = {
            journal: label
            for (label_case, journal), label in labels.items()
            if label_case == case_id
        }
        if not pool:
            continue
        row = {"case_id": case_id, "labeled_candidates": len(pool)}
        for cutoff in cutoffs:
            top = candidates[:cutoff]
            community_relevant = {name for name, value in pool.items() if value["community_match"]}
            acceptable = {name for name, value in pool.items() if value["relevance"] >= 1}
            row[f"community_recall@{cutoff}"] = _recall(top, community_relevant)
            row[f"acceptable_recall@{cutoff}"] = _recall(top, acceptable)
            gains = [pool.get(name, {}).get("relevance", 0) for name in top]
            ideal = sorted((value["relevance"] for value in pool.values()), reverse=True)[:cutoff]
            row[f"ndcg@{cutoff}"] = _ndcg(gains, ideal)
            labeled_top = [pool[name] for name in top if name in pool]
            row[f"generalist_exposure@{cutoff}"] = (
                sum(value["journal_scope_type"] == "generalist" for value in labeled_top)
                / len(labeled_top)
                if labeled_top
                else None
            )
        per_case.append(row)

    summary = {
        "ready": readiness["ready"],
        "cases_scored": len(per_case),
        "min_raters": min_raters,
        "label_coverage": readiness["coverage"],
        "incomplete_candidate_labels": readiness["incomplete_candidate_labels"],
    }
    for cutoff in cutoffs:
        for metric in (
            "community_recall",
            "acceptable_recall",
            "ndcg",
            "generalist_exposure",
        ):
            key = f"{metric}@{cutoff}"
            values = [row[key] for row in per_case if row.get(key) is not None]
            summary[key] = round(statistics.mean(values), 4) if values else None
    summary["label_disagreement_rate"] = _disagreement_rate(labels)
    return {"summary": summary, "label_readiness": readiness, "cases": per_case}


def auxiliary_exact_journal_metrics(
    predictions: Sequence[Dict],
    auxiliary_truth: Sequence[Dict],
    cutoffs: Sequence[int] = (3, 5, 10),
) -> Dict:
    """Report exact original-journal hits only as an auxiliary diagnostic."""
    truth = {row["case_id"]: _normalize(row.get("original_journal", "")) for row in auxiliary_truth}
    hits = {cutoff: 0 for cutoff in cutoffs}
    scored = 0
    for case in predictions:
        target = truth.get(case["case_id"], "")
        if not target:
            continue
        scored += 1
        names = [
            _normalize(row.get("journal") or row.get("name") or "")
            for row in case.get("candidates", [])
        ]
        for cutoff in cutoffs:
            hits[cutoff] += target in names[:cutoff]
    return {
        "cases": scored,
        **{
            f"exact_original_journal_hit@{cutoff}": hits[cutoff]
            for cutoff in cutoffs
        },
        **{
            f"exact_original_journal_rate@{cutoff}": round(hits[cutoff] / scored, 4)
            if scored else None
            for cutoff in cutoffs
        },
        "note": "Auxiliary only: the original journal is not treated as the unique correct answer.",
    }


def _label_readiness(
    predictions: Sequence[Dict],
    rows: Sequence[Dict],
    min_raters: int,
) -> Dict:
    expected = {
        (case["case_id"], _normalize(candidate.get("journal") or candidate.get("name") or ""))
        for case in predictions
        for candidate in case.get("candidates", [])
        if _normalize(candidate.get("journal") or candidate.get("name") or "")
    }
    expected.update(
        (
            str(row.get("case_id", "")).strip(),
            _normalize(row.get("candidate_journal", "")),
        )
        for row in rows
        if str(row.get("case_id", "")).strip()
        and _normalize(row.get("candidate_journal", ""))
    )
    complete = defaultdict(set)
    for row in rows:
        key = (
            str(row.get("case_id", "")).strip(),
            _normalize(row.get("candidate_journal", "")),
        )
        fit = str(row.get("fit_label", "")).strip().lower()
        community = str(row.get("community_match", "")).strip().lower()
        scope_type = str(row.get("journal_scope_type", "")).strip().lower()
        scope_checked = str(row.get("scope_checked", "")).strip().lower()
        rater = str(row.get("rater_id", "")).strip()
        if (
            key in expected
            and rater
            and fit in FIT_RELEVANCE
            and community in TRUE_VALUES | FALSE_VALUES
            and scope_type in {"generalist", "specialist"}
            and scope_checked in TRUE_VALUES | FALSE_VALUES
        ):
            complete[key].add(rater)
    incomplete = sorted(
        f"{case_id}|{journal}"
        for (case_id, journal) in expected
        if len(complete[(case_id, journal)]) < min_raters
    )
    complete_count = len(expected) - len(incomplete)
    return {
        "ready": bool(expected) and not incomplete,
        "expected_candidate_labels": len(expected),
        "complete_candidate_labels": complete_count,
        "coverage": round(complete_count / len(expected), 4) if expected else 0.0,
        "incomplete_candidate_labels": len(incomplete),
        "incomplete_examples": incomplete[:50],
    }


def _aggregate_labels(rows: Iterable[Dict], min_raters: int) -> Dict[Tuple[str, str], Dict]:
    grouped = defaultdict(list)
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        journal = _normalize(row.get("candidate_journal", ""))
        fit = str(row.get("fit_label", "")).strip().lower()
        if not case_id or not journal or fit not in FIT_RELEVANCE:
            continue
        grouped[(case_id, journal)].append(row)

    aggregated = {}
    for key, group in grouped.items():
        by_rater = {
            str(row.get("rater_id", "")).strip(): row
            for row in group
            if str(row.get("rater_id", "")).strip()
        }
        group = list(by_rater.values())
        raters = set(by_rater)
        if len(raters) < min_raters:
            continue
        relevances = [FIT_RELEVANCE[str(row["fit_label"]).strip().lower()] for row in group]
        scope_types = [str(row.get("journal_scope_type", "")).strip().lower() for row in group]
        scope_types = [value for value in scope_types if value in {"generalist", "specialist"}]
        aggregated[key] = {
            "relevance": round(statistics.median(relevances)),
            "community_match": sum(_truthy(row.get("community_match")) for row in group) >= len(group) / 2,
            "journal_scope_type": _mode(scope_types) if scope_types else "unknown",
            "rater_count": len(raters),
            "disagreed": len(set(relevances)) > 1,
        }
    return aggregated


def _recall(ranked: Sequence[str], relevant: set) -> float | None:
    if not relevant:
        return None
    return len(set(ranked) & relevant) / len(relevant)


def _dcg(values: Sequence[int]) -> float:
    return sum((2**value - 1) / math.log2(index + 2) for index, value in enumerate(values))


def _ndcg(values: Sequence[int], ideal: Sequence[int]) -> float | None:
    ideal_dcg = _dcg(ideal)
    return _dcg(values) / ideal_dcg if ideal_dcg else None


def _truthy(value) -> bool:
    return str(value or "").strip().lower() in TRUE_VALUES


def _mode(values: Sequence[str]) -> str:
    return max(sorted(set(values)), key=values.count)


def _disagreement_rate(labels: Dict) -> float | None:
    if not labels:
        return None
    return round(sum(value["disagreed"] for value in labels.values()) / len(labels), 4)


def _normalize(value: str) -> str:
    return "".join(char for char in str(value or "").lower() if char.isalnum())


def _read_csv(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser(description="Score an expert-labeled sci-select benchmark.")
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--labels", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--auxiliary-truth", default="")
    parser.add_argument("--min-raters", type=int, default=2)
    args = parser.parse_args()
    predictions = json.loads(Path(args.predictions).read_text(encoding="utf-8"))
    result = score_benchmark(predictions, _read_csv(args.labels), min_raters=args.min_raters)
    if args.auxiliary_truth:
        truth = json.loads(Path(args.auxiliary_truth).read_text(encoding="utf-8"))
        result["auxiliary"] = auxiliary_exact_journal_metrics(predictions, truth)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0 if result["summary"]["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
