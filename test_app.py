
import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from pathlib import Path

PROJECT_DIR = Path(__file__).parent

DATA_PATH = (
    PROJECT_DIR
    / "data"
    / "synthetic"
    / "oil_gas_land_intelligence_with_asset_parcels.gpkg"
)

@st.cache_data
def load_layer(file_path, layer_name):
    gdf = gpd.read_file(
        file_path,
        layer=layer_name
    )

    return gdf


@st.cache_data
def load_alignment():
    return gpd.read_file(ALIGNMENT_PATH)


def create_gis_map():

    # Load GIS layers
    parcels = load_layer(
        DATA_PATH,
        "original_land_parcels"
    )

    forests = load_layer(
        DATA_PATH,
        "forest_areas"
    )

    facilities = load_layer(
        DATA_PATH,
        "production_facilities"
    )

    pipelines = load_layer(
        DATA_PATH,
        "pipelines"
    )

    alignment = load_alignment()

    # Convert layers to WGS 84 for web mapping
    layers = [
        parcels,
        forests,
        facilities,
        pipelines,
        alignment
    ]

    layers = [
        layer.to_crs(epsg=4326)
        for layer in layers
    ]

    parcels, forests, facilities, pipelines, alignment = layers

    # Calculate map center from study area
    bounds = parcels.total_bounds

    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14,
        tiles=None,
        control_scale=True
    )

    # OpenStreetMap
    folium.TileLayer(
        "OpenStreetMap",
        name="OpenStreetMap",
        show=True
    ).add_to(m)

    # Satellite imagery
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name="Satellite Imagery",
        overlay=False,
        control=True
    ).add_to(m)

    # Topographic map
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name="Topographic Map",
        overlay=False,
        control=True
    ).add_to(m)



    # Land parcels
    folium.GeoJson(
        parcels,
        name="Land Parcels",
        style_function=lambda feature: {
            "color": "#64748b",
            "weight": 1,
            "fillOpacity": 0.05
        }
    ).add_to(m)

    # Forest areas
    folium.GeoJson(
        forests,
        name="Forest Areas",
        style_function=lambda feature: {
            "color": "#15803d",
            "fillColor": "#22c55e",
            "weight": 2,
            "fillOpacity": 0.35
        }
    ).add_to(m)

    # Existing pipelines
    folium.GeoJson(
        pipelines,
        name="Existing Pipelines",
        style_function=lambda feature: {
            "color": "#2563eb",
            "weight": 3
        }
    ).add_to(m)

    # Production facilities
    for _, row in facilities.iterrows():

        point = row.geometry

        folium.CircleMarker(
            location=[point.y, point.x],
            radius=5,
            color="red",
            fill=True,
            fill_opacity=0.8,
            tooltip=str(row.get("facility_name", "Facility"))
        ).add_to(m)

    # Proposed pipeline alignment
    folium.GeoJson(
        alignment,
        name="Proposed Pipeline",
        style_function=lambda feature: {
            "color": "#ea580c",
            "weight": 4
        }
    ).add_to(m)

    folium.LayerControl().add_to(m)

    return m

ALIGNMENT_PATH = (
    PROJECT_DIR
    / "data"
    / "synthetic"
    / "proposed_pipeline_alignment.gpkg"
)

SCREENING_PATH = (
    PROJECT_DIR
    / "outputs"
    / "reports"
    / "proposed_pipeline_screening.gpkg"
)

st.set_page_config(
    page_title="Oil & Gas Land Intelligence",
    page_icon="🗺️",
    layout="wide"
)

st.title("Oil & Gas Land Intelligence")
st.caption("Geospatial Land Management & Pipeline Route Screening Platform")

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Module",
    ["Overview", "Interactive Map", "Land Acquisition", "Environmental Screening"]
)

st.sidebar.divider()
st.sidebar.caption("Portfolio Project | Synthetic Geospatial Dataset")

if page == "Overview":

    st.header("Project Overview")

    st.write(
        "This platform demonstrates the application of GIS technology "
        "for Oil & Gas land management and pipeline route screening."
    )

    st.divider()

    # Key Performance Indicators
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Pipeline Length", "10.81 km")
    col2.metric("Affected Parcels", "18")
    col3.metric("Potential Acquisition", "21.61 ha")
    col4.metric("Forest Intersection", "7.12 ha")

    st.divider()

    st.subheader("Screening Summary")

    col1, col2 = st.columns(2)

    with col1:
        st.info(
            """
            **Land Acquisition**

            - 18 affected land parcels
            - 21.6135 ha potential acquisition area
            """
        )

    with col2:
        st.warning(
            """
            **Environmental Screening**

            - 2 affected forest polygons
            - 7.1175 ha forest intersection
            - 32.93% of ROW within forest
            """
        )

elif page == "Interactive Map":

    st.header("Interactive GIS Map")

    try:
        gis_map = create_gis_map()

        st_folium(
            gis_map,
            width=None,
            height=650,
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Unable to load GIS map: {e}")

elif page == "Land Acquisition":
    st.header("Land Acquisition Analysis")
    st.info("Parcel analysis and acquisition tables will be added here.")

elif page == "Environmental Screening":
    st.header("Environmental Screening")
    st.info("Forest impact analysis will be added here.")
