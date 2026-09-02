"""Deterministic second-pass checks for user/agent-supplied official scope text."""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence
from urllib.parse import urlparse


AGGREGATOR_DOMAINS = {
    "openalex.org",
    "letpub.com.cn",
    "wikipedia.org",
    "scansci.com",
    "scansci.cn",
}
STOPWORDS = {
    "analysis", "article", "international", "journal", "method", "research",
    "science", "study", "system", "using", "with", "from", "that", "this",
}


def build_scope_verification_queue(
    profile: Dict,
    candidates: Sequence[Dict],
    limit: int = 5,
) -> List[Dict]:
    """Prepare a top-candidate queue without scraping or claiming verification."""
    terms = _profile_terms(profile)
    article_type = str(profile.get("contribution_type") or "").strip()
    return [
        {
            "journal": candidate.get("name", ""),
            "status": (
                "已核验"
                if candidate.get("scope_verified")
                else "已读取待判断"
                if candidate.get("scope_checked")
                else "待核验"
            ),
            "scope_match": candidate.get("scope_match", ""),
            "source_url": candidate.get("scope_source_url", ""),
            "terms": terms[:12],
            "article_type": article_type,
            "instruction": (
                "Review the recorded official scope evidence."
                if candidate.get("scope_checked")
                else "Open the official journal aims-and-scope page and supply its text and URL."
            ),
        }
        for candidate in candidates[: max(1, int(limit))]
        if candidate.get("name")
    ]


def verify_official_scope(
    profile: Dict,
    journal_name: str,
    scope_text: str,
    source_url: str,
    publisher_domain_confirmed: bool = False,
) -> Dict:
    """Verify supplied scope evidence only when it comes from a plausible official page."""
    domain = _validated_official_domain(source_url)
    if not publisher_domain_confirmed:
        raise ValueError("Confirm that the source domain belongs to the journal or its publisher")
    text = re.sub(r"\s+", " ", str(scope_text or "")).strip()
    if len(text) < 120:
        raise ValueError("Official scope text is too short to verify")
    terms = _profile_terms(profile)
    if not terms:
        raise ValueError("Paper profile has no usable scope terms")
    normalized = text.lower()
    comparable = [term for term in terms if _same_script_available(term, normalized)]
    matched = [term for term in comparable if _contains(normalized, term)]
    coverage = len(matched) / len(comparable) if comparable else 0.0
    if not comparable:
        match = "unresolved"
    elif coverage >= 0.35 or len(matched) >= 4:
        match = "strong"
    elif coverage >= 0.18 or len(matched) >= 2:
        match = "moderate"
    elif matched:
        match = "weak"
    else:
        match = "incompatible"
    evidence = _matching_sentences(text, matched)[:3]
    return {
        "name": journal_name,
        "scope_checked": True,
        "scope_verified": match in {"strong", "moderate"},
        "scope_match": match,
        "scope_match_score": round(coverage, 4),
        "scope_evidence": evidence,
        "scope_source_url": source_url,
        "scope_source_domain": domain,
        "scope_source_domain_confirmed": True,
        "scope_matched_terms": matched[:12],
    }


def apply_scope_record(record: Dict, scope_records: Iterable[Dict]) -> Dict:
    """Attach a pre-verified scope record to one candidate by normalized journal name."""
    target = _normalize_name(record.get("name", ""))
    for scope in scope_records or []:
        if _normalize_name(scope.get("name") or scope.get("journal") or "") != target:
            continue
        if (
            not scope.get("scope_checked")
            or not scope.get("scope_source_url")
            or scope.get("scope_source_domain_confirmed") is not True
        ):
            continue
        _validated_official_domain(scope["scope_source_url"])
        for key in (
            "scope_checked", "scope_verified", "scope_match", "scope_match_score",
            "scope_evidence", "scope_source_url", "scope_source_domain", "scope_matched_terms",
            "scope_source_domain_confirmed",
        ):
            if key in scope:
                record[key] = scope[key]
        break
    return record


def _validated_official_domain(url: str) -> str:
    parsed = urlparse(str(url or ""))
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Scope evidence requires an HTTPS official-page URL")
    domain = parsed.hostname.lower().removeprefix("www.")
    if any(domain == blocked or domain.endswith(f".{blocked}") for blocked in AGGREGATOR_DOMAINS):
        raise ValueError("Aggregator pages cannot be marked as official scope evidence")
    return domain


def _profile_terms(profile: Dict) -> List[str]:
    values = [
        profile.get("primary_field", ""), profile.get("specialty", ""),
        profile.get("research_object", ""), profile.get("research_question", ""),
        profile.get("contribution_type", ""), *profile.get("target_audience", []),
        *profile.get("topic_evidence", []), *profile.get("matched_terms", []),
    ]
    terms = []
    for value in values:
        for token in re.findall(r"[a-z0-9]+", str(value or "").lower()):
            if len(token) < 4 or token in STOPWORDS or token in terms:
                continue
            terms.append(token)
        for sequence in re.findall(r"[\u4e00-\u9fff]+", str(value or "")):
            for index in range(max(1, len(sequence) - 1)):
                token = sequence if len(sequence) == 1 else sequence[index : index + 2]
                if token not in terms:
                    terms.append(token)
    return terms[:24]


def _same_script_available(term: str, text: str) -> bool:
    if re.search(r"[\u4e00-\u9fff]", term):
        return bool(re.search(r"[\u4e00-\u9fff]", text))
    return bool(re.search(r"[a-z]", text))


def _contains(text: str, term: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def _matching_sentences(text: str, terms: Sequence[str]) -> List[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    ranked = sorted(
        ((sum(_contains(sentence.lower(), term) for term in terms), sentence) for sentence in sentences),
        key=lambda item: (-item[0], len(item[1])),
    )
    return [sentence[:400] for score, sentence in ranked if score > 0]


def _normalize_name(value: str) -> str:
    text = str(value or "").lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", text)
