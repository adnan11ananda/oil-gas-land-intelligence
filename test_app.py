
import streamlit as st
import geopandas as gpd
import folium

from folium.plugins import Draw
from streamlit_folium import st_folium
from shapely.geometry import shape
from pathlib import Path
from src.route_screening import analyze_route

# =====================================================
# 1. PROJECT PATHS
# =====================================================

PROJECT_DIR = Path(__file__).parent

DATA_PATH = (
    PROJECT_DIR
    / "data"
    / "synthetic"
    / "oil_gas_land_intelligence_with_asset_parcels.gpkg"
)

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


# =====================================================
# 2. STREAMLIT CONFIGURATION & SESSION STATE
# =====================================================

st.set_page_config(
    page_title="Oil & Gas Land Intelligence",
    page_icon="🗺️",
    layout="wide"
)

# Store the user's drawn pipeline between reruns
if "drawn_pipeline" not in st.session_state:
    st.session_state.drawn_pipeline = None


# =====================================================
# 3. DATA LOADING FUNCTIONS
# =====================================================

@st.cache_data
def load_layer(file_path, layer_name):

    return gpd.read_file(
        file_path,
        layer=layer_name
    )


@st.cache_data
def load_alignment():

    return gpd.read_file(ALIGNMENT_PATH)


# =====================================================
# 4. INTERACTIVE GIS MAP
# =====================================================

def create_gis_map(
    row_gdf=None,
    drawn_pipeline_gdf=None,
    acquisition_gdf=None,
    forest_intersection_gdf=None
): 

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

    # Convert layers to WGS 84
    parcels = parcels.to_crs(epsg=4326)
    forests = forests.to_crs(epsg=4326)
    facilities = facilities.to_crs(epsg=4326)
    pipelines = pipelines.to_crs(epsg=4326)
    alignment = alignment.to_crs(epsg=4326)
    
    # Convert screening results to WGS 84 for map display
    if acquisition_gdf is not None:
        acquisition_gdf = acquisition_gdf.to_crs(epsg=4326)

    if forest_intersection_gdf is not None:
        forest_intersection_gdf = forest_intersection_gdf.to_crs(
            epsg=4326
        )

    # Calculate map center
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

    # Basemaps
    folium.TileLayer(
        "OpenStreetMap",
        name="OpenStreetMap",
        show=True
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name="Satellite Imagery",
        overlay=False,
        control=True
    ).add_to(m)

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
            tooltip=str(
                row.get("facility_name", "Facility")
            )
        ).add_to(m)

    # Existing proposed alignment
    folium.GeoJson(
        alignment,
        name="Existing Proposed Pipeline",
        style_function=lambda feature: {
            "color": "#ea580c",
            "weight": 4
        }
    ).add_to(m)

    # User-drawn pipeline alignment
    if drawn_pipeline_gdf is not None:

        folium.GeoJson(
            drawn_pipeline_gdf,
            name="User Drawn Pipeline",
            style_function=lambda feature: {
                "color": "#dc2626",
                "weight": 4
            }
        ).add_to(m)

    # Generated ROW corridor
    if row_gdf is not None:

        folium.GeoJson(
            row_gdf,
            name="Generated ROW Corridor",
            style_function=lambda feature: {
                "color": "#ea580c",
                "fillColor": "#fb923c",
                "weight": 2,
                "fillOpacity": 0.35
            },
            tooltip="Generated Pipeline ROW"
        ).add_to(m)

    # Affected land parcels
    if acquisition_gdf is not None and not acquisition_gdf.empty:

        folium.GeoJson(
            acquisition_gdf,
            name="Affected Land Parcels",
            style_function=lambda feature: {
                "color": "#dc2626",
                "fillColor": "#ef4444",
                "weight": 2,
                "fillOpacity": 0.45
            },
            tooltip="Affected Land Parcel"
        ).add_to(m)

    # Forest areas intersected by ROW
    if (
        forest_intersection_gdf is not None
        and not forest_intersection_gdf.empty
    ):

        folium.GeoJson(
            forest_intersection_gdf,
            name="Affected Forest Areas",
            style_function=lambda feature: {
                "color": "#166534",
                "fillColor": "#22c55e",
                "weight": 3,
                "fillOpacity": 0.65
            },
            tooltip="Forest Area Affected by ROW"
        ).add_to(m)

    # Pipeline drawing tools
    Draw(
        export=False,
        position="topleft",
        draw_options={
            "polyline": True,
            "polygon": False,
            "rectangle": False,
            "circle": False,
            "circlemarker": False,
            "marker": False
        },
        edit_options={
            "edit": True,
            "remove": True
        }
    ).add_to(m)

    # Layer control
    folium.LayerControl().add_to(m)

    return m


# =====================================================
# 5. APPLICATION HEADER
# =====================================================

st.title("Oil & Gas Land Intelligence")

st.caption(
    "Geospatial Land Management & Pipeline Route Screening Platform"
)


# =====================================================
# 6. NAVIGATION
# =====================================================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Module",
    [
        "Overview",
        "Interactive Map",
        "Land Acquisition",
        "Environmental Screening"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    "Portfolio Project | Synthetic Geospatial Dataset"
)


# =====================================================
# 7. OVERVIEW DASHBOARD
# =====================================================

if page == "Overview":

    st.header("Project Overview")

    st.write(
        "This platform demonstrates the application of GIS "
        "technology for Oil & Gas land management and "
        "pipeline route screening."
    )

    st.divider()

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


# =====================================================
# 8. INTERACTIVE GIS MAP
# =====================================================

elif page == "Interactive Map":

    st.header("Interactive GIS Map")

    st.subheader("Pipeline ROW Designer")

    # ROW width input
    row_width = st.number_input(
        "ROW Width (metres)",
        min_value=1.0,
        max_value=100.0,
        value=20.0,
        step=1.0
    )

    st.caption(
        f"Buffer distance: {row_width / 2:.1f} metres on each side"
    )

    try:

        # Initialize output layers
        row_gdf = None
        drawn_pipeline_gdf = None
        pipeline_gdf_metric = None
        screening_results = None

        # Process stored pipeline drawing
        if st.session_state.drawn_pipeline is not None:

            line = shape(
                st.session_state.drawn_pipeline["geometry"]
            )

            if line.geom_type != "LineString":
                raise ValueError(
                    "Please draw a pipeline using the polyline tool."
                )

            if line.is_empty or not line.is_valid or line.length == 0:
                raise ValueError(
                    "The drawn pipeline geometry is invalid or empty."
                )

            # Create pipeline GeoDataFrame in WGS 84
            pipeline_gdf = gpd.GeoDataFrame(
                {"pipeline_id": ["PROP-PL-002"]},
                geometry=[line],
                crs="EPSG:4326"
            )

            # Project to UTM Zone 48S for metric calculations
            pipeline_gdf_metric = pipeline_gdf.to_crs(
                epsg=32748
            )

            # Generate ROW buffer
            row_gdf_metric = pipeline_gdf_metric.copy()

            row_gdf_metric["geometry"] = (
                pipeline_gdf_metric.geometry.buffer(
                    row_width / 2
                )
            )
            # Run land acquisition and forest screening
            screening_results = analyze_route(
                pipeline_gdf_metric=pipeline_gdf_metric,
                row_gdf_metric=row_gdf_metric,
                data_path=DATA_PATH
            )

            # Convert geometries back to WGS 84 for map display
            row_gdf = row_gdf_metric.to_crs(
                epsg=4326
            )

            drawn_pipeline_gdf = pipeline_gdf

        # Create map with generated ROW
        gis_map = create_gis_map(
            row_gdf=row_gdf,
            drawn_pipeline_gdf=drawn_pipeline_gdf,
            acquisition_gdf=(
                screening_results["acquisition"]
                if screening_results is not None
                else None
            ),
            forest_intersection_gdf=(
                screening_results["forest_intersection"]
                if screening_results is not None
                else None
            )
)

        # Display map
        map_data = st_folium(
            gis_map,
            width=None,
            height=650,
            use_container_width=True,
            key="pipeline_map"
        )

        # Capture newly drawn pipeline
        drawings = map_data.get("all_drawings")

        if drawings:

            latest_drawing = drawings[-1]

            if (
                latest_drawing
                != st.session_state.drawn_pipeline
            ):

                st.session_state.drawn_pipeline = latest_drawing

                st.rerun()


        # Display ROW and screening results
        if row_gdf is not None:

            summary = screening_results["summary"]

            st.divider()
            st.subheader("Pipeline ROW Results")

            col1, col2 = st.columns(2)

            col1.metric(
                "Pipeline Length",
                f"{summary['pipeline_length_km']:.2f} km"
            )

            col2.metric(
                "ROW Area",
                f"{summary['row_area_ha']:.2f} ha"
            )

            st.success(
                "ROW corridor generated successfully!"
            )

            # Land acquisition summary
            st.divider()
            st.subheader("Land Acquisition Screening")

            col1, col2 = st.columns(2)

            col1.metric(
                "Affected Parcels",
                summary["affected_parcels"]
            )

            col2.metric(
                "Potential Acquisition Area",
                f"{summary['potential_acquisition_area_ha']:.2f} ha"
            )

            st.dataframe(
                screening_results["acquisition"][
                    [
                        "parcel_area_ha",
                        "row_area_ha",
                        "affected_percentage",
                        "acquisition_status"
                    ]
                ],
                use_container_width=True
            )

            # Environmental screening summary
            st.divider()
            st.subheader("Environmental Screening")

            col1, col2 = st.columns(2)

            col1.metric(
                "Affected Forest Polygons",
                summary["affected_forest_polygons"]
            )

            col2.metric(
                "Forest Intersection Area",
                f"{summary['forest_intersection_area_ha']:.2f} ha"
            )

            col3, col4 = st.columns(2)

            col3.metric(
                "ROW Within Forest",
                f"{summary['forest_percentage_of_row']:.2f}%"
            )

            col4.metric(
                "Pipeline Length Within Forest",
                f"{summary['pipeline_length_in_forest_km']:.2f} km"
            )

            st.dataframe(
                screening_results["forest_intersection"][
                    [
                        "forest_id",
                        "forest_type",
                        "forest_area_ha",
                        "intersection_area_ha",
                        "affected_percentage"
                    ]
                ],
                use_container_width=True
            )

        else:

            st.info(
                "Draw a pipeline alignment on the map to generate "
                "ROW and spatial screening results."
            )

    except Exception as e:

        st.error(
            f"Unable to process pipeline alignment: {e}"
        )


# =====================================================
# 9. LAND ACQUISITION
# =====================================================

elif page == "Land Acquisition":

    st.header("Land Acquisition Analysis")

    st.info(
        "Parcel analysis and acquisition tables will be added here."
    )


# =====================================================
# 10. ENVIRONMENTAL SCREENING
# =====================================================

elif page == "Environmental Screening":

    st.header("Environmental Screening")

    st.info(
        "Forest impact analysis will be added here."
    )
