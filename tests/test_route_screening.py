import geopandas as gpd
import pytest
from shapely.geometry import LineString, box

from src.route_screening import (
    analyze_route,
    create_row_corridor,
    summary_to_table,
)

UTM = "EPSG:32748"


# ============================================================
# TEST DATA
#
# A 1 km straight pipeline along the x-axis with a 20 m ROW:
#   ROW area = 1,000 m x 20 m = 20,000 m2 = 2.0 ha
# ============================================================

@pytest.fixture
def pipeline():
    return gpd.GeoDataFrame(
        {"pipeline_id": ["TEST"]},
        geometry=[LineString([(0, 0), (1000, 0)])],
        crs=UTM,
    )


@pytest.fixture
def row(pipeline):
    return create_row_corridor(pipeline, row_width_m=20)


def make_parcels(boxes):
    return gpd.GeoDataFrame(
        {
            "parcel_id": [f"P{i}" for i in range(len(boxes))],
            "owner_type": "Private",
            "land_status": "Unregistered",
        },
        geometry=boxes,
        crs=UTM,
    )


def make_forests(boxes):
    return gpd.GeoDataFrame(
        {
            "forest_id": [f"F{i}" for i in range(len(boxes))],
            "forest_type": "Limited Production Forest",
        },
        geometry=boxes,
        crs=UTM,
    )


# ============================================================
# ROW CORRIDOR
# ============================================================

def test_row_corridor_has_flat_ends(row):

    # Round caps would add about 0.03 ha to this 2.0 ha corridor
    assert row.geometry.area.sum() / 10_000 == pytest.approx(2.0)


def test_row_width_must_be_positive(pipeline):

    with pytest.raises(ValueError, match="greater than zero"):
        create_row_corridor(pipeline, row_width_m=0)


def test_row_requires_projected_crs():

    geographic = gpd.GeoDataFrame(
        geometry=[LineString([(104.2, -3.4), (104.3, -3.4)])],
        crs="EPSG:4326",
    )

    with pytest.raises(ValueError, match="projected CRS"):
        create_row_corridor(geographic, row_width_m=20)


# ============================================================
# AREAS AND LENGTHS
# ============================================================

def test_row_and_forest_areas(pipeline, row):

    parcels = make_parcels([box(-50, -50, 1050, 50)])
    forests = make_forests([box(0, -50, 500, 50)])

    result = analyze_route(pipeline, row, parcels, forests)
    summary = result["summary"]

    assert summary["pipeline_length_km"] == pytest.approx(1.0)
    assert summary["row_area_ha"] == pytest.approx(2.0)
    assert summary["forest_intersection_area_ha"] == pytest.approx(1.0)
    assert summary["forest_percentage_of_row"] == pytest.approx(50.0)
    assert summary["pipeline_length_in_forest_km"] == pytest.approx(0.5)


def test_affected_percentage_uses_whole_parcel(pipeline, row):

    # Parcel is 1,100 m x 100 m = 11 ha; the ROW covers 2 ha of it
    parcels = make_parcels([box(-50, -50, 1050, 50)])
    forests = make_forests([box(5000, 5000, 5100, 5100)])

    acquisition = analyze_route(
        pipeline, row, parcels, forests
    )["acquisition"]

    assert acquisition.loc[0, "row_area_ha"] == pytest.approx(2.0)
    assert acquisition.loc[0, "affected_percentage"] == pytest.approx(
        2.0 / 11.0 * 100
    )


def test_multiple_parcels_are_counted_once_each(pipeline, row):

    parcels = make_parcels([
        box(-50, -50, 500, 50),
        box(500, -50, 1050, 50),
    ])

    forests = make_forests([box(5000, 5000, 5100, 5100)])

    result = analyze_route(pipeline, row, parcels, forests)

    assert result["summary"]["affected_parcels"] == 2
    assert result["summary"][
        "potential_acquisition_area_ha"
    ] == pytest.approx(2.0)


# ============================================================
# NO DOUBLE COUNTING
# ============================================================

def test_overlapping_forests_are_not_double_counted(pipeline, row):

    parcels = make_parcels([box(-50, -50, 1050, 50)])

    # Overlap between x=250 and x=500
    forests = make_forests([
        box(0, -50, 500, 50),
        box(250, -50, 750, 50),
    ])

    summary = analyze_route(
        pipeline, row, parcels, forests
    )["summary"]

    # Union covers x=0..750 -> 750 m x 20 m = 1.5 ha, not 2.0 ha
    assert summary["forest_intersection_area_ha"] == pytest.approx(1.5)
    assert summary["pipeline_length_in_forest_km"] == pytest.approx(0.75)
    assert summary["affected_forest_polygons"] == 2


# ============================================================
# EDGE CASES
# ============================================================

def test_route_missing_every_layer_returns_zero_results(pipeline, row):

    parcels = make_parcels([box(5000, 5000, 5100, 5100)])
    forests = make_forests([box(6000, 6000, 6100, 6100)])

    result = analyze_route(pipeline, row, parcels, forests)

    assert result["summary"]["affected_parcels"] == 0
    assert result["summary"]["potential_acquisition_area_ha"] == 0
    assert result["summary"]["affected_forest_polygons"] == 0
    assert result["summary"]["forest_percentage_of_row"] == 0


def test_original_parcels_are_their_own_parent(pipeline, row):

    parcels = make_parcels([box(-50, -50, 1050, 50)])
    forests = make_forests([box(5000, 5000, 5100, 5100)])

    acquisition = analyze_route(
        pipeline, row, parcels, forests
    )["acquisition"]

    assert acquisition.loc[0, "parent_parcel_id"] == "P0"


def test_missing_required_field_is_rejected(pipeline, row):

    parcels = make_parcels([box(-50, -50, 1050, 50)]).drop(
        columns="owner_type"
    )

    forests = make_forests([box(0, -50, 500, 50)])

    with pytest.raises(ValueError, match="owner_type"):
        analyze_route(pipeline, row, parcels, forests)


def test_geographic_crs_is_rejected(pipeline, row):

    # Parcels in lon/lat degrees must fail loudly, not give wrong areas
    parcels = make_parcels([box(104.2, -3.4, 104.3, -3.3)]).set_crs(
        "EPSG:4326",
        allow_override=True
    )

    forests = make_forests([box(0, -50, 500, 50)])

    with pytest.raises(ValueError, match="projected CRS"):
        analyze_route(pipeline, row, parcels, forests)


# ============================================================
# REPORTING
# ============================================================

def test_summary_table_has_expected_shape(pipeline, row):

    parcels = make_parcels([box(-50, -50, 1050, 50)])
    forests = make_forests([box(0, -50, 500, 50)])

    summary = analyze_route(
        pipeline, row, parcels, forests
    )["summary"]

    table = summary_to_table(summary)

    assert list(table.columns) == [
        "category", "indicator", "value", "unit"
    ]

    assert len(table) == 8
