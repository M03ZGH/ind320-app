"""River-based monthly reservoir filling forecast."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient

from ind320_app.data import load_reservoir_data
from ind320_app.part4 import download_currency_rates, forecast_reservoir_filling
from ind320_app.ui import render_sidebar

render_sidebar()
st.title("Reservoir Filling Forecast")
st.caption(
    "An online lag-based River regression predicts monthly filling. Selected "
    "exogenous variables enter as one-month lags; unknown future values are "
    "held at the latest observed monthly value."
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

@st.cache_data(ttl=600, show_spinner="Loading ENTSO-E flow observations...")
def load_flows() -> pd.DataFrame:
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
            client["ind320"]["crossborder_flows"].find({}, {"_id": 0})
        )
    finally:
        client.close()
    if not records:
        raise ValueError("No ENTSO-E flow observations were found in MongoDB.")
    frame = pd.DataFrame(records)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame["flow_mw"] = pd.to_numeric(frame["flow_mw"], errors="coerce")
    return frame.dropna(subset=["timestamp", "flow_mw"])

@st.cache_data(ttl=3600, show_spinner="Loading currency rates...")
def load_currency(start_date: str, end_date: str) -> pd.DataFrame:
    return download_currency_rates(start_date, end_date, ("EUR", "USD"))

try:
    reservoirs = load_reservoirs()
except Exception as exc:
    st.error(f"Could not load NVE observations: {exc}")
    st.stop()

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

filling = (
    reservoirs[
        (reservoirs["area_type"] == area_type)
        & (reservoirs["area_number"] == area_number)
    ]
    .set_index("date")["filling_degree"]
    .dropna()
)
monthly_history = filling.resample("MS").mean().dropna()
minimum_date = monthly_history.index.min().date()
maximum_date = monthly_history.index.max().date()
default_start = max(
    minimum_date,
    (monthly_history.index.max() - pd.DateOffset(years=10)).date(),
)
training_period = st.date_input(
    "Training period",
    value=(default_start, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
    key="part4_forecast_period",
)
if not isinstance(training_period, tuple) or len(training_period) != 2:
    st.info("Select both a training start and end date.")
    st.stop()
training_start, training_end = training_period
if training_start > training_end:
    st.error("The training start must be on or before the end.")
    st.stop()

selected_filling = filling.loc[
    (filling.index >= pd.Timestamp(training_start))
    & (filling.index <= pd.Timestamp(training_end) + pd.Timedelta(days=31))
]
control_left, control_mid, control_right = st.columns(3)
with control_left:
    history_months = st.slider(
        "Maximum history (months)", 24, 180, min(120, max(24, len(selected_filling)))
    )
with control_mid:
    horizon = st.slider("Forecast horizon (months)", 1, 12, 6, key="forecast_horizon")
with control_right:
    lags = st.slider("Filling lags (months)", 1, 12, 12)
learning_rate = st.select_slider(
    "River learning rate",
    options=[0.001, 0.005, 0.01, 0.05, 0.1],
    value=0.01,
)
source_options = [
    "NO3 temperature",
    "EUR/NOK",
    "USD/NOK",
    "ENTSO-E net flow",
]
selected_sources = st.multiselect(
    "Exogenous data sources",
    source_options,
    default=[],
)

exogenous_parts: list[pd.Series] = []
if "NO3 temperature" in selected_sources:
    try:
        weather = load_weather()
        weather_series = weather["temperature_2m"].rename("weather_temperature")
        exogenous_parts.append(weather_series)
    except Exception as exc:
        st.error(f"Could not load selected weather data: {exc}")
        st.stop()
if "EUR/NOK" in selected_sources or "USD/NOK" in selected_sources:
    try:
        rates = load_currency(str(training_start), str(training_end))
        if "EUR/NOK" in selected_sources:
            exogenous_parts.append(rates["EUR_NOK"].rename("EUR_NOK"))
        if "USD/NOK" in selected_sources:
            exogenous_parts.append(rates["USD_NOK"].rename("USD_NOK"))
    except Exception as exc:
        st.error(f"Could not load selected currency data: {exc}")
        st.stop()
if "ENTSO-E net flow" in selected_sources:
    try:
        flows = load_flows()
        flows = flows[
            flows["timestamp"].dt.date.between(training_start, training_end)
        ].copy()
        flows["net_flow_mw"] = flows["flow_mw"].where(
            flows["direction"] == "export_from_NO", -flows["flow_mw"]
        )
        net_flow = flows.groupby("timestamp")["net_flow_mw"].sum()
        exogenous_parts.append(net_flow.rename("ENTSOE_net_flow"))
    except Exception as exc:
        st.error(f"Could not load selected ENTSO-E data: {exc}")
        st.stop()

exogenous = (
    pd.concat(exogenous_parts, axis=1).sort_index()
    if exogenous_parts
    else None
)
if st.button("Train and forecast", type="primary"):
    try:
        result = forecast_reservoir_filling(
            selected_filling,
            exogenous=exogenous,
            selected_sources=(
                list(exogenous.columns) if exogenous is not None else None
            ),
            history_months=history_months,
            horizon=horizon,
            lags=lags,
            learning_rate=learning_rate,
        )
    except Exception as exc:
        st.error(f"Forecast could not be calculated: {exc}")
        st.stop()

    st.metric("Walk-forward MAE", f"{result.mae:.3f}")
    st.metric("Persistence baseline MAE", f"{result.persistence_mae:.3f}")
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=result.history.index,
            y=result.history,
            name="Observed monthly filling",
            mode="lines",
            line={"color": "#56b4e9"},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=result.forecast.index[:1],
            y=result.forecast.iloc[:1],
            name="River forecast",
            mode="lines+markers",
            line={"color": "#e9c46a", "width": 3},
        )
    )
    frames = [
        go.Frame(
            data=[
                go.Scatter(
                    x=result.forecast.index[:frame_index],
                    y=result.forecast.iloc[:frame_index],
                    mode="lines+markers",
                    line={"color": "#e9c46a", "width": 3},
                )
            ],
            traces=[1],
            name=str(frame_index),
        )
        for frame_index in range(1, len(result.forecast) + 1)
    ]
    figure.frames = frames
    figure.update_layout(
        title=f"{area_type} area {area_number}: monthly filling forecast",
        xaxis_title="Month",
        yaxis_title="Filling fraction",
        yaxis={"range": [0, 1]},
        template="plotly_white",
        updatemenus=[
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Play forecast",
                        "method": "animate",
                        "args": [None, {"frame": {"duration": 500, "redraw": True}}],
                    }
                ],
            }
        ],
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        f"Used {result.observations} monthly observations and "
        f"{result.validation_observations} one-step validation months. "
        "The validation is chronological; it is not a random train/test split."
    )
