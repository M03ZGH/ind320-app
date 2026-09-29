import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


@st.cache_data
def load_data():
    """Load the reservoir data from the local CSV file."""
    return pd.read_csv("data/reservoirs.csv")


df = load_data()

df["dato_Id"] = pd.to_datetime(df["dato_Id"])

plot_columns = [
    "fyllingsgrad",
    "kapasitet_TWh",
    "fylling_TWh",
    "fyllingsgrad_forrige_uke",
    "endring_fyllingsgrad"
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

df["month"] = df["dato_Id"].dt.to_period("M")

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
].sort_values("dato_Id")


if selected_column == "All columns":

    st.subheader("All Reservoir Variables")

    standardized_df = (
        filtered_df[plot_columns]
        - filtered_df[plot_columns].mean()
    ) / filtered_df[plot_columns].std()

    fig, ax = plt.subplots(figsize=(12, 6))

    for column in plot_columns:
        ax.plot(
            filtered_df["dato_Id"],
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
        filtered_df["dato_Id"],
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