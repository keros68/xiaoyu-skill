"""Run sci-select over blinded benchmark inputs without reading auxiliary truth."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Sequence

from .select_journals import select_journals


def run_benchmark(
    inputs: Sequence[Dict],
    profiles: Dict[str, List[Dict]] | None = None,
    max_candidates: int = 20,
    request_delay: float = 1.0,
) -> List[Dict]:
    """Generate candidate pools using inputs and optional independent paper profiles."""
    profiles = profiles or {}
    predictions = []
    for case in inputs:
        case_id = str(case["case_id"])
        independent = profiles.get(case_id, [])
        text = "\n".join(
            value
            for value in (
                str(case.get("title") or ""),
                str(case.get("abstract") or ""),
                "Keywords: " + "; ".join(case.get("keywords") or []),
            )
            if value.strip()
        )
        bundle = select_journals(
            text=text,
            paper_profile=independent[0] if independent else None,
            independent_profiles=independent,
            excluded_titles=[str(case.get("title") or "")],
            max_candidates=max_candidates,
            request_delay=request_delay,
        )
        predictions.append(
            {
                "case_id": case_id,
                "profile_source": "independent-model-profiles" if independent else "deterministic-fallback",
                "profile": bundle["profile"],
                "retrieval": bundle["retrieval"],
                "candidates": [
                    {
                        "journal": row.get("name", ""),
                        "rank": rank,
                        "candidate_status": row.get("tier", ""),
                        "fit_confidence": row.get("fit_confidence", ""),
                        "journal_level": row.get("journal_level", ""),
                        "fit_score": row.get("fit_score"),
                        "similarity_rate_per_10k": row.get("similarity_rate_per_10k"),
                        "scope_checked": bool(row.get("scope_checked")),
                    }
                    for rank, row in enumerate(bundle["results"], 1)
                ],
            }
        )
    return predictions


def _load_profiles(path: str) -> Dict[str, List[Dict]]:
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return {
            str(case_id): value if isinstance(value, list) else [value]
            for case_id, value in payload.items()
        }
    result: Dict[str, List[Dict]] = {}
    for row in payload:
        result.setdefault(str(row["case_id"]), []).append(row.get("profile") or row)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run blinded sci-select benchmark inputs.")
    parser.add_argument("--inputs", required=True)
    parser.add_argument("--profiles", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-candidates", type=int, default=20)
    parser.add_argument("--request-delay", type=float, default=1.0)
    args = parser.parse_args()
    inputs = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
    predictions = run_benchmark(
        inputs,
        profiles=_load_profiles(args.profiles),
        max_candidates=args.max_candidates,
        request_delay=max(0.0, args.request_delay),
    )
    Path(args.output).write_text(
        json.dumps(predictions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"cases": len(predictions), "output": args.output}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
