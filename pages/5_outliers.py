"""Meteorological outlier and anomaly analyses."""

import pandas as pd
from pymongo import MongoClient
import streamlit as st

from ind320_app.part4 import (
    WEATHER_PROPERTIES,
    plot_weather_lof,
    plot_weather_spc,
)
from ind320_app.ui import render_sidebar

render_sidebar()

st.title("Weather Outliers and Anomalies")
st.caption(
    "Data source: hourly ERA5 reanalysis from Open-Meteo, averaged across "
    "randomly sampled locations (the number is given in the Part 4 notebook) and read from MongoDB."
)

@st.cache_data(show_spinner="Loading ERA5 weather data from MongoDB...")
def load_weather(region: str) -> pd.DataFrame:
    if "mongo" not in st.secrets or not st.secrets["mongo"].get("uri"):
        raise RuntimeError("Add [mongo].uri to Streamlit secrets.")
    client = MongoClient(
        st.secrets["mongo"]["uri"],
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
    )
    try:
        client.admin.command("ping")
        records = list(
            client["ind320"]["weather"].find(
                {"region": region}, {"_id": 0}
            ).sort("timestamp", 1)
        )
    finally:
        client.close()
    if not records:
        raise ValueError(f"No MongoDB weather data found for {region}.")
    frame = pd.DataFrame(records)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    return frame.set_index("timestamp")

region = st.selectbox("Weather region data", ["NO3"], index=0)
selected_map_region = st.session_state.get("selected_el_region")
if selected_map_region:
    st.caption(f"Map selection stored in this session: {selected_map_region}")
try:
    weather = load_weather(region)
except Exception as exc:
    st.error(f"Could not load weather data from MongoDB: {exc}")
    st.stop()

property_options = list(WEATHER_PROPERTIES)
property_name = st.selectbox(
    "Weather property",
    property_options,
    index=property_options.index("temperature_2m"),
    format_func=lambda value: WEATHER_PROPERTIES[value][0],
)
spc_tab, lof_tab = st.tabs(["Seasonally adjusted / SPC", "Local anomalies / LOF"])
with spc_tab:
    cutoff = st.number_input("DCT frequency cut-off", min_value=2, value=12, step=1)
    sigma = st.number_input("SPC limit width", min_value=1.0, value=3.0, step=0.5)
    try:
        figure, summary = plot_weather_spc(
            weather[property_name], property_name, cutoff, sigma
        )
    except ValueError as exc:
        st.warning(str(exc))
    else:
        st.plotly_chart(figure, use_container_width=True)
        st.metric("SPC outliers", int(summary["outlier"].sum()))
        st.dataframe(summary[summary["outlier"]], use_container_width=True)
        st.caption(
            "The DCT removes slow variation before robust median/MAD limits "
            "classify unusual observations for the selected property."
        )

with lof_tab:
    contamination = st.slider("LOF outlier proportion", 0.001, 0.2, 0.01, 0.001)
    try:
        figure, summary = plot_weather_lof(
            weather[property_name], property_name, contamination
        )
    except ValueError as exc:
        st.warning(str(exc))
    else:
        st.plotly_chart(figure, use_container_width=True)
        st.metric("LOF anomalies", int(summary["anomaly"].sum()))
        st.dataframe(summary[summary["anomaly"]], use_container_width=True)
        st.caption(
            "LOF compares each selected weather observation with its local "
            "neighbours; the default highlights the most isolated 1%."
        )

with st.expander("Data source and method"):
    st.write(
        "NO3 is an electricity price area, so the sampled locations are "
        "drawn from the NO3 polygon of the NVE bidding-area layer "
        "(Budområder.shp), not from a precipitation region. The notebook "
        "downloads and averages ERA5 data for those locations, then publishes "
        "the 2024 hourly averages to MongoDB for this public page."
    )
