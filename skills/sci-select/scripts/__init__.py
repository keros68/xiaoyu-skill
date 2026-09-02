"""sci-select package."""

from .select_journals import (
    infer_paper_profile,
    merge_paper_profile,
    select_journals,
    rank_metric_records,
    format_selection_report,
    format_selection_matrix,
    assign_candidate_labels,
    rerank_with_scope_evidence,
    assign_submission_bands,
)
from .official_finders import build_finder_checklist, format_finder_checklist
from .scope_evidence import build_scope_verification_queue, verify_official_scope
from .profile_consistency import compare_profiles, validate_profile

__all__ = [
    "infer_paper_profile",
    "merge_paper_profile",
    "select_journals",
    "rank_metric_records",
    "format_selection_report",
    "format_selection_matrix",
    "assign_candidate_labels",
    "rerank_with_scope_evidence",
    "assign_submission_bands",
    "build_finder_checklist",
    "format_finder_checklist",
    "build_scope_verification_queue",
    "verify_official_scope",
    "compare_profiles",
    "validate_profile",
]
