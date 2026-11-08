import streamlit as st

from ind320_app.ui import render_sidebar

render_sidebar()

# This page documents the purpose and development method of the application.
st.title("About This Project")
st.write(
    "This application is the online part of the IND320 Data to Decision project "
    "at NMBU. The notebook documents NVE and Open-Meteo API retrieval, "
    "weather analysis, Spark/Cassandra processing and MongoDB publication."
)

st.subheader("Data used in the app")
st.markdown(
    "- **Reservoir pages:** current observations from the NVE API.\n"
    "- **Weather page:** hourly NO3 averages from ERA5, downloaded from Open-Meteo "
    "using 1000 sampled NVE-region locations and stored in MongoDB.\n"
    "- **Cross-border page:** ENTSO-E observations processed with Spark/Cassandra "
    "and stored in MongoDB."
)

st.subheader("AI usage")
st.write(
    "AI tools were used for troubleshooting, explaining APIs and improving code "
    "structure. All suggestions were reviewed, adapted and tested by the student."
)
