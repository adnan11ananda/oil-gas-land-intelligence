
from pathlib import Path
import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

GPKG = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "oil_gas_land_intelligence.gpkg"
)

print("CHECKING GEOSPATIAL DATABASE")
print("=" * 50)

layers = gpd.list_layers(GPKG)

for _, row in layers.iterrows():

    layer_name = row["name"]

    gdf = gpd.read_file(GPKG, layer=layer_name)

    print(f"\nLayer: {layer_name}")
    print(f"Features: {len(gdf)}")
    print(f"CRS: {gdf.crs}")
    print(f"Geometry: {gdf.geom_type.unique()}")

    invalid = (~gdf.geometry.is_valid).sum()
    empty = gdf.geometry.is_empty.sum()

    print(f"Invalid geometries: {invalid}")
    print(f"Empty geometries: {empty}")

    assert len(gdf) > 0, "Empty layer detected!"
    assert gdf.crs.to_epsg() == 32748, "Incorrect CRS!"
    assert invalid == 0, "Invalid geometry detected!"
    assert empty == 0, "Empty geometry detected!"

print("\nALL DATASETS PASSED VALIDATION!")
