# Oil & Gas Land Intelligence Platform

**A Python-based WebGIS application for preliminary pipeline ROW design, land acquisition screening, and forest area overlay analysis.**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://oil-gas-pipeline-row.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-Geospatial-green)](https://geopandas.org/)
[![Shapely](https://img.shields.io/badge/Shapely-Geometry-orange)](https://shapely.readthedocs.io/)

**Live demo:** [oil-gas-pipeline-row.streamlit.app](https://oil-gas-pipeline-row.streamlit.app/)

<!--
Add screenshots to docs/screenshots/, then uncomment these lines:

![Alignment Designer](docs/screenshots/01-alignment-designer.png)
![Land Acquisition Screening](docs/screenshots/02-land-acquisition.png)
![Forest Area Overlay Report](docs/screenshots/03-forest-overlay.png)
-->

---

## 1. Project Overview

The Oil & Gas Land Intelligence Platform is a geospatial decision-support prototype. It demonstrates how Python GIS tools can support land management and preliminary route screening for oil and gas infrastructure.

Users draw or import a proposed pipeline alignment, generate a Right-of-Way (ROW) corridor, and identify the land parcels and forest areas the corridor crosses. Results are shown on an interactive map, in tables, and as downloadable GIS and CSV outputs.

The project uses **synthetic data** for a fictional operating area. It is a portfolio project, not a tool for real land acquisition decisions.

## 2. Business Context

Pipelines, facilities, wells, and access roads all need land access. Land teams need reliable answers to questions such as:

- Which land parcels does a proposed pipeline route cross?
- How much land is already acquired, and how much still needs to be secured?
- How much of the route runs through forest areas?
- Who owns the affected parcels?

This project automates those preliminary checks so alternative routes can be compared quickly.

## 3. Application Features

The Streamlit app has four modules.

| Module | Purpose |
|---|---|
| **Overview** | Application workflow, reference layers, and data disclaimer. |
| **Alignment Designer** | Draw or import an alignment, set the ROW width, and run the screening. |
| **Land Acquisition** | Affected parcels map, parcel table, and CSV report. |
| **Forest Area Overlay Report** | Affected forest map, forest table, and CSV report. |

### 3.1 Alignment Designer

- Choose the alignment source: **draw** a polyline on the map, or **import** a file.
- Set the ROW width (1 to 100 m, default 20 m).
- Review route metrics: pipeline length, ROW area, acquired ROW, potential acquisition area, affected forest polygons, forest intersection area, share of ROW within forest.
- Download the results:

| Download | Content |
|---|---|
| GeoPackage | Layers `pipeline_alignment`, `row_corridor`, `acquisition_screening`, `forest_screening`. |
| GeoJSON | Pipeline centerline. |
| Preliminary report (CSV) | Route, land acquisition, forest, and ownership indicators. |

### 3.2 Alignment Import

| Format | Notes |
|---|---|
| GeoJSON (`.geojson`, `.json`) | Reprojected to WGS 84 for display. |
| GeoPackage (`.gpkg`) | The first layer containing line features is used. |
| Zipped Shapefile (`.zip`) | Zip the `.shp`, `.shx`, `.dbf`, and `.prj` files together. |
| KML (`.kml`) | Requires a GDAL build with the KML driver. |

Import checks:

- The alignment must be one continuous polyline. Connected segments are merged.
- Files without a coordinate reference system are rejected unless a CRS is chosen in the app.
- Elevation (Z) values are dropped, and non-line features are ignored.
- Alignments outside the study area are rejected, which usually means a wrong CRS.

A sample file is included: `data/synthetic/proposed_pipeline_alignment.gpkg` (layer `proposed_alignment`).

### 3.3 Screening Method

- The ROW is created by buffering the centerline with flat ends and mitred joins, giving a constant-width corridor.
- Parcels are screened against the **original cadastral parcels**, so affected percentages are relative to the whole parcel.
- Forest polygons are dissolved before totals are calculated, so overlapping forests are counted once.
- All areas and lengths are calculated in EPSG:32748 (metres).

**Acquisition status rule**

| Land status | Acquisition status |
|---|---|
| `Acquired` | Already Acquired |
| `Leased`, `Pending Acquisition`, `Unregistered` | Potential Acquisition |

**Potential acquisition area** = total ROW area minus the ROW area over already acquired land. It is a geometric indicator, not a legal or compensable acquisition area.

## 4. Technology Stack

| Technology | Application |
|---|---|
| Python 3.12 | Core language |
| Streamlit | Web application framework |
| Folium / streamlit-folium | Interactive map and drawing tools |
| GeoPandas | Geospatial data processing and overlay analysis |
| Shapely | Geometry operations |
| Pandas / NumPy | Tabular data and synthetic data generation |
| Pyogrio | Geospatial file input and output |
| GeoPackage | Spatial database format |
| pytest | Automated tests |

## 5. Geospatial Database

The reference data is stored in GeoPackage format.

**Coordinate Reference System:** EPSG:32748 – WGS 84 / UTM Zone 48S.

### 5.1 Infrastructure Layers

| Layer | Description |
|---|---|
| `pipelines` | Existing pipeline centerlines. |
| `production_facilities` | Production facility locations. |
| `existing_wells` | Existing well locations. |
| `roads` | Access road centerlines. |
| `forest_areas` | Synthetic forest constraint polygons. |
| `proposed_wells` | Proposed well locations. |
| `study_area` | Project analysis boundary. |

### 5.2 Land Management Layers

| Layer | Description |
|---|---|
| `original_land_parcels` | Original synthetic cadastral parcels (used for screening). |
| `land_parcels` | Remaining general land after infrastructure allocation. |
| `row_parcels` | Land allocated to pipeline ROW corridors. |
| `facility_parcels` | Land occupied by production facilities. |
| `wellsite_parcels` | Land allocated to wellsites. |
| `road_parcels` | Land allocated to access roads. |

### 5.3 Parcel Subdivision Methodology

Infrastructure land is delineated from the original parcels:

1. Buffer pipeline centerlines into ROW corridors.
2. Create facility and wellsite footprints.
3. Buffer road centerlines into road ROW corridors.
4. Intersect the footprints with the original parcels.
5. Use polygon difference to separate allocated land from remaining general land.

Each asset parcel keeps a `parent_parcel_id` that links it to its original parcel. After processing, land area accounting is validated: remaining land plus all asset parcels must equal the original parcel area.

### 5.4 Synthetic Asset Dimensions

| Asset | Assumed dimensions |
|---|---|
| Pipeline ROW | 20 m total width |
| Main access road | 10 m width |
| Well access road | 5 m width |
| Production facility footprint | 100 × 100 m |
| Wellsite footprint | 40 × 40 m |

These are configurable demonstration assumptions, not engineering or cadastral standards.

## 6. Project Structure

```text
oil-gas-land-intelligence/
│
├── app.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── README.md
│
├── data/
│   └── synthetic/
│       ├── oil_gas_land_intelligence.gpkg
│       ├── oil_gas_land_intelligence_with_asset_parcels.gpkg
│       └── proposed_pipeline_alignment.gpkg
│
├── scripts/
│   ├── generate_data.py
│   ├── build_asset_parcels.py
│   ├── check_data.py
│   └── run_screening.py
│
├── src/
│   ├── __init__.py
│   ├── route_screening.py
│   └── alignment_import.py
│
├── tests/
│   ├── test_route_screening.py
│   └── test_alignment_import.py
│
├── docs/
│   └── screenshots/
│
└── outputs/
    └── reports/
```

- `src/route_screening.py` is the single analysis core, used by both the app and the command-line script.
- `src/alignment_import.py` reads and validates uploaded alignment files.

## 7. Installation and Setup

### Prerequisites

- Python 3.12
- Git

### 7.1 Clone and Install

```bash
git clone https://github.com/adnan11ananda/oil-gas-land-intelligence.git
cd oil-gas-land-intelligence

python -m venv .venv
```

Activate the environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 7.2 Run the Application

The synthetic GeoPackages are included in the repository:

```bash
streamlit run app.py
```

### 7.3 Run the Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover alignment import and route screening, using geometries with hand-checkable results (for example, a 1 km line with a 20 m ROW gives exactly 2.0 ha).

### 7.4 Run Route Screening from the Command Line

```bash
python scripts/run_screening.py
python scripts/run_screening.py --row-width 30
```

Reports are written to `outputs/reports/`.

### 7.5 Regenerate the Synthetic Data (Optional)

```bash
python scripts/generate_data.py
python scripts/build_asset_parcels.py
python scripts/check_data.py
```

## 8. Development Roadmap

- [ ] Status-specific acquisition actions for leased, pending, and unregistered land.
- [ ] Forest-type rules (for example, protected versus production forest).
- [ ] Screening of proposed well locations.
- [ ] Screening of crossings with existing pipelines, roads, and facilities.

## 9. Limitations and Disclaimer

This project is an independent technical portfolio and demonstration.

- All datasets are synthetic and do not represent real operational assets, pipeline alignments, facilities, cadastral boundaries, or land ownership records.
- Screening results are preliminary spatial indicators that use assumed ROW dimensions.
- Land acquisition results are not legal ownership verification or formal land valuation.
- Forest overlay results do not replace a formal environmental assessment.
- Outputs must not be used for actual land acquisition, engineering design, or operational decisions.

## 10. Author

**Adnan Ananda**

Geomatics Engineer | GIS Engineer | Oil & Gas Land Management

**GitHub:** [github.com/adnan11ananda](https://github.com/adnan11ananda)

---

*Developed as a personal GIS portfolio project to demonstrate geospatial technology in oil and gas land management and infrastructure planning.*
