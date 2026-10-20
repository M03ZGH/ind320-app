import streamlit as st

st.set_page_config(
    page_title="IND320 Data to Decision",
    page_icon="💧",
    layout="wide",
)

st.title("IND320 – Data to Decision")
st.markdown(
    "Interactive analysis of Norwegian reservoir statistics and cross-border "
    "electricity flows."
)

st.subheader("Project overview")
st.write(
    "Use the pages in the sidebar to fetch current reservoir data from NVE, "
    "inspect the required NVE area types (EL, NO and VASS), and explore ENTSO-E flow data "
    "prepared in the Jupyter Notebook and stored in MongoDB."
)

st.caption(
    "NVE area types and ENTSO-E bidding zones are separate classifications. "
    "For example, the Norway–Denmark interconnector is queried as NO_2 ↔ DK_1."
)

with st.expander("Data sources"):
    st.markdown(
        "- [NVE Magasinstatistikk API](https://biapi.nve.no/magasinstatistikk/swagger/index.html)\n"
        "- [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)\n"
        "- Cassandra and Spark are used in the notebook pipeline.\n"
        "- MongoDB Atlas supplies the online flow view."
    )
