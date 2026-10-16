#!/usr/bin/env python3
"""Exercise the built ZIP with a real QGIS Python interpreter (Qt 5 or Qt 6)."""
# SPDX-License-Identifier: BSD-3-Clause
import importlib
import builtins
import json
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
