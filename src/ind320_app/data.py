"""Shared data access and preparation for the notebook and Streamlit app."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

NVE_URL = (
    "https://biapi.nve.no/magasinstatistikk/"
    "api/Magasinstatistikk/HentOffentligData"
)

NVE_COLUMNS = {
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
    "endring_fyllingsgrad": "change_filling_degree",
}


def load_reservoir_data(timeout: int = 60) -> pd.DataFrame:
    """Fetch and normalize the complete public NVE reservoir dataset."""
    response = requests.get(NVE_URL, timeout=timeout)
    response.raise_for_status()
    payload: Any = response.json()
    if not isinstance(payload, list) or not payload:
        raise ValueError("NVE returned an empty or unexpected response.")

    frame = pd.DataFrame(payload).rename(
        columns={key: value for key, value in NVE_COLUMNS.items() if key in payload[0]}
    )
    required = {"date", "area_type", "area_number", "filling_degree"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"NVE response is missing columns: {sorted(missing)}")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    if "next_publication_date" in frame:
        frame["next_publication_date"] = pd.to_datetime(
            frame["next_publication_date"], format="mixed", errors="coerce"
        )
    for column in frame.columns:
        if column not in {"date", "next_publication_date", "area_type"}:
            converted = pd.to_numeric(frame[column], errors="coerce")
            frame[column] = converted.where(converted.notna(), frame[column])
    return frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def clean_flow_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate and add time dimensions to ENTSO-E flow observations."""
    required = {
        "timestamp", "flow_mw", "connection", "direction",
        "source_zone", "target_zone",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Flow data is missing columns: {sorted(missing)}")

    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
    result["flow_mw"] = pd.to_numeric(result["flow_mw"], errors="coerce")
    result = result.dropna(
        subset=["timestamp", "flow_mw", "connection", "direction"]
    ).drop_duplicates(
        subset=["timestamp", "connection", "direction"]
    )
    result["year"] = result["timestamp"].dt.year
    result["month"] = result["timestamp"].dt.month
    return result.sort_values(["connection", "direction", "timestamp"]).reset_index(
        drop=True
    )


def fetch_entsoe_flows(
    client: Any,
    connections: list[tuple[str, str, str]],
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    """Fetch both directions for each connection, using at most one-year windows."""
    frames: list[pd.DataFrame] = []
    window_start = start
    while window_start < end:
        window_end = min(window_start + pd.DateOffset(years=1), end)
        for no_zone, neighbour_zone, connection in connections:
            for source, target, direction in (
                (no_zone, neighbour_zone, "export_from_NO"),
                (neighbour_zone, no_zone, "import_to_NO"),
            ):
                series = client.query_crossborder_flows(
                    country_code_from=source,
                    country_code_to=target,
                    start=window_start,
                    end=window_end,
                )
                if series is None or series.empty:
                    continue
                part = series.rename("flow_mw").rename_axis("timestamp").reset_index()
                part["connection"] = connection
                part["direction"] = direction
                part["source_zone"] = source
                part["target_zone"] = target
                frames.append(part)
        window_start = window_end

    if not frames:
        raise ValueError("ENTSO-E returned no cross-border observations.")
    return clean_flow_data(pd.concat(frames, ignore_index=True))


def annual_energy_by_direction(
    flows: pd.DataFrame, connection: str, year: int
) -> pd.DataFrame:
    """Estimate annual MWh from hourly MW observations for one connection."""
    selected = flows[(flows["connection"] == connection) & (flows["year"] == year)]
    return (
        selected.assign(energy_mwh=selected["flow_mw"])
        .groupby("direction", as_index=False)["energy_mwh"]
        .sum()
    )


def utc_now() -> pd.Timestamp:
    """Return a timezone-aware timestamp suitable for API queries."""
    return pd.Timestamp(datetime.now(timezone.utc)).floor("h")
