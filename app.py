
import pandas as pd
import streamlit as st
import geopandas as gpd
import folium
import tempfile

from folium.plugins import Draw
from streamlit_folium import st_folium
from shapely.geometry import shape
from pathlib import Path
from src.route_screening import (
    analyze_route,
    create_row_corridor,
    load_screening_layers
)
from src.alignment_import import (
    AlignmentImportError,
    load_alignment,
    overlaps_study_area
)

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

SCREENING_PATH = (
    PROJECT_DIR
    / "outputs"
    / "reports"
    / "proposed_pipeline_screening.gpkg"
)

# CRS choices offered when an imported file has no CRS
ASSUMED_CRS_OPTIONS = {
    "Reject files without a CRS": None,
    "EPSG:4326 (WGS 84, lon/lat)": "EPSG:4326",
    "EPSG:32748 (WGS 84 / UTM 48S)": "EPSG:32748",
}


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

# Shared screening outputs remain available when users navigate between pages.
for state_key, default_value in {
    "active_pipeline_gdf": None,
    "active_row_gdf": None,
    "active_screening_results": None,
    "active_row_width": None,
    "active_pipeline_id": None,
    "active_acquisition_report": None,
    "active_forest_report": None,
    "active_consolidated_report": None,
}.items():
    if state_key not in st.session_state:
        st.session_state[state_key] = default_value


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
def load_screening_data(file_path):
    return load_screening_layers(file_path)

@st.cache_data(show_spinner=False)
def parse_alignment_upload(file_bytes, file_name, assume_crs):

    return load_alignment(
        file_bytes,
        file_name,
        assume_crs=assume_crs
    )

def prepare_alignment_exports(
    pipeline_gdf,
    row_gdf,
    screening_results
):

    # Convert all layers to metric CRS
    pipeline_metric = pipeline_gdf.to_crs(epsg=32748).copy()
    row_metric = row_gdf.to_crs(epsg=32748).copy()

    acquisition_metric = (
        screening_results["acquisition"]
        .to_crs(epsg=32748)
        .copy()
    )

    forest_metric = (
        screening_results["forest_intersection"]
        .to_crs(epsg=32748)
        .copy()
    )

    # Calculate pipeline length
    pipeline_metric["length_km"] = (
        pipeline_metric.geometry.length / 1000
    )

    # Create GeoPackage
    with tempfile.TemporaryDirectory() as temp_dir:

        gpkg_path = (
            Path(temp_dir) / "proposed_pipeline_package.gpkg"
        )

        # Layer 1: Pipeline alignment
        pipeline_metric.to_file(
            gpkg_path,
            layer="pipeline_alignment",
            driver="GPKG"
        )

        # Layer 2: ROW corridor
        row_metric.to_file(
            gpkg_path,
            layer="row_corridor",
            driver="GPKG",
            mode="a"
        )

        # Layer 3: Acquisition screening
        acquisition_metric.to_file(
            gpkg_path,
            layer="acquisition_screening",
            driver="GPKG",
            mode="a"
        )

        # Layer 4: Forest screening
        forest_metric.to_file(
            gpkg_path,
            layer="forest_screening",
            driver="GPKG",
            mode="a"
        )

        gpkg_data = gpkg_path.read_bytes()

    # Export pipeline centerline as GeoJSON
    pipeline_geojson = (
        pipeline_gdf
        .to_crs(epsg=4326)
        .to_json()
        .encode("utf-8")
    )

    return gpkg_data, pipeline_geojson


# =====================================================
# 4. INTERACTIVE GIS MAP
# =====================================================

def create_gis_map(
    row_gdf=None,
    drawn_pipeline_gdf=None,
    acquisition_gdf=None,
    forest_intersection_gdf=None,
    show_draw_tools=True,
    fit_to_alignment=False
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

    # Convert layers to WGS 84
    parcels = parcels.to_crs(epsg=4326)
    forests = forests.to_crs(epsg=4326)
    facilities = facilities.to_crs(epsg=4326)
    pipelines = pipelines.to_crs(epsg=4326)
    
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


    # User-drawn pipeline alignment
    if drawn_pipeline_gdf is not None:

        folium.GeoJson(
            drawn_pipeline_gdf,
            name="Proposed Pipeline Alignment",
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
    if show_draw_tools:
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

    # Zoom to an imported alignment
    if fit_to_alignment and drawn_pipeline_gdf is not None:

        minx, miny, maxx, maxy = drawn_pipeline_gdf.total_bounds

        m.fit_bounds([[miny, minx], [maxy, maxx]])

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
    "Alignment Designer",
    "Land Acquisition",
    "Forest Area Overlay Report",
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

    st.header("Oil & Gas Land Intelligence")
    st.caption(
        "Geospatial Land Management | Pipeline ROW Design | "
        "Land Acquisition & Environmental Screening"
    )

    st.markdown(
        """
        This platform supports preliminary geospatial screening
        of proposed Oil & Gas pipeline routes. It combines pipeline
        alignment design, Right of Way (ROW) generation, land
        acquisition screening, and environmental overlay analysis.
        """
    )

    st.divider()

    # # =====================================================
    # # 1. CURRENT SCREENING STATUS
    # # =====================================================

    # st.subheader("Current Project Screening")

    # screening_results = st.session_state.active_screening_results
    # pipeline_gdf = st.session_state.active_pipeline_gdf

    # if screening_results is not None and pipeline_gdf is not None:

    #     summary = screening_results["summary"]

    #     st.success(
    #         f"Screening results available for pipeline: "
    #         f"{st.session_state.active_pipeline_id}"
    #     )

    #     # KPI row 1
    #     col1, col2, col3, col4 = st.columns(4)

    #     col1.metric(
    #         "Pipeline Length",
    #         f'{summary["pipeline_length_km"]:.2f} km'
    #     )

    #     col2.metric(
    #         "ROW Width",
    #         f'{st.session_state.active_row_width:.1f} m'
    #     )

    #     col3.metric(
    #         "Total ROW Area",
    #         f'{summary["row_area_ha"]:.2f} ha'
    #     )

    #     col4.metric(
    #         "Affected Parcels",
    #         f'{summary["affected_parcels"]}'
    #     )

    #     # KPI row 2
    #     col1, col2, col3, col4 = st.columns(4)

    #     col1.metric(
    #         "Potential Acquisition",
    #         f'{summary["potential_acquisition_area_ha"]:.2f} ha'
    #     )

    #     col2.metric(
    #         "Affected Forest Areas",
    #         f'{summary["affected_forest_polygons"]}'
    #     )

    #     col3.metric(
    #         "Forest Intersection",
    #         f'{summary["forest_intersection_area_ha"]:.2f} ha'
    #     )

    #     col4.metric(
    #         "ROW Within Forest",
    #         f'{summary["forest_percentage_of_row"]:.2f}%'
    #     )

    #     st.caption(
    #         "Metrics represent the latest alignment analyzed in "
    #         "the Alignment Designer."
    #     )

    #     # Screening summary
    #     st.divider()
    #     st.subheader("Screening Highlights")

    #     col1, col2 = st.columns(2)

    #     with col1:
    #         st.markdown("#### Land Acquisition")

    #         st.write(
    #             f'**{summary["affected_parcels"]}** land parcels '
    #             "intersect the proposed ROW."
    #         )

    #         st.write(
    #             f'Potential acquisition area: '
    #             f'**{summary["potential_acquisition_area_ha"]:.2f} ha**'
    #         )

    #     with col2:
    #         st.markdown("#### Environmental Screening")

    #         st.write(
    #             f'**{summary["affected_forest_polygons"]}** forest '
    #             "polygons intersect the proposed ROW."
    #         )

    #         st.write(
    #             f'Forest intersection area: '
    #             f'**{summary["forest_intersection_area_ha"]:.2f} ha**'
    #         )

    # else:

    #     st.info(
    #         "No pipeline screening results are available yet. "
    #         "Open Alignment Designer to draw or import a proposed "
    #         "pipeline alignment and run the spatial analysis."
    #     )

    #     col1, col2, col3 = st.columns(3)

    #     col1.metric("Pipeline Length", "—")
    #     col2.metric("Affected Parcels", "—")
    #     col3.metric("Potential Acquisition", "—")

    # st.divider()

    # =====================================================
    # 2. APPLICATION WORKFLOW
    # =====================================================

    st.subheader("Application Workflow")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 1. Alignment Design")
        st.write(
            """
            - Draw or import a pipeline alignment
            - Define the required ROW width
            - Generate the ROW corridor
            """
        )

    with col2:
        st.markdown("#### 2. Land Acquisition")
        st.write(
            """
            - Identify affected land parcels
            - Calculate ROW intersection areas
            - Review ownership information
            """
        )

    with col3:
        st.markdown("#### 3. Forest Area Overlay")
        st.write(
            """
            - Identify forest area intersections
            - Calculate affected forest areas
            - Review potential environmental constraints
            """
        )

    st.divider()

    # =====================================================
    # 3. REFERENCE DATA
    # =====================================================

    st.subheader("Available Reference Layers")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            """
            - **Land Parcels:** Synthetic cadastral boundaries
            - **Existing Pipelines:** Existing pipeline network
            - **Production Facilities:** Oil & Gas facilities
            """
        )

    with col2:
        st.markdown(
            """
            - **Forest Areas:** Environmental reference polygons
            - **Study Area:** Project analysis boundary
            - **Proposed Alignment:** User-drawn or imported route
            """
        )

    st.divider()

    # =====================================================
    # 4. DATA DISCLAIMER
    # =====================================================

    st.caption(
        """
        **Portfolio Demonstration**

        All spatial data used in this application is synthetic
        and intended for illustrative purposes only. Screening
        results are preliminary spatial indicators and do not
        represent legal land acquisition decisions, approved
        engineering designs, or formal environmental assessments.
        """
    )

# =====================================================
# 8. INTERACTIVE GIS MAP
# =====================================================

elif page == "Alignment Designer":

    st.header("Pipeline Alignment Designer")

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

    # Alignment source: draw on the map or import a file
    alignment_source = st.radio(
        "Alignment source",
        ["Draw on map", "Import file"],
        horizontal=True,
        key="alignment_source"
    )

    imported_line = None
    imported_name = None

    if alignment_source == "Import file":

        st.caption(
            "Upload one continuous polyline: GeoJSON, GeoPackage, "
            "zipped Shapefile or KML."
        )

        uploaded_file = st.file_uploader(
            "Proposed alignment file",
            type=["geojson", "json", "gpkg", "zip", "kml"]
        )

        assumed_crs_label = st.selectbox(
            "If the file has no CRS, assume",
            list(ASSUMED_CRS_OPTIONS)
        )

        if uploaded_file is not None:

            try:

                imported = parse_alignment_upload(
                    uploaded_file.getvalue(),
                    uploaded_file.name,
                    ASSUMED_CRS_OPTIONS[assumed_crs_label]
                )

                study_area = load_layer(DATA_PATH, "study_area")

                if not overlaps_study_area(imported.line, study_area):

                    st.error(
                        "The alignment does not intersect the study "
                        "area. Check the file's CRS."
                    )

                else:

                    imported_line = imported.line
                    imported_name = Path(uploaded_file.name).stem

                    st.success(
                        f"Imported '{uploaded_file.name}' "
                        f"(source CRS: {imported.source_crs})."
                    )

                    for note in imported.notes:
                        st.info(note)

            except AlignmentImportError as e:

                st.error(str(e))

    try:

        # Initialize output layers
        row_gdf = None
        drawn_pipeline_gdf = None
        pipeline_gdf_metric = None
        screening_results = None

        # Resolve the alignment: imported file or map drawing
        line = None
        pipeline_id = "PROP-PL-002"

        if alignment_source == "Import file":

            line = imported_line

            if imported_name:
                pipeline_id = imported_name

        elif st.session_state.drawn_pipeline is not None:

            line = shape(
                st.session_state.drawn_pipeline["geometry"]
            )

            if line.geom_type != "LineString":
                raise ValueError(
                    "Please draw a pipeline using the polyline tool."
                )

        if line is not None:

            if line.is_empty or not line.is_valid or line.length == 0:
                raise ValueError(
                    "The pipeline geometry is invalid or empty."
                )

            # Create pipeline GeoDataFrame in WGS 84
            pipeline_gdf = gpd.GeoDataFrame(
                {"pipeline_id": [pipeline_id]},
                geometry=[line],
                crs="EPSG:4326"
            )

            # Project to UTM Zone 48S for metric calculations
            pipeline_gdf_metric = pipeline_gdf.to_crs(
                epsg=32748
            )

            # Generate ROW corridor (flat ends, shared with the CLI)
            row_gdf_metric = create_row_corridor(
                pipeline_gdf_metric,
                row_width
            )

            # Run land acquisition and forest screening
            parcels, forests = load_screening_data(DATA_PATH)

            screening_results = analyze_route(
                pipeline_gdf_metric,
                row_gdf_metric,
                parcels,
                forests
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
            ),
            show_draw_tools=(alignment_source == "Draw on map"),
            fit_to_alignment=(alignment_source == "Import file")
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

        if alignment_source == "Draw on map" and drawings:

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


            # Current Project Screening
            st.divider()
            st.subheader("Current Project Screening")

            st.success(
                f"Screening results available for pipeline: {pipeline_id}"
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Pipeline Length",
                f"{summary['pipeline_length_km']:.2f} km"
            )
            col2.metric(
                "ROW Width",
                f"{row_width:.1f} m"
            )
            col3.metric(
                "Total ROW Area",
                f"{summary['row_area_ha']:.2f} ha"
            )
            col4.metric(
                "Affected Parcels",
                summary["affected_parcels"]
            )

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Potential Acquisition",
                f"{summary['potential_acquisition_area_ha']:.2f} ha"
            )
            col2.metric(
                "Affected Forest Areas",
                summary["affected_forest_polygons"]
            )
            col3.metric(
                "Forest Intersection",
                f"{summary['forest_intersection_area_ha']:.2f} ha"
            )
            col4.metric(
                "ROW Within Forest",
                f"{summary['forest_percentage_of_row']:.2f}%"
            )

            st.caption(
                "Metrics represent the latest alignment analyzed "
                "in the Alignment Designer."
            )


            # Export Proposed Pipeline Alignment
            st.divider()
            st.subheader("Export Proposed Pipeline Alignment")

            # Generate export files
            gpkg_data, geojson_data = prepare_alignment_exports(
                drawn_pipeline_gdf,
                row_gdf,
                screening_results
            )

            col1, col2 = st.columns(2)

            with col1:
                st.download_button(
                    label="Download GeoPackage",
                    data=gpkg_data,
                    file_name="proposed_pipeline_package.gpkg",
                    mime="application/geopackage+sqlite3"
                )

            with col2:
                st.download_button(
                    label="Download GeoJSON",
                    data=geojson_data,
                    file_name="proposed_pipeline_alignment.geojson",
                    mime="application/geo+json"
                )

            # Prepare detailed reports for their dedicated pages.
            acquisition_report = screening_results["acquisition"][
                [
                    "parcel_id",
                    "parent_parcel_id",
                    "owner_type",
                    "land_status",
                    "parcel_area_ha",
                    "row_area_ha",
                    "affected_percentage",
                    "acquisition_status"
                ]
            ].copy()

            acquisition_report["parcel_area_ha"] = (
                acquisition_report["parcel_area_ha"].round(4)
            )
            acquisition_report["row_area_ha"] = (
                acquisition_report["row_area_ha"].round(4)
            )
            acquisition_report["affected_percentage"] = (
                acquisition_report["affected_percentage"].round(2)
            )

            forest_report = screening_results["forest_intersection"][
                [
                    "forest_id",
                    "forest_type",
                    "forest_area_ha",
                    "intersection_area_ha",
                    "affected_percentage"
                ]
            ].copy()

            for column in [
                "forest_area_ha",
                "intersection_area_ha",
                "affected_percentage"
            ]:
                forest_report[column] = forest_report[column].round(4)

            # Persist the latest analysis so the detailed pages can use
            # exactly the same alignment and screening results.
            st.session_state.active_pipeline_gdf = drawn_pipeline_gdf
            st.session_state.active_row_gdf = row_gdf
            st.session_state.active_screening_results = screening_results
            st.session_state.active_row_width = row_width
            st.session_state.active_pipeline_id = pipeline_id
            st.session_state.active_acquisition_report = acquisition_report
            st.session_state.active_forest_report = forest_report

            # =====================================================
            # CONSOLIDATED PIPELINE SCREENING REPORT
            # =====================================================

            summary = screening_results["summary"]

            # 1. Pipeline information
            report_rows = [
                {
                    "category": "Pipeline",
                    "indicator": "Pipeline Length",
                    "value": summary["pipeline_length_km"],
                    "unit": "km"
                },
                {
                    "category": "Pipeline",
                    "indicator": "ROW Width",
                    "value": row_width,
                    "unit": "m"
                },
                {
                    "category": "Pipeline",
                    "indicator": "Total ROW Area",
                    "value": summary["row_area_ha"],
                    "unit": "ha"
                },

                # 2. Land acquisition
                {
                    "category": "Land Acquisition",
                    "indicator": "Affected Parcels",
                    "value": summary["affected_parcels"],
                    "unit": "parcels"
                },
                {
                    "category": "Land Acquisition",
                    "indicator": "Potential Acquisition Area",
                    "value": summary["potential_acquisition_area_ha"],
                    "unit": "ha"
                },

                # 3. Environmental screening
                {
                    "category": "Environmental",
                    "indicator": "Affected Forest Polygons",
                    "value": summary["affected_forest_polygons"],
                    "unit": "polygons"
                },
                {
                    "category": "Environmental",
                    "indicator": "Forest Intersection Area",
                    "value": summary["forest_intersection_area_ha"],
                    "unit": "ha"
                },
                {
                    "category": "Environmental",
                    "indicator": "ROW Within Forest",
                    "value": summary["forest_percentage_of_row"],
                    "unit": "%"
                },
                {
                    "category": "Environmental",
                    "indicator": "Pipeline Length Within Forest",
                    "value": summary["pipeline_length_in_forest_km"],
                    "unit": "km"
                }
            ]

            # 4. Ownership breakdown
            ownership_summary = (
                acquisition_report
                .groupby("owner_type", as_index=False)
                .agg(
                    affected_parcels=("parcel_id", "count"),
                    potential_acquisition_ha=("row_area_ha", "sum")
                )
            )

            for _, row in ownership_summary.iterrows():

                report_rows.append({
                    "category": "Ownership Breakdown",
                    "indicator": row["owner_type"],
                    "value": round(row["potential_acquisition_ha"], 4),
                    "unit": "ha"
                })

            # 5. Create consolidated DataFrame
            consolidated_report = pd.DataFrame(report_rows)
            
            # Export consolidated report
            consolidated_csv = consolidated_report.to_csv(
                index=False,
                encoding="utf-8-sig"
            )

            st.divider()
            st.session_state.active_consolidated_report = consolidated_report

            st.subheader("Proposed ROW Land Acquisition Preliminary Report")


            st.download_button(
                label="Download Preliminary Report (CSV)",
                data=consolidated_csv,
                file_name="proposed_row_land_acquisition_preliminary_report.csv",
                mime="text/csv"
            )

        else:

            st.info(
                "Upload an alignment file above to generate "
                "ROW and spatial screening results."
                if alignment_source == "Import file"
                else
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

    st.header("Land Acquisition Screening")

    screening_results = st.session_state.active_screening_results
    pipeline_gdf = st.session_state.active_pipeline_gdf
    row_gdf = st.session_state.active_row_gdf
    acquisition_report = st.session_state.active_acquisition_report

    if (
        screening_results is None
        or acquisition_report is None
        or pipeline_gdf is None
        or row_gdf is None
    ):
        st.info(
            "No screening results are available yet. Go to Alignment "
            "Designer and import or draw a proposed pipeline alignment "
            "to generate the land acquisition screening."
        )
    else:
        summary = screening_results["summary"]

        col1, col2, col3 = st.columns(3)
        col1.metric("Affected Parcels", summary["affected_parcels"])
        col2.metric(
            "Potential Acquisition Area",
            f"{summary['potential_acquisition_area_ha']:.2f} ha"
        )
        col3.metric(
            "ROW Width",
            f"{st.session_state.active_row_width:.1f} m"
        )

        st.caption(
            f"Pipeline: {st.session_state.active_pipeline_id} | "
            "Preliminary spatial screening only."
        )

        st.subheader("Affected Land Parcels Map")
        acquisition_map = create_gis_map(
            row_gdf=row_gdf,
            drawn_pipeline_gdf=pipeline_gdf,
            acquisition_gdf=screening_results["acquisition"],
            show_draw_tools=False,
            fit_to_alignment=True
        )
        st_folium(
            acquisition_map,
            width=None,
            height=550,
            use_container_width=True,
            key="land_acquisition_map"
        )

        st.subheader("Land Acquisition Screening Report")
        st.dataframe(
            acquisition_report,
            use_container_width=True,
            hide_index=True
        )

        acquisition_csv = acquisition_report.to_csv(
            index=False,
            encoding="utf-8-sig"
        )
        st.download_button(
            label="Download Land Acquisition Report (CSV)",
            data=acquisition_csv,
            file_name="land_acquisition_screening.csv",
            mime="text/csv"
        )


# =====================================================
# 10. ENVIRONMENTAL SCREENING
# =====================================================

elif page == "Forest Area Overlay Report":

    st.header("Forest Area Overlay Report")

    screening_results = st.session_state.active_screening_results
    pipeline_gdf = st.session_state.active_pipeline_gdf
    row_gdf = st.session_state.active_row_gdf
    forest_report = st.session_state.active_forest_report

    if (
        screening_results is None
        or forest_report is None
        or pipeline_gdf is None
        or row_gdf is None
    ):
        st.info(
            "No environmental screening results are available yet. "
            "Go to Alignment Designer and import or draw a proposed "
            "pipeline alignment to generate the forest area overlay report."
        )
    else:
        summary = screening_results["summary"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "Affected Forest Polygons",
            summary["affected_forest_polygons"]
        )
        col2.metric(
            "Forest Intersection Area",
            f"{summary['forest_intersection_area_ha']:.4f} ha"
        )
        col3.metric(
            "ROW Within Forest",
            f"{summary['forest_percentage_of_row']:.2f}%"
        )
        col4.metric(
            "Pipeline Length Within Forest",
            f"{summary['pipeline_length_in_forest_km']:.2f} km"
        )

        st.caption(
            f"Pipeline: {st.session_state.active_pipeline_id} | "
            "Preliminary spatial overlay; not a formal environmental approval."
        )

        st.subheader("Forest Area Overlay Map")
        forest_map = create_gis_map(
            row_gdf=row_gdf,
            drawn_pipeline_gdf=pipeline_gdf,
            forest_intersection_gdf=screening_results["forest_intersection"],
            show_draw_tools=False,
            fit_to_alignment=True
        )
        st_folium(
            forest_map,
            width=None,
            height=550,
            use_container_width=True,
            key="forest_screening_map"
        )

        st.subheader("Forest Area Overlay Report")
        st.dataframe(
            forest_report,
            use_container_width=True,
            hide_index=True
        )

        forest_csv = forest_report.to_csv(
            index=False,
            encoding="utf-8-sig"
        )
        st.download_button(
            label="Download Forest Area Overlay Report (CSV)",
            data=forest_csv,
            file_name="forest_area_overlay_report.csv",
            mime="text/csv"
        )
