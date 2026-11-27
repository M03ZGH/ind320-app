"""Shared Streamlit presentation helpers.

``render_sidebar`` is called ONCE from ``main.py``. Streamlit runs ``main.py`` on
every page change before the selected page, so calling it again inside the pages
would draw the sidebar content twice.
"""

import base64
from functools import lru_cache
from pathlib import Path

import streamlit as st

from ind320_app import theme  # noqa: F401  (registers the "ind320" Plotly template)

GITHUB_URL = "https://github.com/M03ZGH/ind320-app"
ASSETS = Path(__file__).resolve().parents[2] / "assets"
LOGOS = ("nmbu.png", "indok_nmbu.png")

_CSS = """
<style>
/* ---- Sidebar: dark blue gradient with light text ---- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #102a43 0%, #163d5c 100%);
}
[data-testid="stSidebar"] * { color: #f5f7fa; }
[data-testid="stSidebarNav"] a[aria-current="page"],
[data-testid="stSidebarNav"] a[data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(78, 168, 222, 0.28);
    border-radius: 0.5rem;
}
.project-brand { margin: 0.25rem 0 1rem; line-height: 1.25; }
.project-brand strong { font-size: 1.15rem; }
.project-brand small { color: #b8d5e5; font-size: 0.8rem; }
.sidebar-link {
    display: inline-block;
    margin-top: 0.4rem;
    padding: 0.35rem 0.8rem;
    border: 1px solid rgba(255, 255, 255, 0.45);
    border-radius: 0.5rem;
    color: #9de2ff !important;
    text-decoration: none;
    font-size: 0.9rem;
}
.sidebar-link:hover { background: rgba(255, 255, 255, 0.12); }
/* White card so the dark-text logos stay readable on the dark sidebar */
.logo-card {
    background: #ffffff;
    border-radius: 0.7rem;
    padding: 0.4rem 0.8rem;
    margin-top: 1rem;
}
.logo-card img { display: block; width: 100%; margin: 0.5rem 0; }

/* ---- Main area: headings, metric cards, tabs ---- */
h1 { color: #102a43; border-bottom: 3px solid #1f7a9c; padding-bottom: 0.3rem; }
h2, h3 { color: #163d5c; }
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #d3e2ec;
    border-left: 5px solid #1f7a9c;
    border-radius: 0.6rem;
    padding: 0.7rem 1rem;
    box-shadow: 0 1px 3px rgba(16, 42, 67, 0.08);
}
button[data-baseweb="tab"][aria-selected="true"] { color: #1f7a9c; font-weight: 600; }
.block-container { padding-top: 2rem; max-width: 1250px; }
</style>
"""


@lru_cache(maxsize=1)
def _logo_html() -> str:
    """Embed the logos as base64 so they can sit inside the styled HTML card."""
    images = []
    for name in LOGOS:
        path = ASSETS / name
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode()
            images.append(f'<img src="data:image/png;base64,{data}" alt="{name}">')
    return f'<div class="logo-card">{"".join(images)}</div>' if images else ""


def render_sidebar() -> None:
    """Inject the app CSS and render the project brand and GitHub link."""
    st.markdown(_CSS, unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="project-brand"><strong>💧 Data to Decision</strong><br>'
        "<small>IND320 · NMBU</small><br>"
        f'<a class="sidebar-link" href="{GITHUB_URL}" target="_blank">'
        "GitHub repository ↗</a></div>" + _logo_html(),
        unsafe_allow_html=True,
    )
