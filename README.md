# Oil & Gas Land Intelligence Platform

**A Python-based geospatial platform for Oil & Gas land management, infrastructure mapping, and spatial analysis.**

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://www.python.org/)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-Geospatial-green)](https://geopandas.org/)
[![Shapely](https://img.shields.io/badge/Shapely-Geometry-orange)](https://shapely.readthedocs.io/)
[![Streamlit](https://img.shields.io/badge/Streamlit-WebGIS-red?logo=streamlit)](https://streamlit.io/)

---

## 1. Project Overview

The **Oil & Gas Land Intelligence Platform** is a geospatial project designed to support land management activities in upstream oil and gas operations.

The project integrates cadastral land parcels with existing oil and gas infrastructure, including:

- Pipeline networks and Right-of-Way (ROW) corridors.
- Production facilities.
- Existing oil and gas wells.
- Operational access roads.
- Land ownership and acquisition records.
- Environmental constraint areas.

The platform demonstrates how Python-based geospatial technologies can automate land parcel processing, manage infrastructure-related land requirements, and establish spatial relationships between operational assets and land records.

The project uses synthetic geospatial datasets representing a fictional oil and gas operating area.

## 2. Business Context

Land management is a critical component of upstream oil and gas operations.

Pipelines, production facilities, wells, and access roads require land access and operational rights. Managing these assets requires reliable geospatial information and traceable relationships between infrastructure and land ownership records.

This project addresses several common land management challenges:

- Identifying land parcels affected by pipeline ROW corridors.
- Managing land occupied by production facilities and wellsites.
- Identifying land requirements for operational access roads.
- Linking infrastructure assets to their corresponding land parcels.
- Maintaining traceability between subdivided parcels and original land records.
- Supporting land acquisition monitoring and spatial decision-making.

## 3. Project Objectives

The project aims to:

1. Develop a structured geospatial database for oil and gas infrastructure and land assets.
2. Generate synthetic cadastral land parcel datasets.
3. Integrate pipeline, facility, well, and road infrastructure.
4. Automate infrastructure-related land parcel delineation using spatial operations.
5. Maintain relationships between asset parcels and their original parent parcels.
6. Develop Python-based spatial screening and land analysis workflows.
7. Provide a foundation for an interactive WebGIS land management application.

## 4. Technology Stack

| Technology | Application |
|---|---|
| Python 3.12 | Core programming language |
| GeoPandas | Geospatial data management and analysis |
| Shapely | Geometry processing and spatial operations |
| Pandas | Tabular data processing |
| NumPy | Numerical operations and synthetic data generation |
| Pyogrio | Geospatial data input and output |
| GeoPackage | Spatial database format |
| Streamlit | Interactive application framework |
| Folium | Interactive map visualization |
| Plotly | Data visualization and dashboards |

## 5. Geospatial Database

The project uses GeoPackage as its primary geospatial data format.

**Coordinate Reference System:** EPSG:32748 – WGS 84 / UTM Zone 48S.

### 5.1 Infrastructure Data

| Layer | Description |
|---|---|
| `pipelines` | Pipeline centerline geometries and attributes. |
| `production_facilities` | Existing production facility locations. |
| `existing_wells` | Existing oil and gas well locations. |
| `roads` | Operational access road centerlines. |
| `forest_areas` | Synthetic forest constraint polygons. |
| `proposed_wells` | Proposed development well locations. |

### 5.2 Land Management Data

| Layer | Description |
|---|---|
| `original_land_parcels` | Original synthetic cadastral land parcels. |
| `land_parcels` | Remaining general land after infrastructure land allocation. |
| `row_parcels` | Land allocated to pipeline ROW corridors. |
| `facility_parcels` | Land occupied by production facilities. |
| `wellsite_parcels` | Land allocated to existing wellsites. |
| `road_parcels` | Land allocated to operational access roads. |

### 5.3 Parcel Subdivision Methodology

Infrastructure-related land requirements are delineated from the original cadastral parcel dataset.

The processing workflow consists of:

1. Generating pipeline ROW corridors through buffering of pipeline centerlines.
2. Creating facility footprints around production facility locations.
3. Creating wellsite footprints around existing well locations.
4. Generating road ROW corridors from operational road centerlines.
5. Intersecting infrastructure footprints with original land parcels.
6. Applying polygon difference operations to separate allocated land from remaining general land.

Each resulting asset parcel retains a reference to its original land parcel through the `parent_parcel_id` attribute.

This approach maintains traceability between infrastructure-related land areas and their original parent parcels.

## 6. Infrastructure Network Development

### 6.1 Pipeline Network

Pipeline centerlines are used to generate ROW corridors through configurable buffer operations.

The resulting ROW polygons are intersected with cadastral land parcels to identify the individual land sections occupied by pipeline infrastructure.

### 6.2 Production Facilities and Wells

Production facility and wellsite footprints are generated around existing infrastructure locations.

Each footprint is intersected with the original cadastral parcel boundaries to identify the corresponding land sections.

### 6.3 Access Road Network

A synthetic access road network is generated to connect production facilities and existing wells.

The current implementation uses:

- A Minimum Spanning Tree (MST) approach to connect production facilities.
- Nearest-facility analysis to connect existing wells to production facilities.
- Geometric route generation for conceptual access road alignments.
- Buffer operations to generate road ROW polygons.

### 6.4 Synthetic Asset Dimensions

| Asset | Assumed dimensions |
|---|---|
| Pipeline ROW | 20 m total width |
| Main access road | 10 m width |
| Well access road | 5 m width |
| Production facility footprint | 100 × 100 m |
| Wellsite footprint | 40 × 40 m |

These dimensions are configurable demonstration assumptions, not actual engineering or cadastral standards.

## 7. Current Implementation

The current development includes:

- [x] Synthetic cadastral parcel generation using Voronoi subdivision.
- [x] Synthetic forest polygon generation.
- [x] Existing well and production facility datasets.
- [x] Pipeline network generation.
- [x] Pipeline ROW parcel delineation.
- [x] Production facility parcel delineation.
- [x] Wellsite parcel delineation.
- [x] Access road network generation.
- [x] Road ROW parcel delineation.
- [x] Parent parcel identification.
- [x] Automated parcel subdivision.
- [x] Geometry validity and land area accounting validation.

## 8. Project Structure

```text
oil-gas-land-intelligence/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   └── synthetic/
│       ├── oil_gas_land_intelligence.gpkg
│       └── oil_gas_land_intelligence_with_asset_parcels.gpkg
│
├── scripts/
│   ├── generate_data.py
│   ├── build_asset_parcels.py
│   ├── check_data.py
│   └── spatial_analysis.py
│
├── src/
│   ├── __init__.py
│   ├── analytics.py
│   ├── data_loader.py
│   └── screening.py
│
└── outputs/
```

## 9. Installation and Setup

### Prerequisites

- Python 3.12
- Git
- Visual Studio Code (recommended)

### 9.1 Clone the Repository

```bash
git clone https://github.com/adnan11ananda/oil-gas-land-intelligence.git

cd oil-gas-land-intelligence
```

### 9.2 Create a Virtual Environment

```bash
python -m venv .venv
```

Activate the environment on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 9.3 Install Dependencies

```bash
pip install -r requirements.txt
```

### 9.4 Generate Synthetic Datasets

```bash
python scripts/generate_data.py
```

### 9.5 Generate Infrastructure-Related Land Parcels

```bash
python scripts/build_asset_parcels.py
```

The generated GeoPackage datasets are saved in:

```text
data/synthetic/
```

## 10. Development Roadmap

The following features are planned for future development:

- [ ] Automated pipeline ROW land impact analysis.
- [ ] Land acquisition status monitoring.
- [ ] Infrastructure-to-land parcel relationship analysis.
- [ ] Identification of land parcels affected by proposed well locations.
- [ ] Spatial conflict screening against forest areas.
- [ ] Land area calculation and acquisition dashboard.
- [ ] Interactive Streamlit WebGIS application.
- [ ] Cloud deployment.

## 11. Project Limitations

This project is independently developed as a technical portfolio and geospatial technology demonstration.

All datasets are synthetically generated and do not represent actual operational assets, pipeline alignments, facilities, cadastral boundaries, or land ownership records.

Generated road alignments and infrastructure footprints are conceptual geometries rather than engineering designs or legally verified cadastral boundaries.

The project demonstrates geospatial data management and spatial processing concepts. Its outputs should not be used for actual land acquisition, engineering design, or operational decision-making.

## 12. Author

**Adnan Ananda**

Geomatics Engineer | GIS Engineer | Oil & Gas Land Management

**Technical Interests**

- Oil & Gas Geospatial Information Systems
- Geospatial Database Management
- Cadastral and Land Administration GIS
- Pipeline ROW Management
- Python-based GIS Automation
- WebGIS and Spatial Analytics

**GitHub:** [github.com/adnan11ananda](https://github.com/adnan11ananda)

---

*Developed for professional portfolio and technical demonstration purposes.*