
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "oil_gas_land_intelligence.gpkg"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "oil_gas_land_intelligence_with_asset_parcels.gpkg"
)

CRS = "EPSG:32748"

# Synthetic asset dimensions in metres
PIPELINE_ROW_WIDTH = 20

FACILITY_WIDTH = 100
FACILITY_LENGTH = 100

WELLSITE_WIDTH = 40
WELLSITE_LENGTH = 40

MAIN_ROAD_WIDTH = 10
WELL_ROAD_WIDTH = 5

MIN_AREA = 1.0

# Reproducible road curvature
ROAD_BEND_FACTOR = 0.08


# ============================================================
# 2. GEOMETRY HELPER FUNCTIONS
# ============================================================

def polygon_parts(geometry):
    """Extract polygon parts from any polygonal geometry."""

    if geometry is None or geometry.is_empty:
        return []

    if geometry.geom_type == "Polygon":
        return (
            [geometry]
            if geometry.area > MIN_AREA
            else []
        )

    if geometry.geom_type in (
        "MultiPolygon",
        "GeometryCollection"
    ):
        result = []

        for part in geometry.geoms:
            result.extend(polygon_parts(part))

        return result

    return []


def create_gdf(records):
    """Create a GeoDataFrame using project CRS."""

    return gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs=CRS
    )


def calculate_area(geometry):
    """Calculate area in hectares."""

    return round(geometry.area / 10000, 4)


def make_footprint(point, width, length):
    """Create rectangular facility or wellsite footprint."""

    return box(
        point.x - width / 2,
        point.y - length / 2,
        point.x + width / 2,
        point.y + length / 2
    )


def create_curved_route(start, end, bend_factor=0.08):
    """
    Create a gently curved route between two points.

    This is a synthetic alignment, not an engineered road design.
    """

    x1, y1 = start.x, start.y
    x2, y2 = end.x, end.y

    dx = x2 - x1
    dy = y2 - y1

    distance = (dx**2 + dy**2) ** 0.5

    if distance == 0:
        return LineString([start, end])

    # Perpendicular direction
    px = -dy / distance
    py = dx / distance

    # Deterministic curve offset
    offset = distance * bend_factor

    midpoint_x = (x1 + x2) / 2 + px * offset
    midpoint_y = (y1 + y2) / 2 + py * offset

    return LineString([
        start,
        Point(midpoint_x, midpoint_y),
        end
    ])


def make_road_corridor(line, width, study_area):
    """Create a road ROW polygon from a road centerline."""

    corridor = line.buffer(
        width / 2,
        cap_style="flat",
        join_style="mitre"
    )

    return corridor.intersection(study_area)


def minimum_spanning_tree(points):
    """
    Calculate a simple minimum spanning tree using Prim's algorithm.

    Returns pairs of point indices.
    """

    count = len(points)

    if count < 2:
        return []

    connected = {0}
    edges = []

    while len(connected) < count:

        best_distance = float("inf")
        best_edge = None

        for i in connected:

            for j in range(count):

                if j in connected:
                    continue

                distance = points[i].distance(points[j])

                if distance < best_distance:
                    best_distance = distance
                    best_edge = (i, j)

        if best_edge is None:
            break

        edges.append(best_edge)
        connected.add(best_edge[1])

    return edges


# ============================================================
# 3. LOAD ORIGINAL DATA
# ============================================================

print("\nLoading original GeoPackage...")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file not found: {INPUT_FILE}"
    )

gdf_parcels = gpd.read_file(
    INPUT_FILE,
    layer="land_parcels"
)

gdf_pipelines = gpd.read_file(
    INPUT_FILE,
    layer="pipelines"
)

gdf_facilities = gpd.read_file(
    INPUT_FILE,
    layer="production_facilities"
)

gdf_wells = gpd.read_file(
    INPUT_FILE,
    layer="existing_wells"
)

input_layers = {
    "land_parcels": gdf_parcels,
    "pipelines": gdf_pipelines,
    "production_facilities": gdf_facilities,
    "existing_wells": gdf_wells
}

for layer_name, gdf in input_layers.items():

    if gdf.crs is None:
        raise ValueError(
            f"{layer_name} does not have a CRS."
        )

    if gdf.crs.to_epsg() != 32748:
        raise ValueError(
            f"{layer_name} must use EPSG:32748."
        )

    if gdf.empty:
        raise ValueError(
            f"{layer_name} contains no features."
        )

print(f"Original parcels: {len(gdf_parcels)}")
print(f"Pipelines: {len(gdf_pipelines)}")
print(f"Facilities: {len(gdf_facilities)}")
print(f"Existing wells: {len(gdf_wells)}")


# ============================================================
# 4. DEFINE STUDY AREA AND ORIGINAL PARCELS
# ============================================================

print("\nPreparing original parcels...")

study_area = unary_union(
    gdf_parcels.geometry.tolist()
)

# Preserve original parcel boundaries and attributes
original_parcels = []

for _, parcel in gdf_parcels.iterrows():

    original_parcels.append({

        "parent_parcel_id": str(parcel["parcel_id"]),

        "owner_type": parcel["owner_type"],

        "land_status": parcel["land_status"],

        "original_geometry": parcel.geometry,

        "remaining_geometry": parcel.geometry

    })


# ============================================================
# 5. CREATE PIPELINE ROW PARCELS
# ============================================================

print("\nCreating pipeline ROW parcels...")

pipeline_assets = []

for _, pipeline in gdf_pipelines.iterrows():

    corridor = pipeline.geometry.buffer(
        PIPELINE_ROW_WIDTH / 2,
        cap_style="flat",
        join_style="mitre"
    ).intersection(study_area)

    pipeline_assets.append({

        "asset_id": pipeline["pipeline_id"],

        "asset_name": pipeline["pipeline_name"],

        "geometry": corridor

    })


row_records = []

for asset in pipeline_assets:

    for parcel in original_parcels:

        intersection = (
            parcel["remaining_geometry"]
            .intersection(asset["geometry"])
        )

        for part in polygon_parts(intersection):

            row_records.append({

                "row_id": (
                    f"ROW-{len(row_records) + 1:04d}"
                ),

                "parent_parcel_id": (
                    parcel["parent_parcel_id"]
                ),

                "pipeline_id": asset["asset_id"],

                "pipeline_name": asset["asset_name"],

                "row_width_m": PIPELINE_ROW_WIDTH,

                "area_ha": calculate_area(part),

                "geometry": part

            })

        parcel["remaining_geometry"] = (
            parcel["remaining_geometry"]
            .difference(asset["geometry"])
        )


gdf_row = create_gdf(row_records)

print(f"Created {len(gdf_row)} pipeline ROW parcel sections.")


# ============================================================
# 6. CREATE FACILITY PARCELS
# ============================================================

print("\nCreating production facility parcels...")

facility_assets = []

for _, facility in gdf_facilities.iterrows():

    footprint = make_footprint(
        facility.geometry,
        FACILITY_WIDTH,
        FACILITY_LENGTH
    ).intersection(study_area)

    facility_assets.append({

        "asset_id": facility["facility_id"],

        "asset_name": facility["facility_name"],

        "geometry": footprint

    })


facility_records = []

for asset in facility_assets:

    for parcel in original_parcels:

        intersection = (
            parcel["remaining_geometry"]
            .intersection(asset["geometry"])
        )

        for part in polygon_parts(intersection):

            facility_records.append({

                "parcel_id": (
                    f"FAC-PAR-{len(facility_records) + 1:04d}"
                ),

                "parent_parcel_id": (
                    parcel["parent_parcel_id"]
                ),

                "facility_id": asset["asset_id"],

                "facility_name": asset["asset_name"],

                "area_ha": calculate_area(part),

                "land_status": parcel["land_status"],

                "geometry": part

            })

        parcel["remaining_geometry"] = (
            parcel["remaining_geometry"]
            .difference(asset["geometry"])
        )


gdf_facility_parcels = create_gdf(
    facility_records
)

print(
    f"Created {len(gdf_facility_parcels)} facility parcel sections."
)


# ============================================================
# 7. CREATE EXISTING WELLSITE PARCELS
# ============================================================

print("\nCreating existing wellsite parcels...")

well_assets = []

for _, well in gdf_wells.iterrows():

    footprint = make_footprint(
        well.geometry,
        WELLSITE_WIDTH,
        WELLSITE_LENGTH
    ).intersection(study_area)

    well_assets.append({

        "asset_id": well["well_id"],

        "well_type": well["well_type"],

        "geometry": footprint

    })


wellsite_records = []

for asset in well_assets:

    for parcel in original_parcels:

        intersection = (
            parcel["remaining_geometry"]
            .intersection(asset["geometry"])
        )

        for part in polygon_parts(intersection):

            wellsite_records.append({

                "parcel_id": (
                    f"WELL-PAR-{len(wellsite_records) + 1:04d}"
                ),

                "parent_parcel_id": (
                    parcel["parent_parcel_id"]
                ),

                "well_id": asset["asset_id"],

                "well_type": asset["well_type"],

                "area_ha": calculate_area(part),

                "land_status": parcel["land_status"],

                "geometry": part

            })

        parcel["remaining_geometry"] = (
            parcel["remaining_geometry"]
            .difference(asset["geometry"])
        )


gdf_wellsite_parcels = create_gdf(
    wellsite_records
)

print(
    f"Created {len(gdf_wellsite_parcels)} wellsite parcel sections."
)


# ============================================================
# 8. GENERATE ACCESS ROAD NETWORK
# ============================================================

print("\nGenerating Oil & Gas access road network...")

road_records = []

# ------------------------------------------------------------
# 8A. Facility-to-facility roads
# ------------------------------------------------------------

facility_points = list(gdf_facilities.geometry)

facility_ids = list(gdf_facilities["facility_id"])

facility_edges = minimum_spanning_tree(
    facility_points
)

for index, (i, j) in enumerate(facility_edges, start=1):

    start = facility_points[i]
    end = facility_points[j]

    route = create_curved_route(
        start,
        end,
        bend_factor=ROAD_BEND_FACTOR
    ).intersection(study_area)

    if route.is_empty:
        continue

    road_records.append({

        "road_id": f"ROAD-{len(road_records) + 1:04d}",

        "road_name": f"Facility Connection {index}",

        "road_type": "Main Access Road",

        "from_asset": facility_ids[i],

        "to_asset": facility_ids[j],

        "road_width_m": MAIN_ROAD_WIDTH,

        "length_km": round(route.length / 1000, 3),

        "geometry": route

    })


# ------------------------------------------------------------
# 8B. Well-to-nearest-facility roads
# ------------------------------------------------------------

for _, well in gdf_wells.iterrows():

    well_point = well.geometry

    # Find nearest production facility
    distances = gdf_facilities.geometry.distance(
        well_point
    )

    nearest_index = distances.idxmin()

    nearest_facility = gdf_facilities.loc[
        nearest_index
    ]

    facility_point = nearest_facility.geometry

    route = create_curved_route(
        facility_point,
        well_point,
        bend_factor=ROAD_BEND_FACTOR
    ).intersection(study_area)

    if route.is_empty:
        continue

    road_records.append({

        "road_id": f"ROAD-{len(road_records) + 1:04d}",

        "road_name": f"Access Road {well['well_id']}",

        "road_type": "Well Access Road",

        "from_asset": nearest_facility["facility_id"],

        "to_asset": well["well_id"],

        "road_width_m": WELL_ROAD_WIDTH,

        "length_km": round(route.length / 1000, 3),

        "geometry": route

    })


gdf_roads = create_gdf(road_records)

print(f"Created {len(gdf_roads)} road centerlines.")

print(
    "Facility connections:",
    len(facility_edges)
)

print(
    "Well access connections:",
    len(gdf_wells)
)


# ============================================================
# 9. CREATE ROAD ROW PARCELS
# ============================================================

print("\nCreating road ROW parcels...")

road_assets = []

# Roads are carved out after pipeline, facility and wellsite
# footprints. This prevents double-counting their areas.

for _, road in gdf_roads.iterrows():

    width = road["road_width_m"]

    corridor = make_road_corridor(
        road.geometry,
        width,
        study_area
    )

    road_assets.append({

        "road_id": road["road_id"],

        "road_name": road["road_name"],

        "road_type": road["road_type"],

        "road_width_m": width,

        "geometry": corridor

    })


road_parcel_records = []

for asset in road_assets:

    for parcel in original_parcels:

        intersection = (
            parcel["remaining_geometry"]
            .intersection(asset["geometry"])
        )

        for part in polygon_parts(intersection):

            road_parcel_records.append({

                "road_parcel_id": (
                    f"ROAD-PAR-{len(road_parcel_records) + 1:04d}"
                ),

                "parent_parcel_id": (
                    parcel["parent_parcel_id"]
                ),

                "road_id": asset["road_id"],

                "road_name": asset["road_name"],

                "road_type": asset["road_type"],

                "road_width_m": asset["road_width_m"],

                "area_ha": calculate_area(part),

                "land_status": parcel["land_status"],

                "geometry": part

            })

        # Remove the allocated road footprint from remaining land
        parcel["remaining_geometry"] = (
            parcel["remaining_geometry"]
            .difference(asset["geometry"])
        )


gdf_road_parcels = create_gdf(
    road_parcel_records
)

print(
    f"Created {len(gdf_road_parcels)} road ROW parcel sections."
)


# ============================================================
# 10. CREATE REMAINING GENERAL LAND PARCELS
# ============================================================

print("\nCreating remaining general land parcels...")

remaining_records = []

for parcel in original_parcels:

    for part in polygon_parts(
        parcel["remaining_geometry"]
    ):

        remaining_records.append({

            "parcel_id": (
                f"{parcel['parent_parcel_id']}-REM-"
                f"{len(remaining_records) + 1:04d}"
            ),

            "parent_parcel_id": (
                parcel["parent_parcel_id"]
            ),

            "owner_type": parcel["owner_type"],

            "land_status": parcel["land_status"],

            "area_ha": calculate_area(part),

            "geometry": part

        })


gdf_remaining = create_gdf(remaining_records)

print(
    f"Created {len(gdf_remaining)} remaining land parcels."
)


# ============================================================
# 11. VALIDATE LAND AREA ACCOUNTING
# ============================================================

print("\n========================================")
print("LAND AREA VALIDATION")
print("========================================")

original_area = sum(
    parcel.geometry.area
    for _, parcel in gdf_parcels.iterrows()
)

remaining_area = gdf_remaining.geometry.area.sum()

row_area = gdf_row.geometry.area.sum()

facility_area = gdf_facility_parcels.geometry.area.sum()

wellsite_area = gdf_wellsite_parcels.geometry.area.sum()

road_area = gdf_road_parcels.geometry.area.sum()

total_area = (
    remaining_area
    + row_area
    + facility_area
    + wellsite_area
    + road_area
)

difference = abs(original_area - total_area)

print(f"Original land area: {original_area:,.2f} m2")
print(f"Remaining land: {remaining_area:,.2f} m2")
print(f"Pipeline ROW: {row_area:,.2f} m2")
print(f"Facility parcels: {facility_area:,.2f} m2")
print(f"Wellsite parcels: {wellsite_area:,.2f} m2")
print(f"Road ROW: {road_area:,.2f} m2")

print(f"\nArea difference: {difference:.6f} m2")

if difference < 0.1:
    print("PASS: Land area accounting is balanced.")
else:
    print("WARNING: Land area accounting needs review.")


# Check whether the asset parcels have valid geometries
new_layers = {

    "land_parcels": gdf_remaining,

    "row_parcels": gdf_row,

    "facility_parcels": gdf_facility_parcels,

    "wellsite_parcels": gdf_wellsite_parcels,

    "road_parcels": gdf_road_parcels,

    "roads": gdf_roads

}

print("\nGeometry validation:")

for layer_name, gdf in new_layers.items():

    invalid_count = (
        ~gdf.geometry.is_valid
    ).sum()

    empty_count = (
        gdf.geometry.is_empty
    ).sum()

    print(
        f"{layer_name}: "
        f"{len(gdf)} features, "
        f"{invalid_count} invalid, "
        f"{empty_count} empty"
    )


# ============================================================
# 12. EXPORT FINAL GEOPACKAGE
# ============================================================

print("\nExporting final GeoPackage...")

if OUTPUT_FILE.exists():
    OUTPUT_FILE.unlink()


# Preserve original infrastructure and reference layers.
# Rename the original parcels to retain the baseline.

source_layer_names = (
    gpd.list_layers(INPUT_FILE)["name"].tolist()
)

for layer_name in source_layer_names:

    source_gdf = gpd.read_file(
        INPUT_FILE,
        layer=layer_name
    )

    output_layer_name = (
        "original_land_parcels"
        if layer_name == "land_parcels"
        else layer_name
    )

    source_gdf.to_file(
        OUTPUT_FILE,
        layer=output_layer_name,
        driver="GPKG",
        engine="pyogrio"
    )


# Add newly generated layers

for layer_name, gdf in new_layers.items():

    gdf.to_file(
        OUTPUT_FILE,
        layer=layer_name,
        driver="GPKG",
        engine="pyogrio",
        mode="a"
    )

    print(
        f"Exported {layer_name}: {len(gdf)} features"
    )


# ============================================================
# 13. COMPLETION
# ============================================================

print("\n========================================")
print("ASSET PARCEL GENERATION COMPLETED")
print("========================================")

print(f"Output file: {OUTPUT_FILE}")

print("\nFinal layers:")

for layer_name in (
    source_layer_names
    + list(new_layers.keys())
):
    print(f"- {layer_name}")

print("\nRoad network summary:")

print(
    f"Total road centerlines: {len(gdf_roads)}"
)

print(
    f"Total road ROW parcel sections: "
    f"{len(gdf_road_parcels)}"
)

print("\nCRS:", CRS)

print("========================================")
