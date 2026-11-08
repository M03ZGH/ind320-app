"""STL and spectrogram analyses for reservoir filling."""

import matplotlib.pyplot as plt
import streamlit as st

from ind320_app.data import load_reservoir_data
from ind320_app.part3 import plot_spectrogram, plot_stl
from ind320_app.ui import render_sidebar

render_sidebar()

st.title("Time-Series Analysis")
st.caption(
    "Data source: NVE Magasinstatistikk API. The degree-of-filling series is "
    "weekly and analysed with STL and a spectrogram."
)

try:
    reservoirs = load_reservoir_data()
except Exception as exc:
    st.error(f"Could not retrieve data from NVE: {exc}")
    st.stop()

area_type = st.radio("Area type", ["EL", "NO", "VASS"], horizontal=True)
area_numbers = sorted(
    reservoirs.loc[reservoirs["area_type"] == area_type, "area_number"].dropna().unique()
)
area_number = st.selectbox("Area", area_numbers)
series = (
    reservoirs[
        (reservoirs["area_type"] == area_type)
        & (reservoirs["area_number"] == area_number)
    ]
    .set_index("date")["filling_degree"]
    .dropna()
)

stl_tab, spectrogram_tab = st.tabs(["STL decomposition", "Spectrogram"])
with stl_tab:
    seasonal = st.number_input(
        "Seasonal smoother (weeks)",
        min_value=3,
        max_value=max(3, len(series) - 1),
        value=13,
        step=2,
    )
    trend_choice = st.selectbox(
        "Trend smoother (weeks)",
        options=["Automatic", 53, 55, 57, 59, 61],
        help=(
            "For weekly data, a manual trend smoother must be an odd number "
            "larger than the 52-week seasonal period."
        ),
    )
    trend = None if trend_choice == "Automatic" else trend_choice
    robust = st.checkbox("Robust fitting", value=True)
    if seasonal % 2 == 0:
        st.warning("The seasonal smoother must be odd.")
    else:
        figure = plot_stl(series, seasonal=seasonal, trend=trend, robust=robust)
        st.pyplot(figure)
        plt.close(figure)

with spectrogram_tab:
    window = st.number_input(
        "Window length (weeks)", min_value=4, max_value=max(4, len(series)), value=min(52, len(series)), step=1
    )
    overlap = st.slider("Window overlap", 0.0, 0.9, 0.5, 0.05)
    figure = plot_spectrogram(series, window_length=window, overlap=overlap)
    st.pyplot(figure)
    plt.close(figure)
    st.caption(
        "Bright areas show stronger periodic components. Low frequencies represent "
        "slow seasonal variation, while higher frequencies represent shorter-term "
        "changes. Since the observations are weekly, frequency is measured in cycles per week."
    )

with st.expander("Method"):
    st.write(
        "STL separates the observed series into seasonal, trend and remainder "
        "components. The spectrogram shows how signal power is distributed across "
        "frequency and time windows."
    )
