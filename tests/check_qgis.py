#!/usr/bin/env python3
"""Exercise the built ZIP with a real QGIS Python interpreter (Qt 5 or Qt 6)."""
# SPDX-License-Identifier: BSD-3-Clause
import importlib
import builtins
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from qgis.core import Qgis, QgsApplication, QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry
from qgis.PyQt.QtCore import QT_VERSION_STR, QLocale, QTimer
from qgis.PyQt.QtWidgets import QMainWindow, QMessageBox

APP = QgsApplication([], False)
APP.initQgis()
# QGIS itself may load optional scientific packages. Block plugin imports even
# when a package is already cached in sys.modules by the host application.
INITIAL_MODULES = set(sys.modules)
_original_import = builtins.__import__

def without_optional_packages(name, *args, **kwargs):
    if name.split('.')[0] in ('geopandas', 'scipy', 'shapely', 'rasterio'):
        raise ImportError(f'Deliberately unavailable for plugin test: {name}')
    return _original_import(name, *args, **kwargs)

builtins.__import__ = without_optional_packages
ARCHIVE = Path(sys.argv.pop(1)).resolve()
TEMP = tempfile.TemporaryDirectory()
with zipfile.ZipFile(ARCHIVE) as archive:
    archive.extractall(TEMP.name)
sys.path.insert(0, TEMP.name)
plugin_package = importlib.import_module('contours2mesh')
implementation = importlib.import_module('contours2mesh.contours2mesh')
dialogs = importlib.import_module('contours2mesh.input_dialog')


class Interface:
    def __init__(self):
        self.window = QMainWindow()
        self.actions = []
    def mainWindow(self):
        return self.window
    def addPluginToVectorMenu(self, menu, action):
        self.actions.append(action)
    def removePluginVectorMenu(self, menu, action):
        self.actions.remove(action)
    def addToolBarIcon(self, action):
        pass
    def removeToolBarIcon(self, action):
        pass


class QgisTests(unittest.TestCase):
    def setUp(self):
        self.project = QgsProject.instance()
        self.iface = Interface()
        self.plugin = plugin_package.classFactory(self.iface)
        self.plugin.initGui()
        self.layer = QgsVectorLayer(str(Path(TEMP.name) / 'contours2mesh/examples/contours.geojson'),
                                    'example', 'ogr')
        self.assertTrue(self.layer.isValid())
        self.project.addMapLayer(self.layer)
        self.dialog = dialogs.MeshInputDialog(None, preselected_layer=self.layer)

    def tearDown(self):
        self.dialog.close()
        self.plugin.unload()
        self.assertEqual(self.iface.actions, [])
        self.project.removeAllMapLayers()

    def generate(self, dialog):
        output = Path(TEMP.name) / 'result.geojson'
        dialog.name_input.setText('test_fault')
        dialog.is_temp_file = False
        dialog.path_input.setText(str(output))
        with patch.object(QMessageBox, 'critical') as critical, \
                patch.object(QMessageBox, 'information') as information:
            self.plugin.process_contours(dialog)
            self.assertFalse(critical.called, critical.call_args)
            self.assertTrue(information.called)
        result = json.loads(output.read_text())
        geometry = result['features'][0]['geometry']
        self.assertEqual(geometry['type'], 'MultiPolygon')
        self.assertGreater(len(geometry['coordinates']), 0)
        for polygon in geometry['coordinates']:
            ring = polygon[0]
            self.assertEqual(len(ring), 4)
            self.assertEqual(ring[0], ring[-1])
            self.assertTrue(all(len(vertex) == 3 for vertex in ring))
        self.assertTrue(QgsVectorLayer(str(output), 'result', 'ogr').isValid())
        return geometry

    def test_modal_dialog_and_legacy_ui(self):
        # Exercise QDialog.exec on both Qt versions, closing via the event loop.
        self.iface.activeLayer = lambda: self.layer
        with patch.object(implementation, 'MeshInputDialog', return_value=self.dialog):
            QTimer.singleShot(0, self.dialog.reject)
            self.plugin.run()
        legacy = importlib.import_module('contours2mesh.contours2mesh_dialog')
        window = legacy.Contours2MeshPluginDialog()
        window.close()

    def test_z_mesh_preserves_trace_elevation(self):
        self.assertEqual(self.dialog.get_selected_layer().id(), self.layer.id())
        self.assertEqual(len(self.dialog.get_selected_contours()), 3)
        geometry = self.generate(self.dialog)
        elevations = [vertex[2] for polygon in geometry['coordinates'] for vertex in polygon[0]]
        self.assertGreater(max(elevations), 0)
        self.assertEqual(min(elevations), -2000)
        for package in ('geopandas', 'scipy', 'shapely'):
            self.assertEqual(package in sys.modules, package in INITIAL_MODULES, package)
        self.assertNotIn('contours2mesh._ccfm_backend.cfm_io', sys.modules)

    def test_2d_mesh_uses_elev_field(self):
        layer = QgsVectorLayer('LineString?crs=EPSG:4326&field=name:string&field=elev:double',
                               '2d', 'memory')
        for latitude, elevation in ((47, 0), (46.99, -1000)):
            feature = QgsFeature(layer.fields())
            feature.setAttributes(['same name', elevation])
            feature.setGeometry(QgsGeometry.fromWkt(
                f'LINESTRING(-120.1 {latitude}, -120.08 {latitude}, '
                f'-120.06 {latitude}, -120.04 {latitude})'))
            layer.dataProvider().addFeatures([feature])
        self.project.addMapLayer(layer)
        dialog = dialogs.MeshInputDialog(None, preselected_layer=layer)
        try:
            geometry = self.generate(dialog)
            self.assertEqual(min(vertex[2] for p in geometry['coordinates'] for vertex in p[0]), -1000)
        finally:
            dialog.close()

    def test_reorder_exclude_and_remove_duplicate_labels(self):
        self.layer.startEditing()
        for feature in self.layer.getFeatures():
            self.layer.changeAttributeValue(feature.id(), self.layer.fields().indexFromName('name'), 'duplicate')
            self.layer.changeAttributeValue(feature.id(), self.layer.fields().indexFromName('elev'), 0)
        self.dialog.update_contour_list()
        original = [c['feature'].id() for c in self.dialog.get_selected_contours()]
        self.assertEqual(len(set(original)), 3)
        self.dialog.contour_list.setCurrentRow(0)
        self.dialog.move_contour_down()
        self.assertEqual([c['feature'].id() for c in self.dialog.get_selected_contours()],
                         [original[1], original[0], original[2]])
        self.dialog.move_contour_up()
        item = self.dialog.contour_list.item(0)
        self.dialog.contour_list.itemWidget(item).checkbox.setChecked(False)
        self.assertEqual(len(self.dialog.get_selected_contours()), 2)
        self.dialog.remove_contour()
        self.assertEqual(self.dialog.contour_list.count(), 2)

    def test_projected_crs_rejected(self):
        from qgis.core import QgsCoordinateReferenceSystem
        self.layer.setCrs(QgsCoordinateReferenceSystem('EPSG:32610'))
        with patch.object(QMessageBox, 'critical') as critical:
            self.plugin.process_contours(self.dialog)
            self.assertEqual(critical.call_args.args[1], 'Invalid CRS')

    def manastash_dialog(self):
        """Load the real fixture and move the null-elev trace above all contours."""
        path = Path(__file__).resolve().parent / 'data' / 'manastash_contours.geojson'
        layer = QgsVectorLayer(str(path), 'Manastash contours', 'ogr')
        self.assertTrue(layer.isValid())
        self.assertEqual(layer.featureCount(), 16)
        self.project.addMapLayer(layer)
        dialog = dialogs.MeshInputDialog(None, preselected_layer=layer)
        self.addCleanup(dialog.close)
        contours = dialog.get_selected_contours()
        trace_rows = [row for row, contour in enumerate(contours)
                      if contour['name'] == 'manastash_trace']
        self.assertEqual(len(trace_rows), 1)
        # The dialog initially sorts null elev last. Exercise the same move-up
        # control the user needs to place the draped trace at the surface.
        self.assertEqual(trace_rows[0], len(contours) - 1)
        self.assertIsNone(contours[trace_rows[0]]['elev'])
        dialog.contour_list.setCurrentRow(trace_rows[0])
        for _ in range(trace_rows[0]):
            dialog.move_contour_up()
        ordered = dialog.get_selected_contours()
        self.assertEqual(ordered[0]['name'], 'manastash_trace')
        self.assertEqual(len({c['feature'].id() for c in ordered}), 16)
        return dialog

    def test_manastash_trace_first_and_remaining_contours_descend(self):
        dialog = self.manastash_dialog()
        selected = dialog.get_selected_contours()
        self.assertEqual(selected[1]['name'], 'manastash_228')
        self.assertEqual(selected[-1]['name'], 'manastash_-9060')
        elevations = [contour['elev'] for contour in selected[1:]]
        self.assertEqual(elevations, sorted(elevations, reverse=True))
        self.assertIsNone(selected[0]['elev'])
        # Moving the trace must not lose its feature or its vertex elevations.
        original_trace = next(feature for feature in dialog.get_selected_layer().getFeatures()
                              if feature['name'] == 'manastash_trace')
        self.assertEqual(selected[0]['feature'].id(), original_trace.id())
        self.assertEqual([vertex.z() for vertex in selected[0]['feature'].geometry().vertices()],
                         [vertex.z() for vertex in original_trace.geometry().vertices()])

    def test_manastash_resampling_preserves_vertex_elevations(self):
        self.manastash_dialog()  # Also verify trace-first ordering through the UI.
        path = Path(__file__).resolve().parent / 'data' / 'manastash_contours.geojson'
        features = json.loads(path.read_text())['features']
        trace = next(feature for feature in features
                     if feature['properties']['name'] == 'manastash_trace')
        ordered = [trace] + sorted(
            [feature for feature in features if feature is not trace],
            key=lambda feature: feature['properties']['elev'], reverse=True)
        prepared = implementation.prepare_fault_contours(ordered, pt_distance=0.5)
        self.assertEqual(len(prepared), 16)
        self.assertGreater(len(prepared[0]), 4)
        self.assertTrue(all(len(contour) == len(prepared[0]) for contour in prepared))
        for source, sampled in zip(ordered, prepared):
            original = source['geometry']['coordinates']
            low = min(vertex[2] for vertex in original)
            high = max(vertex[2] for vertex in original)
            for vertex in sampled:
                self.assertEqual(len(vertex), 3)
                self.assertTrue(all(math.isfinite(value) for value in vertex))
                self.assertGreaterEqual(vertex[2], low - 1e-8)
                self.assertLessEqual(vertex[2], high + 1e-8)
            for source_end, sampled_end in ((original[0], sampled[0]),
                                            (original[-1], sampled[-1])):
                for expected, actual in zip(source_end, sampled_end):
                    self.assertAlmostEqual(actual, expected, places=7)
        # The fixture's manastash_228 has elev=228 but Z=288. Z must win.
        self.assertEqual(ordered[1]['properties']['elev'], 228)
        self.assertTrue(all(vertex[2] == 288 for vertex in prepared[1]))
        self.assertGreater(max(v[2] for v in prepared[0]) - min(v[2] for v in prepared[0]), 100)
        self.assertTrue(all(vertex[2] == -9060 for vertex in prepared[-1]))

    def test_manastash_full_mesh_with_trace_on_top(self):
        dialog = self.manastash_dialog()
        dialog.spacing_input.setValue(0.5)
        geometry = self.generate(dialog)
        vertices = [vertex for polygon in geometry['coordinates'] for vertex in polygon[0]]
        self.assertTrue(all(math.isfinite(value) for vertex in vertices for value in vertex))
        elevations = [vertex[2] for vertex in vertices]
        self.assertEqual(min(elevations), -9060)
        self.assertGreater(max(elevations), 800)
        self.assertLessEqual(max(elevations), 940.4371337890625)
        # Both original endpoints of the draped surface trace survive meshing.
        trace = dialog.get_selected_contours()[0]['feature']
        trace_vertices = list(trace.geometry().vertices())
        rounded_vertices = {tuple(round(value, 7) for value in vertex) for vertex in vertices}
        for point in (trace_vertices[0], trace_vertices[-1]):
            self.assertIn(tuple(round(value, 7) for value in (point.x(), point.y(), point.z())),
                          rounded_vertices)

    def test_locale_spacing_uses_numeric_value(self):
        self.dialog.spacing_input.setLocale(QLocale('de_DE'))
        self.dialog.spacing_input.setValue(0.75)
        self.assertEqual(self.dialog.get_values()[1], 0.75)


if __name__ == '__main__':
    print(f'Testing archive {ARCHIVE.name}: QGIS {Qgis.QGIS_VERSION}, Qt {QT_VERSION_STR}', flush=True)
    result = unittest.main(verbosity=2, exit=False)
    QgsProject.instance().removeAllMapLayers()
    APP.exitQgis()
    TEMP.cleanup()
    sys.exit(0 if result.result.wasSuccessful() else 1)
