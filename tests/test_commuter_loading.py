"""Progressive commuter publication contracts, without geometry service calls."""
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from _build.staging import _commuter_outputs
from _build.transport.compiler import compact_script_json, compile_resources, reference_bundle


def read_resource(root, reference):
    raw = (root / reference["url"].lstrip("/")).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == reference["sha256"]
    assert reference["url"].endswith("-" + reference["sha256"] + ".json")
    return json.loads(raw)


def test_hashed_resources_deterministic_preserve_every_public_record(tmp_path, monkeypatch):
    monkeypatch.setattr("socket.create_connection", lambda *a, **k: pytest.fail("Build network"))
    original = reference_bundle()
    bundle = deepcopy(original)
    manifest = compile_resources(tmp_path, bundle)
    assert bundle == original
    assert manifest == compile_resources(tmp_path, bundle)
    assert "direction_steps" not in manifest
    assert all("geometry" not in shape for shape in manifest["shapes"])
    for route in original["catalog"]:
        summary = next(item for item in manifest["catalog"] if item["id"] == route["id"])
        assert all(route[key] == value for key, value in summary.items())
        refs = manifest["resources"][route["directions"][0][0]]
        assert read_resource(tmp_path, refs["detail"])["data"]["routes"][route["id"]] == route
    assert manifest["features"] == original["features"]
    assert manifest["observations"] == original["observations"]
    for shape in original["shapes"]:
        pattern = shape["properties"]["pattern_id"]
        refs = manifest["resources"][pattern]
        geometry = read_resource(tmp_path, refs["geometry"])
        detail = read_resource(tmp_path, refs["detail"])
        assert geometry == {"schema_version": 1, "pattern_id": pattern, "kind": "geometry", "data": shape["geometry"]}
        assert detail["data"]["properties"] == shape["properties"]
    for pattern, source in original["direction_steps"].items():
        assert read_resource(tmp_path, manifest["resources"][pattern]["detail"])["data"]["directions"] == source
    shared = "shared-mapandan-border-arch"
    journeys = [route for route in manifest["catalog"] if shared in route["directions"][0]]
    assert len(journeys) >= 2
    url = manifest["resources"][shared]["geometry"]["url"]
    assert sum(path.name == Path(url).name for path in (tmp_path / "assets/commuter").iterdir()) == 1


@pytest.mark.parametrize("shapes", [[], "partial"])
def test_empty_partial_resources_no_fabricated_lines(tmp_path, shapes):
    original = reference_bundle()
    original["shapes"] = original["shapes"][:1] if shapes else []
    manifest = compile_resources(tmp_path, original)
    assert len(manifest["shapes"]) == len(original["shapes"])
    available = {shape["properties"]["pattern_id"] for shape in original["shapes"]}
    for pattern, refs in manifest["resources"].items():
        assert (read_resource(tmp_path, refs["geometry"])["data"] is not None) == (pattern in available)
    assert [route["fare_summary"] for route in manifest["catalog"]] == [route["fare_summary"] for route in original["catalog"]]


def test_script_safe_compact_resource_text():
    value = {"source": '</script>&<>\u2028\u2029"', "coordinate": 120.4512345678901}
    raw = compact_script_json(value)
    assert "</script>" not in raw and "&" not in raw and "\u2028" not in raw
    assert json.loads(raw) == value


def test_locale_render_reads_once_compiled_manifest(tmp_path, monkeypatch):
    from _build.locales import load_locale
    from _build.transport import compiler
    manifest = compiler.compile_resources(tmp_path, reference_bundle())
    monkeypatch.setattr("_build.config.ROOT", tmp_path)
    monkeypatch.setattr(compiler, "reference_bundle", lambda: pytest.fail("Recompiled during locale rendering"))
    for language in ("en", "fil", "pag"):
        output = compiler.commuter_placeholders(load_locale(language))
        bootstrap = json.loads(output["COMMUTER_DATA"])
        assert bootstrap["resources"] == manifest["resources"]
        assert bootstrap["catalog"] == manifest["catalog"]
        assert output["COMMUTER_DIRECTORY"].count("<article ") == 7


def test_stage_only_current_namespace_and_verify_hash(tmp_path):
    manifest = compile_resources(tmp_path, reference_bundle())
    directory = tmp_path / "assets/commuter"
    (directory / "fixture.json").write_text("private fixture")
    (directory / ("geometry-" + "a" * 64 + ".json")).write_text("obsolete")
    outputs = _commuter_outputs(tmp_path)
    assert Path("assets/commuter/fixture.json") not in outputs
    assert Path("assets/commuter/geometry-" + "a" * 64 + ".json") not in outputs
    ref = next(iter(manifest["resources"].values()))["geometry"]
    path = tmp_path / ref["url"].lstrip("/")
    path.write_text("corrupt")
    with pytest.raises(ValueError, match="checksum"):
        _commuter_outputs(tmp_path)


@pytest.mark.parametrize("where", ["assets", "assets/commuter", "assets/commuter/manifest.json", "assets/commuter/manifest.tmp"])
def test_compiler_rejects_linked_output(tmp_path, where):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / where
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="Linked"):
        compile_resources(tmp_path, reference_bundle())


def test_stage_rejects_unsafe_manifest_reference(tmp_path):
    manifest = compile_resources(tmp_path, reference_bundle())
    next(iter(manifest["resources"].values()))["geometry"]["url"] = "/assets/commuter/../../private.json"
    (tmp_path / "assets/commuter/manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Unsafe"):
        _commuter_outputs(tmp_path)


@pytest.mark.parametrize("action", ["compile", "stage"])
def test_linked_hashed_resource_rejected(tmp_path, action):
    bundle = reference_bundle()
    manifest = compile_resources(tmp_path, bundle)
    ref = next(iter(manifest["resources"].values()))["geometry"]
    resource = tmp_path / ref["url"].lstrip("/")
    target = tmp_path / "unrelated.json"
    target.write_bytes(resource.read_bytes())
    expected = target.read_bytes()
    resource.unlink()
    resource.symlink_to(target)
    with pytest.raises(ValueError, match="(?i)link"):
        if action == "compile":
            compile_resources(tmp_path, bundle)
        else:
            _commuter_outputs(tmp_path)
    assert target.read_bytes() == expected


def test_pinned_leaflet_provenance_license_and_checksums():
    directory = Path(__file__).resolve().parent.parent / "assets/vendor/leaflet-1.9.4"
    provenance = (directory / "PROVENANCE.md").read_text()
    records = re.findall(r"^([a-f0-9]{64})  (.+)$", provenance, re.MULTILINE)
    assert len(records) == 9
    assert "https://registry.npmjs.org/leaflet/-/leaflet-1.9.4.tgz" in provenance
    for digest, name in records:
        if name.endswith(".tgz"):
            continue
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest
    assert "Redistribution and use" in (directory / "LICENSE").read_text()


@pytest.mark.parametrize("language", ["en", "fil", "pag"])
def test_page_aware_assets_preserve_main_shell(language):
    from _build.chrome import assemble_page
    from _build.locales import load_locale
    root = Path(__file__).resolve().parent.parent
    base = (root / "src/partials/base.html").read_text(encoding="utf-8")
    header = '<nav><a href="/gis/">Map</a><img src="..//assets/logo.svg"></nav>'
    args = (base, "../", "Title", "Description", header, "Content", "Footer", language)
    prefix = "" if language == "en" else language + "/"
    main = assemble_page(*args, page_url=prefix + "index.html", locale=load_locale(language))
    commuter = assemble_page(*args, page_url=prefix + "commuter.html", locale=load_locale(language))
    for dependency in ("chart.umd.min.js", "barangay-data.min.js", "lucide@0.460.0", "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", "mapandan-gateway-emblem.png"):
        assert dependency in main
        assert dependency not in commuter
    assert 'src="/assets/script.min.js"' in commuter
    assert 'href="/assets/style.min.css"' in commuter
    assert 'src="/assets/logo.svg"' in commuter
    assert 'href="/assets/vendor/leaflet-1.9.4/leaflet.css"' in commuter
    assert "Footer" not in commuter and "Footer" in main
