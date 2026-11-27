"""Norges Bank currency-rate exploration."""

import pandas as pd
import plotly.express as px
import streamlit as st

from ind320_app import theme  # noqa: F401  (registers the Plotly template)

from ind320_app.part4 import download_currency_rates

st.title("Currency Exchange Rates")
st.caption(
    "Norges Bank daily spot rates, quoted as Norwegian kroner per euro or US "
    "dollar. Non-business days have no observation."
)

today = pd.Timestamp.now().normalize()
period = st.date_input(
    "Observation period",
    value=(today - pd.DateOffset(years=1), today),
    max_value=today,
)
currencies = st.multiselect(
    "Currencies",
    options=["EUR", "USD"],
    default=["EUR", "USD"],
)

if not currencies:
    st.info("Select EUR and/or USD to download rates.")
    st.stop()
if not isinstance(period, tuple) or len(period) != 2:
    st.info("Select both a start and end date.")
    st.stop()
start, end = period

@st.cache_data(ttl=3600, show_spinner="Downloading currency rates from Norges Bank...")
def load_rates(start_date: str, end_date: str, selected: tuple[str, ...]) -> pd.DataFrame:
    return download_currency_rates(start_date, end_date, selected)

try:
    rates = load_rates(start.isoformat(), end.isoformat(), tuple(currencies))
except Exception as exc:
    st.error(f"Could not retrieve exchange rates from Norges Bank: {exc}")
    st.stop()

st.metric("Daily observations", f"{len(rates):,}")
st.plotly_chart(
    px.line(
        rates.reset_index().melt(
            id_vars="date", var_name="currency", value_name="NOK per unit"
        ),
        x="date",
        y="NOK per unit",
        color="currency",
        markers=True,
        title="Daily exchange rates",
        template="ind320",
    ),
    width="stretch",
)
st.dataframe(rates.tail(20), width="stretch")
with st.expander("Source and timing"):
    st.write(
        "Rates are downloaded from Norges Bank's public SDMX API. The daily "
        "observation is a date, not an instant; Norges Bank describes the spot "
        "rate as an ECB concertation-time observation around 14:15 CET. Do not "
        "interpret this date-only series as UTC midnight."
    )
