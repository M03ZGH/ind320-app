"""STL and spectrogram analyses for reservoir filling."""

import streamlit as st

from ind320_app.data import load_reservoir_data
from ind320_app.part4 import (
    plot_spectrogram_interactive,
    plot_stl_interactive,
)
from ind320_app.ui import render_sidebar

render_sidebar()

st.title("Time-Series Analysis")
st.caption(
    "Data source: NVE Magasinstatistikk API. The degree-of-filling series is "
    "weekly and analysed with STL and a spectrogram."
)

@st.cache_data(ttl=3600, show_spinner="Loading NVE reservoir observations...")
def load_cached_reservoir_data():
    return load_reservoir_data()

try:
    reservoirs = load_cached_reservoir_data()
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
    robust = st.checkbox("Robust fitting", value=True)
    if seasonal % 2 == 0:
        st.warning("The seasonal smoother must be odd.")
    else:
        try:
            figure = plot_stl_interactive(
                series, seasonal=seasonal, robust=robust
            )
        except ValueError as exc:
            st.warning(str(exc))
        else:
            st.plotly_chart(figure, use_container_width=True)

with spectrogram_tab:
    window = st.number_input(
        "Window length (weeks)", min_value=4, max_value=max(4, len(series)), value=min(52, len(series)), step=1
    )
    overlap = st.slider("Window overlap", 0.0, 0.9, 0.5, 0.05)
    try:
        figure = plot_spectrogram_interactive(
            series, window_length=window, overlap=overlap
        )
    except ValueError as exc:
        st.warning(str(exc))
    else:
        st.plotly_chart(figure, use_container_width=True)
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
