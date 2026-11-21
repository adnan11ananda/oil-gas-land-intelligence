# Oil & Gas Land Intelligence Platform

**A Python-based geospatial platform for preliminary pipeline ROW, land acquisition, and forest-area screening.**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-Geospatial-green)](https://geopandas.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-WebGIS-red?logo=streamlit)](https://streamlit.io/)

---

## 1. Project Overview

The Oil & Gas Land Intelligence Platform demonstrates a Python-based GIS workflow for preliminary screening of proposed pipeline routes against land parcels and forest-area reference data.

Users can draw a pipeline alignment on an interactive map or import an existing polyline, define the required Right-of-Way (ROW) width, generate a ROW corridor, and review the resulting land and forest intersections.

The application separates the workflow into three functional modules:

1. **Alignment Designer** — create/import a proposed alignment, generate its ROW corridor, view route metrics, and download the consolidated preliminary report and GIS data.
2. **Land Acquisition** — review affected parcels, ownership information, potential ROW acquisition areas, and download a parcel-level CSV report.
3. **Environmental Screening** — review forest-area overlays, affected forest polygons, area metrics, and download a forest overlay CSV report.

All project datasets are synthetic and represent a fictional operating area. Outputs are intended for portfolio demonstration and preliminary spatial screening only.

## 2. Business Context

Pipeline route planning requires early understanding of land access and environmental constraints. A proposed ROW can intersect multiple land parcels and land-cover categories. GIS can help identify these spatial relationships before detailed field verification and formal approval processes.

This project demonstrates workflows for:

- Generating a ROW corridor from a pipeline centerline.
- Identifying land parcels intersected by a proposed ROW.
- Calculating the portion of each parcel within the proposed ROW.
- Summarizing potential acquisition areas by ownership category.
- Identifying forest polygons intersected by the ROW.
- Calculating forest intersection areas and preliminary impact percentages.
- Exporting results in interoperable geospatial and tabular formats.

## 3. Application Workflow

### 3.1 Alignment Designer

- Draw a proposed pipeline alignment using the map drawing tool, or import an existing alignment.
- Configure ROW width.
- Generate the ROW corridor using a metric projected CRS.
- Review pipeline length and ROW area.
- View the **Proposed ROW Land Acquisition Preliminary Report**.
- Download a GeoPackage containing the alignment, ROW corridor, acquisition screening, and forest screening layers.
- Download the proposed alignment as GeoJSON.

Supported import formats:
- GeoPackage (`.gpkg`)
- GeoJSON (`.geojson`, `.json`)
- Zipped Shapefile (`.zip`)
- KML (`.kml`, subject to the local GDAL/KML driver installation)

The importer checks for usable line geometries, handles missing CRS only when the user selects an assumed CRS, converts the alignment to WGS 84 for mapping, and prepares one continuous line for the screening workflow. It can merge connected line segments and rejects disconnected segments.

### 3.2 Land Acquisition

The Land Acquisition page uses the latest alignment and screening results generated in Alignment Designer. It provides:

- A map showing the proposed alignment, ROW corridor, and affected land parcels.
- Affected parcel count.
- Potential acquisition area.
- ROW width.
- A parcel-level screening table containing parcel identifiers, parent parcel identifiers, ownership category, land status, parcel area, ROW intersection area, affected percentage, and acquisition screening status.
- CSV export.

The reported ROW intersection area is a preliminary geometric estimate. It is not a legal determination of land ownership, compensation, or approved acquisition area.

### 3.3 Environmental Screening

The Environmental Screening page presents the **Forest Area Overlay Report**, based on the same latest alignment and ROW screening results. It provides:

- A map showing the proposed alignment, ROW corridor, and forest polygons intersected by the ROW.
- Number of affected forest polygons.
- Forest intersection area.
- Percentage of the ROW within forest areas.
- Pipeline alignment length within forest areas.
- A forest polygon-level report with forest identifier, forest type, original forest area, intersection area, and affected percentage.
- CSV export.

This is a preliminary spatial overlay, not a formal environmental assessment, permit, or approval.

## 4. Technology Stack

| Technology | Application |
|---|---|
| Python 3.12 | Core programming language |
| GeoPandas | Geospatial data management and spatial analysis |
| Shapely | Geometry processing and buffering |
| Pandas | Tabular processing and reporting |
| PyProj | Coordinate reference system transformations |
| Pyogrio | Geospatial data input/output |
| GeoPackage | Multi-layer spatial data delivery |
| Streamlit | Interactive application framework |
| Folium | Interactive map visualization |
| streamlit-folium | Streamlit/Folium integration |
| Plotly | Data visualization components |
| Pytest | Automated tests |

## 5. Geospatial Data

The synthetic project data is stored in GeoPackage format using **EPSG:32748 — WGS 84 / UTM Zone 48S**.

### Reference layers

| Layer | Description |
|---|---|
| `study_area` | Synthetic project study boundary |
| `original_land_parcels` | Original synthetic cadastral parcels |
| `land_parcels` | Remaining general land after asset land allocation |
| `row_parcels` | Land allocated to pipeline ROW |
| `facility_parcels` | Land allocated to production facilities |
| `wellsite_parcels` | Land allocated to wellsites |
| `road_parcels` | Land allocated to operational access roads |
| `forest_areas` | Synthetic forest reference polygons |
| `pipelines` | Existing pipeline centerlines |
| `production_facilities` | Production facility locations |
| `existing_wells` | Existing well locations |
| `proposed_wells` | Proposed well locations |
| `roads` | Synthetic operational access road centerlines |

## 6. Screening Methodology

### 6.1 ROW Generation

The proposed pipeline centerline is reprojected to EPSG:32748. The ROW corridor is generated by buffering the centerline by half the user-defined total ROW width on each side. Flat end caps are used to avoid adding round end areas.

### 6.2 Land Acquisition Screening

The generated ROW is intersected with the original parcel layer. For each affected parcel, the workflow calculates:

- Original parcel area.
- ROW intersection area.
- Percentage of the original parcel intersected.
- Preliminary acquisition screening status.

Only the part of the parcel intersecting the proposed ROW is counted as potential ROW acquisition area; the entire parcel is not assumed to be acquired.

### 6.3 Forest Area Screening

The generated ROW is intersected with forest reference polygons. The workflow calculates the area of each forest polygon intersected and the percentage of its original area affected. Forest geometries are dissolved when calculating the total forest intersection with the ROW to avoid double-counting overlapping forest polygons in the route-level metric.

## 7. GeoPackage Export

The Alignment Designer provides a consolidated GeoPackage with four layers:

| Layer | Geometry | Description |
|---|---|---|
| `pipeline_alignment` | Line | Proposed pipeline centerline |
| `row_corridor` | Polygon | Generated proposed ROW corridor |
| `acquisition_screening` | Polygon | Parcel portions intersected by the ROW |
| `forest_screening` | Polygon | Forest portions intersected by the ROW |

The alignment can also be downloaded separately as GeoJSON in WGS 84.

## 8. Project Structure

```text
oil-gas-land-intelligence/
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── data/
│   └── synthetic/
├── scripts/
│   ├── build_asset_parcels.py
│   ├── check_data.py
│   ├── generate_data.py
│   ├── run_screening.py
│   └── spatial_analysis.py
├── src/
│   ├── __init__.py
│   ├── alignment_import.py
│   ├── analytics.py
│   ├── data_loader.py
│   ├── route_screening.py
│   └── screening.py
├── tests/
│   ├── test_alignment_import.py
│   └── test_route_screening.py
└── outputs/
    └── reports/
```

## 9. Installation and Setup

### Prerequisites

- Python 3.12 recommended.
- Git.
- Visual Studio Code recommended.

### 9.1 Clone the repository

```bash
git clone https://github.com/adnan11ananda/oil-gas-land-intelligence.git
cd oil-gas-land-intelligence
```

### 9.2 Create and activate a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 9.3 Install dependencies

```bash
pip install -r requirements-dev.txt
```

### 9.4 Run the application

```bash
streamlit run app.py
```

### 9.5 Run automated tests

```bash
pytest
```

## 10. Current Implementation Status

- [x] Synthetic cadastral and forest datasets.
- [x] Oil & Gas infrastructure reference layers.
- [x] Infrastructure-related land parcel delineation.
- [x] Parent parcel traceability.
- [x] Interactive pipeline alignment drawing.
- [x] Proposed alignment file import (GeoPackage, GeoJSON, zipped Shapefile, and KML where supported).
- [x] ROW corridor generation with configurable width.
- [x] Land acquisition spatial screening.
- [x] Forest-area overlay screening.
- [x] Dedicated Land Acquisition report page.
- [x] Dedicated Forest Area Overlay report page.
- [x] Consolidated GeoPackage export with four layers.
- [x] GeoJSON alignment export.
- [x] CSV report exports.
- [x] Automated tests for alignment import and route screening.

## 11. Known Limitations

- All datasets are synthetic and do not represent actual operating assets, cadastral boundaries, landowners, pipeline routes, or forest boundaries.
- The application uses EPSG:32748 for metric screening, which is appropriate for the demonstration dataset's geographic area; other project locations may require a different projected CRS.
- The current GeoPackage importer selects the first detected line layer. Selection among multiple line layers is not yet implemented.
- Study-area validation currently checks whether the alignment intersects the study area; partial coverage warnings are not yet implemented.
- KML support depends on the installed GDAL driver.
- Screening results are preliminary spatial calculations and must not be treated as legal land acquisition determinations, engineering design, environmental approvals, or operational instructions.

## 12. Author

**Adnan Ananda**  
Geomatics Engineer | GIS Engineer | Oil & Gas Land Management

Technical interests:
- Oil & Gas Geospatial Information Systems
- Geospatial Database Management
- Cadastral and Land Administration GIS
- Pipeline ROW Management
- Python-based GIS Automation
- WebGIS and Spatial Analytics

GitHub: [github.com/adnan11ananda](https://github.com/adnan11ananda)

---

*Developed for professional portfolio and technical demonstration purposes.*
