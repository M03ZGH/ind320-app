"""Meteorological outlier and anomaly analyses."""

import matplotlib.pyplot as plt
import pandas as pd
from pymongo import MongoClient
import streamlit as st

from ind320_app.part3 import (
    plot_lof_temperature,
    plot_spc_precipitation,
)
from ind320_app.ui import render_sidebar

render_sidebar()

st.title("Weather Outliers and Anomalies")
st.caption(
    "Data source: hourly ERA5 reanalysis from Open-Meteo, averaged across 1000 "
    "sampled NVE-region locations and read from MongoDB."
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

region = st.selectbox("Region", ["NO3"], index=0)
try:
    weather = load_weather(region)
except Exception as exc:
    st.error(f"Could not load weather data from MongoDB: {exc}")
    st.stop()

spc_tab, lof_tab = st.tabs(["Precipitation / SPC", "Temperature / LOF"])
with spc_tab:
    cutoff = st.number_input("DCT frequency cut-off", min_value=2, value=12, step=1)
    sigma = st.number_input("SPC standard deviations", min_value=1.0, value=3.0, step=0.5)
    figure, summary = plot_spc_precipitation(weather["precipitation"], cutoff, sigma)
    st.pyplot(figure)
    plt.close(figure)
    st.metric("SPC outliers", int(summary["outlier"].sum()))
    st.dataframe(summary[summary["outlier"]], use_container_width=True)

with lof_tab:
    contamination = st.slider("LOF outlier proportion", 0.001, 0.2, 0.01, 0.001)
    figure, summary = plot_lof_temperature(weather["temperature_2m"], contamination)
    st.pyplot(figure)
    plt.close(figure)
    st.metric("LOF anomalies", int(summary["anomaly"].sum()))
    st.dataframe(summary[summary["anomaly"]], use_container_width=True)

with st.expander("Data source"):
    st.write(
        "The notebook sampled 1000 locations inside the NVE region and downloaded "
        "hourly ERA5 reanalysis data from Open-Meteo. The spatial averages are "
        "stored in MongoDB and read by this public Streamlit page."
    )
