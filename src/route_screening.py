
import geopandas as gpd
import pandas as pd


def analyze_route(
    pipeline_gdf_metric,
    row_gdf_metric,
    data_path
):
    """
    Analyze land acquisition and forest impacts
    using a proposed pipeline ROW corridor.

    All input geometries must use a projected CRS
    with metre units, such as EPSG:32748.
    """

    # -------------------------------------------------
    # 1. LOAD SOURCE DATA
    # -------------------------------------------------

    parcels = gpd.read_file(
        data_path,
        layer="original_land_parcels"
    )

    forests = gpd.read_file(
        data_path,
        layer="forest_areas"
    )

    parcels = parcels.to_crs(
        pipeline_gdf_metric.crs
    )

    forests = forests.to_crs(
        pipeline_gdf_metric.crs
    )

    # -------------------------------------------------
    # 2. LAND ACQUISITION ANALYSIS
    # -------------------------------------------------

    # Calculate original parcel area
    parcels["parcel_area_ha"] = (
        parcels.geometry.area / 10000
    )

    # Intersect parcels with proposed ROW
    acquisition = gpd.overlay(
        parcels,
        row_gdf_metric,
        how="intersection",
        keep_geom_type=True
    )

    # Calculate affected area
    acquisition["row_area_ha"] = (
        acquisition.geometry.area / 10000
    )

    # Calculate percentage of parcel affected
    acquisition["affected_percentage"] = (
        acquisition["row_area_ha"]
        / acquisition["parcel_area_ha"]
        * 100
    )

    acquisition["acquisition_status"] = (
        "Potential Acquisition"
    )

    # Remove zero-area geometries
    acquisition = acquisition[
        acquisition["row_area_ha"] > 0
    ].copy()

    # -------------------------------------------------
    # 3. FOREST AREA ANALYSIS
    # -------------------------------------------------

    # Calculate original forest area
    forests["forest_area_ha"] = (
        forests.geometry.area / 10000
    )

    # Intersect forest polygons with ROW
    forest_intersection = gpd.overlay(
        forests,
        row_gdf_metric,
        how="intersection",
        keep_geom_type=True
    )

    # Calculate affected forest area
    forest_intersection["intersection_area_ha"] = (
        forest_intersection.geometry.area / 10000
    )

    # Calculate percentage of each forest polygon affected
    forest_intersection["affected_percentage"] = (
        forest_intersection["intersection_area_ha"]
        / forest_intersection["forest_area_ha"]
        * 100
    )

    forest_intersection = forest_intersection[
        forest_intersection["intersection_area_ha"] > 0
    ].copy()

    # -------------------------------------------------
    # 4. PIPELINE LENGTH WITHIN FOREST
    # -------------------------------------------------

    # Dissolve forest polygons to avoid double counting
    forest_union = forests.geometry.union_all()

    # Calculate the unique pipeline length inside forest
    alignment_in_forest = (
        pipeline_gdf_metric.geometry.intersection(
            forest_union
        )
    )

    alignment_length_in_forest_km = (
        alignment_in_forest.length.sum() / 1000
    )

    # -------------------------------------------------
    # 5. SUMMARY METRICS
    # -------------------------------------------------

    total_pipeline_length_km = (
        pipeline_gdf_metric.geometry.length.sum()
        / 1000
    )

    total_row_area_ha = (
        row_gdf_metric.geometry.area.sum()
        / 10000
    )

    total_acquisition_area_ha = (
        acquisition["row_area_ha"].sum()
    )

    total_forest_intersection_ha = (
        forest_intersection[
            "intersection_area_ha"
        ].sum()
    )

    forest_percentage_of_row = (
        total_forest_intersection_ha
        / total_row_area_ha
        * 100
        if total_row_area_ha > 0
        else 0
    )

    summary = {
        "pipeline_length_km": total_pipeline_length_km,
        "row_area_ha": total_row_area_ha,
        "affected_parcels": len(acquisition),
        "potential_acquisition_area_ha": (
            total_acquisition_area_ha
        ),
        "affected_forest_polygons": len(
            forest_intersection
        ),
        "forest_intersection_area_ha": (
            total_forest_intersection_ha
        ),
        "forest_percentage_of_row": (
            forest_percentage_of_row
        ),
        "pipeline_length_in_forest_km": (
            alignment_length_in_forest_km
        )
    }

    return {
        "acquisition": acquisition,
        "forest_intersection": forest_intersection,
        "summary": summary
    }
