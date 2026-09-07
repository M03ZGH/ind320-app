# IND320 — Streamlit-app

Obligatorisk oppgave i IND320 Data to Decision, NMBU.

Eget repo, adskilt fra `IND320-mine`, fordi appen skal kunne deployes.
Deployment krever et lett miljø — derfor kun `streamlit`, `pandas` og `plotly`
her, ikke PySpark, Cassandra-drivere og Jupyter.

---

## Kjøre appen

```bash
conda deactivate
cd ~/Github/ind320-app
uv run streamlit run app.py
```

Appen åpnes på http://localhost:8501 og laster inn på nytt hver gang du lagrer
`app.py`. Avslutt med Ctrl+C i terminalen.

---

## Mappestruktur

```
ind320-app/
├── .venv/              ← miljøet, bygges av uv, aldri i Git
├── .streamlit/
│   └── secrets.toml    ← API-nøkler. ALDRI i Git.
├── data/               ← datafiler
├── app.py              ← selve appen
├── pyproject.toml      ← avhengigheter
├── uv.lock             ← låste versjoner
└── .gitignore
```

---

## Legge til pakker

```bash
uv add plotly
uv add requests
```

`uv add` oppdaterer både `pyproject.toml` og `uv.lock` automatisk. Ikke rediger
dem for hånd.

Hold listen kort. Hver pakke gjør deployment tregere og mer skjør.

---

## Hemmeligheter

API-nøkler skal aldri i koden eller i Git. Lag `.streamlit/secrets.toml`:

```toml
openweather_api_key = "din-nokkel-her"
```

Les den i appen med:

```python
nokkel = st.secrets["openweather_api_key"]
```

Filen er allerede i `.gitignore`. Ved deployment limes innholdet inn i
Streamlit Cloud sitt eget innstillingspanel, ikke i repoet.

---

## Deployment til Streamlit Community Cloud

1. Push repoet til GitHub (kan være privat).
2. Gå til https://share.streamlit.io og logg inn med GitHub.
3. Velg repo, gren og `app.py`.
4. Legg inn eventuelle secrets under **Advanced settings**.
5. Deploy. Hver push til GitHub oppdaterer appen automatisk.

Feiler bygget, er det nesten alltid en tung avhengighet. Sjekk at
`pyproject.toml` kun inneholder det appen faktisk trenger.

---

## Arbeidsflyt

```bash
# start økt
conda deactivate
cd ~/Github/ind320-app
uv run streamlit run app.py

# lagre arbeid
git add -A
git status          # kontroller: ingen .venv, ingen secrets.toml
git commit -m "Beskriv endringen"
git push
```

---

## Nyttige Streamlit-byggeklosser

| Formål | Kode |
|---|---|
| Overskrift | `st.title("Tekst")` |
| Tekst | `st.write("Tekst")` eller `st.markdown(...)` |
| Tabell | `st.dataframe(df)` |
| Graf | `st.plotly_chart(fig, use_container_width=True)` |
| Nedtrekksmeny | `st.selectbox("Velg", liste)` |
| Skyvekontroll | `st.select_slider("Tidsrom", options=...)` |
| Sidemeny | `st.sidebar.radio("Gå til", sider)` |
| Kolonner | `col1, col2 = st.columns(2)` |
| Sammenleggbar boks | `with st.expander("Vis mer"):` |
| Hurtigbuffer | `@st.cache_data` over en funksjon |

`@st.cache_data` er viktig: uten den leses datafilen på nytt hver gang du
klikker noe, og appen blir treg.

---

## Feilsøking

| Symptom | Løsning |
|---|---|
| `ModuleNotFoundError` | Bruk `uv run streamlit ...`, ikke `streamlit ...` |
| `(base)` i prompten | `conda deactivate` |
| Appen oppdateres ikke | Trykk «Rerun» øverst til høyre, eller Ctrl+C og start på nytt |
| Port opptatt | `uv run streamlit run app.py --server.port 8502` |
| Miljøet virker ødelagt | `rm -rf .venv && uv sync` |

---

## Lenker

- Kursbok: https://khliland.github.io/IND320/
- Streamlit-dokumentasjon: https://docs.streamlit.io
- Streamlit Cloud: https://share.streamlit.io
- OpenWeatherMap (API-nøkkel): https://openweathermap.org/api
