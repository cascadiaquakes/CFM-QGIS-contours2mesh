# Licensing and third-party notices

CRESCENT's original code is available under the BSD 3-Clause license in
[LICENSE](LICENSE). This does not replace licenses on third-party code.

## Retained Plugin Builder scaffolding

`__init__.py`, `contours2mesh.py`, `contours2mesh_dialog.py`, `Makefile`,
`pb_tool.cfg`, and some development helpers and tests retain their original
GPL version 2 or later notices. Those notices continue to apply to those files;
the root BSD notice does not relicense them. The Plugin Builder attribution in
these files and the author and copyright notices in the legacy tests are retained.
See [GPL-2.0.txt](licenses/GPL-2.0.txt) and [GPL-3.0.txt](licenses/GPL-3.0.txt).

## Bundled meshing library

CFM-ccfm is copyright (c) 2025 CRESCENT and licensed under BSD-3-Clause.
The submission archive contains the Python sources and the upstream license at
`vendor/ccfm/LICENSE`. The git submodule pins the upstream revision used:
<https://github.com/cascadiaquakes/CFM-ccfm>.

## QGIS, PyQt and Qt (provided by the user's QGIS installation)

QGIS is licensed under GPL version 2 or later. PyQt5 and PyQt6 are copyright
Riverbank Computing Limited and are dual licensed under GNU GPL version 3 and a
Riverbank commercial license. **PyQt is not LGPL licensed.** This plugin uses
QGIS's `qgis.PyQt` bindings; it does not bundle PyQt, Qt or QGIS. With the GPL
edition of PyQt, distribution of the combined work must comply with GPLv3.
The BSD terms on CRESCENT's original contributions and the GPL version 2 or later
scaffolding are compatible with that use. This is not a claim that PyQt itself is
BSD licensed or that a Riverbank commercial license is supplied by this project.
Qt has its own license terms, separate from PyQt.

- QGIS plugin licensing: <https://plugins.qgis.org/docs/publish>
- QGIS licensing guidance: <https://blog.qgis.org/2016/05/29/licensing-requirements-for-qgis-plugins/>
- PyQt licensing: <https://www.riverbankcomputing.com/software/pyqt/intro>
- PyQt license FAQ: <https://www.riverbankcomputing.com/commercial/license-faq>

## External Python dependencies

NumPy (BSD-3-Clause) is the required external numerical dependency. QGIS
normally supplies it. The plugin loads the bundled `geom` and `mesh_helpers`
modules in a private package without executing upstream `ccfm.__init__` or
`cfm_io`. GeoPandas, SciPy and Shapely are therefore not plugin requirements.
The GeoJSON writer uses Python's standard `json` library. GDAL is supplied by
QGIS; the backend also attempts an optional Rasterio import, but Rasterio is
not required. No dependency binaries are bundled, and the plugin does not
install packages or download code at runtime. Dependencies retain their own
licenses and copyright notices.

The synthetic data in `examples/` was created for this repository and is covered
by the root BSD-3-Clause license. No manuscript figures or tutorial datasets are
redistributed in the plugin archive.
