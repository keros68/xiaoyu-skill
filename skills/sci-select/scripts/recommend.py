"""Backward-compatible wrappers for the sci-select selector."""
from __future__ import annotations

from typing import Dict, List

from .select_journals import (
    infer_paper_profile,
    rank_metric_records,
    search_candidates,
    select_journals,
    format_selection_report,
)


def match_categories(text: str) -> List[Dict]:
    """Compatibility wrapper: return inferred LetPub category pairs."""
    return [
        {"category1": c["category1"], "category2": c["category2"]}
        for c in infer_paper_profile(text).get("categories", [])
    ]


def recommend(
    text: str = "",
    categories: List[Dict] = None,
    impact_low: str = "",
    impact_high: str = "",
    sci_type: str = "SCIE",
    oa: str = "",
    partition: str = "",
    xinrui_partition: str = "",
    sort: str = "impactor",
    max_candidates: int = 10,
    enrich_details: bool = True,
) -> List[Dict]:
    """
    Compatibility wrapper for the old recommend() API.

    New code should call scripts.select_journals.select_journals().
    """
    profile = infer_paper_profile(text)
    if categories:
        profile["categories"] = categories

    if not enrich_details:
        candidates = search_candidates(
            profile["categories"],
            impact_low=impact_low,
            impact_high=impact_high,
            sci_type=sci_type,
            oa=oa,
            partition=partition,
            xinrui_partition=xinrui_partition,
            sort=sort,
            limit_per_category=max_candidates // max(1, len(profile["categories"])) + 2,
        )[:max_candidates]
        metric_records = [
            {
                "name": c.get("name", ""),
                "shortname": c.get("shortname", ""),
                "impact_factor": c.get("impact_factor"),
                "partition": "",
                "cas_partition_2025": "",
                "xinrui_partition_2026": c.get("xinrui_partition_2026", ""),
                "sci_type": c.get("sci_type", ""),
                "field": c.get("field", ""),
                "_sources": ["letpub-search"],
            }
            for c in candidates
        ]
        return rank_metric_records(profile, metric_records)

    return select_journals(
        text=text,
        categories=categories,
        impact_low=impact_low,
        impact_high=impact_high,
        sci_type=sci_type,
        oa=oa,
        partition=partition,
        xinrui_partition=xinrui_partition,
        sort=sort,
        max_candidates=max_candidates,
    )["results"]


def format_report(results: List[Dict], title: str = "") -> str:
    return format_selection_report({"categories": []}, results, title=title)


def format_report_compact(results: List[Dict]) -> str:
    if not results:
        return "sci-select 未找到匹配期刊。"

    lines = ["sci-select 期刊推荐", ""]
    for item in results:
        lines.append(f"- {item.get('tier', '备选')}｜{item.get('name', '')}：{item.get('metrics_line', '')}")
    return "\n".join(lines)


if __name__ == "__main__":
    demo = recommend(
        text="groundwater nitrate source identification using stable isotopes and hydrochemistry",
        impact_low="3",
        max_candidates=8,
    )
    print(format_report(demo))
