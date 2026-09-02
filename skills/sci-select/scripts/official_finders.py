"""
Manual official journal-finder helpers.

This module intentionally does not automate publisher websites. It prepares
links and copy-ready text so a user can run optional checks in their browser.
"""
from __future__ import annotations

from typing import Dict, Iterable, List


FINDER_LINKS = [
    {
        "name": "Elsevier Journal Finder",
        "url": "https://journalfinder.elsevier.com/",
        "note": "基础匹配通常无需机构账号；登录多用于保存列表。",
    },
    {
        "name": "Springer Nature Journal Finder",
        "url": "https://link.springer.com/journals",
        "note": "期刊匹配可直接使用；机构字段主要用于开放获取资助核验。",
    },
    {
        "name": "Wiley Journal Finder",
        "url": "https://www.wiley.com/en-us/journal-finder/",
        "note": "可手动提交题名和摘要；遇到验证页面时以人工访问为准。",
    },
    {
        "name": "Taylor & Francis Journal Suggester",
        "url": "https://authorservices.taylorandfrancis.com/publishing-your-research/choosing-a-journal/journal-suggester/",
        "note": "可手动粘贴摘要或关键词获取出版社候选。",
    },
]


def build_finder_checklist(
    title: str = "",
    abstract: str = "",
    keywords: Iterable[str] | str = "",
) -> Dict:
    """Build an opt-in manual checklist for official publisher finders."""
    keyword_text = _format_keywords(keywords)
    query_parts = []
    if title:
        query_parts.append(f"Title: {title.strip()}")
    if abstract:
        query_parts.append(f"Abstract: {abstract.strip()}")
    if keyword_text:
        query_parts.append(f"Keywords: {keyword_text}")

    return {
        "mode": "manual_optional",
        "links": [dict(link) for link in FINDER_LINKS],
        "query_text": "\n".join(query_parts).strip(),
        "keywords": keyword_text,
        "notes": [
            "可选：这些官方 Journal Finder 仅作为出版社侧人工核验。",
            "手动打开链接并粘贴题名、摘要或关键词；不要把结果当作录用概率。",
            "本工具只提供人工核验入口，不处理账号状态或验证码。",
        ],
    }


def format_finder_checklist(checklist: Dict) -> str:
    """Format a manual official-finder checklist as Markdown."""
    lines: List[str] = [
        "## 官方 Journal Finder 人工核验（可选）",
        "",
    ]
    lines.extend(f"- {note}" for note in checklist.get("notes", []))
    lines.append("")
    lines.append("### 手动打开")
    for link in checklist.get("links", []):
        lines.append(f"- [{link['name']}]({link['url']})：{link['note']}")

    query_text = checklist.get("query_text", "")
    if query_text:
        lines.extend(["", "### 复制文本", "", "```text", query_text, "```"])

    return "\n".join(lines).strip()


def _format_keywords(keywords: Iterable[str] | str) -> str:
    if isinstance(keywords, str):
        return keywords.strip()
    return "; ".join(str(keyword).strip() for keyword in keywords if str(keyword).strip())
