"""Interactive map of the available NVE weather-region boundaries."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient

from ind320_app.data import load_reservoir_data
from ind320_app.part4 import WEATHER_PROPERTIES
from ind320_app.ui import render_sidebar

render_sidebar()
st.title("Map")
st.caption(
    "Electricity price areas (NO1-NO5) come from the NVE bidding-area shapefile "
    "(Budområder.shp). The NVE precipitation regions from NVE_Region.shp are "
    "available as a second layer, and Norway as a whole (area type NO) is the "
    "union of the price areas. All are converted to GeoJSON in the Part 4 "
    "notebook. VASS (water-area) polygons are not part of this project, so VASS "
    "cannot be drawn on the map."
)

# Each layer: GeoJSON file, property holding the area code, label property.
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
LAYERS = {
    "Price area (EL)": {
        "file": DATA_DIR / "nve_el_areas.geojson",
        "key": "EL",
        "name": "EL",
    },
    "Norway (NO)": {
        "file": DATA_DIR / "nve_norway.geojson",
        "key": "NO",
        "name": "NO",
    },
    "Weather region": {
        "file": DATA_DIR / "nve_weather_regions.geojson",
        "key": "REGION",
        "name": "REGIONNAVN",
    },
}
layer_name = st.radio("Area type", list(LAYERS), horizontal=True, key="map_area_type")
layer = LAYERS[layer_name]
geojson_path = layer["file"]
if not geojson_path.exists():
    st.error(f"{geojson_path.name} is missing. Run the conversion cell in Part 4.")
    st.stop()
geojson = json.loads(geojson_path.read_text(encoding="utf-8"))
features = geojson["features"]
feature_key = layer["key"]
region_codes = [feature["properties"][feature_key] for feature in features]
region_names = {
    feature["properties"][feature_key]: feature["properties"][layer["name"]]
    for feature in features
}
selection_key = (
    f"selected_{ {'EL': 'el', 'NO': 'no'}.get(feature_key, 'weather') }_region"
)

colour_by = st.radio(
    "Colour areas by",
    ["Weather property", "Reservoir filling"],
    horizontal=True,
    key="map_colour_by",
    help="Reservoir filling is the NVE Magasinstatistikk filling degree for the "
    "chosen week (price areas and Norway only).",
)
property_name = st.selectbox(
    "Weather property",
    options=list(WEATHER_PROPERTIES),
    index=list(WEATHER_PROPERTIES).index("temperature_2m"),
    format_func=lambda value: WEATHER_PROPERTIES[value][0],
    disabled=colour_by != "Weather property",
    key="map_weather_property",
)
st.slider(
    "Forecast horizon (months)",
    min_value=1,
    max_value=12,
    value=6,
    key="forecast_horizon",
    help="Shared with the Filling Forecast page.",
)

@st.cache_data(ttl=600, show_spinner="Loading weather observations...")
def load_weather(selected_property: str) -> pd.DataFrame:
    if "mongo" not in st.secrets or not st.secrets["mongo"].get("uri"):
        raise RuntimeError("Add [mongo].uri to Streamlit secrets.")
    client = MongoClient(
        st.secrets["mongo"]["uri"],
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
    )
    try:
        client.admin.command("ping")
        records = list(
            client["ind320"]["weather"].find(
                {}, {"_id": 0, "region": 1, "timestamp": 1, selected_property: 1}
            )
        )
    finally:
        client.close()
    if not records:
        raise ValueError("MongoDB contains no weather observations.")
    frame = pd.DataFrame(records)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame[selected_property] = pd.to_numeric(frame[selected_property], errors="coerce")
    return frame.dropna(subset=["timestamp", selected_property])

@st.cache_data(ttl=3600, show_spinner="Loading NVE reservoir observations...")
def load_filling() -> pd.DataFrame:
    return load_reservoir_data()

weather = pd.DataFrame(columns=["timestamp", "region", property_name])
if colour_by == "Weather property":
    try:
        weather = load_weather(property_name)
    except Exception as exc:
        st.warning(f"Could not load weather observations: {exc}")

if colour_by != "Weather property":
    date_range = (date(2024, 1, 1), date(2024, 12, 31))
elif weather.empty:
    date_range = st.date_input(
        "Aggregation period",
        value=(date(2024, 1, 1), date(2024, 12, 31)),
        key="part4_map_period",
    )
else:
    minimum_date = weather["timestamp"].min().date()
    maximum_date = weather["timestamp"].max().date()
    date_range = st.date_input(
        "Aggregation period",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
        key="part4_map_period",
    )
if not isinstance(date_range, tuple) or len(date_range) != 2:
    st.info("Select both a start and end date.")
    st.stop()
start_date, end_date = date_range
if start_date > end_date:
    st.error("The start date must be on or before the end date.")
    st.stop()

selected_weather = weather
if not weather.empty:
    selected_weather = weather[
        weather["timestamp"].dt.date.between(start_date, end_date)
    ]
region_values: dict[str, float] = {}
value_label, value_unit = "", ""
if colour_by == "Weather property":
    value_label = f"Mean {WEATHER_PROPERTIES[property_name][0].lower()}"
    value_unit = WEATHER_PROPERTIES[property_name][1]
    if feature_key == "EL":
        # The MongoDB weather documents are labelled by price area (e.g. "NO3").
        for region, group in selected_weather.groupby("region"):
            if str(region) in region_codes:
                region_values[str(region)] = float(group[property_name].mean())
    elif feature_key == "NO" and not selected_weather.empty:
        region_values["NO"] = float(selected_weather[property_name].mean())
else:
    value_label, value_unit = "Reservoir filling", "%"
    if feature_key == "REGION":
        st.info("Reservoir filling is not available for the precipitation regions.")
    else:
        try:
            reservoirs = load_filling()
        except Exception as exc:
            st.warning(f"Could not load NVE reservoir data: {exc}")
            reservoirs = pd.DataFrame()
        if not reservoirs.empty:
            area_type = "EL" if feature_key == "EL" else "NO"
            areas = reservoirs[reservoirs["area_type"] == area_type]
            weeks = sorted(areas["date"].dropna().unique())[-520:]
            chosen_week = st.select_slider(
                "Week",
                options=weeks,
                value=weeks[-1],
                format_func=lambda value: pd.Timestamp(value).strftime("%Y-%m-%d"),
                key="map_week",
            )
            week_rows = areas[areas["date"] == chosen_week]
            for row in week_rows.itertuples():
                code = f"NO{int(row.area_number)}" if feature_key == "EL" else "NO"
                if code in region_codes and pd.notna(row.filling_degree):
                    region_values[code] = float(row.filling_degree) * 100

selected_region = st.selectbox(
    f"Selected {layer_name.lower()}",
    options=region_codes,
    format_func=lambda code: f"{region_names[code]} ({code})"
    if region_names[code] != code
    else code,
    key=selection_key,
)
z_values = [region_values.get(code, float("nan")) for code in region_codes]
figure = go.Figure(
    go.Choroplethmap(
        geojson=geojson,
        locations=region_codes,
        z=z_values,
        featureidkey=f"properties.{feature_key}",
        customdata=[region_names[code] for code in region_codes],
        colorscale="YlOrRd",
        marker={"opacity": 0.65, "line": {"color": "#f4f1de", "width": 1.5}},
        colorbar={"title": value_unit},
        hovertemplate="%{customdata}<br>%{z:.2f}<extra></extra>",
    )
)
selected_feature = next(
    feature for feature in features if feature["properties"][feature_key] == selected_region
)
geometry = selected_feature["geometry"]
polygons = (
    geometry["coordinates"]
    if geometry["type"] == "MultiPolygon"
    else [geometry["coordinates"]]
)
outline_lon: list[float | None] = []
outline_lat: list[float | None] = []
for polygon in polygons:
    for ring in polygon:
        outline_lon.extend([point[0] for point in ring] + [None])
        outline_lat.extend([point[1] for point in ring] + [None])
figure.add_trace(
    go.Scattermap(
        lon=outline_lon,
        lat=outline_lat,
        mode="lines",
        line={"color": "#e76f51", "width": 4},
        name=f"Selected: {region_names[selected_region]}",
        hoverinfo="skip",
    )
)
figure.update_layout(
    map={
        "style": "open-street-map",
        "center": {"lat": 64.5, "lon": 12.0},
        "zoom": 3.2,
    },
    height=650,
    template="plotly_white",
    margin={"l": 0, "r": 0, "t": 20, "b": 0},
)
map_state = st.plotly_chart(
    figure,
    use_container_width=True,
    key=f"map_{feature_key}",
    on_select="rerun",
    selection_mode="points",
)
if map_state.selection.points:
    selected_point = map_state.selection.points[-1]
    clicked_region = selected_point.get("location")
    if clicked_region in region_codes and clicked_region != selected_region:
        st.session_state[selection_key] = clicked_region
        st.rerun()
if selected_region not in region_values:
    st.warning(
        f"No {value_label.lower()} data is available "
        f"for {region_names[selected_region]} in the selected period."
    )
else:
    st.metric(
        f"{value_label} in {region_names[selected_region]}",
        f"{region_values[selected_region]:.2f} {value_unit}",
    )
if colour_by == "Reservoir filling":
    pass
elif feature_key == "EL":
    st.info(
        "Only NO3 weather data is currently published, so only the NO3 polygon "
        "is coloured. The other price areas are shown as outlines."
    )
elif feature_key == "REGION":
    st.info(
        "Weather data is stored per price area, not per precipitation region, "
        "so this layer shows outlines only. Switch to Price area (EL) for values."
    )
