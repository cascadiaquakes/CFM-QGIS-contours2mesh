"""Release archive regression checks; standard Python, no QGIS needed."""
# SPDX-License-Identifier: BSD-3-Clause
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_plugin', ROOT / 'scripts/build_plugin.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackagingTests(unittest.TestCase):
    def test_archive_is_reproducible_and_contains_runtime_and_licenses(self):
        with tempfile.TemporaryDirectory() as directory:
            first = builder.build(output=Path(directory) / 'first.zip')
            second = builder.build(output=Path(directory) / 'second.zip')
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
                for required in ('__init__.py', 'metadata.txt', 'meshing.py',
                                 'vendor/ccfm/ccfm/geom.py', 'vendor/ccfm/LICENSE',
                                 'LICENSE', 'licenses/GPL-3.0.txt', 'licenses/GPL-2.0.txt',
                                 'THIRD_PARTY_NOTICES.md', 'examples/contours.geojson'):
                    self.assertIn('contours2mesh/' + required, names)
                for name in names:
                    self.assertTrue(name.startswith('contours2mesh/'))
                    self.assertFalse(any(part.startswith('.') or part == '__pycache__'
                                         for part in Path(name).parts))
                    self.assertNotIn(Path(name).suffix, ('.pyc', '.so', '.dll', '.dylib', '.zip'))
                self.assertIsNone(archive.testzip())
                self.assertLess(first.stat().st_size, 25 * 1024 * 1024)

    def test_missing_submodule_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'metadata.txt').write_bytes((ROOT / 'metadata.txt').read_bytes())
            (root / 'icon.png').write_bytes((ROOT / 'icon.png').read_bytes())
            with self.assertRaisesRegex(ValueError, 'Missing ccfm submodule'):
                builder.build(root, root / 'bad.zip')

    def test_metadata_has_explicit_qgis4_range(self):
        metadata = builder.validate_metadata(ROOT)
        self.assertEqual(metadata['qgisMaximumVersion'], '4.99')
        self.assertIn('NumPy', metadata['about'])
        self.assertIn('not required', metadata['about'])


if __name__ == '__main__':
    unittest.main()
