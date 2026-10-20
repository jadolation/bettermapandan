import json
from pathlib import Path

import pytest
from test_gis_sources import configuration, layer

from _build.orchestrator import _check_removed_gis_options
from _build.preview import copy_inputs, isolated_build


def fixture_root(tmp_path):
    root = tmp_path / 'root'
    for name in ('_build', 'src/data', 'locales', 'assets'):
        (root / name).mkdir(parents=True)
    (root / 'build.py').write_text('# synthetic build')
    (root / 'src/data/audit-reports.json').write_text(json.dumps({'audit_archive': []}))
    (root / 'assets/current.js').write_text('working tree input')
    configuration(root, [])
    return root


@pytest.mark.parametrize('name', ['GIS_MODE', 'GIS_RESEARCH_INPUTS', 'GIS_RESEARCH_OTHER'])
def test_obsolete_options_explain_removal(monkeypatch, name):
    monkeypatch.setenv(name, 'old')
    with pytest.raises(ValueError, match='Obsolete GIS options'):
        _check_removed_gis_options()


def test_controlled_copy_current_inputs_and_configured_datasets(tmp_path):
    root = fixture_root(tmp_path)
    configuration(root, [layer('roads', 'datasets/GIS/roads.geojson'),
                         layer('disabled', 'src/data/disabled.json', enabled=False)])
    (root / 'datasets/GIS').mkdir(parents=True)
    (root / 'datasets/GIS/roads.geojson').write_text('configured bytes')
    (root / 'datasets/GIS/not-configured.geojson').write_text('DO_NOT_COPY')
    (root / 'src/data/disabled.json').write_text('DO_NOT_COPY')
    for name in ('node_modules', 'vcpkg', '.git', '_site', '_preview_gis', 'pag', 'fil', 'assets/gis-preview', 'assets/gis'):
        (root / name).mkdir(parents=True, exist_ok=True)
        (root / name / 'DO_NOT_COPY').write_text('private')
    workspace = tmp_path / 'workspace'
    copy_inputs(root, workspace)
    assert (workspace / 'assets/current.js').read_text() == 'working tree input'
    assert (workspace / 'datasets/GIS/roads.geojson').read_text() == 'configured bytes'
    assert not list(workspace.rglob('DO_NOT_COPY'))
    assert not (workspace / 'src/data/disabled.json').exists()
    assert not (workspace / 'datasets/GIS/not-configured.geojson').exists()


def test_selected_symlink_rejected(tmp_path):
    root = fixture_root(tmp_path)
    (root / 'assets/link.js').symlink_to(root / 'assets/current.js')
    with pytest.raises(ValueError, match='Symlink'):
        copy_inputs(root, tmp_path / 'workspace')


def test_worker_mutates_only_workspace_and_exports_site(monkeypatch, tmp_path):
    import _build.preview as preview
    root = fixture_root(tmp_path)
    (root / '_site').mkdir()
    (root / '_site/stale').write_text('stale')
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file() and '_site' not in p.parts}
    calls = []

    def run(command, cwd, env, check):
        calls.append(command)
        assert Path(cwd) != root
        assert 'GIS_MODE' not in env
        if '-c' in command:
            assert '--offline' in command
            (Path(cwd) / 'assets/current.js').write_text('mutated only in worker')
        else:
            site = Path(cwd) / '_site'
            site.mkdir()
            (site / 'index.html').write_text('synthetic staged site')

    monkeypatch.setattr(preview.subprocess, 'run', run)
    destination = isolated_build(root, offline=True)
    assert len(calls) == 2 and destination.name == '_site'
    assert (destination / 'index.html').read_text() == 'synthetic staged site'
    assert not (destination / 'stale').exists()
    for rel, raw in before.items():
        assert (root / rel).read_bytes() == raw


def test_destination_symlink_rejected_before_worker(tmp_path):
    root = fixture_root(tmp_path)
    (root / '_site').symlink_to(tmp_path / 'elsewhere')
    with pytest.raises(ValueError, match='Linked'):
        isolated_build(root, offline=True)
