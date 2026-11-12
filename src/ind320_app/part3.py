"""Reusable weather and time-series analyses for IND320 Part 3."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import requests
import time
from pymongo import MongoClient, UpdateOne
from scipy.fft import dct, idct
from scipy.signal import spectrogram
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def publish_weather_to_mongodb(
    weather: pd.DataFrame,
    region: str,
    mongo_uri: str,
    database: str = "ind320",
    collection: str = "weather",
    batch_size: int = 1000,
) -> int:
    """Upsert aggregated weather observations into MongoDB."""
    if not mongo_uri:
        raise ValueError("mongo_uri cannot be empty.")
    if weather.empty:
        raise ValueError("Cannot publish an empty weather frame.")
    required = {"precipitation", "temperature_2m"}
    missing = required.difference(weather.columns)
    if missing:
        raise ValueError(f"Weather data is missing columns: {sorted(missing)}")

    frame = weather.copy()
    frame.index = pd.to_datetime(frame.index, utc=True, errors="coerce")
    frame = frame.reset_index(names="timestamp").dropna(subset=["timestamp"])
    frame["region"] = region
    records = frame.to_dict("records")
    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        maxPoolSize=5,
    )
    try:
        client.admin.command("ping")
        target = client[database][collection]
        target.create_index([("region", 1), ("timestamp", 1)], unique=True)
        written = 0
        for offset in range(0, len(records), batch_size):
            operations = [
                UpdateOne(
                    {"region": record["region"], "timestamp": record["timestamp"].to_pydatetime()},
                    {"$set": {**record, "timestamp": record["timestamp"].to_pydatetime()}},
                    upsert=True,
                )
                for record in records[offset : offset + batch_size]
            ]
            if operations:
                target.bulk_write(operations, ordered=False)
                written += len(operations)
        return written
    finally:
        client.close()


def sample_region_coordinates(
    shapefile: str | Path, points_per_region: int = 1000, random_state: int = 42
) -> dict[str, list[tuple[float, float]]]:
    """Sample WGS84 ``(longitude, latitude)`` pairs from each NVE polygon."""
    import geopandas as gpd

    if points_per_region < 1:
        raise ValueError("points_per_region must be positive.")
    regions = gpd.read_file(shapefile)
    name_column = next(
        (column for column in ("REGION", "region", "NAME", "name") if column in regions),
        None,
    )
    if name_column is None:
        raise ValueError("The shapefile must contain a region-name column.")
    # Match the Atlas lecture example: sample inside the source polygons,
    # then transform the sampled points to longitude/latitude.
    sampled = regions.geometry.sample_points(
        size=points_per_region, random_state=random_state
    ).to_crs(epsg=4326)
    regions_wgs84 = regions.to_crs(epsg=4326)
    result: dict[str, list[tuple[float, float]]] = {}
    for index, multipoint in sampled.items():
        name = str(regions_wgs84.loc[index, name_column])
        result[name] = [(point.x, point.y) for point in multipoint.geoms]
    return result


def _find_region(
    coordinates: dict[str, list[tuple[float, float]]], region: str
) -> list[tuple[float, float]]:
    # The Atlas layer uses precipitation-region codes. The course mapping
    # combines RM+RN for North and RS+RØ for East.
    aliases = {
        "NO1": ("NO1", "RØ", "RÃ", "Øst", "East"),
        "NO2": ("NO2", "RS", "Sør", "South"),
        "NO3": ("NO3", "RM", "Midt", "Middle"),
        "NO4": ("NO4", "RM", "RN", "RM+RN", "North"),
        "NO5": ("NO5", "RV", "Vest", "West"),
    }
    points: list[tuple[float, float]] = []
    for key in (region, *aliases.get(region, ())):
        points.extend(coordinates.get(key, []))
    if points:
        return points
    raise KeyError(f"No sampled coordinates found for region {region!r}.")


def download_weather(
    region: str,
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    coordinates: dict[str, list[tuple[float, float]]],
    timeout: int = 60,
    session: requests.Session | None = None,
    batch_size: int = 10,
    request_pause: float = 2.0,
    max_retries: int = 6,
    cache_dir: str | Path | None = None,
    show_progress: bool = True,
) -> pd.DataFrame:
    """Download ERA5 hourly weather and average the sampled locations.

    Small sequential batches avoid the public API's request-size and rate
    limits while still using every sampled location.
    """
    points = _find_region(coordinates, region)
    if batch_size < 1:
        raise ValueError("batch_size must be positive.")
    if request_pause < 0:
        raise ValueError("request_pause cannot be negative.")
    start_date = pd.Timestamp(start).date().isoformat()
    end_date = pd.Timestamp(end).date().isoformat()
    client = session or requests.Session()
    cache_path = Path(cache_dir) if cache_dir is not None else None
    if cache_path is not None:
        cache_path.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    # Open-Meteo accepts comma-separated coordinates, so 1000 samples do not
    # require 1000 HTTP requests.
    total_batches = (len(points) + batch_size - 1) // batch_size
    for batch_number, offset in enumerate(
        range(0, len(points), batch_size), start=1
    ):
        batch = points[offset : offset + batch_size]
        params = {
            "latitude": ",".join(str(latitude) for _, latitude in batch),
            "longitude": ",".join(str(longitude) for longitude, _ in batch),
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,precipitation,wind_speed_10m",
            "models": "era5",
            "timezone": "UTC",
        }
        cache_file = None
        if cache_path is not None:
            cache_file = cache_path / f"{region}_{start_date}_{end_date}_{offset}.json"
        if cache_file is not None and cache_file.exists():
            payload = json.loads(cache_file.read_text())
            source = "cache"
        else:
            source = "API"
            for attempt in range(max_retries + 1):
                response = client.get(ARCHIVE_URL, params=params, timeout=timeout)
                if response.status_code != 429:
                    try:
                        response.raise_for_status()
                    except requests.HTTPError as error:
                        raise requests.HTTPError(
                            f"Open-Meteo request failed for batch "
                            f"{offset + 1}-{offset + len(batch)}: "
                            f"{response.text[:500]}",
                            response=response,
                        ) from error
                    break
                if attempt == max_retries:
                    raise requests.HTTPError(
                        f"Open-Meteo rate limit persisted for batch "
                        f"{offset + 1}-{offset + len(batch)}. "
                        "Wait and rerun; cached batches will be reused.",
                        response=response,
                    )
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(120.0, 10 * 2**attempt)
                if show_progress and (
                    batch_number % 10 == 0 or batch_number == total_batches
                ):
                    print(
                        f"Weather download: batch {batch_number}/{total_batches} "
                        f"rate-limited (429); retry {attempt + 1}/{max_retries} "
                        f"in {delay:.0f}s",
                        flush=True,
                    )
                time.sleep(delay)
            time.sleep(request_pause)
            payload = response.json()
            if cache_file is not None:
                cache_file.write_text(response.text)
        if show_progress:
            percentage = 100 * batch_number / total_batches
            print(
                f"Weather download: batch {batch_number}/{total_batches} "
                f"({percentage:5.1f}%) | points {min(offset + len(batch), len(points))}/"
                f"{len(points)} | {source}",
                flush=True,
            )
        payloads = payload if isinstance(payload, list) else [payload]
        for location in payloads:
            hourly = location.get("hourly")
            if not hourly or "time" not in hourly:
                raise ValueError("Open-Meteo returned no hourly data for a sampled location.")
            frame = pd.DataFrame(hourly)
            frame["time"] = pd.to_datetime(frame["time"], utc=True)
            frames.append(frame.set_index("time"))
    if not frames:
        raise ValueError(f"No coordinates available for {region}.")
    combined = pd.concat(frames, axis=1)
    return combined.T.groupby(level=0).mean().T.sort_index()


def _series(values: pd.Series | Iterable[float]) -> pd.Series:
    result = pd.Series(values, dtype="float64").sort_index()
    return result.interpolate(limit_direction="both").dropna()


def plot_spc_precipitation(
    precipitation: pd.Series | Iterable[float],
    cutoff: int = 12,
    sigma: float = 3.0,
) -> tuple[plt.Figure, pd.DataFrame]:
    """Plot precipitation with robust SPC limits after DCT high-pass filtering."""
    values = _series(precipitation)
    if not 0 < cutoff < len(values):
        raise ValueError("cutoff must be between 1 and the number of observations.")
    coefficients = dct(values.to_numpy(), type=2, norm="ortho")
    seasonal = idct(
        np.r_[coefficients[:cutoff], np.zeros(len(values) - cutoff)],
        type=2,
        norm="ortho",
    )
    satv = values.to_numpy() - seasonal
    center = float(np.median(satv))
    mad = float(np.median(np.abs(satv - center)))
    scale = 1.4826 * mad or float(np.std(satv)) or 1.0
    lower, upper = center - sigma * scale, center + sigma * scale
    outlier = (satv < lower) | (satv > upper)
    summary = pd.DataFrame(
        {"value": values, "satv": satv, "outlier": outlier},
        index=values.index,
    )
    figure, axis = plt.subplots(figsize=(11, 4))
    axis.plot(values.index, values, label="Average precipitation")
    axis.scatter(values.index[outlier], values[outlier], color="crimson", label="SPC outlier")
    axis.axhline(values.mean(), color="black", alpha=0.25, label="Mean")
    axis.fill_between(values.index, lower + seasonal, upper + seasonal, alpha=0.15, label="SPC limits")
    axis.set(
        title="Average precipitation with robust SPC limits",
        ylabel="Precipitation (mm/h)",
    )
    axis.legend(loc="upper right", framealpha=0.8)
    figure.tight_layout()
    return figure, summary


def plot_lof_temperature(
    temperature: pd.Series | Iterable[float], contamination: float = 0.01
) -> tuple[plt.Figure, pd.DataFrame]:
    """Plot temperature and Local Outlier Factor anomalies."""
    values = _series(temperature)
    if not 0 < contamination < 0.5:
        raise ValueError("contamination must be between 0 and 0.5.")
    neighbours = max(2, min(20, len(values) - 1))
    labels = LocalOutlierFactor(
        n_neighbors=neighbours, contamination=contamination
    ).fit_predict(values.to_numpy().reshape(-1, 1))
    summary = pd.DataFrame(
        {"value": values, "anomaly": labels == -1}, index=values.index
    )
    figure, axis = plt.subplots(figsize=(11, 4))
    axis.plot(values.index, values, label="Average temperature")
    anomalies = summary["anomaly"]
    axis.scatter(values.index[anomalies], values[anomalies], color="crimson", label="LOF anomaly")
    axis.set(title="Average temperature and Local Outlier Factor anomalies", ylabel="°C")
    axis.legend()
    figure.tight_layout()
    return figure, summary


def plot_stl(
    filling_degree: pd.Series | Iterable[float],
    seasonal: int = 13,
    trend: int | None = None,
    robust: bool = True,
) -> plt.Figure:
    """Return an STL decomposition plot for a regularly sampled series."""
    values = _series(filling_degree).asfreq("W").interpolate()
    if seasonal < 3 or seasonal % 2 == 0:
        raise ValueError("seasonal must be an odd integer of at least 3.")
    # Reservoir observations are weekly, so one annual seasonal cycle is 52 weeks.
    result = STL(values, period=52, seasonal=seasonal, trend=trend, robust=robust).fit()
    figure = result.plot()
    figure.set_size_inches(11, 8)
    figure.suptitle("STL decomposition of reservoir degree of filling", y=1.02)
    figure.tight_layout()
    return figure


def plot_spectrogram(
    values: pd.Series | Iterable[float], window_length: int = 52, overlap: float = 0.5
) -> plt.Figure:
    """Return a spectrogram plot with configurable window and overlap."""
    series = _series(values)
    if window_length < 4 or window_length > len(series):
        raise ValueError("window_length must be between 4 and the series length.")
    if not 0 <= overlap < 1:
        raise ValueError("overlap must be in the interval [0, 1).")
    frequencies, times, power = spectrogram(
        series.to_numpy(),
        nperseg=window_length,
        noverlap=int(window_length * overlap),
        detrend="linear",
    )
    power_db = 10 * np.log10(np.maximum(power, np.finfo(float).tiny))
    start = series.index[0]
    dates = start + pd.to_timedelta(times, unit="W")
    figure, axis = plt.subplots(figsize=(11, 4))
    mesh = axis.pcolormesh(dates, frequencies, power_db, shading="auto")
    figure.colorbar(mesh, ax=axis, label="Power (dB)")
    axis.set_ylim(0, min(0.25, frequencies[-1]))
    axis.set(
        title="Spectrogram of reservoir filling degree",
        xlabel="Date",
        ylabel="Frequency (cycles/week)",
    )
    axis.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    figure.autofmt_xdate()
    figure.tight_layout()
    return figure
