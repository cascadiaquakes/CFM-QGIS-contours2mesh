# Manastash regression fixture

`manastash_contours.geojson` is an unmodified copy of the user-provided file at
`/Users/itchy/research/cascadia/yfp_3d/data/gis/manastash_contours.geojson`.
It contains 16 LineStringZ contours in longitude/latitude coordinates.
It is test data only and is not included in the submission ZIP.

The contour `manastash_trace` has `elev: null` and variable vertex Z elevations.
It must be moved to the top before meshing. Remaining contours are ordered by
`elev` descending. The tests exercise that reordering using the dialog controls.

The feature `manastash_228` has `elev: 228` but Z coordinates of 288 m. This is
preserved as supplied, and the tests verify that vertex Z takes precedence.
The deepest contour is at -9060 m. Integration tests mesh the complete set at
0.5 km spacing and verify saved output, finite XYZ coordinates, closed triangular
rings, trace endpoints and preservation of contour elevations during resampling.
