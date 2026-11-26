import streamlit as st

from ind320_app.ui import render_sidebar

render_sidebar()

st.title("Data to Decision")
st.markdown(
    "An interactive portfolio for Norwegian reservoir statistics, ERA5 weather "
    "analysis, currency rates and cross-border electricity flows."
)
st.write(
    "Explore the data and methods in the grouped navigation. The forecast and "
    "correlation pages use monthly observations so model fitting stays fast and "
    "results remain interpretable."
)
st.caption(
    "NVE reservoir area types (EL, NO, VASS) and ENTSO-E bidding zones "
    "(NO_2, DK_1, etc.) are separate classifications."
)
with st.expander("Data sources"):
    st.markdown(
        "- [NVE Magasinstatistikk API](https://biapi.nve.no/magasinstatistikk/swagger/index.html)\n"
        "- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) (ERA5)\n"
        "- [Norges Bank exchange-rate API](https://data.norges-bank.no/)\n"
        "- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)\n"
        "- MongoDB Atlas supplies prepared weather and cross-border flow observations.\n"
        "- Spark and Cassandra are used in the Part 2 notebook pipeline."
    )
