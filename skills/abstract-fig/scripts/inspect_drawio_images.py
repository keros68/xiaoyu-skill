#!/usr/bin/env python3
"""Inspect draw.io image embedding; flag large images for visual review.

Vector-only figures are valid. These structural diagnostics cannot certify
rendering, scientific accuracy, or full editability.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path


def _float_attr(node: ET.Element | None, name: str) -> float | None:
    if node is None:
        return None
    try:
        return float(node.attrib[name])
    except (KeyError, ValueError):
        return None


def _models(root: ET.Element) -> list[tuple[str, ET.Element]]:
    if root.tag == "mxGraphModel":
        pages = [("1", root)]
    elif root.tag == "mxfile":
        pages = []
        for index, diagram in enumerate(root.findall("diagram"), 1):
            model = diagram.find("mxGraphModel")
            if model is None:
                payload = (diagram.text or "").strip()
                if not payload:
                    raise ValueError(f"Page {index} has no graph model")
                if payload.startswith("<"):
                    model = ET.fromstring(payload)
                else:
                    raw = base64.b64decode("".join(payload.split()), validate=True)
                    encoded = zlib.decompress(raw, -15).decode("utf-8")
                    model = ET.fromstring(urllib.parse.unquote(encoded))
            pages.append((diagram.get("name") or str(index), model))
    else:
        raise ValueError("Expected mxfile or mxGraphModel")
    if not pages or any(m.tag != "mxGraphModel" or m.find("root") is None for _, m in pages):
        raise ValueError("No valid graph model found")
    return pages


def inspect_drawio(drawio_path: Path, elements_dir: Path | None = None) -> dict:
    pages = _models(ET.fromstring(drawio_path.read_text(encoding="utf-8-sig")))
    image_cells = []
    text_count = 0
    warnings = []
    for page_index, (page_name, model) in enumerate(pages, 1):
        pw = _float_attr(model, "pageWidth") or 0
        ph = _float_attr(model, "pageHeight") or 0
        for cell in model.iter("mxCell"):
            if cell.get("vertex") == "1" and cell.get("value", "").strip():
                text_count += 1
            style = cell.get("style", "")
            match = re.search(r"(?:^|;)image=([^;]*)", style)
            if not match:
                continue
            geom = cell.find("mxGeometry")
            width = _float_attr(geom, "width")
            height = _float_attr(geom, "height")
            large = bool(pw > 0 and ph > 0 and (width or 0) >= pw * .55 and (height or 0) >= ph * .55)
            sheet = bool(re.search(r"element[_ -]?sheet|full[_ -]?figure", match.group(1), re.I))
            item = {
                "id": cell.get("id"), "page_index": page_index, "page_name": page_name,
                "x": _float_attr(geom, "x"), "y": _float_attr(geom, "y"),
                "width": width, "height": height,
                "embedded": match.group(1).strip().startswith("data:image/"),
                "mentions_sheet": sheet, "large": large,
            }
            image_cells.append(item)
            label = f"page {page_index}, cell {cell.get('id')}"
            if large:
                warnings.append(f"Review {label}: large image; distinguish a legitimate map/photo from a flattened diagram.")
            if sheet:
                warnings.append(f"Review {label}: image reference mentions an element sheet or full figure.")
            if pw <= 0 or ph <= 0 or width is None or height is None:
                warnings.append(f"Review {label}: missing page/image dimensions; size could not be assessed.")
    png_files = sorted(p.name for p in elements_dir.glob("*.png")) if elements_dir and elements_dir.is_dir() else []
    return {
        "drawio": str(drawio_path), "page_count": len(pages),
        "elements_dir": str(elements_dir) if elements_dir else None,
        "element_png_count": len(png_files), "element_png_files": png_files,
        "text_cell_count": text_count, "image_cell_count": len(image_cells),
        "embedded_image_cell_count": sum(c["embedded"] for c in image_cells),
        "nonembedded_image_cell_count": sum(not c["embedded"] for c in image_cells),
        "large_image_cell_ids": [c["id"] for c in image_cells if c["large"]],
        "sheet_like_image_cell_ids": [c["id"] for c in image_cells if c["mentions_sheet"]],
        "warnings": warnings, "image_cells": image_cells,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect embedded draw.io images; vector-only files are valid.",
        epilog="Exit codes: 0 = structural checks passed (review warnings); 1 = read error; "
               "2 = fewer than explicitly requested --min-images; 3 = external image reference; "
               "6 = invalid or unsupported draw.io XML/page data. Visual review is still required.",
    )
    parser.add_argument("drawio", type=Path)
    parser.add_argument("--elements-dir", type=Path, default=None)
    parser.add_argument("--min-images", type=int, default=0, help="Optional design-specific minimum; default 0.")
    args = parser.parse_args(argv)
    if args.min_images < 0:
        parser.error("--min-images must be non-negative")
    try:
        report = inspect_drawio(args.drawio, args.elements_dir)
    except OSError as exc:
        print(f"Error reading {args.drawio}: {exc}", file=sys.stderr)
        return 1
    except (ET.ParseError, ValueError, zlib.error) as exc:
        print(f"Invalid draw.io file {args.drawio}: {exc}", file=sys.stderr)
        return 6
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["image_cell_count"] < args.min_images:
        print(f"FAIL: expected at least {args.min_images} image cells.", file=sys.stderr)
        return 2
    if report["nonembedded_image_cell_count"]:
        print("FAIL: image references are not embedded; portable delivery requires embedded assets.", file=sys.stderr)
        return 3
    for warning in report["warnings"]:
        print(f"REVIEW: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
