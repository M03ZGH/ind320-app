import streamlit as st

from ind320_app.ui import render_sidebar

# Configure the shared layout before rendering any page content.
st.set_page_config(
    page_title="IND320 Data to Decision",
    page_icon="💧",
    layout="wide",
)
render_sidebar()

st.title("Data to Decision")
st.markdown(
    "An interactive portfolio for Norwegian reservoir statistics, ERA5 weather "
    "analysis and cross-border electricity flows."
)

st.subheader("Project overview")
st.write(
    "Use the pages in the sidebar to explore live NVE reservoir observations, "
    "prepared ERA5 weather observations, outliers, time-series structure and "
    "ENTSO-E cross-border electricity flows."
)

st.caption(
    "NVE area types and ENTSO-E bidding zones are separate classifications. "
    "For example, the Norway–Denmark interconnector is queried as NO_2 ↔ DK_1."
)

with st.expander("Data sources"):
    st.markdown(
        "- [NVE Magasinstatistikk API](https://biapi.nve.no/magasinstatistikk/swagger/index.html)\n"
        "- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (ERA5)\n"
        "- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)\n"
        "- MongoDB Atlas supplies prepared weather and cross-border flow observations.\n"
        "- Spark and Cassandra are used in the Part 2 notebook pipeline."
    )
