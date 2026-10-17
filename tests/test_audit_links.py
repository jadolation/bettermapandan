"""Audit-file archive regression tests — GitHub Pages has no directory listings.

The audit report archive is rendered from ``audit-reports.json`` (key
``audit_archive``) by ``_build/generators/audit.py``. Every archive ``path``
must point at a real file on disk (not a trailing-slash directory URL, which
404s on Pages even though local dev servers auto-list directories).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
AUDIT_JSON = ROOT / "src" / "data" / "audit-reports.json"


def _archive_entries():
    data = json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    return data.get("audit_archive", [])


def _all_paths():
    return [f["path"] for entry in _archive_entries() for f in entry.get("files", [])]


def test_archive_present_and_nonempty():
    entries = _archive_entries()
    assert entries, "audit_archive must exist in audit-reports.json"
    years = {e["year"] for e in entries}
    assert 2025 in years, "CY 2025 must appear in the audit archive"


def test_no_directory_style_dataset_paths():
    """No /datasets/ path may end with '/' (directory URL 404s on Pages)."""
    directory_paths = [p for p in _all_paths() if p.endswith("/")]
    assert not directory_paths, f"directory-style paths 404 on Pages: {directory_paths}"


def test_archive_paths_point_at_files():
    """Every archive path must have a file extension and exist on disk."""
    paths = _all_paths()
    assert paths, "expected archive file paths"
    for path in paths:
        assert "." in Path(path).name, f"{path} has no file extension"
        assert (ROOT / path.lstrip("/")).is_file(), f"{path} target missing on disk"


def test_2025_archive_links_annual_set():
    """2025 must link the annual report set, not just the compliance audit."""
    entry = next(e for e in _archive_entries() if e["year"] == 2025)
    paths = [f["path"] for f in entry["files"]]
    assert len(paths) >= 5, f"CY 2025 under-linked: {paths}"
    assert any("Audit_Report" in p for p in paths), "missing 2025 audit report"
    assert any("Mapandan2025_car.docx" in p for p in paths), "missing 2025 LDRRMF compliance audit"
