import pandas as pd
import plotly.express as px
import streamlit as st
from pymongo import MongoClient

st.title("Cross-border electricity flows")


@st.cache_resource
def get_collection():
    """Create one reusable MongoDB client for the Streamlit process."""
    # Streamlit Cloud supplies the same structure through its Secrets setting.
    if "mongo" not in st.secrets or not st.secrets["mongo"].get("uri"):
        raise RuntimeError("Add [mongo].uri to Streamlit secrets.")
    client = MongoClient(
        st.secrets["mongo"]["uri"],
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        maxPoolSize=5,
        minPoolSize=0,
        maxIdleTimeMS=60000,
        waitQueueTimeoutMS=30000,
    )
    client.admin.command("ping")
    return client["ind320"]["crossborder_flows"]


@st.cache_data(ttl=600)
def load_flows() -> pd.DataFrame:
    """Read the notebook's curated ENTSO-E observations from MongoDB."""
    records = list(get_collection().find({}, {"_id": 0}))
    if not records:
        raise ValueError("MongoDB contains no flow data. Run the notebook pipeline first.")
    frame = pd.DataFrame(records)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame["flow_mw"] = pd.to_numeric(frame["flow_mw"], errors="coerce")
    frame = frame.dropna(subset=["timestamp", "flow_mw", "connection"])
    frame["year"] = frame["timestamp"].dt.year
    frame["month"] = frame["timestamp"].dt.month
    return frame


# Stop with an explanatory message instead of drawing an empty chart.
try:
    flows = load_flows()
except Exception as exc:
    st.error(f"Could not load flow data from MongoDB: {exc}")
    st.info("Run the notebook data pipeline and configure Streamlit secrets.")
    st.stop()

connections = sorted(flows["connection"].unique())
connection = st.radio("Connection", connections, horizontal=True)
connection_data = flows[flows["connection"] == connection]
years = sorted(connection_data["year"].unique())

left, right = st.columns(2)
with left:
    # The pie chart compares the two flow directions for one connection/year.
    year = st.selectbox("Year", years, index=len(years) - 1)
    selected = connection_data[connection_data["year"] == year]
    annual = (
        selected.assign(energy_mwh=selected["flow_mw"])
        .groupby("direction", as_index=False)["energy_mwh"]
        .sum()
    )
    st.plotly_chart(
        px.pie(
            annual,
            names="direction",
            values="energy_mwh",
            title=f"{connection} – {year} (MWh estimate)",
        ),
        use_container_width=True,
    )

with right:
    # The task asks for a line plot that can include any selection of months.
    available_months = sorted(selected["month"].unique())
    months = st.pills(
        "Months",
        options=available_months,
        default=available_months[:1],
        selection_mode="multi",
        format_func=lambda month: pd.Timestamp(2000, int(month), 1).strftime("%B"),
    )
    month_data = selected[selected["month"].isin(months or [])]
    st.plotly_chart(
        px.line(
            month_data.sort_values("timestamp"),
            x="timestamp",
            y="flow_mw",
            color="direction",
            title=f"{connection} – selected months",
        ),
        use_container_width=True,
    )

with st.expander("Data source and methodology"):
    st.write(
        "The observations originate from the ENTSO-E Transparency Platform API. "
        "The notebook retrieves both directions, stores the raw observations in "
        "Cassandra through Spark, and publishes the curated records to MongoDB. "
        "The annual pie chart treats each hourly MW observation as one MWh."
    )
