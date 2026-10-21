"""Offline GIS runtime and template checks; no root build or npm dependencies."""
import json
import re
import shutil
import subprocess
import unittest
from html import escape
from html.parser import HTMLParser
from pathlib import Path

from _build.gis import directory_html
from _build.labels import resolve_body_placeholders

ROOT = Path(__file__).resolve().parents[1]


class GISRuntimeTests(unittest.TestCase):
    def test_node_runtime(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required for GIS runtime regression checks")
        result = subprocess.run([node, "--test", str(ROOT / "tests/gis-runtime.cjs")],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_localized_template_and_static_directories(self):
        template = (ROOT / "src/pages/gis.html").read_text(encoding="utf-8")
        keys = set(re.findall(r"\{\{GIS_([A-Z_]+)\}\}", template))
        expected = None
        for lang in ("en", "fil", "pag"):
            locale = json.loads((ROOT / f"locales/{lang}.json").read_text(encoding="utf-8"))
            self.assertEqual(keys, {key.upper() for key, value in locale["gis"].items() if isinstance(value, str)})
            if expected is not None:
                self.assertEqual(set(locale["gis"]), expected)
            expected = set(locale["gis"])
            resolved = resolve_body_placeholders(template, locale, "..")
            self.assertNotRegex(resolved, r"\{\{GIS_")
            self.assertIn(f'aria-label="{locale["gis"]["map_name"]}"', resolved)
            self.assertIn('id="gis-map-fallback" class=', resolved)
            self.assertNotIn('style="', resolved)
            self.assertIn("{GIS_FACILITY_DIRECTORY}", resolved)
            self.assertIn("{GIS_BARANGAY_DIRECTORY}", resolved)
            # These fragments are inserted at build time, independently of JavaScript.
            page = resolved.replace("{GIS_FACILITY_DIRECTORY}", directory_html({"features": []}, "facilities", locale))
            page = page.replace("{GIS_BARANGAY_DIRECTORY}", directory_html({"features": [
                {"properties": {"name": "<Barangay>", "gid": "0105528001", "pop2024": 1656}}
            ]}, "barangays", locale))
            page = page.split("<script>", 1)[0]
            self.assertIn('<ul class="gis-directory"></ul>', page)
            self.assertIn("&lt;Barangay&gt;", page)
            self.assertIn(locale["gis"]["empty"], page)

    def test_gis_locale_text_is_safe_in_attributes_and_prose(self):
        unsafe = '" onfocus="alert(1)" data-x="<&\'>'
        locale = {"gis": {key: unsafe for key in ("map_name", "library_error", "intro")}}
        template = ('<div aria-label="{{GIS_MAP_NAME}}" data-error="{{GIS_LIBRARY_ERROR}}">'
                    '<p>{{GIS_INTRO}}</p></div>')
        rendered = resolve_body_placeholders(template, locale, "..")
        self.assertEqual(rendered.count(escape(unsafe)), 3)

        class Tags(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []

            def handle_starttag(self, tag, attrs):
                self.tags.append((tag, dict(attrs)))

        parser = Tags()
        parser.feed(rendered)
        self.assertEqual(parser.tags, [
            ("div", {"aria-label": unsafe, "data-error": unsafe}), ("p", {})])

    def test_directory_precision_is_localized_without_mutating_payload(self):
        methods = [("source_reported", "exact_from_source", "source_reported"),
                   ("source_reported", "approximate", "approximate_source"),
                   ("plus_code_cell_center", "approximate", "cell_center"),
                   ("polygon_centroid", "approximate", "centroid"),
                   ("field_observation", "exact_from_source", "field_position")]
        for lang in ("en", "fil", "pag"):
            locale = json.loads((ROOT / f"locales/{lang}.json").read_text(encoding="utf-8"))
            for method, precision, key in methods:
                data = {"features": [{"properties": {
                    "name": "<Facility>", "coordinate_method": method,
                    "location_precision": precision, "coordinate_description": "English fallback"}}]}
                before = json.dumps(data)
                rendered = directory_html(data, "facilities", locale)
                self.assertIn(escape(locale["gis"][key]), rendered)
                self.assertIn("&lt;Facility&gt;", rendered)
                self.assertEqual(json.dumps(data), before)
                self.assertIn("English fallback", directory_html(data, "facilities"))
                self.assertIn("English fallback", directory_html(data, "facilities", {}))

    def test_directory_labels_and_translations_are_escaped(self):
        data = {"features": [{"properties": {
            "name": "Barangay", "gid": "0105528001", "pop2024": 1656}}]}
        for lang in ("en", "fil", "pag"):
            locale = json.loads((ROOT / f"locales/{lang}.json").read_text(encoding="utf-8"))
            rendered = directory_html(data, "barangays", locale)
            self.assertIn(escape(locale["about"]["population"]), rendered)
            self.assertIn("PSGC: 0105528001", rendered)
            self.assertIn("1656 (2024 POPCEN)", rendered)
        self.assertIn("0105528001", directory_html(data, "barangays"))
        self.assertIn("1656 (2024 POPCEN)", directory_html(data, "barangays"))
        unsafe = '<img src=x onerror="alert(1)"> & \'quoted\''
        rendered = directory_html(data, "barangays", {"about": {"population": unsafe}})
        self.assertIn(escape(unsafe), rendered)
        self.assertNotIn("<img", rendered)
        facility = {"features": [{"properties": {"name": "Example",
                    "coordinate_method": "polygon_centroid", "coordinate_description": "Fallback"}}]}
        rendered = directory_html(facility, "facilities", {"gis": {"centroid": unsafe}})
        self.assertIn(escape(unsafe), rendered)
        self.assertNotIn("<img", rendered)

    def test_mobile_height_is_not_overridden_by_inline_style(self):
        css = (ROOT / "assets/css/map.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"#gis-map\s*\{[^}]*min-height: 280px")
        self.assertIn("--gis-map-height: clamp(280px, 46dvh, 420px)", css)
        self.assertIn("height: var(--gis-column-height)", css)

    def test_explorer_tokens_and_accessible_panels(self):
        template = (ROOT / "src/pages/gis.html").read_text(encoding="utf-8")
        self.assertEqual(template.count("<h1>"), 1)
        self.assertIn("<h1>{{GIS_TITLE}}</h1>", template)
        self.assertIn('role="tablist"', template)
        for panel in ("explore", "layers"):
            self.assertIn(f'aria-controls="gis-{panel}-panel"', template)
            self.assertIn(f'role="tabpanel" aria-labelledby="gis-{panel}-tab"', template)
        css = (ROOT / "assets/css/map.css").read_text(encoding="utf-8")
        self.assertNotRegex(css, r"var\(--(?:surface|text(?:-secondary)?|amber(?:-pale|-line|-text)?|blue)\)")
        self.assertIn("--gis-sticky-clearance", css)
        self.assertIn("overscroll-behavior: contain", css)
        tokens = (ROOT / "assets/css/tokens.css").read_text(encoding="utf-8")
        defined = set(re.findall(r"(--[\w-]+)\s*:", tokens + css))
        self.assertLessEqual(set(re.findall(r"var\((--[\w-]+)", css)), defined | {"--gis-sticky-clearance"})

    def test_gis_metadata_describes_current_explorer(self):
        meta = json.loads((ROOT / "src/data/page-meta.json").read_text(encoding="utf-8"))["gis.html"]
        for lang in ("fil", "pag"):
            self.assertNotRegex(meta[lang]["description"], r"aprubado|naaproban|Hindi magagamit|Ag magagamit")

    def test_v3_controls_and_cautions_are_localized(self):
        template = (ROOT / "src/pages/gis.html").read_text(encoding="utf-8")
        keys = ("opacity", "reference_only", "list_records", "locate", "coarse_geometry",
                "contract_amount", "approved_budget", "accomplishment", "fiscal_year",
                "contractor", "project_status", "status_key", "transaction_id", "project_id",
                "contract_id", "actual_start_date", "actual_completion_date", "contract_effectivity_date",
                "contract_expiry_date", "status_completed", "status_ongoing", "status_not_started", "status_unknown")
        for lang in ("en", "fil", "pag"):
            locale = json.loads((ROOT / f"locales/{lang}.json").read_text(encoding="utf-8"))
            rendered = resolve_body_placeholders(template, locale, "..")
            for key in keys:
                self.assertTrue(locale["gis"][key].strip(), (lang, key))
                self.assertIn(f'data-{key.replace("_", "-")}="{escape(locale["gis"][key])}"', rendered)
        runtime = (ROOT / "assets/gis-map.js").read_text(encoding="utf-8")
        self.assertIn('interactive: false', runtime)
        self.assertIn('rasterPane.style.pointerEvents = "none"', runtime)
        self.assertIn('slider.setAttribute("aria-label"', runtime)
        self.assertIn('slider.setAttribute("aria-valuetext"', runtime)

    def test_typed_payload_tokens_remain_distinct_from_locale_labels(self):
        template = (ROOT / "src/pages/gis.html").read_text(encoding="utf-8")
        for name in ("LAYERS", "FACILITIES", "BARANGAYS", "RECORDS"):
            self.assertIn(f"window.GIS_{name} = {{GIS_{name}_DATA}};", template)
        self.assertNotIn("{GIS_RECORD_DIRECTORY}", template)
        for removed in ("GIS_MODE", "GIS_PREVIEW_BANNER", "GIS_RESEARCH_DIRECTORY", "gis-status-filter"):
            self.assertNotIn(removed, template)
        self.assertIn('id="gis-workspace" class="gis-workspace" hidden', template)
        self.assertIn('id="gis-results"', template)
        self.assertIn('type="search"', template)


if __name__ == "__main__":
    unittest.main()
