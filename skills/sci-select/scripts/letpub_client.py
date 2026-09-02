"""Small LetPub public-data client used by sci-select."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup


BASE = "https://letpub.com.cn"
WWW_BASE = "https://www.letpub.com.cn"

HEADERS = {
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
    ),
}


def autocomplete_journal(name: str, timeout: int = 15) -> List[Dict]:
    response = requests.get(
        f"{BASE}/journalappAjax.php",
        params={"querytype": "autojournal", "term": name},
        headers={**HEADERS, "x-requested-with": "XMLHttpRequest"},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def advanced_search(
    searchname: str = "",
    searchissn: str = "",
    searchfield: str = "",
    searchimpactlow: str = "",
    searchimpacthigh: str = "",
    searchscitype: str = "",
    searchcategory1: str = "",
    searchcategory2: str = "",
    searchjcrkind: str = "",
    searchopenaccess: str = "",
    searchsort: str = "relevance",
    timeout: int = 20,
) -> Dict:
    response = requests.post(
        f"{WWW_BASE}/index.php?page=journalapp&view=search",
        data={
            "searchname": searchname,
            "searchissn": searchissn,
            "searchfield": searchfield,
            "searchimpactlow": searchimpactlow,
            "searchimpacthigh": searchimpacthigh,
            "searchscitype": searchscitype,
            "view": "search",
            "searchcategory1": searchcategory1,
            "searchcategory2": searchcategory2,
            "searchjcrkind": searchjcrkind,
            "searchopenaccess": searchopenaccess,
            "searchsort": searchsort,
        },
        headers={**HEADERS, "content-type": "application/x-www-form-urlencoded"},
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_search_results(response.text)


def parse_search_results(html: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    info_text = _clean(soup.get_text(" ", strip=True))
    total_records = _first_int(re.search(r"(\d+)条记录", info_text))
    total_pages = _first_int(re.search(r"共(\d+)页", info_text)) or 1

    table = soup.select_one("table.table_yjfx")
    journals: List[Dict] = []
    if not table:
        return {"journals": journals, "total_pages": total_pages, "total_records": total_records}

    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 7:
            continue

        name_link = cells[1].find("a")
        name = _clean(name_link.get_text(" ", strip=True)) if name_link else ""
        href = name_link.get("href", "") if name_link else ""
        stat_text = _clean(cells[3].get_text(" ", strip=True))

        journals.append(
            {
                "issn": _clean(cells[0].get_text(" ", strip=True)),
                "name": name,
                "journal_id": _extract_query_value(href, "journalid"),
                "shortname": _extract_shortname(cells[1]),
                "rating": _first_number(_clean(cells[2].get_text(" ", strip=True))),
                "real_time_if": _match_text(r"IF:\s*([\d.]+)", stat_text),
                "h_index": _match_text(r"h-index:\s*(\d+)", stat_text),
                "cite_score": _match_text(r"CiteScore:\s*([\d.]+)", stat_text),
                "xinrui_partition_2026": _clean(cells[4].get_text(" ", strip=True)),
                "field": _clean(cells[5].get_text(" ", strip=True)),
                "sci_type": _clean(cells[6].get_text(" ", strip=True)),
            }
        )

    return {"journals": journals, "total_pages": total_pages, "total_records": total_records}


def lookup_journal(
    name: str,
    issn: str = "",
    source_errors: Optional[Dict] = None,
) -> Optional[Dict]:
    candidates = autocomplete_journal(name)
    if not candidates:
        for sep in (" - ", ": ", " (", " – ", " / "):
            if sep in name:
                candidates = autocomplete_journal(name.split(sep)[0].strip())
                if candidates:
                    break

    search_hit = _best_search_hit(name, issn, source_errors)
    journal_id = ""
    if search_hit:
        journal_id = search_hit.get("journal_id", "")
    if not journal_id and candidates:
        journal_id = str(candidates[0].get("id", ""))
    if not journal_id:
        return None

    detail = get_journal_detail(journal_id)
    if not detail:
        detail = {}

    detail["_journal_id"] = journal_id
    if search_hit:
        for key in (
            "sci_type", "partition", "xinrui_partition_2026", "field",
            "rating", "real_time_if", "issn", "name", "shortname",
        ):
            if search_hit.get(key) and not detail.get(key):
                detail[key] = search_hit[key]
        detail["_sci_type"] = search_hit.get("sci_type", "")

    if candidates and not detail.get("name"):
        detail["name"] = candidates[0].get("label") or candidates[0].get("value") or name
    known_issns = [detail.get("issn", ""), (search_hit or {}).get("issn", "")]
    if issn and _normalize_issn(issn) not in {_normalize_issn(value) for value in known_issns if value}:
        return None
    if detail.get("name") and not _names_compatible(name, detail["name"]):
        return None
    return detail


def get_journal_detail(journal_id: str, timeout: int = 20) -> Dict:
    response = requests.get(
        f"{BASE}/index.php",
        params={"journalid": journal_id, "page": "journalapp", "view": "detail"},
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_detail_page(response.text)


def parse_detail_page(html: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    detail: Dict = {}

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        label = _clean(cells[0].get_text(" ", strip=True))
        value_text = _clean(cells[1].get_text(" ", strip=True))

        if "期刊名字" in label:
            link = cells[1].find("a")
            detail["name"] = _clean(link.get_text(" ", strip=True)) if link else value_text
            detail["shortname"] = _extract_shortname(cells[1])
        elif "期刊ISSN" in label:
            detail["issn"] = value_text
        elif "最新影响因子" in label and "实时" not in label:
            detail["impact_factor"] = _first_number(value_text)
        elif "实时影响因子" in label:
            detail["real_time_if"] = _last_number(value_text)
        elif "五年影响因子" in label or "五年IF" in label:
            detail["five_year_if"] = _last_number(value_text)
        elif "是否OA开放访问" in label:
            detail["open_access"] = "yes" in value_text.lower()
        elif "OA期刊相关信息" in label:
            detail["oa_price"] = _first_int(re.search(r"USD\s*([\d,]+)", value_text.replace(",", "")))
        elif "出版商" in label:
            detail["publisher"] = value_text
        elif "涉及的研究方向" in label:
            detail["field"] = value_text
        elif "期刊分区表预警名单" in label or "国际期刊预警名单" in label:
            detail["warning"] = bool(value_text and "不在预警名单中" not in value_text)
        elif "期刊分区表" in label and "2025" in label:
            detail["ch_sci_2025"] = _parse_partition(cells[1])
        elif "新锐期刊分区表" in label:
            detail["xinrui_2026"] = _parse_partition_block(cells[1:])
            detail["xinrui_partition_2026"] = detail["xinrui_2026"].get("分区", "")
        elif "平均审稿速度" in label:
            detail["speed"] = value_text
        elif "平均录用比例" in label:
            detail["accept"] = value_text

    return detail


def _best_search_hit(
    name: str,
    issn: str = "",
    source_errors: Optional[Dict] = None,
) -> Optional[Dict]:
    try:
        if issn:
            result = advanced_search(searchissn=issn, searchsort="relevance")
        else:
            result = advanced_search(searchname=name, searchsort="relevance")
    except Exception as exc:
        if source_errors is not None:
            source_errors["advanced_search"] = str(exc)
        return None

    journals = result.get("journals", [])
    if not journals:
        return None

    normalized_issn = _normalize_issn(issn)
    if normalized_issn:
        return next(
            (
                journal
                for journal in journals
                if _normalize_issn(journal.get("issn", "")) == normalized_issn
                and _names_compatible(name, journal.get("name", ""))
            ),
            None,
        )

    for journal in journals:
        if _names_compatible(name, journal.get("name", "")):
            return journal
    return None


def _parse_partition(cell) -> Dict:
    text = _clean(cell.get_text(" ", strip=True))
    return {
        "大类学科": _match_text(r"([^\s\d]+)\s*\d区", text),
        "小类学科": _match_text(r"小类学科[:：]?\s*([^\s]+)", text),
        "分区": _match_text(r"([1-4]区)", text),
        "Top期刊": "Top" in text and "否" not in text,
        "综述期刊": "综述" in text and "否" not in text,
    }


def _parse_partition_block(cells) -> Dict:
    table = next((cell.find("table") for cell in cells if cell.find("table")), None)
    if table:
        row = next(
            (
                tr
                for tr in table.find_all("tr", recursive=False)
                if tr.find_all("td", recursive=False)
            ),
            None,
        )
        if row:
            row_cells = row.find_all("td", recursive=False)
            major_text = _visible_text(row_cells[0]) if len(row_cells) > 0 else ""
            minor_text = _visible_text(row_cells[1]) if len(row_cells) > 1 else ""
            top_text = _visible_text(row_cells[2]) if len(row_cells) > 2 else ""
            review_text = _visible_text(row_cells[3]) if len(row_cells) > 3 else ""
            partition = _match_text(r"([1-4]区)", major_text)
            return {
                "大类学科": _match_text(r"^(.+?)\s+[1-4]区", major_text),
                "小类学科": minor_text,
                "分区": partition,
                "Top期刊": top_text == "是",
                "综述期刊": review_text == "是",
            }

    values = [_visible_text(cell) for cell in cells]
    major_text = next((value for value in values if re.search(r"[1-4]区\s+[1-4]区\s+[1-4]区", value)), "")
    top_text = _first_flag_after_partition(values, default="")
    review_text = _first_flag_after_partition(values, default="", start_after=top_text)

    tiers = re.findall(r"[1-4]区", major_text)
    return {
        "大类学科": _match_text(r"^(.+?)\s+[1-4]区", major_text),
        "小类学科": _parse_minor_partition(values),
        "分区": tiers[0] if tiers else "",
        "Top期刊": top_text == "是",
        "综述期刊": review_text == "是",
    }


def _parse_minor_partition(values: List[str]) -> str:
    minor_values = [
        value
        for value in values
        if re.search(r"[A-Z][A-Z,\s-]+", value) and re.search(r"[1-4]区", value)
    ]
    return "; ".join(minor_values[:3])


def _first_flag_after_partition(values: List[str], default: str = "", start_after: str = "") -> str:
    seen_partition = False
    skip_first_flag = bool(start_after)
    for value in values:
        if re.search(r"[1-4]区\s+[1-4]区\s+[1-4]区", value):
            seen_partition = True
            continue
        if seen_partition and value in {"是", "否", "N/A"}:
            if skip_first_flag and value == start_after:
                skip_first_flag = False
                continue
            return value
    return default


def _extract_shortname(cell) -> str:
    grey = cell.select_one('font[color="grey"]')
    return _clean(grey.get_text(" ", strip=True)) if grey else ""


def _extract_query_value(href: str, key: str) -> str:
    match = re.search(rf"[?&]{re.escape(key)}=([^&]+)", href or "")
    return match.group(1) if match else ""


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _visible_text(node) -> str:
    parts: List[str] = []

    def walk(current) -> None:
        style = str(getattr(current, "attrs", {}).get("style", "")).replace(" ", "").lower()
        if "display:none" in style or "visibility:hidden" in style:
            return
        if isinstance(current, str):
            parts.append(current)
            return
        for child in getattr(current, "children", []):
            walk(child)

    walk(node)
    return _clean(" ".join(parts))


def _match_text(pattern: str, value: str) -> str:
    match = re.search(pattern, value or "", flags=re.I)
    return match.group(1).strip() if match else ""


def _first_number(value: str) -> str:
    return _match_text(r"([\d]+(?:\.\d+)?)", value)


def _last_number(value: str) -> str:
    matches = re.findall(r"[\d]+(?:\.\d+)?", value or "")
    return matches[-1] if matches else ""


def _normalize_issn(value: str) -> str:
    return re.sub(r"[^0-9Xx]", "", str(value or "")).upper()


def _names_compatible(left: str, right: str) -> bool:
    def normalize(value: str) -> str:
        text = str(value or "").lower().replace("&", " and ")
        text = re.sub(r"^the\b[\s:,-]*", "", text.strip())
        return re.sub(r"[^a-z0-9]+", "", text)

    left_name = normalize(left)
    right_name = normalize(right)
    if not left_name or not right_name:
        return False
    if left_name == right_name:
        return True
    shorter, longer = sorted((left_name, right_name), key=len)
    return len(shorter) >= 8 and longer.startswith(shorter) and len(shorter) / len(longer) >= 0.7


def _first_int(match) -> int:
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def _to_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
