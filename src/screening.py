
from pathlib import Path

import geopandas as gpd
import pandas as pd


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "oil_gas_land_intelligence_with_asset_parcels.gpkg"
)

PROPOSED_ALIGNMENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "proposed_pipeline_alignment.gpkg"
)

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "reports"

PARCEL_LAYER = "original_land_parcels"
ALIGNMENT_LAYER = "proposed_alignment"

ROW_WIDTH_M = 20


# ============================================================
# 1. LOAD ORIGINAL LAND PARCELS
# ============================================================

def load_parcels():

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Land parcel dataset not found: {DATA_FILE}"
        )

    parcels = gpd.read_file(
        DATA_FILE,
        layer=PARCEL_LAYER
    )

    required_fields = [
        "parcel_id",
        "owner_type",
        "geometry"
    ]

    missing_fields = [
        field for field in required_fields
        if field not in parcels.columns
    ]

    if missing_fields:
        raise ValueError(
            f"Missing parcel fields: {missing_fields}"
        )

    if parcels.crs is None:
        raise ValueError("Parcel dataset has no CRS.")

    if not parcels.geometry.is_valid.all():
        raise ValueError(
            "Invalid parcel geometries detected."
        )

    if not parcels["parcel_id"].is_unique:
        raise ValueError(
            "Parcel IDs must be unique."
        )

    # Calculate original parcel area
    parcels["parcel_area_ha"] = (
        parcels.geometry.area / 10000
    )

    # Our synthetic case study assumes all parcels
    # have not yet been acquired.
    parcels["land_status"] = "Not Acquired"

    print("Original land parcels loaded successfully.")
    print(f"Number of parcels: {len(parcels)}")
    print(f"CRS: {parcels.crs}")

    return parcels


# ============================================================
# 2. LOAD PROPOSED PIPELINE ALIGNMENT
# ============================================================

def load_proposed_alignment():

    if not PROPOSED_ALIGNMENT_FILE.exists():
        raise FileNotFoundError(
            "Proposed pipeline alignment not found: "
            f"{PROPOSED_ALIGNMENT_FILE}"
        )

    alignment = gpd.read_file(
        PROPOSED_ALIGNMENT_FILE,
        layer=ALIGNMENT_LAYER
    )

    if alignment.empty:
        raise ValueError(
            "Proposed pipeline alignment is empty."
        )

    if alignment.crs is None:
        raise ValueError(
            "Proposed alignment has no CRS."
        )

    if not alignment.geometry.is_valid.all():
        raise ValueError(
            "Invalid alignment geometries detected."
        )

    allowed_types = {"LineString", "MultiLineString"}

    if not set(alignment.geometry.geom_type).issubset(
        allowed_types
    ):
        raise ValueError(
            "Alignment must contain LineString or MultiLineString."
        )

    print("\nProposed pipeline alignment loaded successfully.")
    print(f"Number of features: {len(alignment)}")

    return alignment


# ============================================================
# 3. PERFORM PIPELINE ROW ACQUISITION SCREENING
# ============================================================

def screen_pipeline_row(
    parcels,
    alignment,
    row_width_m=ROW_WIDTH_M
):

    print("\n" + "=" * 45)
    print("PROPOSED PIPELINE ROW SCREENING")
    print("=" * 45)

    if row_width_m <= 0:
        raise ValueError(
            "ROW width must be greater than zero."
        )

    # Reproject alignment to parcel CRS
    if alignment.crs != parcels.crs:
        alignment = alignment.to_crs(parcels.crs)

    # Dissolve all alignment features into one geometry
    alignment_geometry = alignment.geometry.union_all()

    # Buffer centerline by half of the total ROW width
    row_corridor = alignment_geometry.buffer(
        row_width_m / 2,
        cap_style="flat",
        join_style="mitre"
    )

    # Create ROW corridor GeoDataFrame
    corridor = gpd.GeoDataFrame(
        {"corridor_id": [1]},
        geometry=[row_corridor],
        crs=parcels.crs
    )

    # Spatial intersection between ROW corridor and parcels
    affected = gpd.overlay(
        parcels,
        corridor,
        how="intersection",
        keep_geom_type=False
    )

    if affected.empty:
        print("No land parcels intersect the proposed ROW.")
        return affected

    # Calculate potential acquisition area
    affected["row_area_ha"] = (
        affected.geometry.area / 10000
    )

    # Calculate percentage of original parcel affected
    affected["affected_percentage"] = (
        affected["row_area_ha"]
        / affected["parcel_area_ha"]
        * 100
    )

    # Acquisition classification
    affected["land_status"] = "Not Acquired"

    affected["acquisition_status"] = "Not Acquired"

    affected["acquisition_action"] = (
        "Acquisition required"
    )

    # Keep relevant output attributes
    output_fields = [
        "parcel_id",
        "owner_type",
        "land_status",
        "parcel_area_ha",
        "row_area_ha",
        "affected_percentage",
        "acquisition_status",
        "acquisition_action",
        "geometry"
    ]

    results = affected[output_fields].copy()

    # Sort by potential acquisition area
    results = results.sort_values(
        by="row_area_ha",
        ascending=False
    )

    # Summary statistics
    total_affected_parcels = results["parcel_id"].nunique()

    total_acquisition_area = results["row_area_ha"].sum()

    print(f"ROW width: {row_width_m} m")
    print(
        f"Affected parcels: {total_affected_parcels}"
    )

    print(
        "Parcels requiring acquisition: "
        f"{total_affected_parcels}"
    )

    print(
        "Total potential acquisition area: "
        f"{total_acquisition_area:.4f} ha"
    )

    print("\nAcquisition requirements:")

    print(
        results[
            [
                "parcel_id",
                "owner_type",
                "parcel_area_ha",
                "row_area_ha",
                "affected_percentage",
                "acquisition_action"
            ]
        ].to_string(index=False)
    )

    return results


# ============================================================
# 4. EXPORT SCREENING RESULTS
# ============================================================

def export_screening_results(results):

    if results.empty:
        print(
            "\nNo screening results to export."
        )
        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    csv_output = (
        OUTPUT_DIR
        / "proposed_pipeline_acquisition.csv"
    )

    gpkg_output = (
        OUTPUT_DIR
        / "proposed_pipeline_acquisition.gpkg"
    )

    # Export CSV without geometry
    results.drop(
        columns="geometry"
    ).to_csv(
        csv_output,
        index=False
    )

    # Export spatial results
    if gpkg_output.exists():
        gpkg_output.unlink()

    results.to_file(
        gpkg_output,
        layer="acquisition_screening",
        driver="GPKG"
    )

    print("\nScreening results exported:")
    print(csv_output)
    print(gpkg_output)


# ============================================================
# 5. MAIN WORKFLOW
# ============================================================

def main():

    print("\nOIL & GAS LAND INTELLIGENCE")
    print("PROPOSED PIPELINE ACQUISITION SCREENING")

    parcels = load_parcels()

    alignment = load_proposed_alignment()

    results = screen_pipeline_row(
        parcels=parcels,
        alignment=alignment,
        row_width_m=ROW_WIDTH_M
    )

    export_screening_results(results)

    print("\nScreening process completed.")


if __name__ == "__main__":
    main()
