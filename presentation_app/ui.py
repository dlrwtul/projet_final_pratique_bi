"""Thème visuel, composants HTML partagés et navigation entre pages."""
import base64
from functools import lru_cache

import altair as alt
import pandas as pd
import streamlit as st

from settings import ASSETS_DIR

NAVY = "#0F1B2D"
OCEAN = "#0B6E99"
MUTED = "#536176"
BORDER = "#E4E8EE"
SURFACE = "#F6F8FA"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, .stApp, .stMarkdown p, h1, h2, h3, label, input, textarea, button p {{
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
}}
code, pre, .stCode code {{ font-family: 'IBM Plex Mono', ui-monospace, monospace !important; }}

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 2rem; max-width: 1180px; }}

[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
[data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    border-radius: 6px; font-weight: 500; min-height: 42px;
}}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {{
    background: {OCEAN}; border-color: {OCEAN}; color: #fff;
}}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {{
    background: #095B7F; border-color: #095B7F;
}}
/* Dossiers de la barre latérale : le dossier actif est surligné, les autres sont discrets. */
[data-testid="stSidebar"] .stButton > button > div {{ justify-content: flex-start; width: 100%; }}
[data-testid="stSidebar"] .stButton > button[kind="primary"] {{
    background: #E6ECF2; border-color: #E6ECF2; color: {NAVY}; font-weight: 600;
}}
[data-testid="stSidebar"] .stButton > button[kind="tertiary"] {{ color: {NAVY}; }}

.stTextInput input, .stTextArea textarea {{ border-radius: 6px; }}
[data-testid="stChatInput"] {{ border-radius: 8px; }}
[data-testid="stExpander"] details {{ border-radius: 8px; border-color: {BORDER}; }}

.wwi-eyebrow {{ font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: {OCEAN}; letter-spacing: .04em; }}
.wwi-muted {{ color: {MUTED}; }}
.wwi-kpi {{ border: 1px solid {BORDER}; border-radius: 8px; padding: 18px 20px; background: #fff; }}
.wwi-kpi span {{ display: block; font-size: 13px; color: {MUTED}; }}
.wwi-kpi strong {{ display: block; font-size: 28px; font-weight: 600; color: {NAVY}; margin-top: 4px; }}
.wwi-chip {{ display: inline-block; padding: 4px 10px; margin: 0 6px 6px 0; border-radius: 4px;
    background: #EEF3F8; font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: {NAVY}; }}
.wwi-badge {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #34445A; }}
.wwi-badge i {{ display: inline-block; width: 7px; height: 7px; border-radius: 4px; background: #1F8A5B; margin-right: 6px; }}
</style>
"""


def inject_css() -> None:
    st.html(CSS)


def go(page: str) -> None:
    st.session_state.page = page
    st.rerun()


@lru_cache
def png_uri(name: str) -> str:
    # st.html retire les <svg> : les icônes sont des PNG intégrés en data URI.
    data = (ASSETS_DIR / name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def emblem_uri() -> str:
    return png_uri("ucad_emblem.png")


def brand(size: int = 30, subtitle: bool = True, dark: bool = False) -> str:
    icon, text, sub_color = ("globe_light.png", "#FFFFFF", "#A9B6C6") if dark else ("globe.png", NAVY, MUTED)
    sub = (f'<span style="font-size:12px;color:{sub_color}">'
           "Wide World Importers · Analytics</span>") if subtitle else ""
    return (
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<img src="{png_uri(icon)}" alt="" width="{size}" height="{size}" style="flex:none">'
        f'<div style="display:flex;flex-direction:column;line-height:1.2">'
        f'<span style="font-size:18px;font-weight:600;color:{text}">WWI Insight</span>{sub}</div></div>'
    )


def ucad_block(size: int = 44, dark: bool = False, detail: str = "FST · Master 2 BI") -> str:
    title, sub = ("#FFFFFF", "#A9B6C6") if dark else (NAVY, MUTED)
    return (
        f'<div style="display:flex;align-items:center;gap:12px">'
        f'<img src="{emblem_uri()}" alt="Emblème de l\'Université Cheikh Anta Diop" '
        f'style="width:{size}px;height:{size}px">'
        f'<div style="display:flex;flex-direction:column;gap:2px">'
        f'<span style="font-size:14px;font-weight:600;color:{title}">Université Cheikh Anta Diop de Dakar</span>'
        f'<span style="font-size:13px;color:{sub}">{detail}</span></div></div>'
    )


def money(value) -> str:
    if value is None or pd.isna(value):
        return "—"
    if abs(value) >= 1e6:
        return f"{value / 1e6:,.1f} M$".replace(",", " ").replace(".", ",")
    return f"{value:,.0f} $".replace(",", " ")


def integer(value) -> str:
    return "—" if value is None or pd.isna(value) else f"{int(value):,}".replace(",", " ")


# --- Graphiques ---------------------------------------------------------------

def _as_dates(series: pd.Series) -> pd.Series | None:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    sample = series.dropna().astype(str).head(20)
    if not sample.empty and sample.str.match(r"^\d{4}-\d{2}-\d{2}").all():
        return pd.to_datetime(series, errors="coerce")
    return None


def chart(df: pd.DataFrame) -> alt.Chart | None:
    """Courbe si la première dimension est une date, sinon barres horizontales triées."""
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric or df.shape[1] < 2:
        return None
    y = numeric[0]
    dims = [c for c in df.columns if c != y]
    x = dims[0]
    dates = _as_dates(df[x])
    if dates is not None:
        data = df.assign(**{x: dates})
        return (
            alt.Chart(data)
            .mark_line(color=OCEAN, strokeWidth=2.5, point=alt.OverlayMarkDef(color=OCEAN, size=28))
            .encode(x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format="%m/%Y")), y=alt.Y(f"{y}:Q", title=y),
                    tooltip=[alt.Tooltip(f"{x}:T"), alt.Tooltip(f"{y}:Q", format=",.0f")])
            .properties(height=340)
        )
    data = df.head(30)
    return (
        alt.Chart(data)
        .mark_bar(color=OCEAN, cornerRadiusEnd=2)
        .encode(y=alt.Y(f"{x}:N", sort="-x", title=None),
                x=alt.X(f"{y}:Q", title=y),
                tooltip=[alt.Tooltip(f"{x}:N"), alt.Tooltip(f"{y}:Q", format=",.0f")])
        .properties(height=max(160, 28 * len(data)))
    )
