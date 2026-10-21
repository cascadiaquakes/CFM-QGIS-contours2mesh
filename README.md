# Contours2Mesh QGIS Plugin

Build a triangular 3D fault surface from two or more elevation contours. Adjust
point spacing, reorder or exclude contours, and create a temporary map layer or
save a MultiPolygonZ GeoJSON file. Contours2Mesh is part of the CRESCENT workflow
for building nonplanar fault geometries from cross-sections and mapped traces.

[Full illustrated tutorial](https://cascadiaquakes.github.io/fault-geometry-building-tutorial/QGIS_plugin.html)
| [Source](https://github.com/cascadiaquakes/CFM-QGIS-contours2mesh)
| [Report an issue](https://github.com/cascadiaquakes/CFM-QGIS-contours2mesh/issues)

## Requirements and installation

- QGIS 3.34 or later in the QGIS 3 series, or QGIS 4.x (Qt 6).
- NumPy >=1.20 in QGIS's Python environment, normally included with QGIS.
- No GeoPandas, SciPy, Shapely or Rasterio installation is needed. The plugin
  loads only the numerical modules of the bundled CFM-ccfm library and writes
  GeoJSON using Python's standard library.
- CrossSectionDigitizer and Qgis2threejs are optional tools for preparing inputs
  and viewing the resulting surfaces; neither is a plugin dependency.

Install a release ZIP using **Plugins > Manage and Install Plugins > Install
from ZIP**, then enable **Contours2Mesh**. Once the plugin is approved in the
QGIS repository, it can also be installed from the **All** tab.

To check NumPy in the QGIS Python console, run:

```python
import numpy
print(numpy.__version__)
```

If NumPy is missing or older than 1.20, install or update it in the Python
environment that runs QGIS. On Windows, open the OSGeo4W Shell supplied with
that QGIS installation and run `python -m pip install "numpy>=1.20"`. On Linux,
use the distribution's `python3-numpy` package or the environment's package
manager. On macOS, use the Python launcher supplied by the QGIS installation,
for example `"/Applications/QGIS.app/Contents/MacOS/bin/python3" -m pip install
"numpy>=1.20"` for bundles with that layout; newer bundles may provide
`Contents/MacOS/python` instead. Use a writable QGIS Python environment and
restart QGIS after installation. The plugin does not install dependencies itself.

## Quick start

1. Load a contour layer in a geographic longitude/latitude CRS, preferably
   EPSG:4326. Use **Reproject layer** or **Save Features As** to transform a
   projected layer; changing the assigned CRS alone does not transform it.
2. Provide at least two single LineString or LineStringZ features, each with
   at least four vertices. Elevations are in **meters**, positive upwards
   (negative below sea level). Vertex Z coordinates take precedence; for 2D
   contours, supply a numeric `elev` attribute. A `name` field helps identify
   contours. Convert multipart lines to singleparts before using the plugin.
3. Digitize all contours in the same along-strike direction. The algorithm
   matches their start and end points and interpolates between them.
4. Choose **Vector > Contours2Mesh > Generate 3D Surface from Contours** or
   click the toolbar icon. Select the input layer and enter a fault name.
5. Set **Point Spacing (km)** (default 0.5 km). Check contours are ordered
   from top to bottom, move them with the arrow buttons, and uncheck or remove
   any to exclude. The initial sort uses `elev`; a surface trace with varying
   vertex elevations and no `elev` value may need to be moved to the top.
6. Keep temporary output selected, or browse to a `.geojson` output file, then
   click **Run**. The result is added to QGIS. Save temporary results to a
   permanent file before closing QGIS. Inspect the mesh in 3D, adjust contours
   if needed, and run again.

Load [examples/contours.geojson](examples/contours.geojson) for a small synthetic
example with three four-vertex contours. With the default 0.5 km spacing, name
it `example_fault` and click Run. Expect one MultiPolygonZ feature whose polygons
are triangles, with a surface trace above sea level and a base at -2000 m.
The example is synthetic and is not a geological interpretation.

## Algorithm and limits

The uppermost contour is resampled at approximately the requested spacing.
Remaining contours are resampled to the same point count, intermediate rows are
interpolated down dip, and adjacent points are connected into triangles. Output
is a vector surface represented by a MultiPolygonZ, rather than a QGIS mesh-layer
provider. There is no geographic coverage restriction.

The backend limits the resampled upper contour to 1,000 points; the plugin also
rejects an estimated mesh size above 50,000 triangles. Increase spacing for large
faults. These are safeguards, and geological quality still depends on contour
ordering, consistent direction and reasonable spacing between contours.

This method is described in *Open-source tools for making geometrically-complex
fault surfaces* by Richard Styron, Loïc Bachelot and Amanda M. Thomas, and in the
[illustrated tutorial](https://cascadiaquakes.github.io/fault-geometry-building-tutorial/QGIS_plugin.html).

## Development and release

Clone the source and pinned numerical backend together:

```sh
git clone --recurse-submodules https://github.com/cascadiaquakes/CFM-QGIS-contours2mesh.git
cd CFM-QGIS-contours2mesh
# For an existing clone:
git submodule update --init --recursive
python3 scripts/build_plugin.py
python3 -m unittest discover -s tests -p 'test_packaging.py' -v
```

The canonical build produces `dist/contours2mesh-1.0.5.zip` with one
`contours2mesh/` root directory. It includes Python sources, UI, icon, metadata,
documentation, example data, upstream license and GPL texts. It excludes git
metadata, caches, binary dependencies and development files. No Qt resource
compiler, pb_tool deployment or write to an installed QGIS profile is needed.
The release workflow uses the same builder and attaches the ZIP to GitHub releases.

The plugin was checked locally against QGIS 3.40.1 / Qt 5.15.2 / NumPy 1.20.1
and QGIS 4.2.3 / Qt 6.11.1 / NumPy 2.5.2. Ten archive-based integration checks
passed in each runtime, as well as three packaging checks. These checks use
Qt's offscreen platform; they do not replace a desktop installation smoke test.
The bundled CFM-ccfm source is pinned to merged commit `6e81b57`, which includes
the explicit dip-direction validation. The upstream library's `pyproject.toml`
lists broader installation dependencies;
the plugin's private numerical backend does not install that Python distribution.

Run the integration checks with each target QGIS installation's Python launcher:

```sh
QT_QPA_PLATFORM=offscreen /path/to/qgis/python tests/check_qgis.py dist/contours2mesh-1.0.5.zip
```

These checks load the **extracted archive**, create the dialog and menu action,
mesh both 2D and Z contours, reload the output in QGIS, check contour reordering,
check localized spacing and reject a projected CRS. The Manastash regression
fixture in `tests/data/` adds three checks: move the null-elevation trace to the
top using the dialog controls, preserve vertex elevations during resampling,
and generate and reload a mesh from all 16 contours at 0.5 km spacing. The
fixture is kept in the source repository and excluded from the submission ZIP.
The checks also verify dip-direction validation and deliberately block GeoPandas, SciPy, Shapely and Rasterio imports to catch dependency regressions.
The older `test/` directory contains Plugin Builder template tests; `tests/`
contains the maintained release checks.

The optional legacy `plugin_upload.py` helper requires `defusedxml` to harden
XML-RPC response parsing (`python -m pip install defusedxml`). This is a tool
dependency, not a plugin runtime requirement. Its parser regression checks can
be run with `python -m unittest discover -s tests -p 'test_plugin_upload.py' -v`.

Before uploading, run the integration checks and a desktop install-from-ZIP smoke
test in QGIS 3 and QGIS 4. Confirm the displayed plugin information, toolbar,
Vector menu, example mesh and saved output. Make sure release metadata matches
the source revision and release tag. Upload the generated ZIP through the
[QGIS plugin repository](https://plugins.qgis.org/plugins/add/).
See the [publishing requirements](https://plugins.qgis.org/docs/publish) and
[QGIS 4 migration guidance](https://plugins.qgis.org/docs/migrate-qgis4).

## License

CRESCENT original contributions are BSD-3-Clause; retained Plugin Builder
scaffolding is GPL-2.0-or-later. The numerical backend is BSD-3-Clause.
QGIS and PyQt retain their own terms; use with the GPL edition of PyQt is
subject to GPLv3. PyQt is not LGPL licensed. See [LICENSE](LICENSE),
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the full texts in `licenses/`.

## Contacts

Contact the CRESCENT CFM team at
[crescentcfm@cascadiaquakes.org](mailto:crescentcfm@cascadiaquakes.org), or
[open an issue](https://github.com/cascadiaquakes/CFM-QGIS-contours2mesh/issues).

## Acknowledgments

<table>
  <tr>
    <td align="center" valign="middle">
      <img src="https://raw.githubusercontent.com/cascadiaquakes/.github/main/assets/crescent-circle.png" alt="CRESCENT Logo" width="150" />
    </td>
    <td align="center" valign="middle">
      <img src="https://raw.githubusercontent.com/cascadiaquakes/.github/main/assets/nsf-logo.png" alt="NSF Logo" width="450" />
    </td>
  </tr>
</table>

This project is supported by the National Science Foundation through the Cascadia Region Earthquake Science Center (CRESCENT), Cooperative Agreement EAR-2225286.
