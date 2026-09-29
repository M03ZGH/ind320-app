import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

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

plot_columns = [
    "filling_degree",
    "capacity_TWh",
    "filled_TWh",
    "filling_degree_previous_week",
    "change_filling_degree"
]

st.title("Reservoir Data Visualization")

st.write(
    "Select a variable or display all five variables together. "
    "Use the slider to select a period of months."
)

plot_options = plot_columns + ["All columns"]

selected_column = st.selectbox(
    "Select a variable",
    plot_options
)

df["month"] = df["date"].dt.to_period("M")

available_months = sorted(df["month"].unique())

selected_months = st.select_slider(
    "Select period",
    options=available_months,
    value=(available_months[0], available_months[0])
)

start_month, end_month = selected_months

filtered_df = df[
    (df["month"] >= start_month)
    & (df["month"] <= end_month)
].sort_values("date")


if selected_column == "All columns":

    st.subheader("All Reservoir Variables")

    standardized_df = (
        filtered_df[plot_columns]
        - filtered_df[plot_columns].mean()
    ) / filtered_df[plot_columns].std()

    fig, ax = plt.subplots(figsize=(12, 6))

    for column in plot_columns:
        ax.plot(
            filtered_df["date"],
            standardized_df[column],
            label=column.replace("_", " ").title()
        )

    ax.set_title("Standardized Reservoir Variables")
    ax.set_xlabel("Date")
    ax.set_ylabel("Standardized Value")
    ax.legend()
    ax.grid(True)

    st.pyplot(fig)

else:

    st.subheader(
        selected_column.replace("_", " ").title()
    )

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(
        filtered_df["date"],
        filtered_df[selected_column]
    )

    ax.set_title(
        selected_column.replace("_", " ").title()
    )
    ax.set_xlabel("Date")
    ax.set_ylabel(
        selected_column.replace("_", " ").title()
    )
    ax.grid(True)

    st.pyplot(fig)