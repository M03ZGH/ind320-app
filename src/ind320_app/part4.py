"""Part 4 currency, correlation, and online reservoir-forecast helpers.

Imported by the Streamlit pages and by Notebooks/IND320_part4.ipynb.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from typing import Sequence

import numpy as np
import pandas as pd
import requests
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from scipy.fft import dct, idct
from sklearn.neighbors import LocalOutlierFactor
from statsmodels.tsa.seasonal import STL

NORGES_BANK_URL = "https://data.norges-bank.no/api/data/EXR"
WEATHER_PROPERTIES = {
    "temperature_2m": ("Temperature", "°C"),
    "precipitation": ("Precipitation", "mm/h"),
    "wind_speed_10m": ("Wind speed", "km/h"),
}


def download_currency_rates(
    start: str | pd.Timestamp,
    end: str | pd.Timestamp,
    currencies: Sequence[str] = ("EUR", "USD"),
    timeout: int = 30,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Download Norges Bank's daily spot rates, quoted as NOK per currency unit."""
    start_date = pd.Timestamp(start).date()
    end_date = pd.Timestamp(end).date()
    if start_date > end_date:
        raise ValueError("start must be on or before end.")
    requested = tuple(dict.fromkeys(currency.upper() for currency in currencies))
    unsupported = set(requested).difference({"EUR", "USD"})
    if not requested or unsupported:
        raise ValueError(
            f"currencies must contain EUR and/or USD; unsupported: {sorted(unsupported)}"
        )

    # One request per currency; the SDMX series key is B.<CCY>.NOK.SP (daily spot).
    client = session or requests.Session()
    rates: list[pd.Series] = []
    for currency in requested:
        response = client.get(
            f"{NORGES_BANK_URL}/B.{currency}.NOK.SP",
            params={
                "startPeriod": start_date.isoformat(),
                "endPeriod": end_date.isoformat(),
                "format": "csv",
                "locale": "en",
            },
            timeout=timeout,
        )
        response.raise_for_status()
        frame = pd.read_csv(StringIO(response.text), sep=";")
        required = {"TIME_PERIOD", "OBS_VALUE"}
        if not required.issubset(frame.columns):
            raise ValueError(
                f"Norges Bank returned an unexpected {currency} response."
            )
        values = pd.to_numeric(frame["OBS_VALUE"], errors="coerce")
        dates = pd.to_datetime(frame["TIME_PERIOD"], errors="coerce")
        series = pd.Series(values.to_numpy(), index=dates, name=f"{currency}_NOK")
        series = series.dropna()
        if series.empty:
            raise ValueError(
                f"Norges Bank returned no {currency}/NOK observations for "
                f"{start_date} through {end_date}."
            )
        rates.append(series)

    result = pd.concat(rates, axis=1).sort_index()
    result.index.name = "date"
    return result


def _monthly_series(values: pd.Series, name: str) -> pd.Series:
    """Normalize a series to month-start values while preserving local dates."""
    series = pd.Series(values, copy=True, name=name).dropna()
    index = pd.DatetimeIndex(pd.to_datetime(series.index))
    if index.tz is not None:
        index = index.tz_convert("Europe/Oslo").tz_localize(None)
    series.index = index
    series = pd.to_numeric(series, errors="coerce").dropna().sort_index()
    return series.resample("MS").mean()


def sliding_window_correlation(
    weather: pd.Series,
    reservoir: pd.Series,
    lag: int = 0,
    window: int = 12,
) -> pd.DataFrame:
    """Correlate monthly weather with filling; positive lag means weather leads."""
    if lag < 0:
        raise ValueError("lag must be zero or a positive number of months.")
    if window < 3:
        raise ValueError("window must be at least 3 months.")
    weather_monthly = _monthly_series(weather, "weather")
    reservoir_monthly = _monthly_series(reservoir, "filling")
    paired = pd.concat(
        [weather_monthly.shift(lag), reservoir_monthly], axis=1
    ).dropna()
    if len(paired) < window:
        raise ValueError(
            f"Only {len(paired)} paired months are available; window={window}."
        )
    correlations = paired["weather"].rolling(window).corr(paired["filling"])
    return pd.DataFrame(
        {
            "correlation": correlations,
            "observations": paired["weather"].rolling(window).count(),
        }
    ).dropna()


@dataclass(frozen=True)
class ForecastResult:
    """Forecast values and chronological one-step validation metrics."""

    forecast: pd.Series
    history: pd.Series
    mae: float
    persistence_mae: float
    observations: int
    validation_observations: int


def forecast_reservoir_filling(
    filling: pd.Series,
    exogenous: pd.DataFrame | None = None,
    selected_sources: Sequence[str] | None = None,
    history_months: int = 120,
    horizon: int = 6,
    lags: int = 12,
    learning_rate: float = 0.01,
) -> ForecastResult:
    """Train a River lag-based regressor and recursively forecast monthly filling.

    Optional exogenous inputs are lagged by one month. As future observations
    are not known, the latest observed monthly value is held constant in the
    forecast horizon.
    """
    from river import linear_model, optim, preprocessing

    if history_months < 24:
        raise ValueError("history_months must be at least 24.")
    if horizon < 1:
        raise ValueError("horizon must be at least 1 month.")
    if lags < 1 or lags >= history_months - 12:
        raise ValueError("lags must be positive and leave at least 12 training months.")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be positive.")

    # 1) Monthly resolution keeps training fast (~120 rows) and still captures
    #    the seasonal cycle; weekly NVE values are averaged per month.
    target = _monthly_series(filling, "filling").tail(history_months)
    target = target.asfreq("MS").interpolate(method="time", limit_direction="both")
    if target.isna().any() or len(target) < lags + 18:
        raise ValueError(
            "The selected history does not contain enough monthly observations "
            f"for lags={lags}; provide at least {lags + 18} months."
        )

    exog: pd.DataFrame | None = None
    if selected_sources and exogenous is None:
        raise ValueError("Provide exogenous data for the selected sources.")
    if exogenous is not None and not exogenous.empty:
        exog = exogenous.copy()
        if selected_sources is not None:
            missing_sources = set(selected_sources).difference(exog.columns)
            if missing_sources:
                raise ValueError(
                    f"Selected exogenous columns are missing: "
                    f"{sorted(missing_sources)}"
                )
            exog = exog.loc[:, list(selected_sources)]
        idx = pd.DatetimeIndex(pd.to_datetime(exog.index))
        if idx.tz is not None:
            idx = idx.tz_convert("Europe/Oslo").tz_localize(None)
        exog.index = idx
        exog = exog.apply(pd.to_numeric, errors="coerce")
        exog = exog.groupby(exog.index.to_period("M").to_timestamp()).mean()
        exog = exog.reindex(target.index).ffill()
        exog = exog.dropna(axis=1, how="all")
        if exog.empty:
            exog = None

    # 2) Feature builder: lagged filling, cyclical month encoding and
    #    (optional) one-month-lagged exogenous variables.
    def features(position: int, values: list[float]) -> dict[str, float]:
        result = {
            f"filling_lag_{lag}": float(values[position - lag])
            for lag in range(1, lags + 1)
        }
        month = int(
            (target.index[0] + pd.DateOffset(months=position)).month
        )
        result["month_sin"] = float(np.sin(2 * np.pi * month / 12))
        result["month_cos"] = float(np.cos(2 * np.pi * month / 12))
        if exog is not None:
            previous = max(0, min(position - 1, len(target) - 1))
            for column in exog.columns:
                value = exog.iloc[previous][column]
                if pd.notna(value):
                    result[f"{column}_lag_1"] = float(value)
        return result

    # 3) Online linear model: scaling + SGD regression from the River framework.
    def new_model():
        return preprocessing.StandardScaler() | linear_model.LinearRegression(
            optimizer=optim.SGD(lr=learning_rate),
            intercept_lr=learning_rate,
        )

    # 4) Chronological walk-forward validation: learn up to a split point, then
    #    predict one step ahead and learn from the true value (no look-ahead).
    values = target.astype(float).tolist()
    test_start = max(lags + 12, len(values) - min(12, max(6, len(values) // 5)))
    validation_model = new_model()
    for position in range(lags, test_start):
        validation_model.learn_one(
            features(position, values), values[position]
        )

    predictions: list[float] = []
    actuals: list[float] = []
    persistence: list[float] = []
    for position in range(test_start, len(values)):
        prediction = validation_model.predict_one(features(position, values))
        predicted_value = float(prediction) if prediction is not None else values[position - 1]
        predictions.append(predicted_value)
        actuals.append(values[position])
        persistence.append(values[position - 1])
        validation_model.learn_one(features(position, values), values[position])

    if not actuals:
        raise ValueError("Not enough monthly observations for validation.")

    # 5) Refit on all history, then forecast recursively: each prediction is fed
    #    back as the newest lag value for the next month.
    model = new_model()
    for position in range(lags, len(values)):
        model.learn_one(features(position, values), values[position])

    recursive_values = values.copy()
    forecast_values: list[float] = []
    future_index = pd.date_range(
        target.index[-1] + pd.offsets.MonthBegin(1),
        periods=horizon,
        freq="MS",
        name="date",
    )
    for position in range(len(values), len(values) + horizon):
        prediction = model.predict_one(features(position, recursive_values))
        next_value = (
            float(prediction)
            if prediction is not None and np.isfinite(prediction)
            else recursive_values[-1]
        )
        next_value = float(np.clip(next_value, 0.0, 1.0))
        forecast_values.append(next_value)
        recursive_values.append(next_value)

    return ForecastResult(
        forecast=pd.Series(forecast_values, index=future_index, name="forecast"),
        history=target,
        mae=float(np.mean(np.abs(np.asarray(actuals) - np.asarray(predictions)))),
        persistence_mae=float(
            np.mean(np.abs(np.asarray(actuals) - np.asarray(persistence)))
        ),
        observations=len(target),
        validation_observations=len(actuals),
    )


def plot_weather_spc(
    weather: pd.Series,
    property_name: str,
    cutoff: int = 12,
    sigma: float = 3.0,
) -> tuple[go.Figure, pd.DataFrame]:
    """Create an interactive DCT/SPC view for a selected weather variable."""
    values = pd.to_numeric(weather, errors="coerce").dropna().sort_index()
    if len(values) < 4 or not 1 <= cutoff < len(values):
        raise ValueError("SPC requires at least four values and a valid DCT cutoff.")
    if sigma <= 0:
        raise ValueError("sigma must be positive.")
    coefficients = dct(values.to_numpy(), type=2, norm="ortho")
    seasonal = idct(
        np.r_[coefficients[:cutoff], np.zeros(len(values) - cutoff)],
        type=2,
        norm="ortho",
    )
    adjusted = values.to_numpy() - seasonal
    center = float(np.median(adjusted))
    mad = float(np.median(np.abs(adjusted - center)))
    scale = 1.4826 * mad or float(np.std(adjusted)) or 1.0
    lower = center - sigma * scale + seasonal
    upper = center + sigma * scale + seasonal
    outlier = (adjusted < center - sigma * scale) | (
        adjusted > center + sigma * scale
    )
    summary = pd.DataFrame(
        {
            "value": values,
            "seasonally_adjusted": adjusted,
            "lower_limit": lower,
            "upper_limit": upper,
            "outlier": outlier,
        },
        index=values.index,
    )
    label, unit = WEATHER_PROPERTIES.get(property_name, (property_name, ""))
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(x=values.index, y=values, name=label, mode="lines")
    )
    figure.add_trace(
        go.Scatter(
            x=values.index,
            y=upper,
            name="Upper SPC limit",
            mode="lines",
            line={"width": 1, "dash": "dash"},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=values.index,
            y=lower,
            name="Lower SPC limit",
            mode="lines",
            line={"width": 1, "dash": "dash"},
            fill="tonexty",
            fillcolor="rgba(58, 160, 190, 0.12)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=values.index[outlier],
            y=values[outlier],
            name="SPC outlier",
            mode="markers",
            marker={"color": "#e76f51", "size": 8},
        )
    )
    figure.update_layout(
        title=f"{label} with robust SPC limits",
        xaxis_title="Date",
        yaxis_title=unit,
        template="plotly_white",
        hovermode="x unified",
    )
    return figure, summary


def plot_weather_lof(
    weather: pd.Series, property_name: str, contamination: float = 0.01
) -> tuple[go.Figure, pd.DataFrame]:
    """Create an interactive LOF anomaly chart for a selected weather variable."""
    values = pd.to_numeric(weather, errors="coerce").dropna().sort_index()
    if not 0 < contamination < 0.5:
        raise ValueError("contamination must be between 0 and 0.5.")
    if len(values) < 4:
        raise ValueError("LOF requires at least four non-missing observations.")
    neighbours = max(2, min(20, len(values) - 1))
    labels = LocalOutlierFactor(
        n_neighbors=neighbours, contamination=contamination
    ).fit_predict(values.to_numpy().reshape(-1, 1))
    summary = pd.DataFrame(
        {"value": values, "anomaly": labels == -1}, index=values.index
    )
    label, unit = WEATHER_PROPERTIES.get(property_name, (property_name, ""))
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=values.index, y=values, name=label, mode="lines"))
    anomalies = summary["anomaly"]
    figure.add_trace(
        go.Scatter(
            x=values.index[anomalies],
            y=values[anomalies],
            name="LOF anomaly",
            mode="markers",
            marker={"color": "#e76f51", "size": 8},
        )
    )
    figure.update_layout(
        title=f"{label} with Local Outlier Factor anomalies",
        xaxis_title="Date",
        yaxis_title=unit,
        template="plotly_white",
        hovermode="x unified",
    )
    return figure, summary


def plot_stl_interactive(
    filling: pd.Series, seasonal: int = 13, robust: bool = True
) -> go.Figure:
    """Return an interactive Plotly decomposition for weekly filling."""
    values = pd.to_numeric(filling, errors="coerce").dropna().sort_index()
    values = values.asfreq("W").interpolate(method="time")
    if seasonal < 3 or seasonal % 2 == 0:
        raise ValueError("seasonal must be an odd integer of at least 3.")
    if len(values) < 2 * 52:
        raise ValueError("STL requires at least two years of weekly observations.")
    result = STL(values, period=52, seasonal=seasonal, robust=robust).fit()
    figure = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        subplot_titles=("Observed", "Trend", "Seasonal", "Remainder"),
        vertical_spacing=0.07,
    )
    for row, series in enumerate(
        (values, result.trend, result.seasonal, result.resid), start=1
    ):
        figure.add_trace(
            go.Scatter(x=values.index, y=series, mode="lines", showlegend=False),
            row=row,
            col=1,
        )
    figure.update_layout(
        title="STL decomposition of weekly reservoir filling",
        height=800,
        template="plotly_white",
    )
    return figure


def plot_spectrogram_interactive(
    values: pd.Series, window_length: int = 52, overlap: float = 0.5
) -> go.Figure:
    """Return an interactive spectrogram for a weekly filling series."""
    from scipy.signal import spectrogram

    series = pd.to_numeric(values, errors="coerce").dropna().sort_index()
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
    dates = series.index[0] + pd.to_timedelta(times, unit="W")
    power_db = 10 * np.log10(np.maximum(power, np.finfo(float).tiny))
    figure = go.Figure(
        go.Heatmap(
            x=dates,
            y=frequencies,
            z=power_db,
            colorscale="Viridis",
            colorbar={"title": "Power (dB)"},
        )
    )
    figure.update_layout(
        title="Spectrogram of reservoir filling",
        xaxis_title="Date",
        yaxis_title="Frequency (cycles/week)",
        template="plotly_white",
    )
    return figure
