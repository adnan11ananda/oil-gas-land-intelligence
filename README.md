# Oil & Gas Land Intelligence Platform

**A Python-based WebGIS application for preliminary pipeline ROW design, land acquisition screening, and environmental overlay analysis.**

## Overview

The Oil & Gas Land Intelligence Platform is a geospatial decision-support prototype designed to demonstrate how GIS technologies can support land management and preliminary spatial screening for Oil & Gas infrastructure projects.

The application allows users to draw or import proposed pipeline alignments, generate Right of Way (ROW) corridors, and identify potentially affected land parcels and forest areas through automated spatial analysis.

The platform combines Python geospatial libraries with an interactive Streamlit interface to make spatial screening results accessible and easier to review.

## Key Features

### 1. Overview Dashboard
- Displays the latest pipeline screening results.
- Presents key performance indicators (KPIs), including pipeline length, ROW area, affected parcels, potential acquisition area, and forest intersection.
- Summarizes land acquisition and environmental screening results.
- Provides an overview of application workflows and reference datasets.

### 2. Pipeline Alignment Designer
- Draw a proposed pipeline alignment directly on an interactive map.
- Import an existing alignment from:
  - GeoJSON
  - GeoPackage
  - Zipped Shapefile
  - KML
- Configure the required ROW width.
- Generate a ROW corridor using spatial buffering.
- Validate alignment geometry and coordinate reference systems.
- Check whether the proposed alignment intersects the project study area.

### 3. Land Acquisition Screening
- Identify land parcels intersected by the proposed ROW.
- Calculate the area of each parcel intersecting the ROW.
- Estimate potential land acquisition areas.
- Review affected parcel and ownership information.
- Export screening results for further review.

### 4. Environmental Screening
- Identify forest areas intersected by the proposed ROW.
- Calculate forest intersection areas.
- Evaluate the percentage of the ROW located within forest areas.
- Estimate pipeline alignment length within forest areas.
- Export environmental screening results.

### 5. GIS Data Export
- Export pipeline alignment and ROW spatial data.
- Export acquisition and environmental screening layers.
- Generate GeoPackage and GeoJSON outputs.
- Download preliminary screening reports in CSV format.

## Application Workflow

The application follows this general workflow:

1. **Define Pipeline Alignment** — Draw a new pipeline route or import an existing alignment.
2. **Configure ROW** — Specify the required ROW width.
3. **Generate ROW Corridor** — Create a polygon corridor using the pipeline centerline.
4. **Perform Land Acquisition Screening** — Intersect the ROW with land parcel boundaries.
5. **Perform Environmental Screening** — Identify forest areas intersecting the ROW.
6. **Review and Export Results** — Review summary metrics, detailed reports, and spatial outputs.

## Technology Stack

| Category | Technology |
|---|---|
| Programming Language | Python |
| WebGIS Framework | Streamlit |
| Interactive Mapping | Folium |
| Geospatial Data Processing | GeoPandas |
| Geometry Operations | Shapely |
| Data Analysis | Pandas |
| Spatial Data Format | GeoPackage, GeoJSON, Shapefile, KML |
| Coordinate Reference System | EPSG:32748, EPSG:4326 |

## Reference Datasets

The application uses a synthetic geospatial dataset containing:

| Dataset | Description |
|---|---|
| Study Area | Project analysis boundary |
| Land Parcels | Synthetic cadastral parcel boundaries |
| Forest Areas | Environmental reference polygons |
| Existing Pipelines | Existing pipeline network |
| Production Facilities | Oil & Gas production facilities |
| Existing Wells | Existing well locations |
| Proposed Wells | Proposed well locations |
| Roads | Synthetic access road network |
| ROW Parcels | Pipeline ROW footprint |
| Facility Parcels | Production facility land footprints |
| Wellsite Parcels | Wellsite land footprints |
| Road Parcels | Road land footprints |

The reference dataset is stored in GeoPackage format.

## Coordinate Reference System

The primary spatial analysis uses:

- **EPSG:32748** — WGS 84 / UTM Zone 48S

This projected coordinate system supports metric-based spatial calculations, including distance, buffering, and area measurement.

Imported alignments are transformed to the appropriate coordinate system for analysis and map display.

## Project Structure

```text
oil-gas-land-intelligence/
│
├── app.py
├── requirements.txt
├── README.md
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── synthetic/
│
├── scripts/
│   ├── generate_data.py
│   ├── spatial_analysis.py
│   └── build_asset_parcels.py
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py
│   ├── screening.py
│   ├── analytics.py
│   ├── route_screening.py
│   └── alignment_import.py
│
└── outputs/
    ├── maps/
    └── reports/
```

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/adnan11ananda/oil-gas-land-intelligence.git
cd oil-gas-land-intelligence
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
streamlit run app.py
```

The application will open in your default browser.

## Analytical Methodology

The platform applies standard vector-based GIS operations:

- **Buffering:** Generates a ROW corridor around the proposed pipeline centerline.
- **Intersection:** Identifies land parcels and forest polygons intersecting the ROW.
- **Area Calculation:** Calculates the spatial area of affected land and forest intersections.
- **Length Calculation:** Measures pipeline alignment length and the portion intersecting forest areas.
- **Coordinate Transformation:** Uses projected coordinates for metric calculations and geographic coordinates for web mapping.

Potential acquisition area represents the geometric portion of land parcels intersecting the proposed ROW. It should not be interpreted as an approved or legally compensable acquisition area.

## Limitations and Disclaimer

This project is a portfolio demonstration and uses synthetic geospatial data.

- Spatial datasets are illustrative and do not represent actual operational assets or cadastral records.
- Screening results are preliminary spatial indicators.
- Land acquisition results do not constitute legal ownership verification or formal land valuation.
- Environmental screening does not replace a formal environmental assessment.
- Pipeline alignments and ROW widths must be validated against applicable engineering, regulatory, and project requirements before real-world use.

## Project Objective

This project demonstrates practical capabilities in:

- Geospatial data management.
- Python-based GIS automation.
- Spatial analysis and overlay operations.
- Pipeline ROW and land acquisition screening.
- Environmental constraint screening.
- Interactive WebGIS application development.
- Geospatial reporting and data export.

**Developed as a personal GIS portfolio project to demonstrate the application of geospatial technologies in Oil & Gas land management and infrastructure planning.**