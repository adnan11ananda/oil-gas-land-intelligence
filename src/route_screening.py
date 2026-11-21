"""
Core pipeline route screening.

Single source of truth for ROW generation and spatial screening.
Used by both the Streamlit app and scripts/run_screening.py.
"""

import geopandas as gpd
import pandas as pd


# ============================================================
# 1. CONFIGURATION
# ============================================================

METRIC_CRS = "EPSG:32748"

PARCEL_LAYER = "original_land_parcels"
FOREST_LAYER = "forest_areas"

DEFAULT_ROW_WIDTH_M = 20.0

SQM_PER_HA = 10_000

# Overlay slivers smaller than this (hectares) are ignored
MIN_AREA_HA = 1e-6

REQUIRED_PARCEL_FIELDS = ["parcel_id", "owner_type", "land_status"]
REQUIRED_FOREST_FIELDS = ["forest_id", "forest_type"]


# ============================================================
# 2. VALIDATION HELPERS
# ============================================================

def _require_projected(name, gdf):

    if gdf.crs is None or not gdf.crs.is_projected:
        raise ValueError(
            f"{name} must use a projected CRS in metres "
            f"(for example {METRIC_CRS})."
        )


def _require_fields(name, gdf, fields):

    missing = [field for field in fields if field not in gdf.columns]

    if missing:
        raise ValueError(
            f"{name} is missing field(s): {', '.join(missing)}"
        )


# ============================================================
# 3. DATA LOADING
# ============================================================

def load_screening_layers(data_path, metric_crs=METRIC_CRS):
    """
    Read the parcel and forest layers and project them to metres.

    Screening uses the ORIGINAL parcels, so affected percentages
    are relative to the whole parcel owned by one party.
    """

    parcels = gpd.read_file(data_path, layer=PARCEL_LAYER)
    forests = gpd.read_file(data_path, layer=FOREST_LAYER)

    for name, gdf in (
        ("Parcel layer", parcels),
        ("Forest layer", forests)
    ):

        if gdf.empty:
            raise ValueError(f"{name} is empty.")

        if gdf.crs is None:
            raise ValueError(f"{name} has no CRS.")

    return parcels.to_crs(metric_crs), forests.to_crs(metric_crs)


# ============================================================
# 4. ROW CORRIDOR
# ============================================================

def create_row_corridor(
    alignment_gdf_metric,
    row_width_m=DEFAULT_ROW_WIDTH_M
):
    """
    Buffer a pipeline centerline into a ROW corridor.

    Flat ends and mitred joins give a true corridor of constant
    width. Round caps would add extra area at both ends.
    """

    if row_width_m <= 0:
        raise ValueError("ROW width must be greater than zero.")

    _require_projected("Alignment", alignment_gdf_metric)

    row_gdf = alignment_gdf_metric.copy()

    row_gdf["geometry"] = alignment_gdf_metric.geometry.buffer(
        row_width_m / 2,
        cap_style="flat",
        join_style="mitre"
    )

    return row_gdf


# ============================================================
# 5. ROUTE SCREENING
# ============================================================

def analyze_route(
    pipeline_gdf_metric,
    row_gdf_metric,
    parcels,
    forests
):
    """
    Screen a proposed ROW against land parcels and forest areas.

    All inputs must use a projected CRS in metres. Layers are
    passed in (not read from disk) so results are easy to test
    and the app can cache the source data.

    Returns a dict with:
        acquisition          parcels intersected by the ROW
        forest_intersection  forest polygons intersected by the ROW
        summary              route-level metrics
    """

    _require_projected("Pipeline", pipeline_gdf_metric)
    _require_projected("ROW", row_gdf_metric)
    _require_projected("Parcels", parcels)
    _require_projected("Forests", forests)

    _require_fields("Parcels", parcels, REQUIRED_PARCEL_FIELDS)
    _require_fields("Forests", forests, REQUIRED_FOREST_FIELDS)

    crs = pipeline_gdf_metric.crs

    row_gdf_metric = row_gdf_metric.to_crs(crs)
    parcels = parcels.to_crs(crs).copy()
    forests = forests.to_crs(crs).copy()

    # One dissolved ROW polygon prevents double counting
    row_union = row_gdf_metric.geometry.union_all()

    row_dissolved = gpd.GeoDataFrame(
        geometry=[row_union],
        crs=crs
    )

    # -------------------------------------------------
    # LAND ACQUISITION
    # -------------------------------------------------

    # Original parcels are their own parent
    if "parent_parcel_id" not in parcels.columns:
        parcels["parent_parcel_id"] = parcels["parcel_id"]

    parcels["parcel_area_ha"] = (
        parcels.geometry.area / SQM_PER_HA
    )

    acquisition = gpd.overlay(
        parcels[
            [
                "parcel_id",
                "parent_parcel_id",
                "owner_type",
                "land_status",
                "parcel_area_ha",
                "geometry"
            ]
        ],
        row_dissolved,
        how="intersection",
        keep_geom_type=True
    )

    acquisition["row_area_ha"] = (
        acquisition.geometry.area / SQM_PER_HA
    )

    acquisition = acquisition[
        acquisition["row_area_ha"] > MIN_AREA_HA
    ].copy()

    acquisition["affected_percentage"] = (
        acquisition["row_area_ha"]
        / acquisition["parcel_area_ha"]
        * 100
    )

    acquisition["acquisition_status"] = "Potential Acquisition"

    acquisition = acquisition.sort_values(
        "row_area_ha",
        ascending=False
    ).reset_index(drop=True)

    # -------------------------------------------------
    # FOREST IMPACT
    # -------------------------------------------------

    forests["forest_area_ha"] = (
        forests.geometry.area / SQM_PER_HA
    )

    forest_intersection = gpd.overlay(
        forests[
            [
                "forest_id",
                "forest_type",
                "forest_area_ha",
                "geometry"
            ]
        ],
        row_dissolved,
        how="intersection",
        keep_geom_type=True
    )

    forest_intersection["intersection_area_ha"] = (
        forest_intersection.geometry.area / SQM_PER_HA
    )

    forest_intersection = forest_intersection[
        forest_intersection["intersection_area_ha"] > MIN_AREA_HA
    ].copy()

    forest_intersection["affected_percentage"] = (
        forest_intersection["intersection_area_ha"]
        / forest_intersection["forest_area_ha"]
        * 100
    )

    forest_intersection = forest_intersection.sort_values(
        "intersection_area_ha",
        ascending=False
    ).reset_index(drop=True)

    # Dissolve forests so overlapping polygons are counted once
    forest_union = forests.geometry.union_all()

    forest_row_area_ha = (
        row_union.intersection(forest_union).area / SQM_PER_HA
    )

    alignment_union = pipeline_gdf_metric.geometry.union_all()

    length_in_forest_km = (
        alignment_union.intersection(forest_union).length / 1000
    )

    # -------------------------------------------------
    # SUMMARY
    # -------------------------------------------------

    total_row_area_ha = row_union.area / SQM_PER_HA

    summary = {
        "pipeline_length_km": alignment_union.length / 1000,
        "row_area_ha": total_row_area_ha,
        "affected_parcels": int(acquisition["parcel_id"].nunique()),
        "potential_acquisition_area_ha": float(
            acquisition["row_area_ha"].sum()
        ),
        "affected_forest_polygons": int(
            forest_intersection["forest_id"].nunique()
        ),
        "forest_intersection_area_ha": forest_row_area_ha,
        "forest_percentage_of_row": (
            forest_row_area_ha / total_row_area_ha * 100
            if total_row_area_ha > 0
            else 0
        ),
        "pipeline_length_in_forest_km": length_in_forest_km
    }

    return {
        "acquisition": acquisition,
        "forest_intersection": forest_intersection,
        "summary": summary
    }


# ============================================================
# 6. REPORTING
# ============================================================

SUMMARY_ROWS = [
    ("Route", "Pipeline alignment length",
     "pipeline_length_km", "km"),
    ("Route", "Total ROW area",
     "row_area_ha", "ha"),
    ("Land Acquisition", "Affected land parcels",
     "affected_parcels", "parcels"),
    ("Land Acquisition", "Potential acquisition area",
     "potential_acquisition_area_ha", "ha"),
    ("Forest", "Affected forest polygons",
     "affected_forest_polygons", "polygons"),
    ("Forest", "Forest intersection area",
     "forest_intersection_area_ha", "ha"),
    ("Forest", "ROW within forest",
     "forest_percentage_of_row", "%"),
    ("Forest", "Pipeline alignment within forest",
     "pipeline_length_in_forest_km", "km"),
]


def summary_to_table(summary):
    """Convert the summary dict to a category/indicator/value table."""

    return pd.DataFrame([
        {
            "category": category,
            "indicator": indicator,
            "value": summary[key],
            "unit": unit
        }
        for category, indicator, key, unit in SUMMARY_ROWS
    ])
