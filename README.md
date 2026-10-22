# IND320 – Data to Decision

This repository contains my project work for **IND320 Data to Decision** at NMBU.

The project explores Norwegian reservoir data and cross-border electricity flows using Python, Pandas, Spark, Cassandra, MongoDB and Streamlit. Part 2 uses the NVE API directly and publishes curated ENTSO-E observations to MongoDB for the online app.

## Project contents

* `IND320_part1.ipynb` – Jupyter Notebook for Part 1.
* `IND320_part2.ipynb` – Jupyter Notebook documenting the Part 2 API, Spark, Cassandra and MongoDB pipeline.
* `main.py` – Main page of the Streamlit application.
* `pages/` – Additional pages for data exploration and visualization.
* `src/ind320_app/data.py` – Shared API and data-preparation functions.
* `pyproject.toml` – Project dependencies and configuration.
* `uv.lock` – Locked dependency versions.

## Streamlit application

The interactive application provides:

* Current NVE reservoir data fetched directly from the API.
* Radio buttons for EL, NO and VASS area types.
* An interval slider controlling the downloaded reservoir period.
* MongoDB-backed cross-border flow plots with a yearly pie chart and multi-month line chart.

`EL`, `NO` and `VASS` are NVE reservoir area types. They are unrelated to ENTSO-E
bidding zones. ENTSO-E connections use codes such as `NO_2` and `DK_1`; therefore
the Norway–Denmark connection is queried as `NO_2 -> DK_1`, not as a generic
`NO -> DK` connection.

**Live application:**
https://ind320-app-wktckrzn7uk2axexipgwwq.streamlit.app

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

## Running locally

From the `ind320-app` folder:

```bash
.venv/bin/python -m streamlit run main.py
```

The app opens at `http://localhost:8501`. If the virtual environment is
activated first, the equivalent command is `streamlit run main.py`.

The notebook and the Streamlit app use different data destinations:

1. NVE reservoir observations are fetched directly from the public NVE API.
2. ENTSO-E observations are retrieved and processed in the notebook.
3. Spark writes the flow observations to Cassandra and reads the curated data.
4. The notebook writes the fresh, Spark-curated observations to MongoDB with
   batched, idempotent upserts and a unique index.
5. Streamlit reads the MongoDB collection on the cross-border page.

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

### Submission video note

The submission video demonstrates the API-backed NVE pages, area-type
selection, interval slider, reservoir visualisations and MongoDB-backed
cross-border flow page.

## AI usage

AI tools were used as support throughout the project for both programming and writing.

Claude Code was used at the beginning of the project to help understand the course structure, project requirements and development workflow. During implementation, AI was used to understand Python and Streamlit functionality, troubleshoot technical issues, discuss visualization approaches and improve code structure. GitHub Copilot also provided coding suggestions during development.

AI was additionally used as a writing support tool to improve the wording, structure and clarity of project documentation and other written sections. AI-generated suggestions were reviewed and adapted to the project requirements, and the final code and content were tested and reviewed before submission.
