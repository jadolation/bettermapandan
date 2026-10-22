import json
from pathlib import Path

import pytest

from _build.gis_sync import LOCALES, MANIFEST, PAGES, synchronize_gis


def put(base, name, content):
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode())
    return path


@pytest.fixture
def preview(tmp_path):
    root = tmp_path / "checkout"
    site = root / "_site"
    for locale in LOCALES:
        prefix = Path(locale)
        put(site, prefix / "gis/index.html", '<link rel="stylesheet" href="../assets/style.min.css">'
            '<script src="../assets/gis-map.min.js"></script><img src="../assets/logo.svg">'
            '<a href="/transparency/projects/">Do not copy other pages</a>')
        put(site, prefix / "assets/style.min.css", 'body{background:url("images/map.png")}')
        put(site, prefix / "assets/images/map.png", b"image")
        put(site, prefix / "assets/gis-map.min.js", b"new script")
        put(site, prefix / "assets/logo.svg", b"logo")
        put(site, prefix / MANIFEST, json.dumps({"schema_version": 1, "files": ["assets/gis/roads.geojson"]}))
        put(site, prefix / "assets/gis/roads.geojson", b'{"features":[]}')
        put(root, prefix / "gis/index.html", b"old page")
        put(root, prefix / "assets/gis/old.png", b"old generated")
        put(root, prefix / MANIFEST, json.dumps({"schema_version": 1, "files": ["assets/gis/old.png"]}))
    for name in ("fil/unrelated/index.html", "pag/assets/script.js", "src/pages/gis.html",
                 "assets/style.css", "assets/gis-map.js", "assets/gis/user.png", "datasets/GIS/data.geojson"):
        put(root, name, b"user sentinel\r\n")
    return root, site


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*")
            if p.is_file() and "_site" not in p.relative_to(root).parts}


def test_sync_three_routes_dependencies_and_only_managed_cleanup(preview):
    root, site = preview
    old = snapshot(root)
    copied = synchronize_gis(root)
    assert PAGES <= set(copied)
    for rel in copied:
        assert (root / rel).read_bytes() == (site / rel).read_bytes()
    for locale in LOCALES:
        assert not (root / locale / "assets/gis/old.png").exists()
        assert (root / locale / "assets/images/map.png").read_bytes() == b"image"
    for rel, payload in old.items():
        if rel not in PAGES and rel.name not in {"manifest.json", "old.png"}:
            assert (root / rel).read_bytes() == payload
    assert not (root / "transparency/projects/index.html").exists()


def test_statistics_json_is_an_exact_managed_resource(preview):
    root, site = preview
    for locale in LOCALES:
        prefix = Path(locale)
        manifest = site / prefix / MANIFEST
        data = json.loads(manifest.read_text())
        data['files'].append('assets/gis/barangay-statistics.json')
        manifest.write_text(json.dumps(data))
        put(site, prefix / 'assets/gis/barangay-statistics.json', '{"schema_version":1}')
    synchronize_gis(root)
    for locale in LOCALES:
        assert (root / locale / 'assets/gis/barangay-statistics.json').read_text() == '{"schema_version":1}'


@pytest.mark.parametrize("bad", ["pag/gis/index.html", "fil/assets/gis-map.min.js", "assets/gis/roads.geojson",
                                 "pag/assets/images/map.png", "assets/gis/manifest.json"])
def test_missing_input_leaves_old_preview_intact(preview, bad):
    root, site = preview
    before = snapshot(root)
    (site / bad).unlink()
    with pytest.raises(ValueError, match="Missing"):
        synchronize_gis(root)
    assert snapshot(root) == before


@pytest.mark.parametrize("location", ["source", "destination"])
@pytest.mark.parametrize("name", ["pag/gis/index.html", "assets/gis/roads.geojson", "assets/style.min.css"])
def test_linked_input_or_destination_refused(preview, tmp_path, location, name):
    root, site = preview
    base = site if location == "source" else root
    target = put(tmp_path, "external", b"untouched")
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    path.symlink_to(target)
    before = snapshot(root)
    with pytest.raises(ValueError, match="Symlink"):
        synchronize_gis(root)
    assert snapshot(root) == before
    assert target.read_bytes() == b"untouched"


def test_linked_destination_parent_refused(preview, tmp_path):
    root, _ = preview
    external = tmp_path / "external"
    external.mkdir()
    (root / "assets/images").symlink_to(external, target_is_directory=True)
    before = snapshot(root)
    with pytest.raises(ValueError, match="Symlink"):
        synchronize_gis(root)
    assert snapshot(root) == before
    assert list(external.iterdir()) == []


@pytest.mark.parametrize("url", ["../../../outside.png", "/src/data/private.png", "/assets/../../outside.png",
                                "/assets/%2e%2e/src/private.png", "/assets/a%5cb.png"])
def test_unsafe_dependency_refused(preview, url):
    root, site = preview
    put(site, "gis/index.html", f'<img src="{url}">')
    before = snapshot(root)
    with pytest.raises(ValueError):
        synchronize_gis(root)
    assert snapshot(root) == before


def test_unsafe_manifest_cannot_delete_user_file(preview):
    root, _ = preview
    put(root, MANIFEST, json.dumps({"schema_version": 1, "files": ["assets/gis/../../src/pages/gis.html"]}))
    before = snapshot(root)
    with pytest.raises(ValueError, match="Unsafe"):
        synchronize_gis(root)
    assert snapshot(root) == before


@pytest.mark.parametrize("asset", ["assets/logo.svg", "assets/gis-map.js", "assets/style.css"])
def test_changed_raw_assets_never_overwritten(preview, asset):
    root, site = preview
    put(site, asset, b"different")
    put(root, asset, b"user source")
    put(site, "gis/index.html", f'<script src="/{asset}"></script>')
    before = snapshot(root)
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        synchronize_gis(root)
    assert snapshot(root) == before


def test_unchanged_raw_source_is_not_copied(preview):
    root, site = preview
    put(site, "assets/gis-map.js", b"user sentinel\r\n")
    put(site, "gis/index.html", '<script src="/assets/gis-map.js"></script>')
    assert Path("assets/gis-map.js") not in synchronize_gis(root)


@pytest.mark.parametrize("directory", [".", "src", "fil"])
def test_source_directory_not_a_stage(preview, directory):
    root, _ = preview
    before = snapshot(root)
    with pytest.raises(ValueError, match="separate staged"):
        synchronize_gis(root, root / directory)
    assert snapshot(root) == before


def test_sync_flag_rejected_before_build_or_maintenance(monkeypatch):
    from _build import orchestrator
    monkeypatch.setattr("sys.argv", ["build.py", "--offline", "--compress", "--sync-gis"])
    monkeypatch.setattr(orchestrator, "compress_images", lambda: pytest.fail("mutation"))
    monkeypatch.setattr(orchestrator, "build", lambda: pytest.fail("mutation"))
    with pytest.raises(ValueError, match="requires --isolated"):
        orchestrator.main()


@pytest.mark.parametrize("sync", [False, True])
def test_isolated_offline_sync_is_opt_in(monkeypatch, tmp_path, sync):
    from _build import gis_sync, orchestrator, preview
    calls = []
    stage = tmp_path / "_site"
    monkeypatch.setattr(orchestrator, "ROOT", tmp_path)
    monkeypatch.setattr("sys.argv", ["build.py", "--isolated", "--offline"] + (["--sync-gis"] if sync else []))
    monkeypatch.setattr(preview, "isolated_build", lambda root, offline: calls.append(("build", root, offline)) or stage)
    monkeypatch.setattr(gis_sync, "synchronize_gis", lambda root, site: calls.append(("sync", root, site)))
    orchestrator.main()
    assert calls == [("build", tmp_path, True)] + ([("sync", tmp_path, stage)] if sync else [])
