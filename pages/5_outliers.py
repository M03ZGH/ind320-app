"""Meteorological outlier and anomaly analyses."""

from datetime import date

import streamlit as st

from ind320_app.weather import AREAS, LATEST_AVAILABLE, load_area_weather
from ind320_app.part4 import (
    WEATHER_PROPERTIES,
    plot_weather_lof,
    plot_weather_spc,
)


st.title("Weather Outliers and Anomalies")
st.caption(
    "Data source: hourly ERA5 reanalysis from Open-Meteo, averaged across "
    "random locations inside the selected price area and downloaded directly "
    "from the Open-Meteo API for the chosen period."
)

# The price area defaults to the one clicked on the map page (session state).
default_area = st.session_state.get("selected_el_region", "NO3")
col_area, col_period = st.columns(2)
with col_area:
    region = st.selectbox(
        "Price area",
        AREAS,
        index=AREAS.index(default_area) if default_area in AREAS else 2,
        help="Defaults to the area selected on the map page.",
    )
with col_period:
    period = st.date_input(
        "Period",
        value=(date(2024, 1, 1), date(2024, 12, 31)),
        min_value=date(2000, 1, 1),
        max_value=LATEST_AVAILABLE,
        key="part4_outlier_period",
    )
if not isinstance(period, tuple) or len(period) != 2:
    st.info("Select both a start and end date.")
    st.stop()
try:
    weather = load_area_weather([region], *period)
except Exception as exc:
    st.error(f"Could not load weather from Open-Meteo: {exc}")
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
        st.plotly_chart(figure, width="stretch")
        st.metric("SPC outliers", int(summary["outlier"].sum()))
        st.dataframe(summary[summary["outlier"]], width="stretch")
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
        st.plotly_chart(figure, width="stretch")
        st.metric("LOF anomalies", int(summary["anomaly"].sum()))
        st.dataframe(summary[summary["anomaly"]], width="stretch")
        st.caption(
            "LOF compares each selected weather observation with its local "
            "neighbours; the default highlights the most isolated 1%."
        )

with st.expander("Data source and method"):
    st.write(
        "Each price area (NO1-NO5) is a polygon from the NVE bidding-area layer "
        "(Budområder.shp, converted to GeoJSON). A few random locations inside "
        "the polygon are sampled, hourly ERA5 data is downloaded for them from "
        "the Open-Meteo archive API, and the values are averaged. Downloads are "
        "cached per area and year."
    )
