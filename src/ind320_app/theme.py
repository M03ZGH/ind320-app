"""Shared colours and the Plotly template used by the whole app.

The same palette is used by the Streamlit theme (.streamlit/config.toml), the
CSS in ``ui.py`` and every Plotly figure, so the app looks consistent.
"""

import plotly.graph_objects as go
import plotly.io as pio

# Brand palette: deep blue (sidebar), teal (primary) and warm accents.
NAVY = "#102a43"
TEAL = "#1f7a9c"
SKY = "#4ea8de"
GREEN = "#2a9d8f"
SAND = "#e9c46a"
CORAL = "#e76f51"
PURPLE = "#6a4c93"

# Order of the colours used when a chart has several series.
COLORWAY = [TEAL, CORAL, GREEN, SAND, PURPLE, SKY]

# White plot background with light grid lines; registered under the name "ind320"
# so figures can simply use ``template="ind320"``.
pio.templates["ind320"] = go.layout.Template(
    layout={
        "colorway": COLORWAY,
        "font": {"family": "Source Sans Pro, sans-serif", "color": NAVY},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "#ffffff",
        "title": {"font": {"size": 18, "color": NAVY}},
        "xaxis": {"gridcolor": "#e3ebf1", "linecolor": "#b8c9d6", "zeroline": False},
        "yaxis": {"gridcolor": "#e3ebf1", "linecolor": "#b8c9d6", "zeroline": False},
        "legend": {"bgcolor": "rgba(255,255,255,0.6)"},
        "margin": {"l": 60, "r": 20, "t": 60, "b": 50},
    }
)
