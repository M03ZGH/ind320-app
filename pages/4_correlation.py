"""Sliding-window correlation between weather and reservoir filling."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient

from ind320_app.data import load_reservoir_data
from ind320_app.part4 import WEATHER_PROPERTIES, sliding_window_correlation
from ind320_app.ui import render_sidebar

render_sidebar()
st.title("Weather and Reservoir Correlation")
st.caption(
    "Compare monthly weather with NVE filling using a selectable leading lag "
    "and rolling window."
)

@st.cache_data(ttl=3600, show_spinner="Loading NVE reservoir observations...")
def load_reservoirs() -> pd.DataFrame:
    return load_reservoir_data()

@st.cache_data(ttl=600, show_spinner="Loading weather observations...")
def load_weather() -> pd.DataFrame:
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
                {"region": "NO3"}, {"_id": 0}
            ).sort("timestamp", 1)
        )
    finally:
        client.close()
    if not records:
        raise ValueError("No NO3 weather data was found in MongoDB.")
    frame = pd.DataFrame(records)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    return frame.dropna(subset=["timestamp"]).set_index("timestamp")

try:
    reservoirs = load_reservoirs()
    weather = load_weather()
except Exception as exc:
    st.error(f"Could not load correlation inputs: {exc}")
    st.info("This page needs the public NVE API and prepared NO3 weather data.")
    st.stop()

left, right = st.columns(2)
with left:
    area_type = st.selectbox("NVE area type", ["EL", "NO", "VASS"], index=0)
    area_numbers = sorted(
        reservoirs.loc[
            reservoirs["area_type"] == area_type, "area_number"
        ].dropna().unique()
    )
    if not area_numbers:
        st.warning(f"No reservoir areas are available for {area_type}.")
        st.stop()
    area_number = st.selectbox("Reservoir area", area_numbers)
with right:
    property_name = st.selectbox(
        "Weather property",
        list(WEATHER_PROPERTIES),
        index=list(WEATHER_PROPERTIES).index("temperature_2m"),
        format_func=lambda value: WEATHER_PROPERTIES[value][0],
    )
    lag = st.slider("Weather lead (months)", 0, 12, 0)
    window = st.slider("Rolling window (months)", 3, 24, 6)

filling = (
    reservoirs[
        (reservoirs["area_type"] == area_type)
        & (reservoirs["area_number"] == area_number)
    ]
    .set_index("date")["filling_degree"]
    .dropna()
)
try:
    result = sliding_window_correlation(
        weather[property_name], filling, lag=lag, window=window
    )
except ValueError as exc:
    st.warning(str(exc))
    st.stop()

figure = go.Figure()
figure.add_trace(
    go.Scatter(
        x=result.index,
        y=result["correlation"],
        mode="lines+markers",
        name="Rolling Pearson correlation",
        line={"color": "#42c2b5"},
    )
)
figure.add_hline(y=0, line_dash="dash", line_color="#e76f51")
figure.update_layout(
    title=(
        f"{WEATHER_PROPERTIES[property_name][0]} vs {area_type} area "
        f"{area_number} filling"
    ),
    xaxis_title="Month",
    yaxis_title=f"Pearson r (window={window}, weather lead={lag} months)",
    yaxis={"range": [-1, 1]},
    template="plotly_white",
    hovermode="x unified",
)
st.plotly_chart(figure, use_container_width=True)
strongest = result["correlation"].abs().idxmax()
st.metric(
    "Largest absolute rolling correlation",
    f"{result.loc[strongest, 'correlation']:.2f}",
    delta=str(strongest.date()),
)
st.caption(
    "Positive lag pairs weather from earlier months with filling in the current "
    "month. Correlation is descriptive, not evidence that weather causes filling."
)
