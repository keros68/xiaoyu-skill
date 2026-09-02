"""
sci-select main selector.

The public API is intentionally small:
- infer_paper_profile(text): understand paper topics and candidate LetPub categories
- select_journals(text, ...): live LetPub/OpenAlex workflow
- rank_metric_records(profile, records): deterministic scoring for tested/reportable results
- format_selection_report(profile, ranked): user-facing report
"""
from __future__ import annotations

import csv
import io
import math
import re
import time
from typing import Dict, Iterable, List, Optional, Tuple

from .journal_metrics import get_journal_metrics, format_metrics_line
from .journal_index_client import search_index_journals
from .letpub_client import advanced_search
from .similar_works import build_search_queries, discover_journal_candidates
from .scope_evidence import apply_scope_record, build_scope_verification_queue
from .profile_consistency import compare_profiles, validate_profile


Category = Dict[str, str]
MetricRecord = Dict


TERM_RULES: List[Dict] = [
    {
        "label": "groundwater",
        "aliases": ["地下水", "groundwater", "aquifer", "phreatic water"],
        "categories": [("环境科学与生态学", "水资源")],
        "weight": 4,
    },
    {
        "label": "hydrology",
        "aliases": ["水文", "hydrology", "hydrological", "watershed", "catchment", "basin"],
        "categories": [("环境科学与生态学", "水资源")],
        "weight": 3,
    },
    {
        "label": "hydrochemistry",
        "aliases": ["水化学", "hydrochemistry", "hydrochemical", "water chemistry"],
        "categories": [("地球科学", "地球化学与地球物理"), ("环境科学与生态学", "水资源")],
        "weight": 4,
    },
    {
        "label": "stable isotopes",
        "aliases": ["同位素", "stable isotope", "stable isotopes", "isotope", "isotopic"],
        "categories": [("地球科学", "地球化学与地球物理")],
        "weight": 4,
    },
    {
        "label": "water quality",
        "aliases": ["水质", "water quality", "nitrate", "硝酸盐", "污染", "pollution", "contamination"],
        "categories": [("环境科学与生态学", "水资源"), ("环境科学与生态学", "环境科学")],
        "weight": 3,
    },
    {
        "label": "geochemistry",
        "aliases": ["地球化学", "geochemistry", "geochemical"],
        "categories": [("地球科学", "地球化学与地球物理")],
        "weight": 4,
    },
    {
        "label": "geology",
        "aliases": ["地质", "geology", "geological"],
        "categories": [("地球科学", "地质学")],
        "weight": 3,
    },
    {
        "label": "remote sensing",
        "aliases": ["遥感", "remote sensing", "satellite", "modis", "landsat", "sentinel"],
        "categories": [("地球科学", "遥感")],
        "weight": 4,
    },
    {
        "label": "atmosphere",
        "aliases": ["气象", "大气", "climate", "meteorology", "atmospheric", "precipitation"],
        "categories": [("地球科学", "气象与大气科学")],
        "weight": 3,
    },
    {
        "label": "soil",
        "aliases": ["土壤", "soil", "salinity", "盐碱"],
        "categories": [("环境科学与生态学", "土壤科学"), ("农林科学", "土壤科学")],
        "weight": 3,
    },
    {
        "label": "ecology",
        "aliases": ["生态", "ecology", "ecosystem", "biodiversity"],
        "categories": [("环境科学与生态学", "生态学")],
        "weight": 3,
    },
    {
        "label": "environmental science",
        "aliases": ["环境", "environment", "environmental"],
        "categories": [("环境科学与生态学", "环境科学")],
        "weight": 2,
    },
    {
        "label": "machine learning",
        "aliases": ["机器学习", "machine learning", "deep learning", "neural network", "人工智能", "ai"],
        "categories": [("计算机科学", "计算机：人工智能")],
        "weight": 1,
    },
    {
        "label": "gis",
        "aliases": ["gis", "geographic information system", "spatial analysis", "spatial", "mapping", "制图", "空间", "时空"],
        "categories": [("计算机科学", "计算机：跨学科应用"), ("地球科学", "遥感")],
        "weight": 3,
    },
    {
        "label": "oncology",
        "aliases": ["肿瘤", "癌", "cancer", "tumor", "tumour", "carcinoma", "oncology"],
        "categories": [("医学", "肿瘤学")],
        "weight": 4,
    },
    {
        "label": "medical imaging",
        "aliases": ["ct", "mri", "radiomics", "imaging", "医学影像", "放射组学"],
        "categories": [("医学", "成像科学与照相技术")],
        "weight": 3,
    },
    {
        "label": "medicine",
        "aliases": ["clinical", "patient", "disease", "therapy", "treatment", "医学", "临床"],
        "categories": [("医学", "医学：研究与实验")],
        "weight": 2,
    },
    {
        "label": "agriculture",
        "aliases": ["农业", "agriculture", "crop", "irrigation", "farmland"],
        "categories": [("农林科学", "农业综合")],
        "weight": 2,
    },
]


METHOD_RULES: List[Tuple[str, List[str]]] = [
    ("machine learning", ["machine learning", "deep learning", "random forest", "neural network", "机器学习", "深度学习"]),
    ("gis", ["gis", "geographic information system", "spatial analysis", "spatial", "mapping", "制图", "空间", "时空"]),
    ("isotope tracing", ["stable isotope", "isotopic", "同位素"]),
    ("field experiment", ["field experiment", "sampling", "monitoring", "野外", "采样", "监测"]),
    ("modeling", ["model", "simulation", "模型", "模拟"]),
    ("review", ["review", "meta-analysis", "综述"]),
]

METHOD_LABELS = {method for method, _aliases in METHOD_RULES}

TOPIC_EVIDENCE_PATTERNS = [
    r"\b[a-z]+ flood\b",
    r"\bflood(?:ing)?\b",
    r"\bdrought\b",
    r"\brunoff\b",
    r"\bstreamflow\b",
    r"\bdischarge\b",
    r"\bsediment\b",
    r"\bland[- ]use\b",
    r"\bterrain\b",
    r"\brainfall\b",
]


def infer_paper_profile(text: str, max_categories: int = 4) -> Dict:
    """Infer a compact paper profile from title, abstract, keywords, or full text."""
    normalized = _normalize_text(text)
    category_scores: Dict[Tuple[str, str], int] = {}
    matched_terms: List[str] = []

    for rule in TERM_RULES:
        hits = [alias for alias in rule["aliases"] if _contains_term(normalized, alias)]
        if not hits:
            continue

        matched_terms.append(rule["label"])
        for category in rule["categories"]:
            category_scores[category] = category_scores.get(category, 0) + rule["weight"]

    if not category_scores:
        category_scores[("综合性期刊", "")] = 1

    ranked_categories = sorted(category_scores.items(), key=lambda item: -item[1])
    categories = [
        {"category1": cat1, "category2": cat2, "score": score}
        for (cat1, cat2), score in ranked_categories[:max_categories]
    ]

    methods = []
    for method, aliases in METHOD_RULES:
        if any(_contains_term(normalized, alias) for alias in aliases):
            methods.append(method)

    topic_evidence = _topic_evidence(normalized, matched_terms)

    profile = {
        "categories": categories,
        "matched_terms": matched_terms,
        "methods": methods,
        "topic_evidence": topic_evidence,
        "primary_signal": _primary_signal(topic_evidence, matched_terms),
        "input_length": len(text or ""),
        "profile_source": "keyword-fallback",
        "direction_summary": "",
        "primary_field": "",
        "specialty": "",
        "research_object": "",
        "research_question": "",
        "contribution_type": "",
        "target_audience": [],
        "exclusions": [],
        "search_queries": [],
    }
    profile["search_queries"] = build_search_queries(profile)
    return profile


def merge_paper_profile(fallback: Dict, structured: Optional[Dict]) -> Dict:
    """Merge an AI-built manuscript fingerprint over deterministic fallback data."""
    profile = dict(fallback or {})
    if not structured:
        profile.setdefault("profile_source", "keyword-fallback")
        profile["search_queries"] = build_search_queries(profile)
        return profile

    for key in (
        "direction_summary",
        "title",
        "primary_field",
        "specialty",
        "research_object",
        "research_question",
        "contribution_type",
        "target_audience",
        "methods",
        "exclusions",
        "search_queries",
        "categories",
        "topic_evidence",
        "matched_terms",
    ):
        value = structured.get(key)
        if value not in (None, "", [], {}):
            profile[key] = value

    profile["profile_source"] = "ai-structured"
    if profile.get("research_object"):
        profile["primary_signal"] = profile["research_object"]
    profile["search_queries"] = build_search_queries(profile)
    return profile


def search_candidates(
    categories: List[Category],
    impact_low: str = "",
    impact_high: str = "",
    sci_type: str = "SCIE",
    oa: str = "",
    partition: str = "",
    xinrui_partition: str = "",
    sort: str = "impactor",
    limit_per_category: int = 8,
) -> List[MetricRecord]:
    """Search LetPub candidates for multiple inferred categories."""
    grouped_candidates: List[List[MetricRecord]] = []

    for category in categories:
        parsed = advanced_search(
            searchcategory1=category.get("category1", ""),
            searchcategory2=category.get("category2", ""),
            searchimpactlow=impact_low,
            searchimpacthigh=impact_high,
            searchscitype=sci_type,
            searchopenaccess=oa,
            searchjcrkind=partition,
            searchsort=sort,
        )
        category_hits = []
        for journal in parsed.get("journals", []):
            name = journal.get("name", "")
            if name:
                item = dict(journal)
                if xinrui_partition and not _partition_matches(_candidate_xinrui_partition(item), xinrui_partition):
                    continue
                item["_search_category"] = {
                    "category1": category.get("category1", ""),
                    "category2": category.get("category2", ""),
                }
                category_hits.append(item)

        grouped_candidates.append(category_hits[:limit_per_category])
        time.sleep(0.5)

    return interleave_candidate_groups(
        grouped_candidates,
        limit=max(1, limit_per_category) * max(1, len(categories)),
    )


def interleave_candidate_groups(groups: List[List[MetricRecord]], limit: int) -> List[MetricRecord]:
    """Round-robin candidate groups so one broad category cannot fill the list."""
    results: List[MetricRecord] = []
    seen = set()
    max_len = max((len(group) for group in groups), default=0)

    for index in range(max_len):
        for group in groups:
            if index >= len(group):
                continue
            item = group[index]
            name = item.get("name", "")
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)
            results.append(item)
            if len(results) >= limit:
                return results

    return results


def select_journals(
    text: str,
    categories: Optional[List[Category]] = None,
    paper_profile: Optional[Dict] = None,
    independent_profiles: Optional[List[Dict]] = None,
    search_queries: Optional[List[str]] = None,
    excluded_titles: Optional[List[str]] = None,
    excluded_work_ids: Optional[List[str]] = None,
    scope_records: Optional[List[Dict]] = None,
    use_literature_evidence: bool = True,
    impact_low: str = "",
    impact_high: str = "",
    sci_type: str = "SCIE",
    oa: str = "",
    partition: str = "",
    xinrui_partition: str = "",
    jcr_quartiles: Optional[List[str]] = None,
    cas_partitions: Optional[List[str]] = None,
    coverage_types: Optional[List[str]] = None,
    exclude_warnings: bool = False,
    exclude_esci_only: bool = False,
    sort: str = "impactor",
    max_candidates: int = 10,
    request_delay: float = 1.0,
) -> Dict:
    """Run the full sci-select workflow."""
    independent_profiles = list(independent_profiles or [])
    if independent_profiles and paper_profile is None:
        paper_profile = independent_profiles[0]
    profile = merge_paper_profile(infer_paper_profile(text), paper_profile)
    profile["profile_validation"] = validate_profile(profile)
    if len(independent_profiles) >= 2:
        consistency = compare_profiles(independent_profiles)
        profile["profile_consistency"] = consistency
        if consistency["status"] != "high":
            profile["retrieval_search_queries"] = list(
                dict.fromkeys(
                    query
                    for item in independent_profiles
                    for query in item.get("search_queries", [])
                    if query
                )
            )[:6]
    if categories:
        profile["categories"] = categories
    if search_queries:
        profile["search_queries"] = list(search_queries)

    literature = {"queries": [], "candidates": [], "errors": []}
    if use_literature_evidence:
        target_titles = list(excluded_titles or [])
        if profile.get("title"):
            target_titles.append(profile["title"])
        literature = discover_journal_candidates(
            profile.get("retrieval_search_queries")
            or profile.get("search_queries")
            or build_search_queries(profile),
            max_journals=max(12, max_candidates * 2),
            excluded_titles=target_titles,
            excluded_work_ids=excluded_work_ids or [],
        )
    specialist_candidates = discover_specialist_candidates(
        profile,
        max_candidates=max(8, max_candidates),
    )

    search_errors = []
    needs_category_fallback = (
        not use_literature_evidence
        or categories is not None
        or bool(xinrui_partition)
        or len(literature.get("candidates", [])) < max_candidates
    )
    try:
        category_candidates = search_candidates(
            profile["categories"],
            impact_low=impact_low,
            impact_high=impact_high,
            sci_type=sci_type,
            oa=oa,
            partition=partition,
            xinrui_partition=xinrui_partition,
            sort=sort,
            limit_per_category=max(8, max_candidates // max(1, len(profile["categories"])) + 4),
        ) if needs_category_fallback else []
    except Exception as exc:
        category_candidates = []
        search_errors.append(f"LetPub候选检索失败: {exc}")

    candidate_pool = merge_candidate_sources(
        literature.get("candidates", []),
        specialist_candidates,
        category_candidates,
    )
    profile["retrieval_notes"] = [*literature.get("errors", []), *search_errors]
    profile["literature_evidence_available"] = bool(literature.get("candidates"))
    candidates = select_balanced_candidates(candidate_pool, max_candidates)

    metric_records = []
    for candidate in candidates:
        name = candidate.get("name", "")
        candidate_xinrui = _candidate_xinrui_partition(candidate)
        metrics = get_journal_metrics(
            name,
            source_mode="selection",
            issn=candidate.get("issn", ""),
        )
        if not metrics.get("_sources"):
            metrics.update(
                {
                    "impact_factor": candidate.get("impact_factor"),
                    "partition": "",
                    "cas_partition_2025": "",
                    "xinrui_partition_2026": candidate_xinrui,
                    "sci_type": candidate.get("sci_type", ""),
                    "field": candidate.get("field", ""),
                    "_sources": ["letpub-search"],
                }
            )
        elif candidate_xinrui and not metrics.get("xinrui_partition_2026"):
            metrics["xinrui_partition_2026"] = candidate_xinrui
        _merge_candidate_evidence(metrics, candidate)
        apply_scope_record(metrics, scope_records or [])
        if xinrui_partition and not _partition_matches(_xinrui_partition(metrics), xinrui_partition):
            continue
        if not _passes_selection_constraints(
            metrics,
            impact_low=impact_low,
            impact_high=impact_high,
            jcr_quartiles=jcr_quartiles,
            cas_partitions=cas_partitions,
            coverage_types=coverage_types,
            exclude_warnings=exclude_warnings,
            exclude_esci_only=exclude_esci_only,
        ):
            continue
        metrics["_candidate"] = candidate
        metric_records.append(metrics)
        if request_delay > 0:
            time.sleep(request_delay)

    preferences = {"xinrui_partition": xinrui_partition} if xinrui_partition else {}
    ranked = assign_candidate_labels(
        rank_metric_records(profile, metric_records, preferences=preferences),
    )

    return {
        "profile": profile,
        "results": ranked,
        "retrieval": {
            "queries": literature.get("queries", []),
            "similar_work_candidates": len(literature.get("candidates", [])),
            "specialist_title_candidates": len(specialist_candidates),
            "errors": [*literature.get("errors", []), *search_errors],
        },
        "scope_verification": build_scope_verification_queue(profile, ranked, limit=5),
    }


def merge_candidate_sources(*groups: List[MetricRecord]) -> List[MetricRecord]:
    """Merge candidate sources while preserving literature and search evidence."""
    merged: Dict[str, MetricRecord] = {}
    order: List[str] = []
    for group in groups:
        for candidate in group:
            name = candidate.get("name", "")
            key = _normalize_journal_name(name)
            if not key:
                continue
            if key not in merged:
                merged[key] = dict(candidate)
                order.append(key)
                continue
            current = merged[key]
            for field, value in candidate.items():
                if field == "_sources":
                    current[field] = list(dict.fromkeys([*current.get(field, []), *(value or [])]))
                elif field == "publication_precedents":
                    current[field] = _merge_precedents(current.get(field, []), value or [])
                elif value not in (None, "", [], {}) and current.get(field) in (None, "", [], {}):
                    current[field] = value
    return [merged[key] for key in order]


def discover_specialist_candidates(profile: Dict, max_candidates: int = 12) -> List[MetricRecord]:
    """Supplement literature recall with title-matched specialist journals."""
    terms = [
        *_profile_scope_terms(profile),
        *profile.get("topic_evidence", []),
        *profile.get("matched_terms", []),
    ]
    return search_index_journals(terms, limit=max_candidates)


def _merge_precedents(first: List[Dict], second: List[Dict]) -> List[Dict]:
    merged = []
    seen = set()
    for work in [*first, *second]:
        key = work.get("openalex_id") or (work.get("title"), work.get("year"))
        if key in seen:
            continue
        seen.add(key)
        merged.append(work)
    return merged[:5]


def _merge_candidate_evidence(metrics: MetricRecord, candidate: MetricRecord) -> None:
    for key in (
        "similar_works_count",
        "query_coverage",
        "literature_evidence_score",
        "publication_precedents",
        "openalex_topics",
        "openalex_source_id",
        "source_works_count",
        "source_recent_works_count",
        "similarity_rate_per_10k",
        "specialist_title_score",
        "specialist_title_terms",
        "scope_verified",
        "scope_evidence",
    ):
        if candidate.get(key) not in (None, "", [], {}):
            metrics[key] = candidate[key]
    candidate_field = str(candidate.get("field", "")).strip()
    current_field = str(metrics.get("field", "")).strip()
    if candidate_field and not current_field:
        metrics["field"] = candidate_field
    elif candidate_field and candidate_field.lower() not in current_field.lower():
        metrics["field"] = f"{current_field}; {candidate_field}"
    recent_works = int(
        metrics.get("source_recent_works_count")
        or metrics.get("recent_works_count")
        or 0
    )
    precedent_count = int(metrics.get("similar_works_count", 0) or 0)
    if recent_works and precedent_count:
        rate = precedent_count / recent_works * 10000
        metrics["source_recent_works_count"] = recent_works
        metrics["similarity_rate_per_10k"] = round(rate, 4)
        metrics["literature_evidence_score"] = min(
            28,
            int(metrics.get("query_coverage", 0) or 0) * 5
            + min(12, round(math.log1p(rate) * 4)),
        )
    metrics["_sources"] = list(
        dict.fromkeys([*metrics.get("_sources", []), *candidate.get("_sources", [])])
    )


def select_balanced_candidates(candidates: List[MetricRecord], max_candidates: int) -> List[MetricRecord]:
    """Pick high, middle, and lower-difficulty candidates before costly enrichment."""
    buckets = {"high": [], "middle": [], "lower": []}
    for candidate in candidates:
        buckets[_candidate_level(candidate)].append(candidate)

    if max_candidates <= 3:
        targets = {"high": 1, "middle": 1, "lower": 1}
    else:
        targets = {
            "high": max(1, max_candidates // 3),
            "middle": max(1, max_candidates // 3),
            "lower": max(1, max_candidates // 4),
        }

    selected: List[MetricRecord] = []
    seen = set()

    evidence_candidates = sorted(
        (candidate for candidate in candidates if candidate.get("literature_evidence_score")),
        key=lambda candidate: (
            -int(candidate.get("query_coverage", 0)),
            -int(candidate.get("literature_evidence_score", 0)),
            -float(candidate.get("similarity_rate_per_10k") or 0),
            -int(candidate.get("similar_works_count", 0)),
        ),
    )
    for candidate in evidence_candidates[: max(2, max_candidates // 2)]:
        _append_unique_candidate(selected, seen, candidate)

    for level in ("high", "middle", "lower"):
        for candidate in buckets[level][: targets[level]]:
            _append_unique_candidate(selected, seen, candidate)

    for candidate in candidates:
        if len(selected) >= max_candidates:
            break
        _append_unique_candidate(selected, seen, candidate)

    return selected[:max_candidates]


def _append_unique_candidate(selected: List[MetricRecord], seen: set, candidate: MetricRecord) -> None:
    name = candidate.get("name", "")
    key = name.lower()
    if name and key not in seen:
        seen.add(key)
        selected.append(candidate)


def _candidate_level(candidate: MetricRecord) -> str:
    impact = _float(candidate.get("impact_factor"))
    partition = _candidate_xinrui_partition(candidate)
    if "1区" in partition:
        return "high"
    if "2区" in partition:
        return "middle"
    if "3区" in partition or "4区" in partition:
        return "lower"
    if impact >= 8:
        return "high"
    if impact >= 5:
        return "middle"
    return "lower"


def rank_metric_records(
    profile: Dict,
    records: Iterable[MetricRecord],
    preferences: Optional[Dict] = None,
) -> List[Dict]:
    """Score and tier already-fetched journal metric records."""
    preferences = preferences or {}
    ranked = []

    for record in records:
        entry = dict(record)
        fit_score, fit_reasons = _topic_fit(profile, entry)
        quality_score, quality_reasons = _quality_score(entry, preferences)
        risk_penalty, risk_reasons = _risk_penalty(profile, entry)
        # Keep journal standing separate from manuscript-to-scope fit.
        total_score = fit_score - risk_penalty

        entry["fit_score"] = fit_score
        entry["quality_score"] = quality_score
        entry["risk_penalty"] = risk_penalty
        entry["score"] = total_score
        entry["fit_reasons"] = fit_reasons
        entry["quality_reasons"] = quality_reasons
        entry["risk_reasons"] = risk_reasons
        entry["fit_confidence"] = _fit_confidence(entry, fit_reasons)
        entry["journal_level"] = _journal_level(entry)
        entry["tier"] = _tier(entry)
        entry["data_notes"] = _data_notes(entry)
        entry["metrics_line"] = format_metrics_line(entry)
        entry["data_status"] = _compact_data_status(entry)
        ranked.append(entry)

    tier_order = {"推荐": 0, "备选": 1, "谨慎": 2, "不推荐": 3}
    fit_order = {"强": 0, "中": 1, "弱": 2}
    ranked.sort(
        key=lambda item: (
            tier_order.get(item["tier"], 9),
            fit_order.get(item.get("fit_confidence"), 9),
            -item["fit_score"],
            -item["score"],
            _normalize_journal_name(item.get("name", "")),
        )
    )
    return ranked


def assign_candidate_labels(ranked: List[Dict]) -> List[Dict]:
    """Attach objective journal levels and candidate labels without judging the manuscript."""
    for item in ranked:
        item.setdefault("journal_level", _journal_level(item))
        item["candidate_label"] = _candidate_label(item)
        item["submission_band"] = item["candidate_label"]
    return ranked


def rerank_with_scope_evidence(
    profile: Dict,
    records: List[Dict],
    scope_records: List[Dict],
) -> List[Dict]:
    """Apply official scope checks and rerank the same candidate pool."""
    enriched = []
    for record in records:
        item = dict(record)
        apply_scope_record(item, scope_records)
        enriched.append(item)
    return assign_candidate_labels(rank_metric_records(profile, enriched))


def assign_submission_bands(ranked: List[Dict], profile: Optional[Dict] = None) -> List[Dict]:
    """Backward-compatible alias for assign_candidate_labels()."""
    return assign_candidate_labels(ranked)


def format_selection_report(
    profile: Dict,
    ranked: List[Dict],
    title: str = "",
) -> str:
    """Format a concise user-facing sci-select report."""
    if not ranked:
        return "sci-select 未找到合适候选期刊。建议放宽影响因子、分区或学科筛选条件。"
    ranked = assign_candidate_labels([dict(item) for item in ranked])

    lines = []
    heading = "sci-select 选刊建议"
    if title:
        heading += f"：{title}"
    lines.append(f"# {heading}")
    lines.append("")

    direction_summary = profile.get("direction_summary", "")
    if direction_summary:
        lines.append(f"**方向总结**：{direction_summary}")

    profile_parts = []
    for label, key in (
        ("研究对象", "research_object"),
        ("核心问题", "research_question"),
        ("贡献类型", "contribution_type"),
    ):
        if profile.get(key):
            profile_parts.append(f"{label}={profile[key]}")
    if profile_parts:
        lines.append(f"**论文画像**：{'；'.join(profile_parts)}")

    category_text = "；".join(
        f"{c['category1']}/{c['category2'] or '综合'}" for c in profile.get("categories", [])
    )
    if category_text:
        lines.append(f"**识别方向**：{category_text}")

    terms = "、".join(profile.get("matched_terms", [])[:8])
    if terms:
        lines.append(f"**命中主题**：{terms}")

    lines.append(
        "**使用边界**：以下结果用于发现值得人工复核的候选期刊；"
        "不评价稿件水平，不预测录用概率，也不声称存在唯一最优期刊。"
    )
    lines.append(
        "**可追加筛选**：如需收窄结果，可继续说明 IF 范围、JCR Q 区、2025中科院、"
        "2026新锐、SCIE/ESCI、是否排除预警期刊，以及希望返回的数量；"
        "这些会作为筛选条件，不替代方向证据和 scope 判断。"
    )
    if _low_confidence_recall(ranked):
        lines.append("**召回提醒**：候选召回置信度较低，当前列表可能只是大类相关。不要仅按 IF 或分区决策，建议补充人工目标刊、官网 scope 或官方 Journal Finder 复核。")
    if profile.get("retrieval_notes"):
        lines.append(f"**检索降级**：{'；'.join(str(note) for note in profile['retrieval_notes'][:3])}")
    consistency = profile.get("profile_consistency") or {}
    if consistency.get("status") in {"medium", "low"}:
        lines.append(
            "**画像分歧**：独立论文画像一致性为"
            f"{consistency['status']}；已保留多组检索式并扩大召回，"
            "不要把单一方向总结当作确定结论。"
        )

    lines.append("")
    lines.append(format_selection_matrix(profile, ranked))
    lines.append("")
    for idx, item in enumerate(ranked, 1):
        journal_level = item.get("journal_level", "待定")
        lines.append(
            f"## {idx}. {item.get('name', '未知期刊')}｜{journal_level}｜"
            f"{_candidate_status(item)}"
        )
        lines.append(f"**指标**：{item.get('metrics_line') or format_metrics_line(item)}")
        if item.get("fit_reasons"):
            lines.append(f"**匹配理由**：{'；'.join(item['fit_reasons'][:3])}")
        precedents = item.get("publication_precedents") or []
        if precedents:
            examples = "；".join(
                f"{work.get('year') or '-'} {work.get('title', '')}" for work in precedents[:3]
            )
            lines.append(f"**近年发表先例**：{examples}")
        if item.get("scope_verified"):
            scope_text = "；".join(str(value) for value in item.get("scope_evidence", [])[:2])
            source = item.get("scope_source_url", "")
            lines.append(
                f"**官网 scope**：已核验{f'；{scope_text}' if scope_text else ''}"
                f"{f'；来源={source}' if source else ''}"
            )
        elif item.get("scope_checked"):
            source = item.get("scope_source_url", "")
            match = item.get("scope_match", "weak")
            status = "已读取，无法自动判断" if match == "unresolved" else f"已读取，匹配证据为 {match}"
            lines.append(
                f"**官网 scope**：{status}"
                f"{f'；来源={source}' if source else ''}"
            )
        else:
            lines.append("**官网 scope**：官网 scope 待核验")
        if item.get("risk_reasons"):
            lines.append(f"**风险提醒**：{'；'.join(item['risk_reasons'])}")
        if item.get("data_notes"):
            lines.append(f"**数据说明**：{'；'.join(item['data_notes'])}")
        source_status = item.get("_source_status") or {}
        if isinstance(source_status, dict):
            status_notes = []
            for source, detail in source_status.items():
                if not isinstance(detail, dict):
                    continue
                status = detail.get("status", "")
                reason = detail.get("reason", "")
                if status:
                    status_notes.append(f"{source}={status}{f'（{reason}）' if reason else ''}")
            if status_notes:
                lines.append(f"**来源状态**：{'；'.join(status_notes)}")
        lines.append("")

    return "\n".join(lines).strip()


def format_selection_matrix(
    profile: Dict,
    ranked: List[Dict],
) -> str:
    """Format a compact Markdown decision matrix."""
    ranked = assign_candidate_labels([dict(item) for item in ranked])
    lines = [
        "## 快速决策表",
        "",
        "| 期刊 | 候选状态 | 方向证据 | 期刊层级 | IF | 2025中科院 | 2026新锐 | 收录 | OA/APC | 审稿速度 | 数据状态 |",
        "|---|---|---|---|---:|---|---|---|---|---|---|",
    ]

    for item in ranked:
        lines.append(
            "| {name} | {tier} | {fit} | {level} | {impact} | {cas_partition} | {xinrui_partition} | {sci} | {oa} | {speed} | {data} |".format(
                name=_table_cell(item.get("name", "")),
                tier=_candidate_status(item),
                fit=item.get("fit_confidence", "弱"),
                level=item.get("journal_level", "待定"),
                impact=item.get("impact_factor") or "-",
                cas_partition=_table_cell(_cas_partition(item)),
                xinrui_partition=_table_cell(_xinrui_partition(item)),
                sci=_format_sci_cell(item),
                oa=_format_oa_cell(item),
                speed=_table_cell(_short_speed(item.get("speed", ""))),
                data=_table_cell(_compact_data_status(item)),
            )
        )

    return "\n".join(lines)


def format_selection_csv(profile: Dict, ranked: List[Dict]) -> str:
    """Format selected candidates as CSV for spreadsheet export."""
    rows = assign_candidate_labels([dict(item) for item in ranked])
    output = io.StringIO()
    fieldnames = [
        "journal",
        "candidate_status",
        "fit_confidence",
        "journal_level",
        "impact_factor",
        "jcr_quartile",
        "cas_2025",
        "xinrui_2026",
        "coverage",
        "oa_apc",
        "review_speed",
        "data_status",
        "fit_reasons",
        "risk_reasons",
        "data_notes",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for item in rows:
        writer.writerow(
            {
                "journal": item.get("name", ""),
                "candidate_status": _candidate_status(item),
                "fit_confidence": item.get("fit_confidence", ""),
                "journal_level": item.get("journal_level", ""),
                "impact_factor": item.get("impact_factor") or "",
                "jcr_quartile": item.get("jcr_quartile") or "",
                "cas_2025": _cas_partition(item),
                "xinrui_2026": _xinrui_partition(item),
                "coverage": _format_sci_cell(item),
                "oa_apc": _format_oa_cell(item),
                "review_speed": _short_speed(item.get("speed", "")),
                "data_status": _compact_data_status(item),
                "fit_reasons": "; ".join(item.get("fit_reasons", [])),
                "risk_reasons": "; ".join(item.get("risk_reasons", [])),
                "data_notes": "; ".join(item.get("data_notes", [])),
            }
        )
    return output.getvalue()


def format_report(results: List[Dict], profile: Optional[Dict] = None, **kwargs) -> str:
    """Compatibility wrapper for older callers that expect format_report(results)."""
    return format_selection_report(profile or {"categories": []}, results, **kwargs)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def _normalize_journal_name(value: str) -> str:
    text = re.sub(r"^the\b[\s:,-]*", "", str(value or "").lower().strip())
    return re.sub(r"[^a-z0-9]+", "", text)


def _contains_term(normalized_text: str, alias: str) -> bool:
    alias = alias.lower()
    if re.search(r"[\u4e00-\u9fff]", alias):
        return alias in normalized_text
    pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
    return re.search(pattern, normalized_text) is not None


def _topic_fit(profile: Dict, record: MetricRecord) -> Tuple[int, List[str]]:
    candidate = record.get("_candidate", {}) or {}
    search_category = candidate.get("_search_category", {}) or record.get("_search_category", {}) or {}
    fields = " ".join(
        str(record.get(key, ""))
        for key in ("field", "partition_detail", "name", "shortname")
    )
    fields = " ".join(
        [
            fields,
            str(candidate.get("field", "")),
            str(search_category.get("category1", "")),
            str(search_category.get("category2", "")),
        ]
    ).lower()
    score = 0
    reasons: List[str] = []

    journal_name_tokens = {_scope_stem(value) for value in re.findall(r"[a-z0-9]+", record.get("name", "").lower())}
    name_hits = sorted(term for term in _profile_scope_terms(profile) if term in journal_name_tokens)
    if name_hits:
        score += min(16, len(name_hits) * 4)
        reasons.append(f"期刊名称覆盖核心词 {', '.join(name_hits[:4])}")

    if record.get("scope_verified"):
        score += 24
        reasons.append("期刊官网 scope 已核验")
    elif record.get("scope_checked"):
        scope_match = record.get("scope_match", "weak")
        if scope_match == "unresolved":
            reasons.append("期刊官网 scope 已读取，但语言或关键词不足，无法自动判断")
        else:
            penalty = 24 if scope_match == "incompatible" else 8
            score -= penalty
            reasons.append(f"期刊官网 scope 匹配不足 ({scope_match})")

    precedent_count = int(record.get("similar_works_count", 0) or 0)
    query_coverage = int(record.get("query_coverage", 0) or 0)
    literature_score = int(record.get("literature_evidence_score", 0) or 0)
    if precedent_count:
        score += min(28, literature_score or precedent_count * 4 + query_coverage * 4)
        reasons.append(f"近年相似论文先例 {precedent_count} 篇 / 覆盖 {query_coverage or 1} 组检索")

    for category in profile.get("categories", []):
        cat2 = category.get("category2", "")
        cat1 = category.get("category1", "")
        weight = int(category.get("score", 1))
        if cat2 and cat2.lower() in fields:
            score += 12 + weight * 2
            reasons.append(f"覆盖核心方向 {cat2}")
        elif cat1 and cat1.lower() in fields:
            score += 6 + weight
            reasons.append(f"覆盖大类方向 {cat1}")

    for term in profile.get("matched_terms", []):
        if term.lower() in fields:
            score += 4

    evidence_hits = [
        term
        for term in profile.get("topic_evidence", [])
        if term and term.lower() in fields
    ]
    if evidence_hits:
        score += min(18, len(evidence_hits) * 6)
        reasons.append(f"覆盖细分主题 {', '.join(evidence_hits[:3])}")

    exclusion_hits = [
        term
        for term in profile.get("exclusions", [])
        if term and str(term).lower() in fields
    ]
    if exclusion_hits:
        score -= min(24, len(exclusion_hits) * 12)
        reasons.append(f"触及排除方向 {', '.join(exclusion_hits[:2])}")

    if not reasons and profile.get("categories"):
        score += 4
        reasons.append("主题相关性需要人工复核")

    return score, reasons


def _quality_score(record: MetricRecord, preferences: Dict) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    sci = _clean_sci(record.get("sci_type", ""))
    if _is_wos_removed(record):
        reasons.append("Web of Science 收录已异常")
    elif "SCIE" in sci or "SSCI" in sci:
        score += 14
        reasons.append("SCIE/SSCI 收录")
    elif "ESCI" in sci:
        score += 5
        reasons.append("ESCI 收录")

    partition, partition_label = _preferred_partition(record)
    if "1区" in partition:
        score += 18
        reasons.append(f"{partition_label}1区")
    elif "2区" in partition:
        score += 13
        reasons.append(f"{partition_label}2区")
    elif "3区" in partition:
        score += 7
    elif "4区" in partition:
        score += 3

    if not partition:
        quartile = str(record.get("jcr_quartile") or "").upper()
        if "Q1" in quartile:
            score += 13
            reasons.append("JCR Q1")
        elif "Q2" in quartile:
            score += 9
            reasons.append("JCR Q2")
        elif "Q3" in quartile:
            score += 5
        elif "Q4" in quartile:
            score += 2

    impact = _float(record.get("impact_factor"))
    if impact >= 8:
        score += 12
    elif impact >= 5:
        score += 9
    elif impact >= 3:
        score += 5
    elif impact > 0:
        score += 2

    h_index = _float(record.get("h_index"))
    if h_index >= 150:
        score += 6
    elif h_index >= 80:
        score += 4
    elif h_index >= 30:
        score += 2

    if preferences.get("oa_required") and not record.get("is_oa"):
        score -= 8
        reasons.append("不满足 OA 偏好")

    return score, reasons


def _risk_penalty(profile: Dict, record: MetricRecord) -> Tuple[int, List[str]]:
    penalty = 0
    reasons: List[str] = []

    if _is_wos_removed(record):
        penalty += 100
        reasons.append("Web of Science/SCIE 收录异常，需按 Clarivate Master Journal List 复核")

    if record.get("warning"):
        penalty += 60
        reasons.append("LetPub/预警风险")

    sci = _clean_sci(record.get("sci_type", ""))
    if "ESCI" in sci:
        penalty += 12
        reasons.append("ESCI 期刊，需确认是否满足投稿要求")
    elif not sci and "letpub" in record.get("_sources", []):
        penalty += 35
        reasons.append("未确认 SCI/SCIE 收录")

    if _looks_like_review_journal(record.get("name", "")) and "review" not in profile.get("methods", []):
        penalty += 20
        reasons.append("综述型期刊，当前稿件更像研究论文")

    return penalty, reasons


def _tier(entry: MetricRecord) -> str:
    if _is_wos_removed(entry):
        return "不推荐"

    if entry.get("warning"):
        return "不推荐"

    if any("综述型期刊" in reason for reason in entry.get("risk_reasons", [])):
        return "谨慎"

    sci = _clean_sci(entry.get("sci_type", ""))
    if "ESCI" in sci:
        return "谨慎"
    if not sci and "letpub" in entry.get("_sources", []):
        return "谨慎"

    if entry.get("fit_confidence") == "弱":
        return "谨慎" if entry.get("fit_score", 0) >= 4 else "不推荐"

    if entry["fit_score"] >= 22 and entry.get("risk_penalty", 0) == 0:
        return "推荐"
    if entry["fit_score"] >= 14 and entry.get("risk_penalty", 0) < 12:
        return "备选"
    if entry["fit_score"] >= 8:
        return "谨慎"
    return "不推荐"


def _candidate_label(item: Dict) -> str:
    if _is_wos_removed(item):
        return "谨慎"
    if item.get("tier") in ("不推荐", "谨慎"):
        return "谨慎"
    if item.get("warning"):
        return "谨慎"
    if any("综述型期刊" in reason for reason in item.get("risk_reasons", [])):
        return "谨慎"

    sci = _clean_sci(item.get("sci_type", ""))
    if "ESCI" in sci:
        return "谨慎"

    journal_level = item.get("journal_level") or _journal_level(item)
    return {
        "高位": "高位候选",
        "中位": "中位候选",
        "常规": "常规候选",
    }.get(journal_level, "层级待定")


def _candidate_status(item: Dict) -> str:
    return {
        "推荐": "优先核验",
        "备选": "可选",
        "谨慎": "谨慎",
        "不推荐": "排除",
    }.get(item.get("tier", ""), item.get("tier", "待定"))


def _fit_confidence(entry: Dict, fit_reasons: List[str]) -> str:
    if entry.get("scope_verified"):
        return "强"
    precedent_count = int(entry.get("similar_works_count", 0) or 0)
    query_coverage = int(entry.get("query_coverage", 0) or 0)
    if precedent_count >= 2 and query_coverage >= 2:
        return "强"
    if precedent_count >= 2 or any("核心方向" in reason or "细分主题" in reason for reason in fit_reasons):
        return "中"
    return "弱"


def _journal_level(record: Dict) -> str:
    partition, _label = _preferred_partition(record)
    if "1区" in partition:
        return "高位"
    if "2区" in partition:
        return "中位"
    if "3区" in partition or "4区" in partition:
        return "常规"

    quartile = str(record.get("jcr_quartile") or "").upper()
    if "Q1" in quartile:
        return "高位"
    if "Q2" in quartile:
        return "中位"
    if "Q3" in quartile or "Q4" in quartile:
        return "常规"

    impact = _float(record.get("impact_factor"))
    if impact >= 8:
        return "高位"
    if impact >= 4:
        return "中位"
    if impact > 0:
        return "常规"
    return "待定"


SCOPE_STOPWORDS = {
    "analysis",
    "applied",
    "assessment",
    "engineering",
    "international",
    "journal",
    "method",
    "model",
    "research",
    "science",
    "study",
    "system",
    "systems",
    "using",
}


def _profile_scope_terms(profile: Dict) -> List[str]:
    values = [
        profile.get("primary_field", ""),
        profile.get("specialty", ""),
        profile.get("research_object", ""),
        *profile.get("target_audience", []),
        *profile.get("scope_terms", []),
    ]
    terms = []
    for value in values:
        for word in re.findall(r"[a-z0-9]+", str(value or "").lower()):
            stemmed = _scope_stem(word)
            if len(stemmed) < 4 or stemmed in SCOPE_STOPWORDS or stemmed in terms:
                continue
            terms.append(stemmed)
        for sequence in re.findall(r"[\u4e00-\u9fff]+", str(value or "")):
            for index in range(max(1, len(sequence) - 1)):
                token = sequence if len(sequence) == 1 else sequence[index : index + 2]
                if token not in terms:
                    terms.append(token)
    return terms[:20]


def _scope_stem(value: str) -> str:
    word = str(value or "").lower()
    if len(word) > 5 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 5 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _data_notes(record: MetricRecord) -> List[str]:
    notes: List[str] = []
    sources = set(record.get("_sources", []))
    errors = record.get("_source_errors", {}) or {}

    notes.extend(str(note) for note in record.get("status_notes", []) if note)

    skipped_sources = set(record.get("_skipped_sources", []))
    if "letpub" in skipped_sources:
        notes.append("LetPub详情未请求（本地索引已覆盖核心指标）")
    elif "letpub" not in sources and "letpub-search" not in sources:
        notes.append("LetPub详情未获取")
    if "openalex" not in sources:
        notes.append("OpenAlex未获取")
    if not _has_xinrui_partition(record):
        notes.append("2026新锐分区未获取")

    for source, error in errors.items():
        if source == "openalex" and "OpenAlex未获取" not in notes:
            notes.append("OpenAlex未获取")
        elif source == "letpub" and "LetPub详情未获取" not in notes:
            notes.append("LetPub详情未获取")
        if error and len(str(error)) <= 80:
            notes.append(f"{source}: {error}")

    return notes


def _format_sci_cell(item: Dict) -> str:
    if _is_wos_removed(item):
        return "WoS已移除"
    sci = str(item.get("sci_type") or "").replace(" ", "")
    normalized = _clean_sci(sci)
    if "SCIE" in normalized:
        return "SCIE"
    if "SSCI" in normalized:
        return "SSCI"
    if "ESCI" in normalized:
        return "ESCI"
    return sci or "-"


def _format_oa_cell(item: Dict) -> str:
    if item.get("is_oa") is True:
        return f"OA(${item['apc_usd']})" if item.get("apc_usd") else "OA"
    if item.get("is_oa") is False:
        return "非OA"
    return "-"


def _short_speed(speed: str) -> str:
    speed = str(speed or "").split("；")[0].replace("网友分享经验：", "").strip()
    return speed if speed else "-"


def _compact_data_status(item: Dict) -> str:
    notes = []
    sources = set(item.get("_sources", []))
    if "journal-index" in sources:
        notes.append("本地索引")
    if "letpub" in sources or "letpub-search" in sources:
        notes.append("LetPub")
    if "openalex" in sources:
        notes.append("OpenAlex")
    if "openalex-works" in sources:
        notes.append("OpenAlex相似论文")
    if "xinrui" in sources:
        notes.append("新锐")
    elif _has_xinrui_partition(item):
        notes.append("LetPub新锐")
    if not notes:
        notes.append("待复核")
    if item.get("data_notes"):
        missing = [n for n in item["data_notes"] if "未获取" in n or "未核验" in n]
        notes.extend(missing[:2])
    return " / ".join(dict.fromkeys(notes))


def _table_cell(value: str) -> str:
    return str(value or "-").replace("|", "/").replace("\n", " ")


def _clean_sci(value: str) -> str:
    return str(value or "").upper().replace(" ", "")


def _partition_matches(value: str, required: str) -> bool:
    if not required:
        return True
    value = str(value or "")
    required = str(required or "")
    return bool(value and value != "未获取" and required in value)


def _passes_selection_constraints(
    record: MetricRecord,
    impact_low: str = "",
    impact_high: str = "",
    jcr_quartiles: Optional[List[str]] = None,
    cas_partitions: Optional[List[str]] = None,
    coverage_types: Optional[List[str]] = None,
    exclude_warnings: bool = False,
    exclude_esci_only: bool = False,
) -> bool:
    if exclude_warnings and (record.get("warning") or _is_wos_removed(record)):
        return False

    impact = _float(record.get("impact_factor"))
    low = _float(impact_low)
    high = _float(impact_high)
    if low and (not impact or impact < low):
        return False
    if high and (not impact or impact > high):
        return False

    allowed_jcr = {_normalize_filter_token(value) for value in jcr_quartiles or [] if value}
    if allowed_jcr:
        quartile = _normalize_filter_token(record.get("jcr_quartile", ""))
        if quartile not in allowed_jcr:
            return False

    allowed_cas = [str(value) for value in cas_partitions or [] if value]
    if allowed_cas and not any(_partition_matches(_cas_partition(record), value) for value in allowed_cas):
        return False

    sci = _clean_sci(record.get("sci_type", ""))
    if exclude_esci_only and "ESCI" in sci and "SCIE" not in sci and "SSCI" not in sci:
        return False

    allowed_coverage = {_normalize_filter_token(value) for value in coverage_types or [] if value}
    if allowed_coverage:
        if not sci:
            return False
        if not any(value in sci for value in allowed_coverage):
            return False

    return True


def _normalize_filter_token(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def _candidate_xinrui_partition(candidate: MetricRecord) -> str:
    return str(candidate.get("xinrui_partition_2026") or "")


def _cas_partition(record: MetricRecord) -> str:
    return str(record.get("cas_partition_2025") or record.get("partition") or "")


def _xinrui_partition(record: MetricRecord) -> str:
    return str(record.get("xinrui_partition_2026") or "未获取")


def _preferred_partition(record: MetricRecord) -> Tuple[str, str]:
    xinrui_partition = str(record.get("xinrui_partition_2026") or "")
    if xinrui_partition:
        return xinrui_partition, "2026新锐"
    return _cas_partition(record), "2025中科院"


def _has_xinrui_partition(record: MetricRecord) -> bool:
    return bool(record.get("xinrui_partition_2026"))


def _is_wos_removed(record: MetricRecord) -> bool:
    return record.get("wos_status") == "removed" or _clean_sci(record.get("sci_type", "")) == "WOS_REMOVED"


def _looks_like_review_journal(name: str) -> bool:
    text = str(name or "").lower()
    return (
        "review" in text
        or "reviews" in text
        or text.startswith("annual review")
        or "interdisciplinary reviews" in text
    )


def _topic_evidence(normalized_text: str, matched_terms: List[str]) -> List[str]:
    evidence = [term for term in matched_terms if term not in METHOD_LABELS]
    for pattern in TOPIC_EVIDENCE_PATTERNS:
        for match in re.findall(pattern, normalized_text):
            if isinstance(match, tuple):
                match = next((part for part in match if part), "")
            if match and match not in evidence:
                evidence.append(match)
    return evidence[:12]


def _primary_signal(topic_evidence: List[str], matched_terms: List[str]) -> str:
    for term in topic_evidence:
        if term not in METHOD_LABELS:
            return term
    for term in matched_terms:
        if term not in METHOD_LABELS:
            return term
    return matched_terms[0] if matched_terms else ""


def _low_confidence_recall(ranked: List[Dict]) -> bool:
    if not ranked:
        return False

    fit_scores = sorted(int(item.get("fit_score", 0)) for item in ranked)
    median_fit = fit_scores[len(fit_scores) // 2]
    weak_reason_count = sum(
        1
        for item in ranked
        if item.get("fit_reasons") == ["主题相关性需要人工复核"]
    )
    return median_fit <= 6 or weak_reason_count >= max(1, len(ranked) // 2)


def _float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


if __name__ == "__main__":
    demo = select_journals(
        "Groundwater nitrate source identification using stable isotopes and hydrochemistry",
        impact_low="3",
        max_candidates=8,
    )
    print(format_selection_report(demo["profile"], demo["results"]))
