"""Disposable copied-workspace builds exporting the single staged _site artifact."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_COPY_BYTES = 1024 * 1024 * 1024
SKIP = {"__pycache__", ".pytest_cache", "node_modules", "vcpkg", ".git",
        "vcpkg_installed", ".venv", ".mypy_cache", ".ruff_cache",
        "_site", "_preview_gis", "gis-preview"}


def copy_inputs(root, workspace):
    """Copy working-tree inputs, explicitly including configured GIS datasets."""
    from _build.gis_sources import input_path, layer_configuration
    from _build.staging import _download_outputs
    config = layer_configuration(root)
    roots = [Path(name) for name in ("_build", "src", "locales", "assets", "build.py")]
    roots += [Path(name) for name in ("CNAME", ".nojekyll", "robots.txt", "llms.txt", "site.webmanifest") if (root / name).exists()]
    roots += sorted(_download_outputs(root))
    # src/data/gis is skipped below so disabled configured sources are not read.
    roots.append(Path('src/data/gis/layers.json'))
    for layer in config['layers']:
        source = input_path(root, layer['source'])
        if layer['enabled'] and source.is_file():
            roots.append(Path(layer['source']))
    disabled = {Path(layer['source']) for layer in config['layers'] if not layer['enabled']}
    enabled = {Path(layer['source']) for layer in config['layers'] if layer['enabled']}
    disabled -= enabled
    total, copied = 0, set()

    def copy(rel):
        nonlocal total
        if rel in copied or rel in disabled:
            return
        source = root / rel
        for parent in (source, *source.parents):
            if parent == root.parent:
                break
            if parent.is_symlink():
                raise ValueError("Symlink in build inputs")
        if source.is_dir():
            for child in sorted(source.iterdir()):
                if child.name not in SKIP and child.relative_to(root).as_posix() not in {'src/data/gis', 'assets/gis'}:
                    copy(child.relative_to(root))
        elif source.is_file():
            total += source.stat().st_size
            if total > MAX_COPY_BYTES:
                raise ValueError("Build input copy exceeds resource limit")
            destination = workspace / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            copied.add(rel)
        else:
            raise ValueError(f"Missing or special build input: {rel}")
    for rel in roots:
        copy(rel)


def isolated_build(root, offline=False):
    root = Path(root)
    if root.is_symlink():
        raise ValueError("Linked build root")
    root = root.resolve(strict=True)
    destination = root / '_site'
    if destination.is_symlink():
        raise ValueError("Linked build destination")
    with tempfile.TemporaryDirectory(prefix="bettermapandan-build-") as temporary:
        workspace = Path(temporary)
        copy_inputs(root, workspace)
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        command = [sys.executable, "-B", "-c",
                   "from _build.orchestrator import _build_workspace; _build_workspace()"]
        command += ["--offline"] if offline else []
        subprocess.run(command, cwd=workspace, env=environment, check=True)
        subprocess.run([sys.executable, "-B", "-m", "_build.staging"], cwd=workspace, env=environment, check=True)
        from _build.staging import _tree_files
        if destination.exists():
            _tree_files(root, Path("_site"))
            shutil.rmtree(destination)
        shutil.copytree(workspace / "_site", destination)
    print(f"Isolated site artifact: {destination}")
    return destination
