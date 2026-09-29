import streamlit as st
import pandas as pd


@st.cache_data
def load_data():
    """Load and prepare the reservoir data."""
    df = pd.read_csv("data/reservoirs.csv")

    df = df.rename(columns={
        "dato_Id": "date",
        "omrType": "area_type",
        "omrnr": "area_number",
        "iso_aar": "year",
        "iso_uke": "week",
        "fyllingsgrad": "filling_degree",
        "kapasitet_TWh": "capacity_TWh",
        "fylling_TWh": "filled_TWh",
        "neste_Publiseringsdato": "next_publication_date",
        "fyllingsgrad_forrige_uke": "filling_degree_previous_week",
        "endring_fyllingsgrad": "change_filling_degree"
    })

    df["date"] = pd.to_datetime(df["date"])
    df["next_publication_date"] = pd.to_datetime(
        df["next_publication_date"],
        errors="coerce"
    )

    return df


df = load_data()

df["date"] = pd.to_datetime(df["date"])

st.title("Reservoir Data")

st.write(
    "The table shows the variables in the reservoir dataset. "
    "The line chart displays numerical values from the first month "
    "of the data series."
)

# Identify the first month in the dataset
first_month = df["date"].min().to_period("M")

first_month_df = df[
    df["date"].dt.to_period("M") == first_month
].sort_values("date")

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