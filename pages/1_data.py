import streamlit as st
import pandas as pd


@st.cache_data
def load_data():
    """Load the reservoir data from the local CSV file."""
    return pd.read_csv("data/reservoirs.csv")


df = load_data()

df["dato_Id"] = pd.to_datetime(df["dato_Id"])

st.title("Reservoir Data")

st.write(
    "The table shows the variables in the reservoir dataset. "
    "The line chart displays numerical values from the first month "
    "of the data series."
)

# Identify the first month in the dataset
first_month = df["dato_Id"].min().to_period("M")

first_month_df = df[
    df["dato_Id"].dt.to_period("M") == first_month
].sort_values("dato_Id")

# Create one row for each column in the imported data
table_data = []

for column in df.columns:

    if pd.api.types.is_numeric_dtype(df[column]):
        values = first_month_df[column].dropna().tolist()
    else:
        values = []

    table_data.append({
        "Variable": column,
        "First month": values
    })

table_df = pd.DataFrame(table_data)

st.dataframe(
    table_df,
    column_config={
        "Variable": st.column_config.TextColumn(
            "Variable"
        ),
        "First month": st.column_config.LineChartColumn(
            "First month",
            help="Numerical values during the first month"
        ),
    },
    hide_index=True,
    use_container_width=True
)