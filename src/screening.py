
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

PROPOSED_ALIGNMENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "proposed_pipeline_alignment.gpkg"
)

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "reports"

PARCEL_LAYER = "original_land_parcels"
FOREST_LAYER = "forest_areas"
ALIGNMENT_LAYER = "proposed_alignment"

ROW_WIDTH_M = 20


# ============================================================
# 2. LOAD DATA
# ============================================================

def load_data():
    """
    Load original cadastral parcels and forest areas.
    """

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"GeoPackage not found: {DATA_FILE}"
        )

    parcels = gpd.read_file(
        DATA_FILE,
        layer=PARCEL_LAYER
    )

    forests = gpd.read_file(
        DATA_FILE,
        layer=FOREST_LAYER
    )

    if parcels.empty:
        raise ValueError("Original land parcels layer is empty.")

    if forests.empty:
        raise ValueError("Forest areas layer is empty.")

    if parcels.crs is None or forests.crs is None:
        raise ValueError("A source layer has no CRS.")

    required_parcel_fields = [
        "parcel_id",
        "owner_type"
    ]

    required_forest_fields = [
        "forest_id",
        "forest_type",
        "area_ha"
    ]

    for field in required_parcel_fields:
        if field not in parcels.columns:
            raise ValueError(
                f"Missing parcel field: {field}"
            )

    for field in required_forest_fields:
        if field not in forests.columns:
            raise ValueError(
                f"Missing forest field: {field}"
            )

    if not parcels.geometry.is_valid.all():
        raise ValueError("Invalid parcel geometries detected.")

    if not forests.geometry.is_valid.all():
        raise ValueError("Invalid forest geometries detected.")

    if not parcels["parcel_id"].is_unique:
        raise ValueError("Parcel IDs must be unique.")

    if not forests["forest_id"].is_unique:
        raise ValueError("Forest IDs must be unique.")

    # Our synthetic case study assumes all original parcels
    # have not yet been acquired.
    parcels["land_status"] = "Not Acquired"

    # Recalculate parcel area from geometry
    parcels["parcel_area_ha"] = (
        parcels.geometry.area / 10000
    )

    print("Land parcels loaded successfully.")
    print(f"Number of parcels: {len(parcels)}")

    print("\nForest areas loaded successfully.")
    print(f"Number of forest polygons: {len(forests)}")

    print(f"\nCoordinate Reference System: {parcels.crs}")

    return parcels, forests


def load_proposed_alignment():
    """
    Load proposed pipeline alignment.
    """

    if not PROPOSED_ALIGNMENT_FILE.exists():
        raise FileNotFoundError(
            f"Alignment not found: {PROPOSED_ALIGNMENT_FILE}"
        )

    alignment = gpd.read_file(
        PROPOSED_ALIGNMENT_FILE,
        layer=ALIGNMENT_LAYER
    )

    if alignment.empty:
        raise ValueError("Proposed alignment is empty.")

    if alignment.crs is None:
        raise ValueError("Alignment has no CRS.")

    allowed_types = {
        "LineString",
        "MultiLineString",
        "Polygon",
        "MultiPolygon"
    }

    geometry_types = set(
        alignment.geometry.geom_type.dropna()
    )

    if not geometry_types.issubset(allowed_types):
        raise ValueError("Unsupported alignment geometry.")

    print("\nProposed alignment loaded successfully.")
    print(f"Number of features: {len(alignment)}")

    return alignment


# ============================================================
# 3. GENERATE PROPOSED ROW CORRIDOR
# ============================================================

def create_row_corridor(alignment, row_width_m=ROW_WIDTH_M):
    """
    Generate ROW corridor from centerline or use an existing
    ROW polygon.
    """

    if row_width_m <= 0:
        raise ValueError("ROW width must be greater than zero.")

    geometry_types = set(
        alignment.geometry.geom_type.dropna()
    )

    line_types = {
        "LineString",
        "MultiLineString"
    }

    polygon_types = {
        "Polygon",
        "MultiPolygon"
    }

    if geometry_types.issubset(line_types):

        row_geometry = alignment.geometry.buffer(
            row_width_m / 2,
            cap_style="flat",
            join_style="mitre"
        ).union_all()

    elif geometry_types.issubset(polygon_types):

        row_geometry = alignment.geometry.union_all()

    else:
        raise ValueError(
            "Input must contain line or polygon geometries."
        )

    if row_geometry.is_empty:
        raise ValueError("Generated ROW corridor is empty.")

    return row_geometry


# ============================================================
# 4. LAND ACQUISITION SCREENING
# ============================================================

def screen_pipeline_row(
    parcels,
    row_geometry
):
    """
    Identify parcels intersecting proposed pipeline ROW.

    All affected parcels are classified as requiring acquisition.
    Only the ROW intersection area is considered.
    """

    print("\n" + "=" * 45)
    print("LAND ACQUISITION SCREENING")
    print("=" * 45)

    results = []

    for _, parcel in parcels.iterrows():

        intersection = parcel.geometry.intersection(
            row_geometry
        )

        if intersection.is_empty:
            continue

        if intersection.area <= 0:
            continue

        parcel_area = parcel.geometry.area
        row_area = intersection.area

        if parcel_area <= 0:
            continue

        affected_percentage = (
            row_area / parcel_area
        ) * 100

        results.append({

            "parcel_id": parcel["parcel_id"],

            "owner_type": parcel["owner_type"],

            "land_status": "Not Acquired",

            "parcel_area_ha": parcel_area / 10000,

            "row_area_ha": row_area / 10000,

            "affected_percentage": affected_percentage,

            "acquisition_status": "Not Acquired",

            "acquisition_action": "Acquisition required",

            "geometry": intersection

        })

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

    result = gpd.GeoDataFrame(
        results,
        columns=output_fields,
        geometry="geometry",
        crs=parcels.crs
    )

    if result.empty:
        print("No parcels intersect the proposed ROW.")
        return result

    # Round calculated values
    result["parcel_area_ha"] = (
        result["parcel_area_ha"].round(4)
    )

    result["row_area_ha"] = (
        result["row_area_ha"].round(4)
    )

    result["affected_percentage"] = (
        result["affected_percentage"].round(2)
    )

    result = result.sort_values(
        "row_area_ha",
        ascending=False
    )

    print(f"Affected parcels: {len(result)}")

    print(
        "Parcels requiring acquisition: "
        f"{len(result)}"
    )

    print(
        "Total potential acquisition area: "
        f"{result['row_area_ha'].sum():.4f} ha"
    )

    print("\nAcquisition requirements:")

    print(
        result[
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

    return result



# ============================================================
# 5. DETAILED FOREST IMPACT ASSESSMENT
# ============================================================

def screen_forest_areas(
    forests,
    alignment,
    row_geometry
):
    """
    Assess the impact of proposed pipeline ROW on each
    intersected forest polygon.

    Calculates:
    - Original forest area
    - ROW intersection area
    - Percentage of forest polygon affected
    - Pipeline centerline length within each forest polygon
    """

    print("\n" + "=" * 45)
    print("DETAILED FOREST IMPACT ASSESSMENT")
    print("=" * 45)

    # Reproject forest polygons to alignment CRS
    if forests.crs != alignment.crs:
        forests = forests.to_crs(alignment.crs)

    # Combine pipeline centerline features
    line_types = {"LineString", "MultiLineString"}

    if set(alignment.geometry.geom_type).issubset(line_types):
        alignment_geometry = alignment.geometry.union_all()
    else:
        alignment_geometry = None

    results = []

    # Process each forest polygon individually
    for _, forest in forests.iterrows():

        forest_geometry = forest.geometry

        # Intersect forest polygon with proposed ROW
        intersection = forest_geometry.intersection(
            row_geometry
        )

        if intersection.is_empty:
            continue

        if intersection.area <= 0:
            continue

        # Original forest area
        forest_area_ha = forest_geometry.area / 10000

        # Use the source area attribute for comparison
        source_area_ha = forest["area_ha"]

        # ROW intersection area
        intersection_area_ha = (
            intersection.area / 10000
        )

        # Percentage of original forest polygon affected
        affected_percentage = (
            intersection_area_ha / forest_area_ha * 100
            if forest_area_ha > 0 else 0
        )

        # Pipeline centerline length within forest polygon
        if alignment_geometry is not None:

            line_intersection = (
                alignment_geometry.intersection(
                    forest_geometry
                )
            )

            alignment_length_km = (
                line_intersection.length / 1000
            )

        else:
            alignment_length_km = None

        results.append({

            "forest_id": forest["forest_id"],

            "forest_type": forest["forest_type"],

            "forest_area_ha": forest_area_ha,

            "source_area_ha": source_area_ha,

            "intersection_area_ha": intersection_area_ha,

            "affected_percentage": affected_percentage,

            "alignment_length_km": alignment_length_km,

            "geometry": intersection

        })

    # Create output GeoDataFrame
    output_fields = [
        "forest_id",
        "forest_type",
        "forest_area_ha",
        "source_area_ha",
        "intersection_area_ha",
        "affected_percentage",
        "alignment_length_km",
        "geometry"
    ]

    forest_results = gpd.GeoDataFrame(
        results,
        columns=output_fields,
        geometry="geometry",
        crs=forests.crs
    )

    if forest_results.empty:

        print("No forest areas intersect the proposed ROW.")

        return forest_results

    # Round calculated values
    numeric_fields = [
        "forest_area_ha",
        "intersection_area_ha",
        "affected_percentage",
        "alignment_length_km"
    ]

    for field in numeric_fields:

        forest_results[field] = (
            forest_results[field].round(4)
        )

    # Sort by intersection area
    forest_results = forest_results.sort_values(
        "intersection_area_ha",
        ascending=False
    )

    # Summary statistics
    total_forest_area = (
        forest_results["forest_area_ha"].sum()
    )

    total_intersection_area = (
        forest_results["intersection_area_ha"].sum()
    )

    total_alignment_length = (
        forest_results["alignment_length_km"].sum()
        if alignment_geometry is not None else None
    )

    print(
        f"Affected forest polygons: {len(forest_results)}"
    )

    print(
        f"Total original forest area: "
        f"{total_forest_area:.4f} ha"
    )

    print(
        f"Total forest intersection area: "
        f"{total_intersection_area:.4f} ha"
    )

    if total_alignment_length is not None:

        print(
            f"Pipeline alignment within forest: "
            f"{total_alignment_length:.4f} km"
        )

    print("\nDETAILED FOREST IMPACT RESULTS:")

    print(
        forest_results[
            [
                "forest_id",
                "forest_type",
                "forest_area_ha",
                "intersection_area_ha",
                "affected_percentage",
                "alignment_length_km"
            ]
        ].to_string(index=False)
    )

    # Summary by forest classification
    print("\nSUMMARY BY FOREST TYPE:")

    summary = (
        forest_results
        .groupby("forest_type")
        .agg(
            forest_count=("forest_id", "nunique"),
            total_intersection_area_ha=(
                "intersection_area_ha", "sum"
            ),
            total_alignment_length_km=(
                "alignment_length_km", "sum"
            )
        )
        .reset_index()
    )

    print(summary.to_string(index=False))

    return forest_results

# ============================================================
# 6. EXPORT SCREENING RESULTS
# ============================================================

def export_screening_results(
    parcel_results,
    forest_results
):
    """
    Export parcel and forest screening into one GeoPackage
    with separate spatial layers.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    gpkg_file = (
        OUTPUT_DIR
        / "proposed_pipeline_screening.gpkg"
    )

    parcel_csv = (
        OUTPUT_DIR
        / "proposed_pipeline_acquisition.csv"
    )

    forest_csv = (
        OUTPUT_DIR
        / "proposed_pipeline_forest_screening.csv"
    )

    # Export parcel screening CSV
    if not parcel_results.empty:

        parcel_results.drop(
            columns="geometry"
        ).to_csv(
            parcel_csv,
            index=False
        )

    # Export forest screening CSV
    if not forest_results.empty:

        forest_results.drop(
            columns="geometry"
        ).to_csv(
            forest_csv,
            index=False
        )

    # Remove previous output GeoPackage
    if gpkg_file.exists():
        gpkg_file.unlink()

    # Export acquisition screening layer
    if not parcel_results.empty:

        parcel_results.to_file(
            gpkg_file,
            layer="acquisition_screening",
            driver="GPKG",
            engine="pyogrio"
        )

    # Export forest screening layer
    if not forest_results.empty:

        forest_results.to_file(
            gpkg_file,
            layer="forest_screening",
            driver="GPKG",
            engine="pyogrio",
            mode="a"
        )

    print("\n========================================")
    print("SCREENING RESULTS EXPORTED")
    print("========================================")

    print(f"GeoPackage: {gpkg_file}")

    if not parcel_results.empty:
        print(f"Acquisition CSV: {parcel_csv}")

    if not forest_results.empty:
        print(f"Forest CSV: {forest_csv}")


# ============================================================
# 7. MAIN WORKFLOW
# ============================================================

def main():

    print("\nOIL & GAS LAND INTELLIGENCE")
    print("INTEGRATED PIPELINE SPATIAL SCREENING")

    # Load input datasets
    parcels, forests = load_data()

    alignment = load_proposed_alignment()

    # Reproject alignment to parcel CRS
    if alignment.crs != parcels.crs:
        alignment = alignment.to_crs(parcels.crs)

    # Generate proposed ROW corridor
    row_geometry = create_row_corridor(
        alignment,
        row_width_m=ROW_WIDTH_M
    )

    # Run land acquisition screening
    parcel_results = screen_pipeline_row(
        parcels=parcels,
        row_geometry=row_geometry
    )

    # Run forest area screening
    forest_results = screen_forest_areas(
        forests=forests,
        alignment=alignment,
        row_geometry=row_geometry
    )

    # Export both analyses
    export_screening_results(
        parcel_results=parcel_results,
        forest_results=forest_results
    )

    print("\nIntegrated screening process completed.")


if __name__ == "__main__":
    main()
