
import streamlit as st

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Oil & Gas Land Intelligence",
    page_icon="🗺️",
    layout="wide"
)

# ============================================================
# APPLICATION HEADER
# ============================================================

st.title("Oil & Gas Land Intelligence")

st.caption(
    "Geospatial Land Management & Pipeline Route Screening Platform"
)

st.divider()

# ============================================================
# SIDEBAR
# ============================================================

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

# ============================================================
# OVERVIEW PAGE
# ============================================================

if page == "Overview":

    st.header("Project Overview")

    st.write(
        """
        This platform demonstrates the application of GIS
        technology for Oil & Gas land management and pipeline
        route screening.
        """
    )

    # KPI cards
    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Pipeline Length",
        "10.81 km"
    )

    col2.metric(
        "Affected Parcels",
        "18"
    )

    col3.metric(
        "Potential Acquisition",
        "21.61 ha"
    )

    col4.metric(
        "Forest Intersection",
        "7.12 ha"
    )

    st.divider()

    st.subheader("Screening Summary")

    col1, col2 = st.columns(2)

    with col1:

        st.info(
            """
            **Land Acquisition**

            - 18 affected parcels
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

# ============================================================
# OTHER MODULES - UNDER DEVELOPMENT
# ============================================================

elif page == "Interactive Map":

    st.header("Interactive GIS Map")

    st.info(
        "Interactive map implementation is our next development step."
    )

elif page == "Land Acquisition":

    st.header("Land Acquisition Analysis")

    st.info(
        "Parcel analysis and acquisition tables will be added here."
    )

elif page == "Environmental Screening":

    st.header("Environmental Screening")

    st.info(
        "Forest impact analysis will be added here."
    )
