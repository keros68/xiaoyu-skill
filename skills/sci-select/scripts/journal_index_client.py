"""Bundled, local, and static journal index reader.

Runtime prefers a user-configured sci-select SQLite index, then a user-configured
JSON index, then the bundled sci-select SQLite index shipped in assets/. JSON
remains supported via SCI_SELECT_JOURNAL_INDEX_PATH or SCI_SELECT_JOURNAL_INDEX_URL.
"""
import json
import os
import re
import sqlite3
from functools import lru_cache
from typing import Dict, List, Optional
from urllib import request


BUNDLED_SQLITE_INDEX = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "sci_select_journals.sqlite")
)


def lookup_index_journal(journal_name: str, issn: str = "") -> Optional[Dict]:
    configured_db = _configured_sqlite_source()
    if configured_db:
        row = _lookup_sqlite_journal(configured_db, journal_name, issn)
        if row:
            return _to_metrics(row)

    source = _index_source()
    rows = _load_index_rows(source) if source else []
    if rows:
        normalized_issn = _normalize_issn(issn)
        normalized_name = _normalize_name(journal_name)

        if normalized_issn:
            for row in rows:
                if normalized_issn in {
                    _normalize_issn(row.get("issn", "")),
                    _normalize_issn(row.get("eissn", "")),
                } and _names_compatible(journal_name, row.get("title", "")):
                    return _to_metrics(row)

        for row in rows:
            if normalized_name and normalized_name == _normalize_name(row.get("title", "")):
                return _to_metrics(row)

    bundled_db = _bundled_sqlite_source()
    if bundled_db:
        row = _lookup_sqlite_journal(bundled_db, journal_name, issn)
        if row:
            return _to_metrics(row)

    return None


def search_index_journals(scope_terms: List[str], limit: int = 20) -> List[Dict]:
    """Recall specialist candidates from journal titles without a journal blacklist."""
    terms = [
        re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(term or "").lower())
        for term in scope_terms
        if len(re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(term or "").lower())) >= 2
    ]
    terms = list(dict.fromkeys(terms))
    if not terms:
        return []

    rows = []
    configured_db = _configured_sqlite_source()
    if configured_db:
        rows.extend(_all_sqlite_rows(configured_db))
    source = _index_source()
    if source:
        rows.extend(_load_index_rows(source))
    bundled_db = _bundled_sqlite_source()
    if bundled_db:
        rows.extend(_all_sqlite_rows(bundled_db))

    candidates = {}
    for row in rows:
        title = str(row.get("title") or row.get("name") or "").strip()
        normalized = _normalize_name(title)
        tokens = {
            re.sub(r"[^a-z0-9]+", "", token.lower())
            for token in re.findall(r"[A-Za-z0-9]+", title)
        }
        for sequence in re.findall(r"[\u4e00-\u9fff]+", title):
            tokens.add(sequence)
            tokens.update(sequence[index : index + 2] for index in range(len(sequence) - 1))
        exact_hits = [term for term in terms if term in tokens]
        partial_hits = [term for term in terms if term not in tokens and term in normalized]
        score = len(exact_hits) * 4 + len(partial_hits)
        if not score:
            continue
        key = _normalize_name(title)
        record = {
            **_to_metrics(row),
            "name": title,
            "specialist_title_score": score,
            "specialist_title_terms": [*exact_hits, *partial_hits],
            "_sources": ["journal-title-index"],
        }
        if key not in candidates or score > candidates[key]["specialist_title_score"]:
            candidates[key] = record
    return sorted(
        candidates.values(),
        key=lambda row: (-row["specialist_title_score"], len(row["name"]), row["name"]),
    )[: max(1, int(limit))]


@lru_cache(maxsize=4)
def _load_index_rows(source: str) -> List[Dict]:
    try:
        if source.startswith(("http://", "https://")):
            with request.urlopen(source, timeout=20) as resp:
                payload = json.loads(resp.read().decode("utf-8-sig"))
        else:
            with open(source, "r", encoding="utf-8-sig") as f:
                payload = json.load(f)
    except (OSError, json.JSONDecodeError, TimeoutError):
        return []

    if isinstance(payload, dict):
        rows = payload.get("journals", [])
    else:
        rows = payload
    return [row for row in rows if isinstance(row, dict)]


def _index_source() -> str:
    return (
        os.environ.get("SCI_SELECT_JOURNAL_INDEX_PATH", "").strip()
        or os.environ.get("SCI_SELECT_JOURNAL_INDEX_URL", "").strip()
    )


def _configured_sqlite_source() -> str:
    return os.environ.get("SCI_SELECT_JOURNAL_INDEX_DB", "").strip()


def _bundled_sqlite_source() -> str:
    return BUNDLED_SQLITE_INDEX if os.path.exists(BUNDLED_SQLITE_INDEX) else ""


def _lookup_sqlite_journal(source: str, journal_name: str, issn: str = "") -> Optional[Dict]:
    if not os.path.exists(source):
        return None

    normalized_issn = _normalize_issn(issn)
    normalized_name = _normalize_name(journal_name)
    conn = None
    try:
        conn = sqlite3.connect(source)
        conn.row_factory = sqlite3.Row
        if normalized_issn:
            row = conn.execute(
                """
                SELECT payload_json FROM journals
                WHERE normalized_issn = ? OR normalized_eissn = ?
                LIMIT 1
                """,
                (normalized_issn, normalized_issn),
            ).fetchone()
            if row:
                payload = json.loads(row["payload_json"])
                if _names_compatible(journal_name, payload.get("title", "")):
                    return payload

        if normalized_name:
            row = conn.execute(
                """
                SELECT payload_json FROM journals
                WHERE normalized_title = ?
                LIMIT 1
                """,
                (normalized_name,),
            ).fetchone()
            if row:
                return json.loads(row["payload_json"])
    except (OSError, sqlite3.Error, json.JSONDecodeError):
        return None
    finally:
        if conn is not None:
            conn.close()
    return None


@lru_cache(maxsize=4)
def _all_sqlite_rows(source: str) -> List[Dict]:
    if not source or not os.path.exists(source):
        return []
    conn = None
    try:
        conn = sqlite3.connect(source)
        return [
            json.loads(row[0])
            for row in conn.execute("SELECT payload_json FROM journals")
        ]
    except (OSError, sqlite3.Error, json.JSONDecodeError):
        return []
    finally:
        if conn is not None:
            conn.close()


def _to_metrics(row: Dict) -> Dict:
    tags = row.get("tags") if isinstance(row.get("tags"), list) else []
    metrics = {
        "name": row.get("title") or row.get("name") or "",
        "issn": row.get("issn", ""),
        "eissn": row.get("eissn", ""),
        "impact_factor": row.get("jif_2025") or row.get("if_2023") or row.get("impact_factor"),
        "if_year": str(row.get("jcr_data_year") or row.get("if_year") or ""),
        "jcr_release_year": row.get("jcr_release_year"),
        "jcr_data_year": row.get("jcr_data_year"),
        "jcr_quartile": row.get("jcr_quartile_2025") or row.get("jcr_quartile", ""),
        "jcr_categories": row.get("jcr_categories", []),
        "cas_partition_2025": row.get("cas_2025", ""),
        "partition": row.get("cas_2025", ""),
        # 内置库这三项一直写在 payload 里却没有映射出来，取不到：
        # cas_top_2025（中科院 TOP）、open_access、xinrui_subject。
        # open_access 尤其不该丢——letpub_client 走网络时就产出这个键，
        # 内置库有同样的信息却读不到，同一事实两条来路不一致。
        "cas_top_2025": bool(row.get("cas_top_2025")),
        "open_access": bool(row.get("open_access")),
        "xinrui_subject": row.get("xinrui_subject", ""),
        "xinrui_partition_2026": row.get("xuankan_2026", ""),
        "nature_index": bool(row.get("nature_index")),
        "nature_index_year": row.get("nature_index_year"),
        "nature_index_articles": row.get("nature_index_articles"),
        "nature_index_publication_type": row.get("nature_index_publication_type"),
        "nature_index_source_url": row.get("nature_index_source_url"),
        "warning": bool(row.get("warning_latest") or row.get("xuankan_warning")),
        "journal_index_tags": tags,
        "journal_index_provenance": row.get("provenance", {}),
    }
    sci_type = _sci_type_from_tags(tags)
    if sci_type:
        metrics["sci_type"] = sci_type
    return {k: v for k, v in metrics.items() if v not in ("", None, [])}


def _sci_type_from_tags(tags: List[str]) -> str:
    normalized = {str(tag).upper().replace(" ", "") for tag in tags}
    for label in ("SCIE", "SSCI", "ESCI", "AHCI", "SCI"):
        if label in normalized:
            return label
    return ""


def _normalize_issn(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", str(value or "")).upper()


def _normalize_name(value: str) -> str:
    text = str(value or "").lower().strip().replace("&", " and ")
    text = re.sub(r"^the\b[\s:,-]*", "", text)
    return re.sub(r"[^a-z0-9]+", "", text)


def _names_compatible(left: str, right: str) -> bool:
    left_name = _normalize_name(left)
    right_name = _normalize_name(right)
    if not left_name or not right_name:
        return False
    if left_name == right_name:
        return True
    shorter, longer = sorted((left_name, right_name), key=len)
    return len(shorter) >= 8 and longer.startswith(shorter) and len(shorter) / len(longer) >= 0.7
