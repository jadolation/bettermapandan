"""Isolated deployment-boundary tests: no full build, network or root outputs."""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _build.staging import (
    ROOT_FILES,
    _asset_outputs,
    _download_outputs,
    page_outputs,
    stage_site,
)

REPO = Path(__file__).resolve().parent.parent


def put(root, rel, content="public"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def site(tmp_path):
    for rel in ("src/pages/index.html", "src/pages/gis.html",
                "src/pages/support/faq.html", "src/pages/transparency/projects.html"):
        put(tmp_path, rel, "source only")
    put(tmp_path, "src/data/services.json", json.dumps({"services": [{"slug": "birth-certificate"}]}))
    downloads = ["/datasets/audit-reports/Mapandan2025_car.docx",
                 "/datasets/Mapandan-Annual-Audit-Report-2024/AAR/02-MapandanPang2024_FS.xlsx",
                 "/datasets/Mapandan-Executive-Summary-2025.pdf"]
    put(tmp_path, "src/data/audit-reports.json", json.dumps({
        "audit_archive": [{"files": [{"path": path} for path in downloads]}],
    }))
    for path in downloads:
        put(tmp_path, path[1:])
    for rel in page_outputs(tmp_path):
        put(tmp_path, rel, f"built {rel}")
    for rel in ROOT_FILES:
        put(tmp_path, rel)
    for rel in ("assets/style.min.css", "assets/css/map.css", "assets/gis-map.min.js",
                "assets/js/project-explorer.min.js", "assets/search-index.json",
                "assets/data/project-index.json", "assets/projects/bucas.jpg",
                "assets/citizens-charter/birth-certificate.jpg", "assets/logo.svg"):
        put(tmp_path, rel)
    return tmp_path


def test_stages_multilingual_routes_assets_and_exact_downloads(site):
    artifact = stage_site(site)
    expected = page_outputs(site) | _asset_outputs(site) | _download_outputs(site)
    expected.update(Path(name) for name in ROOT_FILES)
    for locale in ("fil", "pag"):
        expected.update(Path(locale) / rel for rel in _asset_outputs(site))
    actual = {path.relative_to(artifact) for path in artifact.rglob("*") if path.is_file()}
    assert actual == expected
    for locale in ("", "fil", "pag"):
        assert (artifact / locale / "services/birth-certificate/index.html").is_file()
        assert (artifact / locale / "transparency/projects/index.html").is_file()
        assert (artifact / locale / "support/faq/index.html").is_file()
        assert (artifact / locale / "assets/gis-map.min.js").read_text() == "public"
    assert (artifact / "datasets/audit-reports/Mapandan2025_car.docx").is_file()


@pytest.mark.parametrize("rel", [
    "src/data/gis/facilities.geojson", "src/data/gis/review/facilities-review.json",
    "datasets/GIS/evac.geojson", "datasets/review/queue.json", "datasets/candidates/match.json",
    "datasets/audit-reports/Mapandan2025_car_debug.xml", "datasets/audit-reports/unlinked.pdf",
    "datasets/Mapandan-Annual-Audit-Report-2024/AAR/extracted.txt",
    "tests/index.html", "_build/staging.py", "scripts/index.html", ".git/config",
    "index_new/index.html", "accidental/index.html", "about.html", "audit-reports.json",
    "assets/facilities.geojson", "assets/facilities.json", "assets/data/facilities.json",
    "assets/gis/hazards.kmz", "assets/review/photo.png", "assets/tests/test.js",
    "assets/data/queue.json", "assets/debug.html", "assets/debug.py", "assets/debug.js",
    "pag/assets/data/facilities.json", "fil/assets/debug.js",
])
def test_uncontracted_files_never_publish(site, rel):
    put(site, rel, "private")
    artifact = stage_site(site)
    assert not (artifact / rel).exists()
    assert all(path.read_text() != "private" for path in artifact.rglob("*") if path.is_file())


@pytest.mark.parametrize("rel,is_dir", [
    ("assets/linked.json", False), ("assets/linked", True),
    ("gis/index.html", False), ("fil/gis", True),
    ("src/pages/link.html", False), ("src/data/services.json", False),
    ("src", True),
    ("datasets/audit-reports/Mapandan2025_car.docx", False),
    ("datasets/audit-reports", True), ("_site", True),
])
def test_symlinks_fail_closed(site, rel, is_dir):
    target = site / "private-target"
    if is_dir:
        target.mkdir()
        put(target, "sentinel", "untouched")
    else:
        target.write_text("untouched")
    link = site / rel
    if link.is_dir():
        shutil.rmtree(link)
    elif link.exists():
        link.unlink()
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target, target_is_directory=is_dir)
    with pytest.raises(ValueError, match="[Ss]ymlink|linked|real directory"):
        stage_site(site)
    if is_dir:
        assert (target / "sentinel").read_text() == "untouched"
    else:
        assert target.read_text() == "untouched"


def test_restage_cleans_stale_files_without_touching_sources(site):
    artifact = stage_site(site)
    put(artifact, "src/data/gis/facilities.geojson", "stale private")
    put(artifact, "deleted-route/index.html", "stale")
    stage_site(site)
    assert not (artifact / "src").exists()
    assert not (artifact / "deleted-route").exists()
    assert (site / "src/pages/index.html").read_text() == "source only"


def test_missing_build_output_does_not_clean_existing_artifact(site):
    artifact = stage_site(site)
    put(artifact, "sentinel", "untouched")
    (site / "pag/services/birth-certificate/index.html").unlink()
    with pytest.raises(ValueError, match="Missing public build output"):
        stage_site(site)
    assert (artifact / "sentinel").read_text() == "untouched"


def test_cleanup_rejects_symlink_inside_existing_stage(site):
    artifact = stage_site(site)
    (artifact / "link").symlink_to(site / "src", target_is_directory=True)
    with pytest.raises(ValueError, match="Symlink"):
        stage_site(site)
    assert (site / "src/pages/index.html").is_file()


@pytest.mark.parametrize("slug", ["../escape", "/absolute", "x/y", "x.html", "..", ""])
def test_service_slug_cannot_inject_output_path(site, slug):
    put(site, "src/data/services.json", json.dumps({"services": [{"slug": slug}]}))
    with pytest.raises(ValueError, match="Unsafe service slug"):
        stage_site(site)


@pytest.mark.parametrize("url", [
    "/src/data/gis/facilities.geojson", "/datasets/GIS/facilities.pdf",
    "/datasets/review/secret.pdf", "/datasets/audit-reports/../review/secret.pdf",
    "/datasets/audit-reports/facilities.geojson", "//host/secret.pdf",
    "/datasets/Mapandan-Annual-Audit-Report-2024/review/secret.pdf",
])
def test_download_manifest_cannot_widen_boundary(site, url):
    put(site, "src/data/audit-reports.json", json.dumps({
        "audit_archive": [{"files": [{"path": url}]}],
    }))
    with pytest.raises(ValueError, match="Unsafe audit download"):
        stage_site(site)


def test_real_current_build_contract_in_isolated_fixture(tmp_path):
    # Derive all current routes and linked downloads, but synthesize outputs.
    # This catches drift without running build.py or reading stale root HTML.
    shutil.copytree(REPO / "src/pages", tmp_path / "src/pages")
    for name in ("services.json", "audit-reports.json"):
        put(tmp_path, f"src/data/{name}", (REPO / "src/data" / name).read_text(encoding="utf-8"))
    routes = page_outputs(tmp_path)
    for rel in routes | _download_outputs(tmp_path):
        assert (REPO / rel).is_file(), f"Missing current output/download contract: {rel}"
        put(tmp_path, rel)
    for rel in ROOT_FILES:
        put(tmp_path, rel)
    (tmp_path / "assets").mkdir()
    artifact = stage_site(tmp_path)
    for locale in ("", "fil", "pag"):
        for route in ("index.html", "gis/index.html", "services/index.html",
                      "services/birth-certificate/index.html", "legislative/index.html",
                      "transparency/budget-fiscal/index.html", "support/privacy/index.html"):
            assert (artifact / locale / route).is_file()
    assert len(routes) >= 300
    assert len(_download_outputs(tmp_path)) == 43


def test_current_asset_tree_is_fully_covered():
    # New browser assets require an explicit review of the staging policy.
    assert _asset_outputs(REPO) == {
        path.relative_to(REPO) for path in (REPO / "assets").rglob("*") if path.is_file()
    }


def test_workflow_uploads_only_staging_directory():
    workflow = (REPO / ".github/workflows/pages.yml").read_text()
    assert "run: python -m _build.staging" in workflow
    assert "path: _site" in workflow
    assert "path: .\n" not in workflow
