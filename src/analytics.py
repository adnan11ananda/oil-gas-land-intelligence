
from pathlib import Path

import geopandas as gpd
import pandas as pd


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

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

SCREENING_FILE = (
    PROJECT_ROOT
    / "outputs"
    / "reports"
    / "proposed_pipeline_screening.gpkg"
)

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "reports"

ROW_WIDTH_M = 20


# ============================================================
# 2. LOAD SCREENING RESULTS
# ============================================================

def load_screening_results():

    if not SCREENING_FILE.exists():
        raise FileNotFoundError(
            f"Screening results not found: {SCREENING_FILE}"
        )

    parcels = gpd.read_file(
        SCREENING_FILE,
        layer="acquisition_screening"
    )

    forests = gpd.read_file(
        SCREENING_FILE,
        layer="forest_screening"
    )

    print("Screening results loaded successfully.")

    return parcels, forests


# ============================================================
# 3. CALCULATE ROUTE GEOMETRY METRICS
# ============================================================

def calculate_route_metrics():

    alignment = gpd.read_file(
        ALIGNMENT_FILE,
        layer="proposed_alignment"
    )

    forests = gpd.read_file(
        DATA_FILE,
        layer="forest_areas"
    )

    if alignment.empty:
        raise ValueError("Proposed alignment is empty.")

    if alignment.crs is None or forests.crs is None:
        raise ValueError("Alignment or forest layer has no CRS.")

    # Use alignment CRS for all spatial calculations
    if forests.crs != alignment.crs:
        forests = forests.to_crs(alignment.crs)

    # Calculate ROW corridor
    geometry_types = set(alignment.geometry.geom_type)

    if geometry_types.issubset(
        {"LineString", "MultiLineString"}
    ):

        alignment_geometry = alignment.geometry.union_all()

        row_geometry = alignment_geometry.buffer(
            ROW_WIDTH_M / 2,
            cap_style="flat",
            join_style="mitre"
        )

        alignment_length_km = (
            alignment_geometry.length / 1000
        )

    else:
        raise ValueError(
            "Alignment must contain line geometries."
        )

    total_row_area_ha = row_geometry.area / 10000

    # Dissolve forest polygons to avoid double-counting
    forest_union = forests.geometry.union_all()

    forest_row_intersection = (
        row_geometry.intersection(forest_union)
    )

    forest_intersection_area_ha = (
        forest_row_intersection.area / 10000
    )

    forest_percentage = (
        forest_intersection_area_ha
        / total_row_area_ha * 100
        if total_row_area_ha > 0 else 0
    )

    # Unique centerline length within forest
    alignment_in_forest = (
        alignment_geometry.intersection(forest_union)
    )

    alignment_in_forest_km = (
        alignment_in_forest.length / 1000
    )

    return {
        "alignment_length_km": alignment_length_km,
        "total_row_area_ha": total_row_area_ha,
        "forest_intersection_area_ha": (
            forest_intersection_area_ha
        ),
        "forest_percentage": forest_percentage,
        "alignment_in_forest_km": alignment_in_forest_km
    }


# ============================================================
# 4. GENERATE CONSOLIDATED SCREENING SUMMARY
# ============================================================

def generate_route_summary():

    print("\n" + "=" * 50)
    print("CONSOLIDATED ROUTE SCREENING SUMMARY")
    print("=" * 50)

    parcel_results, forest_results = load_screening_results()

    route_metrics = calculate_route_metrics()

    # Land acquisition metrics
    affected_parcels = (
        parcel_results["parcel_id"].nunique()
    )

    acquisition_area_ha = (
        parcel_results["row_area_ha"].sum()
    )

    # Forest metrics
    affected_forest_count = (
        forest_results["forest_id"].nunique()
    )

    # Use dissolved geometry for unique forest intersection area
    forest_area_ha = (
        route_metrics["forest_intersection_area_ha"]
    )

    # Build summary table
    summary = pd.DataFrame([
        {
            "category": "Route",
            "indicator": "Pipeline alignment length",
            "value": route_metrics["alignment_length_km"],
            "unit": "km"
        },
        {
            "category": "Route",
            "indicator": "Total ROW area",
            "value": route_metrics["total_row_area_ha"],
            "unit": "ha"
        },
        {
            "category": "Land Acquisition",
            "indicator": "Affected land parcels",
            "value": affected_parcels,
            "unit": "parcels"
        },
        {
            "category": "Land Acquisition",
            "indicator": "Potential acquisition area",
            "value": acquisition_area_ha,
            "unit": "ha"
        },
        {
            "category": "Forest",
            "indicator": "Affected forest polygons",
            "value": affected_forest_count,
            "unit": "polygons"
        },
        {
            "category": "Forest",
            "indicator": "Forest intersection area",
            "value": forest_area_ha,
            "unit": "ha"
        },
        {
            "category": "Forest",
            "indicator": "ROW within forest",
            "value": route_metrics["forest_percentage"],
            "unit": "%"
        },
        {
            "category": "Forest",
            "indicator": "Pipeline alignment within forest",
            "value": route_metrics["alignment_in_forest_km"],
            "unit": "km"
        }
    ])

    # Print report
    print("\nROUTE OVERVIEW")

    print(
        f"Pipeline alignment length: "
        f"{route_metrics['alignment_length_km']:.4f} km"
    )

    print(
        f"Total ROW area: "
        f"{route_metrics['total_row_area_ha']:.4f} ha"
    )

    print("\nLAND ACQUISITION")

    print(f"Affected parcels: {affected_parcels}")

    print(
        f"Potential acquisition area: "
        f"{acquisition_area_ha:.4f} ha"
    )

    print("\nFOREST IMPACT")

    print(f"Affected forest polygons: {affected_forest_count}")

    print(
        f"Forest intersection area: "
        f"{forest_area_ha:.4f} ha"
    )

    print(
        f"ROW within forest: "
        f"{route_metrics['forest_percentage']:.2f}%"
    )

    print(
        f"Pipeline alignment within forest: "
        f"{route_metrics['alignment_in_forest_km']:.4f} km"
    )

    print("\nFULL SCREENING SUMMARY")

    print(
        summary.to_string(
            index=False,
            formatters={
                "value": lambda value: f"{value:,.4f}"
            }
        )
    )

    return summary


# ============================================================
# 5. EXPORT SUMMARY
# ============================================================

def export_summary(summary):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        OUTPUT_DIR
        / "proposed_pipeline_route_summary.csv"
    )

    summary.to_csv(
        output_file,
        index=False
    )

    print("\nSummary exported successfully:")
    print(output_file)


# ============================================================
# 6. MAIN WORKFLOW
# ============================================================

def main():

    print("\nOIL & GAS LAND INTELLIGENCE")
    print("ROUTE ANALYTICS")

    summary = generate_route_summary()

    export_summary(summary)

    print("\nRoute analytics completed.")


if __name__ == "__main__":
    main()
