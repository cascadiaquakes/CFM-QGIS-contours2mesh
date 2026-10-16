#!/usr/bin/env python3
"""Build a reproducible, source-only QGIS plugin ZIP without deploying to QGIS."""
# SPDX-License-Identifier: BSD-3-Clause
import argparse
import ast
import configparser
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = 'contours2mesh'
FILES = (
    '__init__.py', 'contours2mesh.py', 'input_dialog.py', 'meshing.py',
    'contours2mesh_dialog.py', 'contours2mesh_dialog_base.ui',
    'metadata.txt', 'icon.png', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
    'licenses/GPL-2.0.txt', 'licenses/GPL-3.0.txt', 'examples/contours.geojson',
    'vendor/ccfm/LICENSE', 'vendor/ccfm/README.md', 'vendor/ccfm/pyproject.toml',
)


def validate_metadata(root):
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(root / 'metadata.txt', encoding='utf-8')
    metadata = parser['general']
    for key in ('name', 'description', 'about', 'version', 'author', 'email',
                'qgisMinimumVersion', 'qgisMaximumVersion', 'license',
                'homepage', 'repository', 'tracker', 'icon'):
        if not metadata.get(key, '').strip():
            raise ValueError(f'Missing metadata: {key}')
    for key in ('homepage', 'repository', 'tracker'):
        if not metadata[key].startswith('https://') or 'github.com/repo' in metadata[key]:
            raise ValueError(f'Invalid metadata URL: {key}')
    if metadata.get('category') not in ('Vector', 'Raster', 'Database', 'Web'):
        raise ValueError('Invalid plugin category')
    if not (root / metadata['icon']).is_file():
        raise ValueError('Plugin icon is missing')
    return metadata


def build(root=ROOT, output=None):
    root = Path(root)
    metadata = validate_metadata(root)
    source_dir = root / 'vendor/ccfm/ccfm'
    if not (source_dir / '__init__.py').is_file():
        raise ValueError('Missing ccfm submodule: run git submodule update --init --recursive')
    files = sorted(set(FILES) | {
        path.relative_to(root).as_posix() for path in source_dir.rglob('*.py')
        if not any(part.startswith('.') or part == '__pycache__' for part in path.relative_to(root).parts)
    })
    for name in files:
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing file or unexpected symlink: {name}')
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=name)
    output = Path(output) if output else root / 'dist' / f'{PLUGIN}-{metadata["version"]}.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            info = zipfile.ZipInfo(f'{PLUGIN}/{name}', date_time=(2025, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (root / name).read_bytes())
    if output.stat().st_size > 25 * 1024 * 1024:
        raise ValueError('Plugin archive exceeds the QGIS repository 25 MB limit')
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise ValueError('Corrupt plugin archive')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    print(build(output=args.output))
