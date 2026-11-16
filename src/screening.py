
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

OUTPUT_DIR = PROJECT_ROOT / "outputs" / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. LOAD ORIGINAL LAND PARCELS
# ============================================================

def load_data():
    """
    Load original cadastral land parcels from GeoPackage.
    """

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"GeoPackage not found: {DATA_FILE}"
        )

    parcels = gpd.read_file(
        DATA_FILE,
        layer="original_land_parcels"
    )

    if parcels.empty:
        raise ValueError("Original land parcels layer is empty.")

    if parcels.crs is None:
        raise ValueError("Land parcels have no CRS.")

    required_fields = [
        "parcel_id",
        "owner_type",
        "land_status",
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

    print("Original land parcels loaded successfully.")
    print(f"Number of parcels: {len(parcels)}")
    print(f"CRS: {parcels.crs}")

    return parcels


# ============================================================
# 3. PROPOSED PIPELINE ROW LAND ACQUISITION SCREENING
# ============================================================

def screen_pipeline_row(
    parcels,
    proposed_row,
    row_width_m=20,
    layer_name=None,
    acquired_values=("acquired", "fully acquired"),
    include_acquired=False
):
    """
    Identify cadastral parcels affected by a proposed pipeline ROW.

    Input can be:
    - A GeoDataFrame containing pipeline centerline geometry.
    - A GeoDataFrame containing an existing ROW polygon.
    - A file path to a GIS dataset.

    Parameters
    ----------
    parcels : GeoDataFrame
        Original cadastral land parcels.

    proposed_row : GeoDataFrame or str or Path
        Proposed pipeline centerline or ROW polygon.

    row_width_m : float
        Total ROW width in metres when input is a centerline.

    layer_name : str, optional
        Layer name when reading a GeoPackage.

    acquired_values : tuple
        Status values considered fully acquired.

    include_acquired : bool
        If False, return only parcels requiring acquisition
        or status verification.

    Returns
    -------
    GeoDataFrame
        Spatial acquisition screening results.
    """

    # --------------------------------------------------------
    # A. LOAD PROPOSED PIPELINE ALIGNMENT
    # --------------------------------------------------------

    if isinstance(proposed_row, (str, Path)):

        proposed = gpd.read_file(
            proposed_row,
            layer=layer_name
        )

    else:
        proposed = proposed_row.copy()

    if proposed.empty:
        raise ValueError(
            "Proposed pipeline alignment is empty."
        )

    if proposed.crs is None:
        raise ValueError(
            "Proposed pipeline alignment has no CRS."
        )

    # Reproject alignment to parcel CRS
    if proposed.crs != parcels.crs:
        proposed = proposed.to_crs(parcels.crs)

    # --------------------------------------------------------
    # B. CREATE ROW CORRIDOR
    # --------------------------------------------------------

    geometry_types = set(
        proposed.geometry.geom_type.dropna()
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

        if row_width_m <= 0:
            raise ValueError(
                "ROW width must be greater than zero."
            )

        # Buffer both sides of the pipeline centerline
        corridor = proposed.geometry.buffer(
            row_width_m / 2,
            cap_style="flat",
            join_style="mitre"
        )

    elif geometry_types.issubset(polygon_types):

        # Use existing ROW polygon directly
        corridor = proposed.geometry

    else:
        raise ValueError(
            "Input must contain LineString, MultiLineString, "
            "Polygon or MultiPolygon geometry."
        )

    row_geometry = corridor.union_all()

    if row_geometry.is_empty:
        raise ValueError("ROW corridor geometry is empty.")

    # --------------------------------------------------------
    # C. INTERSECT ROW WITH ORIGINAL LAND PARCELS
    # --------------------------------------------------------

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

        status = parcel["land_status"]

        if pd.isna(status):
            status = "Unknown"

        status = str(status).strip()

        normalized_status = status.lower()

        normalized_acquired = {
            str(value).strip().lower()
            for value in acquired_values
        }

        # Determine acquisition action
        if normalized_status in normalized_acquired:

            action = "No new acquisition required"
            requires_acquisition = False
            requires_review = False

        elif any(
            keyword in normalized_status
            for keyword in [
                "pending",
                "not acquired",
                "unacquired",
                "uncompensated"
            ]
        ):

            action = "Acquisition required"
            requires_acquisition = True
            requires_review = False

        else:

            action = "Verify acquisition status"
            requires_acquisition = False
            requires_review = True

        results.append({

            "parcel_id": parcel["parcel_id"],

            "owner_type": parcel["owner_type"],

            "land_status": status,

            "parcel_area_ha": parcel_area / 10000,

            "row_area_ha": row_area / 10000,

            "affected_percentage": affected_percentage,

            "acquisition_action": action,

            "requires_acquisition": requires_acquisition,

            "requires_review": requires_review,

            "geometry": intersection

        })

    # --------------------------------------------------------
    # D. CREATE OUTPUT GEODATAFRAME
    # --------------------------------------------------------

    output_fields = [
        "parcel_id",
        "owner_type",
        "land_status",
        "parcel_area_ha",
        "row_area_ha",
        "affected_percentage",
        "acquisition_action",
        "requires_acquisition",
        "requires_review",
        "geometry"
    ]

    result = gpd.GeoDataFrame(
        results,
        columns=output_fields,
        geometry="geometry",
        crs=parcels.crs
    )

    if result.empty:
        print("No land parcels intersect the proposed ROW.")
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

    # --------------------------------------------------------
    # E. FILTER ACQUISITION REQUIREMENTS
    # --------------------------------------------------------

    if not include_acquired:

        result = result[
            result["requires_acquisition"]
            | result["requires_review"]
        ].copy()

    # --------------------------------------------------------
    # F. PRINT SCREENING SUMMARY
    # --------------------------------------------------------

    print("\n========================================")
    print("PROPOSED PIPELINE ROW SCREENING")
    print("========================================")

    print(f"Affected parcels: {len(results)}")

    print(
        "Parcels requiring acquisition:",
        sum(
            item["requires_acquisition"]
            for item in results
        )
    )

    print(
        "Parcels requiring status verification:",
        sum(
            item["requires_review"]
            for item in results
        )
    )

    print(
        "Total affected ROW area:",
        round(
            sum(
                item["row_area_ha"]
                for item in results
            ),
            4
        ),
        "ha"
    )

    print("\nAcquisition requirements:")

    if not result.empty:

        print(
            result[
                [
                    "parcel_id",
                    "owner_type",
                    "land_status",
                    "row_area_ha",
                    "affected_percentage",
                    "acquisition_action"
                ]
            ].to_string(index=False)
        )

    return result


# ============================================================
# 4. EXPORT SCREENING RESULTS
# ============================================================

def export_screening_results(result):
    """
    Export screening results to CSV and GeoPackage.
    """

    if result.empty:
        print("No results to export.")
        return

    csv_file = (
        OUTPUT_DIR
        / "proposed_pipeline_acquisition.csv"
    )

    gpkg_file = (
        OUTPUT_DIR
        / "proposed_pipeline_acquisition.gpkg"
    )

    # Export tabular report
    result.drop(
        columns="geometry"
    ).to_csv(
        csv_file,
        index=False
    )

    # Export spatial result
    if gpkg_file.exists():
        gpkg_file.unlink()

    result.to_file(
        gpkg_file,
        layer="acquisition_screening",
        driver="GPKG",
        engine="pyogrio"
    )

    print("\nScreening results exported:")
    print(csv_file)
    print(gpkg_file)


# ============================================================
# 5. MAIN TEST
# ============================================================

if __name__ == "__main__":

    print("\nOIL & GAS LAND INTELLIGENCE")
    print("PROPOSED PIPELINE ACQUISITION SCREENING")

    # Load original land parcels
    parcels = load_data()

    # Screen proposed pipeline alignment
    result = screen_pipeline_row(
        parcels=parcels,
        proposed_row=(
            PROJECT_ROOT
            / "data"
            / "synthetic"
            / "proposed_pipeline_alignment.gpkg"
        ),
        layer_name="proposed_alignment",
        row_width_m=20
    )

    # Export results
    export_screening_results(result)

    print("\nScreening process completed.")
