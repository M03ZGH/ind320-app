import pandas as pd
import plotly.express as px
import streamlit as st

from ind320_app.data import load_reservoir_data
from ind320_app.ui import render_sidebar

render_sidebar()

# Capacity is not offered here because it is mostly constant and is not useful
# as a time-series measure.
st.title("Reservoir Development")
st.write(
    "Choose an NVE area type and recent time interval to compare reservoir "
    "measures from the live NVE API."
)

interval = st.slider("Download interval (weeks)", 4, 520, 104, 4)
area_type = st.radio("Area type", ["EL", "NO", "VASS"], horizontal=True)
measure = st.selectbox(
    "Measure",
    ["filling_degree", "filled_TWh", "change_filling_degree"],
)

@st.cache_data(ttl=3600, show_spinner="Loading NVE reservoir observations...")
def load_cached_reservoir_data() -> pd.DataFrame:
    return load_reservoir_data()

# Keep the error visible to the user when the public API is unavailable.
try:
    data = load_cached_reservoir_data()
except Exception as exc:
    st.error(f"Could not retrieve data from NVE: {exc}")
    st.stop()

latest = data["date"].max()
filtered = data[
    (data["area_type"] == area_type)
    & (data["date"] >= latest - pd.Timedelta(weeks=interval))
].copy()
if filtered.empty:
    st.warning("No observations are available for this selection.")
    st.stop()

figure = px.line(
    filtered.sort_values("date"),
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
    template="plotly_white",
)
st.plotly_chart(figure, use_container_width=True)
st.caption(
    "Capacity is excluded because it is largely constant for each area and "
    "does not form an informative time series."
)
