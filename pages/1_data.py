import pandas as pd
import plotly.express as px
import streamlit as st

from ind320_app.data import load_reservoir_data

st.title("NVE reservoir data")
st.caption("The data is fetched directly from the NVE Magasinstatistikk API.")

interval = st.slider(
    "Download interval (number of recent weeks)",
    min_value=4,
    max_value=520,
    value=104,
    step=4,
)

try:
    data = load_reservoir_data()
except Exception as exc:
    st.error(f"Could not retrieve data from NVE: {exc}")
    st.stop()

latest = data["date"].max()
filtered = data[data["date"] >= latest - pd.Timedelta(weeks=interval)]
area_type = st.radio("Area type", ["EL", "NO", "VASS"], horizontal=True)
area_data = filtered[filtered["area_type"] == area_type]

st.metric("Rows", f"{len(area_data):,}")
st.dataframe(area_data, hide_index=True, use_container_width=True)

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
    ),
    use_container_width=True,
)
