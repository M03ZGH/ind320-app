"""
IND320 - Streamlit-app
Startpunkt for obligatorisk oppgave.

Kjor lokalt:
    uv run streamlit run app.py

Appen apnes pa http://localhost:8501 og laster inn pa nytt hver gang du
lagrer filen.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------------------------------
# Sideoppsett - ma vaere den forste streamlit-kommandoen i filen
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="IND320",
    page_icon="📊",
    layout="wide",
)


# --------------------------------------------------------------------------
# Datainnlasting
# --------------------------------------------------------------------------

@st.cache_data
def load_data(path: str = "data/open-meteo-subset.csv") -> pd.DataFrame:
    """
    Les inn datasettet.

    @st.cache_data gjor at filen bare leses EN gang, ikke hver gang du klikker
    noe i appen. Uten den blir appen treg. Endrer du selve funksjonen, tommes
    cachen automatisk.
    """
    df = pd.read_csv(path)

    # Finn tidskolonnen og gjor den om til ekte datoer
    for col in df.columns:
        if "time" in col.lower() or "date" in col.lower():
            df[col] = pd.to_datetime(df[col], errors="coerce")
            df = df.set_index(col)
            break
    return df


# --------------------------------------------------------------------------
# Sider
# --------------------------------------------------------------------------

def side_forside() -> None:
    st.title("IND320 — Data to Decision")
    st.write(
        "Kort om prosjektet: hva appen viser, hvilke data den bruker, "
        "og hvordan den er bygget opp."
    )
    st.info("Bytt side i menyen til venstre.")


def side_tabell(df: pd.DataFrame) -> None:
    st.title("Datatabell")
    st.write(f"{len(df)} rader og {len(df.columns)} kolonner.")

    # En rad per kolonne, med en liten graf som viser forlopet
    oversikt = pd.DataFrame({
        "Kolonne": df.columns,
        "Forlop": [df[c].tolist() for c in df.columns],
    })
    st.dataframe(
        oversikt,
        column_config={"Forlop": st.column_config.LineChartColumn("Forste ar")},
        hide_index=True,
        use_container_width=True,
    )

    with st.expander("Vis raadata"):
        st.dataframe(df, use_container_width=True)


def side_graf(df: pd.DataFrame) -> None:
    st.title("Graf")

    kolonner = list(df.columns)
    valg = st.selectbox("Velg kolonne", ["Alle"] + kolonner)

    # Skyvekontroll for tidsrom
    maaneder = sorted(df.index.to_period("M").unique().astype(str))
    if len(maaneder) > 1:
        start, slutt = st.select_slider(
            "Velg tidsrom",
            options=maaneder,
            value=(maaneder[0], maaneder[0]),
        )
        maske = (df.index.to_period("M").astype(str) >= start) & \
                (df.index.to_period("M").astype(str) <= slutt)
        utvalg = df.loc[maske]
    else:
        utvalg = df

    if utvalg.empty:
        st.warning("Ingen data i valgt tidsrom.")
        return

    if valg == "Alle":
        fig = px.line(utvalg, y=kolonner)
        st.caption(
            "Merk: kolonnene har ulike enheter, saa aksen er ikke direkte "
            "sammenlignbar. Kommenter dette i besvarelsen."
        )
    else:
        fig = px.line(utvalg, y=valg)

    fig.update_layout(height=500, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)


def side_om() -> None:
    st.title("Om")
    st.markdown(
        """
        **Kilder og AI-bruk**

        Beskriv her hvilke kilder du har brukt, og hvordan eventuelle
        AI-verktoy er brukt i arbeidet. Kurset ber om aapenhet om dette.
        """
    )


# --------------------------------------------------------------------------
# Navigasjon
# --------------------------------------------------------------------------

def main() -> None:
    st.sidebar.title("Meny")
    side = st.sidebar.radio("Gaa til", ["Forside", "Datatabell", "Graf", "Om"])

    if side == "Forside":
        side_forside()
        return
    if side == "Om":
        side_om()
        return

    try:
        df = load_data()
    except FileNotFoundError:
        st.error(
            "Fant ikke datafilen. Legg CSV-filen i mappen `data/` og "
            "oppdater stien i `load_data()`."
        )
        return

    if side == "Datatabell":
        side_tabell(df)
    elif side == "Graf":
        side_graf(df)


if __name__ == "__main__":
    main()
