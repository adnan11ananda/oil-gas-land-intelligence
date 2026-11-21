import zipfile

import geopandas as gpd
import pytest
from shapely.geometry import LineString, MultiLineString, Point, box

from src.alignment_import import (
    AlignmentImportError,
    load_alignment,
    overlaps_study_area,
)

UTM = "EPSG:32748"
WGS84 = "EPSG:4326"


# ============================================================
# HELPERS
# ============================================================

def write_bytes(tmp_path, gdf, filename, driver):
    """Write a GeoDataFrame to disk and return the file bytes."""

    path = tmp_path / filename
    gdf.to_file(path, driver=driver)

    return path.read_bytes()


def zipped_shapefile(tmp_path, gdf, name="alignment"):
    """Write a Shapefile, zip all its components, return the zip bytes."""

    folder = tmp_path / f"{name}_shp"
    folder.mkdir()

    gdf.assign(name=name).to_file(folder / f"{name}.shp")

    zip_path = tmp_path / f"{name}.zip"

    with zipfile.ZipFile(zip_path, "w") as archive:
        for file in folder.iterdir():
            archive.write(file, arcname=file.name)

    return zip_path.read_bytes()


# ============================================================
# HAPPY PATHS
# ============================================================

def test_geopackage_in_utm_is_reprojected_to_wgs84(tmp_path):

    line = LineString([(415000, 9625000), (416000, 9625000)])

    data = write_bytes(
        tmp_path,
        gpd.GeoDataFrame(geometry=[line], crs=UTM),
        "alignment.gpkg",
        "GPKG",
    )

    result = load_alignment(data, "alignment.gpkg")

    # Round trip: the projected length must still be 1,000 m
    back = (
        gpd.GeoSeries([result.line], crs=WGS84)
        .to_crs(UTM)
        .iloc[0]
    )

    assert back.length == pytest.approx(1000, abs=0.01)
    assert result.feature_count == 1


def test_geojson_in_wgs84_is_accepted(tmp_path):

    line = LineString([(104.20, -3.40), (104.25, -3.40)])

    data = write_bytes(
        tmp_path,
        gpd.GeoDataFrame(geometry=[line], crs=WGS84),
        "alignment.geojson",
        "GeoJSON",
    )

    result = load_alignment(data, "alignment.geojson")

    assert result.line.geom_type == "LineString"
    assert result.line.bounds == pytest.approx(
        (104.20, -3.40, 104.25, -3.40)
    )


def test_zipped_shapefile_is_accepted(tmp_path):

    line = LineString([(415000, 9625000), (416000, 9625500)])

    data = zipped_shapefile(
        tmp_path,
        gpd.GeoDataFrame(geometry=[line], crs=UTM),
    )

    result = load_alignment(data, "alignment.zip")

    assert result.line.geom_type == "LineString"


def test_connected_segments_are_merged(tmp_path):

    segments = MultiLineString([
        [(415000, 9625000), (415500, 9625000)],
        [(415500, 9625000), (416000, 9625000)],
    ])

    data = write_bytes(
        tmp_path,
        gpd.GeoDataFrame(geometry=[segments], crs=UTM),
        "alignment.gpkg",
        "GPKG",
    )

    result = load_alignment(data, "alignment.gpkg")

    assert result.line.geom_type == "LineString"
    assert any("Merged" in note for note in result.notes)


def test_z_values_are_dropped(tmp_path):

    line = LineString([(104.20, -3.40, 10), (104.25, -3.40, 12)])

    data = write_bytes(
        tmp_path,
        gpd.GeoDataFrame(geometry=[line], crs=WGS84),
        "alignment.geojson",
        "GeoJSON",
    )

    result = load_alignment(data, "alignment.geojson")

    assert not result.line.has_z


# ============================================================
# REJECTED INPUT
# ============================================================

def test_disconnected_segments_are_rejected(tmp_path):

    segments = MultiLineString([
        [(415000, 9625000), (415500, 9625000)],
        [(417000, 9626000), (418000, 9626000)],
    ])

    data = write_bytes(
        tmp_path,
        gpd.GeoDataFrame(geometry=[segments], crs=UTM),
        "alignment.gpkg",
        "GPKG",
    )

    with pytest.raises(AlignmentImportError, match="disconnected"):
        load_alignment(data, "alignment.gpkg")


def test_polygon_only_file_is_rejected(tmp_path):

    data = write_bytes(
        tmp_path,
        gpd.GeoDataFrame(
            geometry=[box(415000, 9625000, 416000, 9626000)],
            crs=UTM,
        ),
        "polygon.gpkg",
        "GPKG",
    )

    with pytest.raises(AlignmentImportError, match="No line"):
        load_alignment(data, "polygon.gpkg")


def test_point_only_file_is_rejected(tmp_path):

    data = write_bytes(
        tmp_path,
        gpd.GeoDataFrame(
            geometry=[Point(104.2, -3.4)],
            crs=WGS84,
        ),
        "points.geojson",
        "GeoJSON",
    )

    with pytest.raises(AlignmentImportError, match="No line"):
        load_alignment(data, "points.geojson")


def test_unsupported_extension_is_rejected():

    with pytest.raises(AlignmentImportError, match="Unsupported"):
        load_alignment(b"not a gis file", "alignment.txt")


def test_corrupt_file_gives_friendly_error():

    with pytest.raises(AlignmentImportError, match="Could not read"):
        load_alignment(b"{ broken json", "alignment.geojson")


# ============================================================
# CRS HANDLING
# ============================================================

@pytest.mark.filterwarnings("ignore:'crs' was not provided")
def test_file_without_crs_is_rejected_unless_crs_is_assumed(tmp_path):

    line = LineString([(415000, 9625000), (416000, 9625000)])

    # A Shapefile written without a CRS has no .prj
    data = zipped_shapefile(
        tmp_path,
        gpd.GeoDataFrame(geometry=[line]),
    )

    with pytest.raises(AlignmentImportError, match="no coordinate"):
        load_alignment(data, "alignment.zip")

    result = load_alignment(data, "alignment.zip", assume_crs=UTM)

    assert any("assumed" in note for note in result.notes)

@pytest.mark.filterwarnings("ignore:'crs' was not provided")
def test_wrong_assumed_crs_is_caught(tmp_path):

    # UTM coordinates mistakenly treated as longitude/latitude
    line = LineString([(415000, 9625000), (416000, 9625000)])

    data = zipped_shapefile(
        tmp_path,
        gpd.GeoDataFrame(geometry=[line]),
    )

    with pytest.raises(AlignmentImportError, match="outside valid"):
        load_alignment(data, "alignment.zip", assume_crs=WGS84)


# ============================================================
# STUDY AREA CHECK
# ============================================================

def test_overlaps_study_area():

    study_area = gpd.GeoDataFrame(
        geometry=[box(410000, 9620000, 420000, 9630000)],
        crs=UTM,
    )

    inside = (
        gpd.GeoSeries(
            [LineString([(414000, 9624000), (416000, 9626000)])],
            crs=UTM,
        )
        .to_crs(WGS84)
        .iloc[0]
    )

    outside = (
        gpd.GeoSeries(
            [LineString([(300000, 9500000), (301000, 9500000)])],
            crs=UTM,
        )
        .to_crs(WGS84)
        .iloc[0]
    )

    assert overlaps_study_area(inside, study_area)
    assert not overlaps_study_area(outside, study_area)
