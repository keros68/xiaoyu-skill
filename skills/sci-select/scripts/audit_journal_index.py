"""Release gate for sci-select SQLite journal indexes."""
from __future__ import annotations

import argparse
import difflib
import json
import math
import random
import re
import sqlite3
from pathlib import Path
from typing import Dict, List

import requests


CRITICAL_SOURCES = {
    "cas_2025": "cas_2025",
    "xuankan_2026": "xinrui_2026",
    "jif_2025": "jcr_2025",
    "jcr_quartile_2025": "jcr_2025",
    "nature_index": "nature_index_2026",
}


def audit_index(
    database: str,
    sample_size: int = 0,
    seed: int = 20260711,
    max_severe_mismatch_rate: float = 0.0,
    require_provenance: bool = True,
    timeout: int = 20,
) -> Dict:
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        metadata = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM metadata")}
        raw_rows = list(conn.execute("SELECT title, issn, eissn, payload_json FROM journals"))
    finally:
        conn.close()

    rows = [json.loads(row["payload_json"]) for row in raw_rows]
    structural_errors: List[str] = []
    provenance_errors: List[str] = []
    normalized_titles = [_normalize_name(row.get("title", "")) for row in rows]
    duplicate_titles = len(normalized_titles) - len(set(normalized_titles))
    if duplicate_titles:
        structural_errors.append(f"duplicate normalized titles: {duplicate_titles}")

    identities: Dict[str, set] = {}
    for row in rows:
        title = row.get("title", "")
        if not title:
            structural_errors.append("row without title")
        for field in ("cas_2025", "xuankan_2026"):
            value = row.get(field)
            if value and not re.fullmatch(r"[1-4]区(?:Top)?", str(value)):
                structural_errors.append(f"invalid {field}: {title}={value}")
        for identity in (row.get("issn"), row.get("eissn")):
            normalized = _normalize_issn(identity)
            if normalized:
                if not _valid_issn(normalized):
                    structural_errors.append(f"invalid ISSN checksum: {title}={identity}")
                identities.setdefault(normalized, set()).add(_normalize_name(title))
        if require_provenance:
            provenance = row.get("provenance") or {}
            for field, expected_source in CRITICAL_SOURCES.items():
                if row.get(field) not in (None, "", [], {}) and not provenance.get(field):
                    provenance_errors.append(f"{title}: {field} lacks provenance ({expected_source})")
    for identity, titles in identities.items():
        if len(titles) > 1:
            structural_errors.append(f"identity {identity} assigned to incompatible titles: {sorted(titles)}")

    eligible = [row for row in rows if row.get("issn")]
    random.Random(seed).shuffle(eligible)
    checked = []
    for row in eligible[: max(0, sample_size)]:
        checked.append(_crossref_check(row, timeout))
    verified = [row for row in checked if row.get("status") == 200]
    mismatches = [row for row in verified if row.get("severe_mismatch")]
    mismatch_rate = len(mismatches) / len(verified) if verified else None
    requested_external = min(max(0, sample_size), len(eligible))
    external_coverage_ok = (
        requested_external == 0
        or len(verified) >= math.ceil(requested_external * 0.5)
    )
    if not external_coverage_ok:
        structural_errors.append(
            f"external identity audit verified only {len(verified)}/{requested_external} sampled rows"
        )
    passed = (
        not structural_errors
        and not provenance_errors
        and (mismatch_rate is None or mismatch_rate <= max_severe_mismatch_rate)
    )
    return {
        "passed": passed,
        "database": str(Path(database).resolve()),
        "metadata": metadata,
        "summary": {
            "journals": len(rows),
            "structural_errors": len(structural_errors),
            "provenance_errors": len(provenance_errors),
            "external_checked": len(verified),
            "external_requested": requested_external,
            "external_identity_gate_applicable": bool(eligible),
            "severe_mismatches": len(mismatches),
            "severe_mismatch_rate": round(mismatch_rate, 4) if mismatch_rate is not None else None,
            "max_severe_mismatch_rate": max_severe_mismatch_rate,
        },
        "structural_errors": structural_errors[:100],
        "provenance_errors": provenance_errors[:100],
        "external_mismatches": mismatches,
    }


def _crossref_check(row: Dict, timeout: int) -> Dict:
    issn = row.get("issn", "")
    try:
        response = requests.get(
            f"https://api.crossref.org/journals/{issn}",
            headers={"User-Agent": "sci-select-index-audit/1.0"},
            timeout=timeout,
        )
        if response.status_code != 200:
            return {"title": row.get("title"), "issn": issn, "status": response.status_code}
        crossref_title = response.json().get("message", {}).get("title", "")
        similarity = _title_similarity(row.get("title", ""), crossref_title)
        return {
            "title": row.get("title"),
            "issn": issn,
            "status": 200,
            "crossref_title": crossref_title,
            "similarity": similarity,
            "severe_mismatch": similarity < 0.65,
        }
    except (requests.RequestException, ValueError) as exc:
        return {"title": row.get("title"), "issn": issn, "status": "error", "error": str(exc)}


def _title_similarity(left: str, right: str) -> float:
    return round(
        difflib.SequenceMatcher(None, _normalize_name(left), _normalize_name(right)).ratio(),
        4,
    )


def _normalize_name(value: str) -> str:
    text = str(value or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", text)


def _normalize_issn(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", str(value or "")).upper()


def _valid_issn(value: str) -> bool:
    if not re.fullmatch(r"\d{7}[\dX]", value):
        return False
    total = sum(int(char) * weight for char, weight in zip(value[:7], range(8, 1, -1)))
    check = (11 - total % 11) % 11
    expected = "X" if check == 10 else str(check)
    return value[-1] == expected


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a sci-select journal index before release.")
    parser.add_argument("database")
    parser.add_argument("--sample-size", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260711)
    parser.add_argument("--max-severe-mismatch-rate", type=float, default=0.0)
    parser.add_argument("--no-require-provenance", action="store_true")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    result = audit_index(
        args.database,
        sample_size=args.sample_size,
        seed=args.seed,
        max_severe_mismatch_rate=args.max_severe_mismatch_rate,
        require_provenance=not args.no_require_provenance,
    )
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
