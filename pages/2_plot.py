import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from ind320_app.data import load_reservoir_data

# Capacity is not offered here because it is mostly constant and is not useful
# as a time-series measure.
st.title("Reservoir development")
st.write("Choose an area type and a download interval to compare reservoir measures.")

interval = st.slider("Download interval (weeks)", 4, 520, 104, 4)
area_type = st.radio("Area type", ["EL", "NO", "VASS"], horizontal=True)
measure = st.selectbox(
    "Measure",
    ["filling_degree", "filled_TWh", "change_filling_degree"],
)

# Keep the error visible to the user when the public API is unavailable.
try:
    data = load_reservoir_data()
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

figure, axis = plt.subplots(figsize=(11, 5))
# Compare the development of each area number over the selected interval.
for area_number, group in filtered.groupby("area_number"):
    axis.plot(group["date"], group[measure], label=str(area_number))
axis.set_title(f"{measure.replace('_', ' ').title()} – {area_type}")
axis.set_xlabel("Date")
axis.set_ylabel(measure.replace("_", " ").title())
axis.grid(True, alpha=0.3)
axis.legend(title="Area number", ncol=3)
figure.tight_layout()
st.pyplot(figure)
st.caption(
    "Capacity is excluded because it is largely constant for each area and "
    "does not form an informative time series."
)
