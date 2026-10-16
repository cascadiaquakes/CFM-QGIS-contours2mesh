#/***************************************************************************
# Contours2MeshPlugin
#
# Generate 3D fault surfaces or geological meshes from top, middle, and bottom contour lines in QGIS.
#							 -------------------
#		begin				: 2025-06-05
#		git sha				: $Format:%H$
#		copyright			: (C) 2025 by CRESCENT
#		email				: lbachelo@uoregon.edu
# ***************************************************************************/
#
#/***************************************************************************
# *																		 *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or	 *
# *   (at your option) any later version.								   *
# *																		 *
# ***************************************************************************/

.PHONY: default zip package test
PYTHON ?= python3

default: zip

zip package:
	$(PYTHON) scripts/build_plugin.py

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_packaging.py' -v
