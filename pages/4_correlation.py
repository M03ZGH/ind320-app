"""Sliding-window correlation between weather and reservoir filling."""

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ind320_app import theme  # noqa: F401  (registers the Plotly template)

from ind320_app.data import load_reservoir_data
from ind320_app.part4 import WEATHER_PROPERTIES, sliding_window_correlation
from ind320_app.weather import AREAS, LATEST_AVAILABLE, load_area_weather

st.title("Weather and Reservoir Correlation")
st.caption(
    "Compare monthly weather with NVE filling using a selectable leading lag "
    "and rolling window."
)

@st.cache_data(ttl=3600, show_spinner="Loading NVE reservoir observations...")
def load_reservoirs() -> pd.DataFrame:
    return load_reservoir_data()

try:
    reservoirs = load_reservoirs()
except Exception as exc:
    st.error(f"Could not load NVE reservoir data: {exc}")
    st.stop()

# Weather area and period. The area defaults to the price area clicked on the
# map page (stored in session state); weather is downloaded directly from
# Open-Meteo for the chosen period.
default_area = st.session_state.get("selected_el_region", "NO3")
weather_area = st.selectbox(
    "Weather price area",
    AREAS,
    index=AREAS.index(default_area) if default_area in AREAS else 2,
    help="Defaults to the area selected on the map page.",
)
weather_period = st.date_input(
    "Weather period",
    value=(date(2018, 1, 1), date(2024, 12, 31)),
    min_value=date(2000, 1, 1),
    max_value=LATEST_AVAILABLE,
    key="part4_correlation_period",
    help="Longer periods give more months for the rolling correlation.",
)
if not isinstance(weather_period, tuple) or len(weather_period) != 2:
    st.info("Select both a start and end date.")
    st.stop()
try:
    weather = load_area_weather([weather_area], *weather_period)
except Exception as exc:
    st.error(f"Could not load weather from Open-Meteo: {exc}")
    st.info("The page needs the public NVE and Open-Meteo APIs.")
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
    template="ind320",
    hovermode="x unified",
)
st.plotly_chart(figure, width="stretch")
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
