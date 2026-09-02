#!/usr/bin/env python
"""Summarize a CUGB thesis format detection HTML report."""

from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path

from lxml import html


CATEGORY_PATTERNS = [
    ("cover-line-spacing", "行距值"),
    ("indent", "缩进"),
    ("keywords", "关键词"),
    ("toc-page", "目录项页码"),
    ("font", "字体"),
    ("font-size", "字号错误"),
    ("ascii-punctuation", "中文段落中出现了英文半角"),
    ("paragraph-continuity", "请保持段落连续"),
    ("mixed-parentheses", "小括号"),
    ("caption-page-break", "图题通常不应是一页首行"),
    ("caption-ending-punctuation", "本段末尾不应该出现标点"),
    ("heading-space", "编号与标题中间"),
    ("reference-comma-space", "逗号后面应该有空格"),
    ("reference-dot-space", "半角小圆点后面应该有空格"),
    ("reference-place", "缺少出版地"),
    ("reference-pages", "析出文献应有页码"),
    ("reference-volume", "年卷期项"),
    ("table-numbering", "表格编号不连续"),
    ("header", "页眉内容错误"),
    ("author", "责任者"),
    ("space-check", "空格是否必要"),
]


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "utf-16", "latin1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def categorize(description: str) -> list[str]:
    matches = [name for name, pattern in CATEGORY_PATTERNS if pattern in description]
    return matches or ["other"]


def parse_report(path: Path) -> dict:
    root = html.fromstring(decode_bytes(path.read_bytes()))
    rows = []
    for tr in root.xpath("//tr"):
        cells = [clean(" ".join(cell.itertext())) for cell in tr.xpath("./th|./td")]
        if len(cells) == 4 and cells[0].isdigit():
            rows.append(
                {
                    "number": int(cells[0]),
                    "level": cells[1],
                    "location": cells[2],
                    "description": cells[3],
                    "categories": categorize(cells[3]),
                }
            )

    levels = collections.Counter(row["level"] for row in rows)
    categories = collections.Counter(category for row in rows for category in row["categories"])
    examples = {}
    for row in rows:
        for category in row["categories"]:
            examples.setdefault(category, row["description"])

    return {
        "file": str(path),
        "total_rows": len(rows),
        "levels": dict(levels),
        "categories": dict(categories),
        "examples": examples,
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html_report", type=Path)
    parser.add_argument("--rows", action="store_true", help="Include every parsed issue row")
    args = parser.parse_args()

    summary = parse_report(args.html_report)
    if not args.rows:
        summary.pop("rows", None)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
