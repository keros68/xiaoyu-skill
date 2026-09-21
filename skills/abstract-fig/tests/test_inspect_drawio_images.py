"""Behavior checks for portable vector, raster, and compressed draw.io files."""
import base64
import contextlib
import importlib.util
import io
import tempfile
import unittest
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inspect_drawio_images.py"
spec = importlib.util.spec_from_file_location("inspect_images", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
IMAGE = "data:image/svg+xml," + base64.b64encode(b'<svg xmlns="http://www.w3.org/2000/svg"/>').decode()


def model(image=None, page=100, size=30):
    m = ET.Element("mxGraphModel", pageWidth=str(page), pageHeight=str(page))
    r = ET.SubElement(m, "root")
    ET.SubElement(r, "mxCell", id="0")
    ET.SubElement(r, "mxCell", id="1", parent="0")
    ET.SubElement(r, "mxCell", id="label", parent="1", vertex="1", value="研究区域 α")
    if image:
        c = ET.SubElement(r, "mxCell", id="image", parent="1", vertex="1", style=f"shape=image;image={image};")
        ET.SubElement(c, "mxGeometry", x="0", y="0", width=str(size), height=str(size))
    return m


def document(*models, compressed=False):
    f = ET.Element("mxfile")
    for i, m in enumerate(models):
        d = ET.SubElement(f, "diagram", name=f"page {i}")
        if compressed:
            raw = urllib.parse.quote(ET.tostring(m, encoding="unicode"), safe="").encode()
            compressor = zlib.compressobj(wbits=-15)
            d.text = base64.b64encode(compressor.compress(raw) + compressor.flush()).decode()
        else:
            d.append(m)
    return ET.tostring(f, encoding="unicode")


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "figure.drawio"

    def run_file(self, content, *args):
        self.path.write_text(content, encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return module.main([str(self.path), *args])

    def test_vector_only_passes(self):
        self.assertEqual(self.run_file(document(model())), 0)
        report = module.inspect_drawio(self.path)
        self.assertEqual(report["image_cell_count"], 0)
        self.assertEqual(report["text_cell_count"], 1)

    def test_single_large_map_warns_but_passes(self):
        self.assertEqual(self.run_file(document(model(IMAGE, size=90))), 0)
        self.assertTrue(module.inspect_drawio(self.path)["warnings"])

    def test_design_specific_minimum_is_enforced(self):
        self.assertEqual(self.run_file(document(model(IMAGE)), "--min-images", "2"), 2)

    def test_external_asset_fails_portability(self):
        self.assertEqual(self.run_file(document(model("https://example.org/map.png"))), 3)

    def test_compressed_unicode_file(self):
        self.assertEqual(self.run_file(document(model(IMAGE), compressed=True)), 0)
        report = module.inspect_drawio(self.path)
        self.assertEqual(report["embedded_image_cell_count"], 1)
        self.assertEqual(report["text_cell_count"], 1)

    def test_sizes_are_assessed_per_page(self):
        self.assertEqual(self.run_file(document(model(IMAGE, 100, 60), model(IMAGE, 1000, 60))), 0)
        images = module.inspect_drawio(self.path)["image_cells"]
        self.assertEqual([c["large"] for c in images], [True, False])
        self.assertEqual([c["page_index"] for c in images], [1, 2])

    def test_direct_model(self):
        self.assertEqual(self.run_file(ET.tostring(model(), encoding="unicode")), 0)

    def test_invalid_input_is_not_misreported_as_vector(self):
        for text in ["<mxfile>", "<mxfile/>", "<other/>", '<mxfile><diagram>not-base64!</diagram></mxfile>', '<mxGraphModel/>']:
            with self.subTest(text=text):
                self.assertEqual(self.run_file(text), 6)

    def test_missing_file(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(module.main([str(self.path)]), 1)


if __name__ == "__main__":
    unittest.main()
