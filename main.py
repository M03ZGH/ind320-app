import streamlit as st

from ind320_app.ui import render_sidebar

# Set the shared presentation before the navigation tree is created.
st.set_page_config(
    page_title="IND320 Data to Decision",
    page_icon="💧",
    layout="wide",
)
render_sidebar()

pages = {
    "Project": [
        st.Page("pages/0_overview.py", title="Overview", icon="💧", default=True),
    ],
    "Explore": [
        st.Page("pages/1_data.py", title="NVE Data", icon="🗃️"),
        st.Page("pages/2_plot.py", title="Reservoir Development", icon="📈"),
        st.Page("pages/3_map.py", title="Map", icon="🗺️"),
        st.Page(
            "pages/4_correlation.py",
            title="Weather Correlation",
            icon="🌦️",
        ),
        st.Page(
            "pages/5_outliers.py",
            title="Weather Outliers",
            icon="🔎",
        ),
        st.Page(
            "pages/6_time_series.py",
            title="Time-Series Analysis",
            icon="〰️",
        ),
    ],
    "Predict": [
        st.Page("pages/7_forecast.py", title="Filling Forecast", icon="🔮"),
    ],
    "Data sources": [
        st.Page("pages/8_currency.py", title="Currency Rates", icon="💱"),
        st.Page(
            "pages/9_crossborder.py",
            title="Cross-Border Flows",
            icon="⚡",
        ),
    ],
}
st.navigation(pages).run()
