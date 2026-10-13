# Contours2Mesh QGIS Plugin

[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](LICENSE)

A QGIS plugin that builds the triangular mesh of a fault surface from its depth contours (top, middle and bottom LineStrings). It is one of three QGIS plugins used to build 3D fault geometries for the CRESCENT Community Fault Model.

**Tutorial:** https://cascadiaquakes.github.io/fault-geometry-building-tutorial/QGIS_plugin.html

---

## Installation and Use

Requires QGIS 3.0 or later. Installation and use instructions are in the [fault geometry building tutorial](https://cascadiaquakes.github.io/fault-geometry-building-tutorial/QGIS_plugin.html).

The meshing code comes from [CFM-ccfm](https://github.com/cascadiaquakes/CFM-ccfm), included as a git submodule in `vendor/ccfm`. Clone with `git clone --recurse-submodules`.

---

## License

This project is licensed under the BSD 3-Clause License. See [LICENSE](LICENSE). All work copyright CRESCENT, 2025.

---

## Contacts

- **CRESCENT CFM team**: [crescentcfm@cascadiaquakes.org](mailto:crescentcfm@cascadiaquakes.org)

For bugs or questions, please [open an issue](https://github.com/cascadiaquakes/CFM-QGIS-contours2mesh/issues).

---

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
