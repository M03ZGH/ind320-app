"""Shared Streamlit presentation helpers."""

import streamlit as st

def render_sidebar() -> None:
    """Render consistent project information beside Streamlit navigation."""
    st.sidebar.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #102a43 0%, #163d5c 100%);
        }
        [data-testid="stSidebar"] * {
            color: #f5f7fa;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] a {
            color: #9de2ff;
        }
        .project-brand {
            align-items: center;
            display: flex;
            gap: 0.65rem;
            line-height: 1.25;
            margin: 0.25rem 0 0.8rem;
        }
        .brand-mark {
            font-size: 1.55rem;
        }
        .project-brand small {
            color: #b8d5e5;
            font-size: 0.78rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<span><strong>Data to Decision</strong><br>"
        "<small>IND320 · NMBU</small></span></div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "[GitHub repository](https://github.com/M03ZGH/ind320-app)"
    )
