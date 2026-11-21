"""
Run pipeline route screening from the command line.

Reads the proposed alignment, screens it with src.route_screening
and writes CSV and GeoPackage reports to outputs/reports/.

Usage:
    python scripts/run_screening.py
    python scripts/run_screening.py --row-width 30
"""

import argparse
import sys
from pathlib import Path

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Allow `from src...` when this file is run as a script
sys.path.insert(0, str(PROJECT_ROOT))

from src.route_screening import (  # noqa: E402
    DEFAULT_ROW_WIDTH_M,
    analyze_route,
    create_row_corridor,
    load_screening_layers,
    summary_to_table,
)


# ============================================================
# 1. PATHS
# ============================================================

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "oil_gas_land_intelligence_with_asset_parcels.gpkg"
)

ALIGNMENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "proposed_pipeline_alignment.gpkg"
)

ALIGNMENT_LAYER = "proposed_alignment"

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "reports"


# ============================================================
# 2. LOAD ALIGNMENT
# ============================================================

def load_alignment(path, layer, target_crs):

    if not path.exists():
        raise FileNotFoundError(f"Alignment not found: {path}")

    alignment = gpd.read_file(path, layer=layer)

    if alignment.empty:
        raise ValueError("Proposed alignment is empty.")

    if alignment.crs is None:
        raise ValueError("Proposed alignment has no CRS.")

    line_types = {"LineString", "MultiLineString"}

    if not set(alignment.geometry.geom_type).issubset(line_types):
        raise ValueError("Alignment must contain line geometries.")

    return alignment.to_crs(target_crs)


# ============================================================
# 3. EXPORT
# ============================================================

def export_results(results):

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    acquisition = results["acquisition"]
    forests = results["forest_intersection"]

    # Tables
    acquisition.drop(columns="geometry").round(4).to_csv(
        OUTPUT_DIR / "proposed_pipeline_acquisition.csv",
        index=False
    )

    forests.drop(columns="geometry").round(4).to_csv(
        OUTPUT_DIR / "proposed_pipeline_forest_screening.csv",
        index=False
    )

    summary_to_table(results["summary"]).to_csv(
        OUTPUT_DIR / "proposed_pipeline_route_summary.csv",
        index=False
    )

    # Spatial layers
    gpkg_file = OUTPUT_DIR / "proposed_pipeline_screening.gpkg"

    if gpkg_file.exists():
        gpkg_file.unlink()

    if not acquisition.empty:
        acquisition.to_file(
            gpkg_file,
            layer="acquisition_screening",
            driver="GPKG",
            engine="pyogrio"
        )

    if not forests.empty:
        forests.to_file(
            gpkg_file,
            layer="forest_screening",
            driver="GPKG",
            engine="pyogrio",
            mode="a"
        )

    print(f"Reports written to: {OUTPUT_DIR}")


# ============================================================
# 4. MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="Screen a proposed pipeline route."
    )

    parser.add_argument(
        "--row-width",
        type=float,
        default=DEFAULT_ROW_WIDTH_M,
        help="ROW width in metres (default: %(default)s)"
    )

    args = parser.parse_args()

    parcels, forests = load_screening_layers(DATA_FILE)

    alignment = load_alignment(
        ALIGNMENT_FILE,
        ALIGNMENT_LAYER,
        parcels.crs
    )

    row = create_row_corridor(alignment, args.row_width)

    results = analyze_route(alignment, row, parcels, forests)

    print("\nROUTE SCREENING SUMMARY")
    print("=" * 40)

    print(
        summary_to_table(results["summary"]).to_string(
            index=False,
            formatters={"value": lambda v: f"{v:,.4f}"}
        )
    )

    export_results(results)


if __name__ == "__main__":
    main()
