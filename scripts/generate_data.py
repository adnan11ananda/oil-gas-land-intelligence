
import random
from pathlib import Path

import geopandas as gpd
import numpy as np

from shapely.geometry import (
    Point,
    Polygon,
    MultiPoint,
    LineString,
    box,
)
from shapely.ops import voronoi_diagram


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "data" / "synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "oil_gas_land_intelligence.gpkg"

CRS = "EPSG:32748"

# Synthetic study area coordinates (UTM Zone 48S)
X_MIN = 410000
X_MAX = 420000
Y_MIN = 9620000
Y_MAX = 9630000

STUDY_AREA = box(
    X_MIN,
    Y_MIN,
    X_MAX,
    Y_MAX
)

# Reproducible random data
random.seed(42)
np.random.seed(42)


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def random_point_in_area(polygon):
    """Generate a random point inside a polygon."""

    minx, miny, maxx, maxy = polygon.bounds

    while True:
        x = random.uniform(minx, maxx)
        y = random.uniform(miny, maxy)

        point = Point(x, y)

        if polygon.contains(point):
            return point


def create_irregular_polygon(
    center_x,
    center_y,
    radius_x,
    radius_y,
    seed,
    rotation=0
):
    """
    Create an irregular polygon using radial variation.
    """

    rng = np.random.default_rng(seed)

    coordinates = []

    angle_rotation = np.radians(rotation)

    number_of_vertices = 80

    for i in range(number_of_vertices):

        angle = (
            2 * np.pi * i / number_of_vertices
        )

        # Irregular radial variation
        variation = (
            1
            + 0.12 * np.sin(3 * angle)
            + 0.08 * np.sin(5 * angle)
            + rng.normal(0, 0.035)
        )

        x = radius_x * variation * np.cos(angle)
        y = radius_y * variation * np.sin(angle)

        # Rotate polygon
        rotated_x = (
            x * np.cos(angle_rotation)
            - y * np.sin(angle_rotation)
        )

        rotated_y = (
            x * np.sin(angle_rotation)
            + y * np.cos(angle_rotation)
        )

        coordinates.append(
            (
                center_x + rotated_x,
                center_y + rotated_y
            )
        )

    polygon = Polygon(coordinates)

    return polygon.buffer(0)


def create_route(start, end, offset=0):
    """
    Create a pipeline route with intermediate bends.
    """

    x1, y1 = start
    x2, y2 = end

    dx = x2 - x1
    dy = y2 - y1

    midpoint_x = (x1 + x2) / 2
    midpoint_y = (y1 + y2) / 2

    # Perpendicular offset to create a route bend
    length = np.sqrt(dx**2 + dy**2)

    if length == 0:
        return LineString([start, end])

    perpendicular_x = -dy / length
    perpendicular_y = dx / length

    bend_x = midpoint_x + perpendicular_x * offset
    bend_y = midpoint_y + perpendicular_y * offset

    return LineString([
        start,
        (bend_x, bend_y),
        end
    ])


def create_geodataframe(records):
    """Create a GeoDataFrame using the project CRS."""

    return gpd.GeoDataFrame(
        records,
        geometry="geometry",
        crs=CRS
    )


# ============================================================
# 3. STUDY AREA
# ============================================================

gdf_study_area = create_geodataframe([
    {
        "area_id": "AREA-001",
        "area_name": "Synthetic Oil and Gas Operating Area",
        "area_ha": round(STUDY_AREA.area / 10000, 2),
        "geometry": STUDY_AREA
    }
])

print("Study area created.")


# ============================================================
# 4. LAND PARCEL GENERATION
# ============================================================

print("Generating land parcels...")

seed_points = []

# Generate 100 seed points with positional variation
for row in range(10):

    for col in range(10):

        x = (
            X_MIN
            + (col + 0.5) * 1000
            + random.uniform(-350, 350)
        )

        y = (
            Y_MIN
            + (row + 0.5) * 1000
            + random.uniform(-350, 350)
        )

        seed_points.append(
            Point(x, y)
        )


# Generate Voronoi polygons
voronoi_cells = voronoi_diagram(
    MultiPoint(seed_points),
    envelope=STUDY_AREA.envelope,
    edges=False
)

parcel_geometries = []

for cell in voronoi_cells.geoms:

    clipped = cell.intersection(STUDY_AREA)

    if clipped.is_empty:
        continue

    if clipped.geom_type == "Polygon":
        parcel_geometries.append(clipped)

    elif clipped.geom_type == "MultiPolygon":

        for polygon in clipped.geoms:
            if polygon.area > 100:
                parcel_geometries.append(polygon)


# Sort parcels by location for consistent IDs
parcel_geometries.sort(
    key=lambda geom: (
        geom.centroid.y,
        geom.centroid.x
    )
)

owner_types = [
    "Private",
    "Government",
    "Company",
    "Community"
]

land_statuses = [
    "Acquired",
    "Pending Acquisition",
    "Leased",
    "Unregistered"
]

parcel_records = []

for i, geometry in enumerate(parcel_geometries, start=1):

    parcel_records.append({

        "parcel_id": f"PAR-{i:03d}",

        "owner_type": random.choice(owner_types),

        "land_status": random.choice(land_statuses),

        "area_ha": round(
            geometry.area / 10000,
            3
        ),

        "geometry": geometry

    })


gdf_parcels = create_geodataframe(parcel_records)

print(f"Created {len(gdf_parcels)} land parcels.")


# ============================================================
# 5. FOREST AREA GENERATION
# ============================================================

print("Generating forest areas...")

forest_specs = [

    (412000, 9622500, 850, 1300, 15),

    (417000, 9627500, 1300, 900, -25),

    (414800, 9628500, 650, 750, 30),

    (418700, 9622000, 700, 1000, -15)

]

forest_records = []

forest_types = [
    "Protected Forest",
    "Production Forest",
    "Limited Production Forest"
]

for i, spec in enumerate(forest_specs, start=1):

    cx, cy, rx, ry, rotation = spec

    forest_polygon = create_irregular_polygon(
        center_x=cx,
        center_y=cy,
        radius_x=rx,
        radius_y=ry,
        seed=i * 100,
        rotation=rotation
    )

    # Keep forest polygons inside the study area
    forest_polygon = forest_polygon.intersection(
        STUDY_AREA
    )

    if forest_polygon.is_empty:
        continue

    if forest_polygon.geom_type == "Polygon":

        forest_geometries = [forest_polygon]

    elif forest_polygon.geom_type == "MultiPolygon":

        forest_geometries = list(forest_polygon.geoms)

    else:
        continue

    for part in forest_geometries:

        if part.area < 1000:
            continue

        forest_records.append({

            "forest_id": f"FOR-{len(forest_records) + 1:03d}",

            "forest_type": random.choice(forest_types),

            "area_ha": round(
                part.area / 10000,
                3
            ),

            "geometry": part

        })


gdf_forests = create_geodataframe(forest_records)

print(f"Created {len(gdf_forests)} forest polygons.")


# ============================================================
# 6. PRODUCTION FACILITIES
# ============================================================

print("Generating production facilities...")

facility_definitions = [

    {
        "facility_id": "FAC-001",
        "facility_name": "Central Processing Station",
        "facility_type": "Central Processing Station",
        "x": 413000,
        "y": 9624000
    },

    {
        "facility_id": "FAC-002",
        "facility_name": "North Production Station",
        "facility_type": "Production Station",
        "x": 416000,
        "y": 9627000
    },

    {
        "facility_id": "FAC-003",
        "facility_name": "South Production Station",
        "facility_type": "Production Station",
        "x": 417500,
        "y": 9622500
    },

    {
        "facility_id": "FAC-004",
        "facility_name": "Gas Gathering Station",
        "facility_type": "Gas Gathering Station",
        "x": 419000,
        "y": 9626500
    },

    {
        "facility_id": "FAC-005",
        "facility_name": "Water Injection Station",
        "facility_type": "Water Injection Station",
        "x": 411500,
        "y": 9628500
    }

]

facility_records = []

for facility in facility_definitions:

    facility_records.append({

        "facility_id": facility["facility_id"],

        "facility_name": facility["facility_name"],

        "facility_type": facility["facility_type"],

        "status": random.choice([
            "Operational",
            "Operational",
            "Under Maintenance"
        ]),

        "geometry": Point(
            facility["x"],
            facility["y"]
        )

    })


gdf_facilities = create_geodataframe(
    facility_records
)

print(f"Created {len(gdf_facilities)} production facilities.")


# ============================================================
# 7. EXISTING WELLS
# ============================================================

print("Generating existing wells...")

# Wells are clustered around production facilities.
# This represents a simplified synthetic field layout.

well_clusters = [

    {
        "cluster_id": "CL-001",
        "center": (413000, 9624000),
        "count": 15
    },

    {
        "cluster_id": "CL-002",
        "center": (416000, 9627000),
        "count": 12
    },

    {
        "cluster_id": "CL-003",
        "center": (417500, 9622500),
        "count": 13
    }

]

well_records = []

well_counter = 1

for cluster in well_clusters:

    cx, cy = cluster["center"]

    for _ in range(cluster["count"]):

        # Generate well locations around cluster center
        x = cx + np.random.normal(0, 450)
        y = cy + np.random.normal(0, 450)

        point = Point(x, y)

        # Ensure wells are inside the study area
        if not STUDY_AREA.contains(point):
            point = random_point_in_area(STUDY_AREA)

        well_records.append({

            "well_id": f"EXW-{well_counter:03d}",

            "cluster_id": cluster["cluster_id"],

            "well_type": random.choice([
                "Oil",
                "Gas",
                "Injection"
            ]),

            "status": random.choice([
                "Producing",
                "Producing",
                "Shut-in",
                "Suspended"
            ]),

            "geometry": point

        })

        well_counter += 1


gdf_wells = create_geodataframe(
    well_records
)

print(f"Created {len(gdf_wells)} existing wells.")


# ============================================================
# 8. PIPELINE NETWORK
# ============================================================

print("Generating pipeline network...")

pipeline_definitions = [

    {
        "pipeline_id": "PPL-001",
        "pipeline_name": "North Trunkline",
        "from_facility": "FAC-002",
        "to_facility": "FAC-001",
        "start": (416000, 9627000),
        "end": (413000, 9624000),
        "offset": 250,
        "diameter_inch": 8,
        "fluid_type": "Crude Oil"
    },

    {
        "pipeline_id": "PPL-002",
        "pipeline_name": "South Trunkline",
        "from_facility": "FAC-003",
        "to_facility": "FAC-001",
        "start": (417500, 9622500),
        "end": (413000, 9624000),
        "offset": -200,
        "diameter_inch": 10,
        "fluid_type": "Crude Oil"
    },

    {
        "pipeline_id": "PPL-003",
        "pipeline_name": "Gas Gathering Line",
        "from_facility": "FAC-004",
        "to_facility": "FAC-002",
        "start": (419000, 9626500),
        "end": (416000, 9627000),
        "offset": 150,
        "diameter_inch": 6,
        "fluid_type": "Natural Gas"
    },

    {
        "pipeline_id": "PPL-004",
        "pipeline_name": "Water Injection Line",
        "from_facility": "FAC-005",
        "to_facility": "FAC-001",
        "start": (411500, 9628500),
        "end": (413000, 9624000),
        "offset": -180,
        "diameter_inch": 4,
        "fluid_type": "Water"
    }

]

pipeline_records = []

for pipeline in pipeline_definitions:

    route = create_route(
        pipeline["start"],
        pipeline["end"],
        pipeline["offset"]
    )

    # Keep the pipeline geometry inside the study area
    route = route.intersection(STUDY_AREA)

    if route.is_empty:
        continue

    pipeline_records.append({

        "pipeline_id": pipeline["pipeline_id"],

        "pipeline_name": pipeline["pipeline_name"],

        "from_facility": pipeline["from_facility"],

        "to_facility": pipeline["to_facility"],

        "diameter_inch": pipeline["diameter_inch"],

        "fluid_type": pipeline["fluid_type"],

        "status": "Operational",

        "length_km": round(
            route.length / 1000,
            3
        ),

        "geometry": route

    })


gdf_pipelines = create_geodataframe(
    pipeline_records
)

print(f"Created {len(gdf_pipelines)} pipeline routes.")


# ============================================================
# 9. PROPOSED WELL LOCATIONS
# ============================================================

print("Generating proposed well locations...")

proposed_well_definitions = [

    # Development area near existing infrastructure
    {
        "well_id": "PRW-001",
        "x": 413700,
        "y": 9624300
    },

    {
        "well_id": "PRW-002",
        "x": 416500,
        "y": 9626700
    },

    {
        "well_id": "PRW-003",
        "x": 417000,
        "y": 9623000
    },

    # Deliberate potential forest conflict cases
    {
        "well_id": "PRW-004",
        "x": 417200,
        "y": 9627600
    },

    {
        "well_id": "PRW-005",
        "x": 414800,
        "y": 9628500
    },

    {
        "well_id": "PRW-006",
        "x": 412000,
        "y": 9622500
    },

    # Additional development locations
    {
        "well_id": "PRW-007",
        "x": 418000,
        "y": 9625000
    },

    {
        "well_id": "PRW-008",
        "x": 415000,
        "y": 9625500
    },

    {
        "well_id": "PRW-009",
        "x": 411800,
        "y": 9626500
    },

    {
        "well_id": "PRW-010",
        "x": 419000,
        "y": 9623500
    }

]

proposed_well_records = []

for well in proposed_well_definitions:

    proposed_well_records.append({

        "well_id": well["well_id"],

        "well_type": random.choice([
            "Oil",
            "Gas"
        ]),

        "project_status": random.choice([
            "Proposed",
            "Under Evaluation"
        ]),

        "geometry": Point(
            well["x"],
            well["y"]
        )

    })


gdf_proposed_wells = create_geodataframe(
    proposed_well_records
)

print(
    f"Created {len(gdf_proposed_wells)} proposed wells."
)


# ============================================================
# 10. EXPORT DATA TO GEOPACKAGE
# ============================================================

print("\nExporting datasets...")

# Remove the previous GeoPackage to avoid stale layers
if OUTPUT_FILE.exists():
    OUTPUT_FILE.unlink()


layers = {

    "study_area": gdf_study_area,

    "land_parcels": gdf_parcels,

    "forest_areas": gdf_forests,

    "existing_wells": gdf_wells,

    "production_facilities": gdf_facilities,

    "pipelines": gdf_pipelines,

    "proposed_wells": gdf_proposed_wells

}


for layer_name, gdf in layers.items():

    gdf.to_file(
        OUTPUT_FILE,
        layer=layer_name,
        driver="GPKG",
        engine="pyogrio"
    )

    print(
        f"Exported {layer_name}: {len(gdf)} features"
    )


# ============================================================
# 11. BASIC DATA VALIDATION
# ============================================================

print("\nValidating generated datasets...")

for layer_name, gdf in layers.items():

    invalid_count = (
        ~gdf.geometry.is_valid
    ).sum()

    empty_count = (
        gdf.geometry.is_empty
    ).sum()

    outside_count = (
        ~gdf.geometry.within(STUDY_AREA)
    ).sum()

    print(f"\nLayer: {layer_name}")
    print(f"Features: {len(gdf)}")
    print(f"Invalid geometries: {invalid_count}")
    print(f"Empty geometries: {empty_count}")
    print(f"Outside study area: {outside_count}")

    if invalid_count > 0:
        print("WARNING: Invalid geometries detected.")

    if empty_count > 0:
        print("WARNING: Empty geometries detected.")

    if outside_count > 0:
        print("WARNING: Features outside study area detected.")


# Check parcel coverage
parcel_total_area = gdf_parcels.geometry.area.sum()

coverage_percentage = (
    parcel_total_area / STUDY_AREA.area
) * 100

print("\nLand parcel coverage:")
print(f"{coverage_percentage:.2f}% of study area")


# ============================================================
# 12. COMPLETION
# ============================================================

print("\n========================================")
print("SYNTHETIC DATA GENERATION COMPLETED")
print("========================================")

print(f"Output file: {OUTPUT_FILE}")

print("\nAvailable GeoPackage layers:")

for layer_name in layers.keys():
    print(f"- {layer_name}")

print("\nAll datasets use CRS:", CRS)

print("========================================")
