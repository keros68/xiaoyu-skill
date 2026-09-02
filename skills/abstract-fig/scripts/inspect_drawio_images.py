#!/usr/bin/env python3
"""Inspect embedded image elements in a draw.io file.

This is a lightweight QA helper for Abstract-Fig. It checks
whether a draw.io file contains separate embedded image cells rather than a
single pasted full figure or element sheet.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _float_attr(node: ET.Element | None, name: str) -> float | None:
    if node is None:
        return None
    value = node.attrib.get(name)
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def inspect_drawio(drawio_path: Path, elements_dir: Path | None = None) -> dict:
    text = drawio_path.read_text(encoding="utf-8")
    root = ET.fromstring(text)

    image_cells = []
    page_width = 0.0
    page_height = 0.0

    for diagram in root.iter("diagram"):
        model = diagram.find("mxGraphModel")
        if model is not None:
            try:
                page_width = max(page_width, float(model.attrib.get("pageWidth", "0")))
                page_height = max(page_height, float(model.attrib.get("pageHeight", "0")))
            except ValueError:
                pass

    for cell in root.iter("mxCell"):
        style = cell.attrib.get("style", "")
        if "image=" not in style:
            continue
        geom = cell.find("mxGeometry")
        width = _float_attr(geom, "width")
        height = _float_attr(geom, "height")
        x = _float_attr(geom, "x")
        y = _float_attr(geom, "y")
        image_cells.append(
            {
                "id": cell.attrib.get("id"),
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "embedded": "data:image" in style,
                "mentions_sheet": bool(re.search(r"element[_ -]?sheet|full[_ -]?figure", style, re.I)),
            }
        )

    png_files = []
    if elements_dir is not None and elements_dir.exists():
        png_files = sorted(p.name for p in elements_dir.glob("*.png"))

    large_threshold = 0.55
    large_cells = []
    for cell in image_cells:
        width = cell.get("width") or 0
        height = cell.get("height") or 0
        if page_width and page_height and width >= page_width * large_threshold and height >= page_height * large_threshold:
            large_cells.append(cell["id"])

    return {
        "drawio": str(drawio_path),
        "elements_dir": str(elements_dir) if elements_dir else None,
        "element_png_count": len(png_files),
        "element_png_files": png_files,
        "image_cell_count": len(image_cells),
        "embedded_image_cell_count": sum(1 for c in image_cells if c["embedded"]),
        "nonembedded_image_cell_count": sum(1 for c in image_cells if not c["embedded"]),
        "large_image_cell_ids": large_cells,
        "sheet_like_image_cell_ids": [c["id"] for c in image_cells if c["mentions_sheet"]],
        "image_cells": image_cells,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect draw.io embedded image cells.",
        epilog=(
            "Exit codes: 0 = OK; 1 = drawio file not found; "
            "2 = fewer than --min-images image cells; "
            "3 = non-embedded (non data:image) image cells found; "
            "4 = large image cells that may be a pasted full figure/sheet; "
            "5 = image cells that look like an element sheet/full figure; "
            "6 = drawio file is not valid XML."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("drawio", type=Path)
    parser.add_argument("--elements-dir", type=Path, default=None)
    parser.add_argument("--min-images", type=int, default=3)
    args = parser.parse_args()

    try:
        report = inspect_drawio(args.drawio, args.elements_dir)
    except FileNotFoundError:
        print(f"Error: drawio file not found: {args.drawio}", file=sys.stderr)
        return 1
    except ET.ParseError:
        print(
            f"Error: {args.drawio} is not valid XML - check the .drawio was saved correctly",
            file=sys.stderr,
        )
        return 6

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["image_cell_count"] < args.min_images:
        print(f"FAIL: expected at least {args.min_images} image cells.", file=sys.stderr)
        return 2
    if report["nonembedded_image_cell_count"]:
        print("FAIL: found image cells that are not embedded data images.", file=sys.stderr)
        return 3
    if report["large_image_cell_ids"]:
        print("FAIL: found large image cells that may be a pasted full figure/sheet.", file=sys.stderr)
        return 4
    if report["sheet_like_image_cell_ids"]:
        print("FAIL: found image cells that look like an element sheet/full figure.", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
