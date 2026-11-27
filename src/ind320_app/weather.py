"""Direct Open-Meteo (ERA5) weather downloads for the Streamlit app.

The app downloads weather straight from the Open-Meteo archive API instead of
reading it from MongoDB. To stay inside the API's rate limits a few random
locations per price area (NO1-NO5) are used; they are sampled inside the
bidding-area polygons in ``data/nve_el_areas.geojson`` (converted from
``Budområder.shp`` in the Part 4 notebook).

Rate-limit arithmetic (Open-Meteo counts roughly locations x days/14 x
variables/10 "calls" per request, with 600 calls/minute and 5000 calls/hour):
one year x 5 locations x 3 variables is about 39 calls, so a handful of years
is fine. Requests are therefore made one calendar year at a time and cached.
"""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Sequence

import pandas as pd
import requests
import streamlit as st

EL_GEOJSON = Path(__file__).resolve().parents[2] / "data" / "nve_el_areas.geojson"
AREAS = ("NO1", "NO2", "NO3", "NO4", "NO5")
POINTS_PER_AREA = 5
# ERA5 is published with a delay of a few days; stay safely behind it.
LATEST_AVAILABLE = date.today() - timedelta(days=7)


@lru_cache(maxsize=8)
def sample_area_points(
    points: int = POINTS_PER_AREA, seed: int = 42
) -> dict[str, list[tuple[float, float]]]:
    """Random (longitude, latitude) points inside each price-area polygon."""
    import geopandas as gpd

    areas = gpd.read_file(EL_GEOJSON)
    # Sample in a metric projection (EPSG:25833) so points are uniform over the
    # area, then convert back to longitude/latitude for the API.
    sampled = (
        areas.to_crs(epsg=25833)
        .geometry.sample_points(size=points, random_state=seed)
        .to_crs(epsg=4326)
    )
    return {
        str(code): [(point.x, point.y) for point in multipoint.geoms]
        for code, multipoint in zip(areas["EL"], sampled)
    }


def fetch_weather_chunk(
    area: str, start: str, end: str, points: int = POINTS_PER_AREA
) -> pd.DataFrame:
    """Download hourly ERA5 data for one area and period (one API request).

    Temperature, precipitation and wind speed are averaged over the sampled
    locations. ``max_retries=1`` makes the app fail fast with a clear message
    if the API is rate limiting, instead of sleeping for minutes.
    """
    from ind320_app.part3 import download_weather

    return download_weather(
        area,
        start,
        end,
        sample_area_points(points),
        timeout=30,
        batch_size=points,
        request_pause=0,
        max_retries=1,
        show_progress=False,
    )


@st.cache_data(ttl=86400, show_spinner=False)
def _cached_chunk(area: str, start: str, end: str, points: int) -> pd.DataFrame:
    """Cache each (area, calendar-year) download for 24 hours."""
    return fetch_weather_chunk(area, start, end, points)


def _year_chunks(start: date, end: date) -> list[tuple[str, str]]:
    """Whole calendar years covering ``start``..``end`` (better cache reuse)."""
    chunks = []
    for year in range(start.year, end.year + 1):
        chunk_end = min(date(year, 12, 31), LATEST_AVAILABLE)
        chunks.append((date(year, 1, 1).isoformat(), chunk_end.isoformat()))
    return chunks


def load_area_weather(
    areas: Sequence[str],
    start: date,
    end: date,
    points: int = POINTS_PER_AREA,
) -> pd.DataFrame:
    """Hourly weather for the given areas and period, indexed by UTC time.

    The result has the columns temperature_2m, precipitation, wind_speed_10m
    and ``region`` (the price area). Raises ``RuntimeError`` with a readable
    message when Open-Meteo cannot be reached or rate limits the request.
    """
    if start > end:
        raise ValueError("The start date must be on or before the end date.")
    if end > LATEST_AVAILABLE:
        end = LATEST_AVAILABLE
    jobs = [(a, s, e) for a in areas for s, e in _year_chunks(start, end)]
    progress = st.progress(0.0, text="Downloading ERA5 weather from Open-Meteo...")
    frames = []
    try:
        for number, (area, chunk_start, chunk_end) in enumerate(jobs, start=1):
            progress.progress(
                (number - 1) / len(jobs),
                text=f"Open-Meteo ERA5: {area} {chunk_start[:4]} "
                f"({number}/{len(jobs)})",
            )
            frame = _cached_chunk(area, chunk_start, chunk_end, points).copy()
            frame["region"] = area
            frames.append(frame)
    except requests.HTTPError as exc:
        if "limit" in str(exc).lower() or "429" in str(exc):
            raise RuntimeError(
                "Open-Meteo's request limit was reached. The limit resets "
                "hourly; wait a while or choose a shorter period."
            ) from exc
        raise RuntimeError(f"Open-Meteo returned an error: {exc}") from exc
    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not reach Open-Meteo (check the internet connection): {exc}"
        ) from exc
    finally:
        progress.empty()

    weather = pd.concat(frames).sort_index()
    weather.index.name = "timestamp"
    # Trim the whole-year downloads to the period the user asked for.
    first = pd.Timestamp(start, tz="UTC")
    last = pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
    weather = weather[(weather.index >= first) & (weather.index < last)]
    if weather.empty:
        raise ValueError("Open-Meteo returned no data for the selected period.")
    return weather
