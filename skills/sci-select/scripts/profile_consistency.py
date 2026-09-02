"""Model-neutral manuscript profile validation and independent-profile comparison."""
from __future__ import annotations

import itertools
import re
from typing import Dict, List, Sequence


REQUIRED_FIELDS = (
    "direction_summary",
    "primary_field",
    "specialty",
    "research_object",
    "research_question",
    "contribution_type",
    "target_audience",
    "methods",
    "exclusions",
    "search_queries",
)
TEXT_FIELDS = (
    "primary_field",
    "specialty",
    "research_object",
    "research_question",
    "contribution_type",
)
LIST_FIELDS = ("target_audience", "methods", "exclusions", "search_queries")


def validate_profile(profile: Dict) -> Dict:
    """Validate the shared profile protocol without any discipline-specific rules."""
    errors = []
    for field in REQUIRED_FIELDS:
        if field not in profile:
            errors.append(f"missing field: {field}")
    for field in LIST_FIELDS:
        if field in profile and not isinstance(profile[field], list):
            errors.append(f"{field} must be a list")
    query_count = len(profile.get("search_queries") or [])
    if query_count not in range(2, 4):
        errors.append("search_queries must contain two or three queries")
    return {"valid": not errors, "errors": errors}


def compare_profiles(profiles: Sequence[Dict]) -> Dict:
    """Compare independently generated profiles; do not synthesize a false consensus."""
    if len(profiles) < 2:
        raise ValueError("At least two independent profiles are required")
    validations = [validate_profile(profile) for profile in profiles]
    field_scores = {}
    for field in TEXT_FIELDS:
        field_scores[field] = _mean_pairwise(
            [_token_set(profile.get(field, "")) for profile in profiles]
        )
    for field in LIST_FIELDS:
        field_scores[field] = _mean_pairwise(
            [_token_set(" ".join(profile.get(field) or [])) for profile in profiles]
        )
    overall = sum(field_scores.values()) / len(field_scores)
    if overall >= 0.7:
        status = "high"
    elif overall >= 0.45:
        status = "medium"
    else:
        status = "low"
    disagreements = [field for field, score in field_scores.items() if score < 0.4]
    return {
        "profile_count": len(profiles),
        "validations": validations,
        "agreement": round(overall, 4),
        "status": status,
        "field_agreement": {field: round(score, 4) for field, score in field_scores.items()},
        "disagreements": disagreements,
        "action": (
            "Use the shared queries and proceed."
            if status == "high"
            else "Keep multiple query variants, broaden recall, and report profile disagreement."
        ),
    }


def _mean_pairwise(values: Sequence[set]) -> float:
    scores = [_jaccard(left, right) for left, right in itertools.combinations(values, 2)]
    return sum(scores) / len(scores) if scores else 0.0


def _jaccard(left: set, right: set) -> float:
    if not left and not right:
        return 1.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _token_set(value: str) -> set:
    text = str(value or "").lower()
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", text)
        if len(token) >= 2
    }
    for sequence in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(sequence) == 1:
            tokens.add(sequence)
        else:
            tokens.update(sequence[index : index + 2] for index in range(len(sequence) - 1))
    return tokens
