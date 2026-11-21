"""
Import a proposed pipeline alignment from an uploaded file.

Supported formats:
    GeoJSON (.geojson, .json), GeoPackage (.gpkg),
    zipped Shapefile (.zip), KML (.kml, if the local GDAL build
    includes the KML driver).

The importer returns ONE continuous LineString in EPSG:4326 so it can
feed the same workflow as a line drawn on the map.
"""

from __future__ import annotations

import math
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import shapely
from shapely.geometry import LineString
from shapely.ops import linemerge


# ============================================================
# 1. CONFIGURATION
# ============================================================

SUPPORTED_EXTENSIONS = (".geojson", ".json", ".gpkg", ".zip", ".kml")

MAX_FILE_MB = 10
MAX_UNZIPPED_MB = 50
DENSE_LINE_VERTICES = 20_000

LINE_TYPES = {"LineString", "MultiLineString"}

WGS84 = "EPSG:4326"


# ============================================================
# 2. RESULT AND ERROR TYPES
# ============================================================

class AlignmentImportError(ValueError):
    """Raised with a user-friendly message when a file can't be used."""


@dataclass
class AlignmentImport:
    """A validated alignment, ready for ROW generation."""

    line: LineString                 # EPSG:4326
    source_crs: str
    feature_count: int
    notes: list[str] = field(default_factory=list)


# ============================================================
# 3. FILE READING
# ============================================================

def _read_zipped_shapefile(zip_path: Path, work_dir: Path):
    """Extract a zip and read the first .shp inside it."""

    try:
        with zipfile.ZipFile(zip_path) as archive:

            total_bytes = sum(
                info.file_size for info in archive.infolist()
            )

            if total_bytes > MAX_UNZIPPED_MB * 1024 * 1024:
                raise AlignmentImportError(
                    "No line features found in the GeoPackage. "
                    "The alignment must be a polyline."
                )

            # ZipFile.extractall strips absolute paths and '..'
            archive.extractall(work_dir)

    except zipfile.BadZipFile as exc:
        raise AlignmentImportError(
            "The file is not a valid zip archive."
        ) from exc

    shapefiles = sorted(work_dir.rglob("*.shp"))

    if not shapefiles:
        raise AlignmentImportError(
            "No .shp file found inside the zip. Zip the Shapefile "
            "components (.shp, .shx, .dbf and .prj) together."
        )

    return gpd.read_file(shapefiles[0])


def _read_first_line_layer(gpkg_path: Path):
    """Read the first GeoPackage layer that contains line features."""

    layers = gpd.list_layers(gpkg_path)

    names = layers["name"].tolist()

    # Prefer layers declared as line layers, then try the rest
    declared_lines = [
        name
        for name, geometry_type in zip(
            layers["name"], layers["geometry_type"]
        )
        if geometry_type and "Line" in str(geometry_type)
    ]

    candidates = declared_lines + [
        name for name in names if name not in declared_lines
    ]

    for name in candidates:

        gdf = gpd.read_file(gpkg_path, layer=name)

        if (
            not gdf.empty
            and gdf.geometry.geom_type.isin(LINE_TYPES).any()
        ):
            return gdf

    raise AlignmentImportError(
        "No line features found in the GeoPackage. "
        "The alignment must be a polyline."
    )


def _read_file(data: bytes, filename: str):
    """Write the upload to a temp folder and read it with GeoPandas."""

    suffix = Path(filename).suffix.lower()

    if suffix not in SUPPORTED_EXTENSIONS:
        raise AlignmentImportError(
            f"Unsupported file type '{suffix or filename}'. "
            f"Use one of: {', '.join(SUPPORTED_EXTENSIONS)}."
        )

    if len(data) > MAX_FILE_MB * 1024 * 1024:
        raise AlignmentImportError(
            f"File is larger than {MAX_FILE_MB} MB."
        )

    with tempfile.TemporaryDirectory() as temp_dir:

        work_dir = Path(temp_dir)
        path = work_dir / f"upload{suffix}"
        path.write_bytes(data)

        try:

            if suffix == ".zip":
                extract_dir = work_dir / "unzipped"
                extract_dir.mkdir()
                return _read_zipped_shapefile(path, extract_dir)

            if suffix == ".gpkg":
                return _read_first_line_layer(path)

            return gpd.read_file(path)

        except AlignmentImportError:
            raise

        except Exception as exc:
            raise AlignmentImportError(
                f"Could not read '{filename}': {exc}"
            ) from exc


# ============================================================
# 4. PUBLIC API
# ============================================================

def load_alignment(
    data: bytes,
    filename: str,
    assume_crs: str | None = None
) -> AlignmentImport:
    """
    Read, clean and validate an uploaded alignment file.

    Parameters
    ----------
    data
        Raw bytes of the uploaded file.
    filename
        Original file name (the extension selects the reader).
    assume_crs
        CRS to assume when the file has none (for example a
        Shapefile without a .prj). If None, such files are rejected.
    """

    gdf = _read_file(data, filename)

    notes: list[str] = []

    if gdf.empty:
        raise AlignmentImportError("The file contains no features.")

    # ---- CRS -------------------------------------------------

    if gdf.crs is None:

        if assume_crs is None:
            raise AlignmentImportError(
                "The file has no coordinate reference system "
                "(missing .prj?). Choose a CRS to assume, or add "
                "the CRS in your GIS software and export again."
            )

        gdf = gdf.set_crs(assume_crs)

        notes.append(
            f"File had no CRS; assumed {assume_crs}."
        )

    source_crs = gdf.crs.to_string()

    # ---- Geometry selection ----------------------------------

    geometries = gdf.geometry.dropna()
    geometries = geometries[~geometries.is_empty]

    lines = geometries[geometries.geom_type.isin(LINE_TYPES)]

    if lines.empty:

        found = ", ".join(
            sorted(set(geometries.geom_type))
        ) or "no geometries"

        raise AlignmentImportError(
            f"No line features found (the file contains: {found}). "
            "The alignment must be a polyline."
        )

    ignored = len(geometries) - len(lines)

    if ignored:
        notes.append(
            f"Ignored {ignored} non-line feature(s)."
        )

    if lines.has_z.any():
        notes.append("Elevation (Z) values were dropped.")

    # ---- Merge into one continuous line ----------------------

    parts = []

    for geometry in lines:

        geometry = shapely.force_2d(geometry)

        if geometry.geom_type == "MultiLineString":
            parts.extend(geometry.geoms)
        else:
            parts.append(geometry)

    merged = linemerge(parts) if len(parts) > 1 else parts[0]

    if merged.geom_type != "LineString":

        raise AlignmentImportError(
            f"The alignment has {len(merged.geoms)} disconnected "
            "segments. Provide one continuous polyline (merge or "
            "snap the segments in your GIS software)."
        )

    if len(parts) > 1:
        notes.append(
            f"Merged {len(parts)} segments into one line."
        )

    if merged.length == 0 or not merged.is_valid:
        raise AlignmentImportError(
            "The alignment geometry is empty or invalid."
        )

    if not merged.is_simple:
        notes.append(
            "The alignment crosses itself. Check the geometry."
        )

    # ---- Reproject to WGS 84 and sanity-check ----------------

    line = (
        gpd.GeoSeries([merged], crs=gdf.crs)
        .to_crs(WGS84)
        .iloc[0]
    )

    minx, miny, maxx, maxy = line.bounds

    bounds_ok = (
        all(math.isfinite(value) for value in (minx, miny, maxx, maxy))
        and -180 <= minx <= maxx <= 180
        and -90 <= miny <= maxy <= 90
    )

    if not bounds_ok:
        raise AlignmentImportError(
            "Coordinates fall outside valid longitude/latitude "
            "ranges after reprojection. The CRS is probably wrong."
        )

    vertex_count = len(line.coords)

    if vertex_count > DENSE_LINE_VERTICES:
        notes.append(
            f"Very dense line ({vertex_count:,} vertices). "
            "Analysis may be slow."
        )

    return AlignmentImport(
        line=line,
        source_crs=source_crs,
        feature_count=len(lines),
        notes=notes
    )


def overlaps_study_area(line: LineString, study_area_gdf) -> bool:
    """
    Check that a WGS 84 line intersects the study area.

    A line outside the study area gives empty screening results,
    which usually means a wrong CRS rather than a real finding.
    """

    study_area = study_area_gdf.to_crs(WGS84).geometry.union_all()

    return bool(line.intersects(study_area))
