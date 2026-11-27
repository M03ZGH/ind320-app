import pandas as pd
import plotly.express as px
import streamlit as st

from ind320_app import theme  # noqa: F401  (registers the Plotly template)

from ind320_app.data import load_reservoir_data


# This page deliberately fetches NVE data instead of reading the old Part 1 CSV.
st.title("NVE Reservoir Data")
st.caption(
    "Data source: NVE Magasinstatistikk API. The old Part 1 CSV is not used."
)

interval = st.slider(
    "Download interval (number of recent weeks)",
    min_value=4,
    max_value=520,
    value=104,
    step=4,
)

@st.cache_data(ttl=3600, show_spinner="Loading NVE reservoir observations...")
def load_cached_reservoir_data() -> pd.DataFrame:
    return load_reservoir_data()

# Network errors are shown in the app so a failed API request is not mistaken
# for an empty dataset.
try:
    data = load_cached_reservoir_data()
except Exception as exc:
    st.error(f"Could not retrieve data from NVE: {exc}")
    st.stop()

latest = data["date"].max()
# The slider controls how many recent weeks remain visible after the API fetch.
filtered = data[data["date"] >= latest - pd.Timedelta(weeks=interval)]
area_type = st.radio("Area type", ["EL", "NO", "VASS"], horizontal=True)
area_data = filtered[filtered["area_type"] == area_type]

st.metric("Rows", f"{len(area_data):,}")

# One row per area with a mini line chart (row-wise LineChartColumn) of the
# last 12 weekly filling values, next to the latest value and capacity.
trend_rows = []
for number, group in area_data.sort_values("date").groupby("area_number"):
    last = group.tail(12)
    trend_rows.append(
        {
            "area_number": number,
            "last_12_weeks_filling": last["filling_degree"].tolist(),
            "latest_filling": group["filling_degree"].iloc[-1],
            "capacity_TWh": group["capacity_TWh"].iloc[-1],
        }
    )
if trend_rows:
    st.subheader("Overview per area")
    st.dataframe(
        pd.DataFrame(trend_rows),
        hide_index=True,
        width="stretch",
        column_config={
            "area_number": "Area",
            "last_12_weeks_filling": st.column_config.LineChartColumn(
                "Last 12 weeks (filling)", y_min=0, y_max=1
            ),
            "latest_filling": st.column_config.ProgressColumn(
                "Latest filling", min_value=0, max_value=1, format="percent"
            ),
            "capacity_TWh": st.column_config.NumberColumn(
                "Capacity (TWh)", format="%.2f"
            ),
        },
    )

st.subheader("Data table")
st.dataframe(area_data, hide_index=True, width="stretch")

st.subheader("Reservoir development")
st.caption(
    "Capacity is a relatively static property of an area and is therefore "
    "shown in the table, not as a time-series chart."
)
measure = st.selectbox(
    "Measure",
    ["filling_degree", "filled_TWh", "change_filling_degree"],
    format_func=lambda value: value.replace("_", " ").title(),
)
chart_data = area_data[["date", "area_number", measure]].dropna()
# Plotly gives each NVE area number its own line for the selected area type.
st.plotly_chart(
    px.line(
        chart_data.sort_values("date"),
        x="date",
        y=measure,
        color="area_number",
        markers=True,
        title=f"{measure.replace('_', ' ').title()} – {area_type}",
        labels={
            "date": "Date",
            measure: measure.replace("_", " ").title(),
            "area_number": "Area number",
        },
        template="ind320",
    ),
    width="stretch",
)
