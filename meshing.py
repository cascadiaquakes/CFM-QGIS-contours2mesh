"""Use the bundled numerical backend without importing its optional GIS I/O stack.

ccfm.__init__ eagerly imports cfm_io (and GeoPandas). Load just the meshing
modules in a plugin-private package, keeping upstream sources unmodified and
avoiding conflicts with other plugins that may use another ccfm version.
"""
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2026, CRESCENT
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType

_backend_path = Path(__file__).parent / 'vendor' / 'ccfm' / 'ccfm'
if not (_backend_path / 'geom.py').is_file():
    raise ImportError('Missing meshing source. Run git submodule update --init --recursive '
                      'for a source checkout, or reinstall the complete plugin ZIP.')
_backend_name = __package__ + '._ccfm_backend'
if _backend_name not in sys.modules:
    _backend = ModuleType(_backend_name)
    _backend.__path__ = [str(_backend_path)]
    sys.modules[_backend_name] = _backend

_geom = importlib.import_module(_backend_name + '.geom')
_helpers = importlib.import_module(_backend_name + '.mesh_helpers')
make_tri_mesh = _geom.make_tri_mesh
make_mesh_from_prepared_contours = _helpers.make_mesh_from_prepared_contours
estimate_triangle_count = _helpers.estimate_triangle_count


def prepare_fault_contours(contours, pt_distance=0.5, elevation_path=None):
    """Resample with the upstream backend and restore interpolated vertex Z.

    The pinned backend's resamplers return XY only, even for XYZ inputs.
    Give them a numeric fallback elevation, then recover each sampled point's
    height from its position on the original contour's great-circle segments.
    """
    inputs = []
    for contour in contours:
        properties = dict(contour['properties'])
        coordinates = contour['geometry']['coordinates']
        if len(coordinates[0]) >= 3:
            properties['elev'] = coordinates[0][2]
        inputs.append({**contour, 'properties': properties})
    prepared = _helpers.prepare_fault_contours(inputs, pt_distance, elevation_path)
    for contour, sampled in zip(contours, prepared):
        coordinates = contour['geometry']['coordinates']
        if len(coordinates[0]) < 3:
            continue
        segments = [(start, end, _geom.haversine_distance(*start[:2], *end[:2]))
                    for start, end in zip(coordinates, coordinates[1:])]
        segments = [(start, end, length) for start, end, length in segments if length > 0]
        if not segments:
            raise ValueError('A contour must contain distinct horizontal points.')
        for point in sampled:
            candidates = []
            for start, end, length in segments:
                distance = _geom.haversine_distance(*start[:2], *point[:2])
                to_end = _geom.haversine_distance(*point[:2], *end[:2])
                fraction = min(1.0, max(0.0, distance / length))
                height = start[2] + fraction * (end[2] - start[2])
                candidates.append((abs(distance + to_end - length), height))
            point[2] = min(candidates, key=lambda candidate: candidate[0])[1]
    return prepared


def write_mesh(path, triangles, name):
    """Write the mesh as one MultiPolygonZ GeoJSON feature using standard JSON."""
    feature = {
        'type': 'Feature',
        'properties': {'name': name},
        'geometry': {
            'type': 'MultiPolygon',
            'coordinates': [[triangle] for triangle in triangles],
        },
    }
    with open(path, 'w', encoding='utf-8') as stream:
        json.dump({'type': 'FeatureCollection', 'features': [feature]}, stream,
                  allow_nan=False)
