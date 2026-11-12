# IND320 – Data to Decision

This repository contains my project work for **IND320 Data to Decision** at NMBU.

The project explores Norwegian reservoir data and cross-border electricity flows using Python, Pandas, Spark, Cassandra, MongoDB and Streamlit. Part 2 uses the NVE API directly and publishes curated ENTSO-E observations to MongoDB for the online app.

## Project contents

* `IND320_part1.ipynb` – Jupyter Notebook for Part 1.
* `IND320_part2.ipynb` – Jupyter Notebook documenting the Part 2 API, Spark, Cassandra and MongoDB pipeline.
* `IND320_part3.ipynb` – Jupyter Notebook for ERA5 weather, outliers, STL and spectrogram.
* `main.py` – Main page of the Streamlit application.
* `pages/` – Additional pages for data exploration and visualization.
* `src/ind320_app/data.py` – Shared API and data-preparation functions.
* `src/ind320_app/part3.py` – Shared Part 3 weather and time-series functions.
* `src/ind320_app/ui.py` – Shared Streamlit sidebar and project navigation styling.
* `pyproject.toml` – Project dependencies and configuration.
* `uv.lock` – Locked dependency versions.

## Streamlit application

The interactive application provides:

* Current NVE reservoir data fetched directly from the API.
* Radio buttons for EL, NO and VASS area types.
* An interval slider controlling the downloaded reservoir period.
* MongoDB-backed cross-border flow plots with a yearly pie chart and multi-month line chart.
* STL and spectrogram tabs for reservoir filling.
* DCT/SPC precipitation outlier and LOF temperature anomaly tabs using MongoDB-published Open-Meteo data.
* A consistent sidebar with navigation, data-pipeline explanations and project links.

`EL`, `NO` and `VASS` are NVE reservoir area types. They are unrelated to ENTSO-E
bidding zones. ENTSO-E connections use codes such as `NO_2` and `DK_1`; therefore
the Norway–Denmark connection is queried as `NO_2 -> DK_1`, not as a generic
`NO -> DK` connection.

**Live application:**
https://ind320-data-to-decision-moez.streamlit.app

**Public GitHub repository:**
https://github.com/M03ZGH/ind320-app

## Technologies

* Python
* Pandas
* Matplotlib
* Streamlit
* Jupyter Notebook
* uv
* GitHub

## Configuration

Create `.streamlit/secrets.toml` locally (it is ignored by Git) with:

```toml
[entsoe]
token = "your-token"

[mongo]
uri = "your-mongodb-connection-string"
```

The notebook also requires local Cassandra and Spark for the database part of the pipeline.
Part 3 additionally requires the complete `NVE_Region` shapefile set (`.shp`, `.shx`,
`.dbf` and `.prj`) from [Atlas](https://atlas.nve.no/), placed in `data/`.

The shapefile is a local input and must not be committed without all companion
files. The weather cache in `data/weather_cache/` is also local and ignored by
Git. The notebook samples 1000 points per NVE region, sends them to Open-Meteo
in small batches, averages the hourly ERA5 observations and publishes the
resulting NO3 series to MongoDB.

## Running locally

Open a terminal and run these commands from the `ind320-app` folder:

```bash
cd /Users/moezyadgar/GitHub/IND320/ind320-app
uv sync
.venv/bin/python -m streamlit run main.py
```

The app opens at [http://localhost:8501](http://localhost:8501). Keep the
terminal open while using the app and press `Ctrl+C` to stop it. If the
environment is activated first, use:

```bash
source .venv/bin/activate
streamlit run main.py
```

The NVE and reservoir pages work without local database secrets. The
cross-border page additionally needs `.streamlit/secrets.toml`, and the
Part 3 weather page needs `data/NVE_Region.shp`, `.shx`, `.dbf` and `.prj`.

The notebook and the Streamlit app use different data destinations:

1. NVE reservoir observations are fetched directly from the public NVE API.
2. ENTSO-E observations are retrieved and processed in the notebook.
3. Spark writes the flow observations to Cassandra and reads the curated data.
4. The notebook writes the fresh, Spark-curated observations to MongoDB with
   batched, idempotent upserts and a unique index.
5. The notebook publishes aggregated Part 3 weather observations to MongoDB.
6. Streamlit reads MongoDB on the cross-border and weather pages.

The ENTSO-E cell requests the latest two years for four selected Norwegian
connections in both directions. Requests are split into one-year windows and
run with bounded concurrency (`max_workers=4`) so a slow sequential request
does not block the whole pipeline. The MongoDB client uses a small connection
pool, and rerunning the publication step updates existing observations instead
of creating duplicates. Editing the Python files or README does not restart
the notebook kernel or change its current execution.

### Streamlit Cloud secrets

Do not upload `.streamlit/secrets.toml` or put tokens in Python files. In the
Streamlit Cloud app, open **Settings → Secrets** and paste:

```toml
[entsoe]
token = "your-entsoe-token"

[mongo]
uri = "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"
```

The `Cross-border electricity flows` page verifies the MongoDB connection with
`ping`, reads the curated `ind320.crossborder_flows` collection, and displays an
error instead of silently showing an empty chart if the connection or collection
is unavailable.

## Part 3 notebook run order

Run `IND320_part3.ipynb` from the `ind320-app` folder in this order:

1. Load the project imports and locate `data/NVE_Region.shp`.
2. Sample 1000 points per NVE region.
3. Download the 2024 NO3 ERA5 data. Requests are batched and cached in
   `data/weather_cache/`; progress is printed every tenth batch.
4. Run the MongoDB publication cell. It requires `[mongo].uri` in local
   `.streamlit/secrets.toml` and writes `ind320.weather`.
5. Run the SPC, LOF, STL and spectrogram cells.
6. Save the executed notebook and export it to PDF with outputs and figures
   visible.

The public Streamlit weather page reads the prepared `ind320.weather` collection
instead of downloading weather data for every visitor.

## Part 2 log and AI usage

During Part 2 I replaced the reservoir CSV workflow with a direct connection to
the NVE Magasinstatistikk API. I inspected the returned columns, converted the
date fields to pandas datetimes and checked the available EL, NO and VASS area
types. The reservoir plots were recreated from the live response, and the same
loader is used by Streamlit.

I worked with the ENTSO-E Transparency Platform API by selecting four Norwegian
interconnections and requesting the previous two years in one-year windows.
Both directions were labelled as export from Norway or import to Norway. The
requests use bounded concurrency, retries and progress output so a slow request
does not block all remaining connections. The data was converted to UTC
timestamps and duplicate observations were removed. One hourly MW observation
is treated as one MWh in the required annual estimate, and this assumption is
documented in the app.

Spark was used to create a DataFrame and write observations to Cassandra. Before
the fresh run, the Cassandra flow table is truncated so old rows cannot be mixed
with new API data. I read the data back, selected the relevant columns and
added year and month fields. The curated result is then published to MongoDB
with a unique index and batched upserts, making reruns safe and giving the
Streamlit app a database designed for online reads.

The Streamlit experience showed me the difference between notebook exploration
and an application. I added an API-backed reservoir page with an interval slider
and radio buttons for area type. A separate page reads MongoDB and uses two
columns: the left side contains the yearly connection pie chart, while the
right side contains a multi-month line plot. The source explanation is placed
in an expander.

AI tools were used to understand error messages, check API usage, discuss the
data pipeline and improve Python and Streamlit structure. I reviewed and adapted
all suggestions and tested the resulting code. Secrets remain in local
Streamlit configuration and are excluded from GitHub.

## Part 3 log and AI usage

In Part 3 I extended the Part 2 project with spatial weather data and time-series
analysis. I downloaded the NVE region shapefile from Atlas and used GeoPandas to
sample 1000 reproducible locations inside every polygon. The sampled points were
transformed to WGS84 longitude and latitude before being sent to Open-Meteo. The
download function accepts a region identifier and a time interval, requests
hourly ERA5 reanalysis data for precipitation, temperature and wind speed, and
averages the values across the sampled locations. The requests are split into
small batches because the public API limits very large requests. Completed
batches are cached locally, and progress messages make a long download
observable and restartable.

The resulting NO3 series for 2024 is published to the existing MongoDB account
in the `ind320.weather` collection. Upserts and a unique index on region and
timestamp make the publication safe to repeat. The Streamlit weather page reads
this prepared collection rather than downloading weather data every time a
visitor opens the public app.

For precipitation, I used a Discrete Cosine Transform high-pass filter to remove
low-frequency seasonal variation. Robust median and median absolute deviation
estimates from the full year define the SPC boundaries. The plot displays the
original average precipitation and highlights observations outside the limits;
the seasonally adjusted values are used only for classification. For
temperature, Local Outlier Factor identifies anomalies using a default
contamination proportion of 1%.

I also applied STL decomposition to the NVE degree-of-filling series and created
a spectrogram of the same weekly series. The seasonal smoother, trend smoother,
robust fitting, window length and overlap are explicit parameters. The Streamlit
application presents these analyses in two tabbed pages: STL/spectrogram and
precipitation SPC/temperature LOF. AI tools were used to understand GeoPandas,
Open-Meteo, DCT, robust statistics, LOF, STL, MongoDB and Streamlit. I reviewed
and adapted the suggestions, tested the functions with synthetic data, checked
the notebook and Python syntax, and kept all credentials in local or Streamlit
Cloud secrets.

### Submission video note

The submission video demonstrates the API-backed NVE pages, area-type
selection, interval slider, reservoir visualisations and MongoDB-backed
cross-border flow page.

## AI usage

AI tools were used as support throughout the project for both programming and writing.

Claude Code was used at the beginning of the project to help understand the course structure, project requirements and development workflow. During implementation, AI was used to understand Python and Streamlit functionality, troubleshoot technical issues, discuss visualization approaches and improve code structure. GitHub Copilot also provided coding suggestions during development.

AI was additionally used as a writing support tool to improve the wording, structure and clarity of project documentation and other written sections. AI-generated suggestions were reviewed and adapted to the project requirements, and the final code and content were tested and reviewed before submission.
