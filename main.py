import streamlit as st

st.set_page_config(
    page_title="IND320 Data to Decision",
    page_icon="💧",
    layout="wide"
)

st.title("IND320 – Data to Decision")

st.write(
    "This Streamlit application is part of the IND320 project work. "
    "It provides an interactive exploration of Norwegian reservoir data."
)

st.header("Project overview")

st.write(
    "Use the navigation menu in the sidebar to explore the reservoir data, "
    "view interactive plots, and learn more about the project."
)

st.info(
    "The reservoir data is loaded from the local CSV file "
    "`data/reservoirs.csv`."
)