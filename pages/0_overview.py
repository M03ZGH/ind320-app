"""Front page: what the app is, what each page does and where the data comes from."""

from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parents[1] / "assets"

# Header: title on the left, university and study-programme logos on the right.
title_col, logo_col = st.columns([3, 2], vertical_alignment="center")
with title_col:
    st.title("Data to Decision")
    st.markdown(
        "An interactive portfolio for Norwegian reservoir statistics, ERA5 weather "
        "analysis, currency rates and cross-border electricity flows."
    )
with logo_col:
    nmbu, indok = st.columns(2, vertical_alignment="center")
    nmbu.image(str(ASSETS / "nmbu.png"))
    indok.image(str(ASSETS / "indok_nmbu.png"))

st.write(
    "Use the grouped menu on the left, or the shortcuts below. Selections made on "
    "the **Map** page (the clicked price area, the period and the forecast "
    "horizon) are kept in the session and become the defaults on the weather and "
    "forecast pages."
)

st.subheader("Explore")
left, right = st.columns(2)
with left:
    st.page_link("pages/1_data.py", label="NVE Data", icon="🗃️")
    st.caption(
        "Magasinstatistikk table with a mini trend per area (the row-wise line "
        "chart) and a time-series plot. Pick the area type (EL, NO or VASS) and "
        "how many recent weeks to download."
    )
    st.page_link("pages/2_plot.py", label="Reservoir Development", icon="📈")
    st.caption(
        "Plot one area or all areas of a type over time, and choose which part "
        "of the history to show."
    )
    st.page_link("pages/3_map.py", label="Map", icon="🗺️")
    st.caption(
        "Price areas NO1–NO5, Norway and the precipitation regions, coloured by a "
        "weather property (temperature, precipitation, wind) or by reservoir "
        "filling for a chosen week. Click an area to outline it and use it on "
        "the other pages."
    )
with right:
    st.page_link("pages/4_correlation.py", label="Weather Correlation", icon="🌦️")
    st.caption(
        "Sliding-window correlation between a weather property and reservoir "
        "filling, with selectable lead lag and window length."
    )
    st.page_link("pages/5_outliers.py", label="Weather Outliers", icon="🔎")
    st.caption(
        "Two tabs: seasonally adjusted SPC limits (DCT high-pass filter) and "
        "Local Outlier Factor anomalies, for any weather property."
    )
    st.page_link("pages/6_time_series.py", label="Time-Series Analysis", icon="〰️")
    st.caption(
        "Two tabs: STL decomposition (seasonal, trend, remainder) and a "
        "spectrogram of reservoir filling."
    )

st.subheader("Predict")
st.page_link("pages/7_forecast.py", label="Filling Forecast", icon="🔮")
st.caption(
    "Monthly forecast of reservoir filling with an online River regression. "
    "Choose training period, history, lags, learning rate and optional extra "
    "inputs (temperature, EUR/NOK, USD/NOK, ENTSO-E net flow). The forecast is "
    "drawn as an animation and compared with a persistence baseline."
)

st.subheader("Data sources")
left, right = st.columns(2)
with left:
    st.page_link("pages/8_currency.py", label="Currency Rates", icon="💱")
    st.caption("Daily EUR/NOK and USD/NOK from the Norges Bank API.")
with right:
    st.page_link("pages/9_crossborder.py", label="Cross-Border Flows", icon="⚡")
    st.caption(
        "ENTSO-E electricity flows between Norway and its neighbours: a yearly "
        "pie chart and a monthly line chart per connection."
    )

st.caption(
    "NVE reservoir area types (EL, NO, VASS) and ENTSO-E bidding zones "
    "(NO_2, DK_1, etc.) are separate classifications."
)
with st.expander("Data sources and technology"):
    st.markdown(
        "- [NVE Magasinstatistikk API](https://biapi.nve.no/magasinstatistikk/swagger/index.html) – reservoir filling, downloaded directly\n"
        "- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (ERA5) – weather, downloaded directly\n"
        "- [Norges Bank exchange-rate API](https://data.norges-bank.no/) – currency, downloaded directly\n"
        "- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) – cross-border flows, prepared in Part 2 and read from MongoDB Atlas\n"
        "- Spark and Cassandra are used in the Part 2 notebook pipeline.\n"
        "- All charts are interactive Plotly figures; data loads are cached."
    )
