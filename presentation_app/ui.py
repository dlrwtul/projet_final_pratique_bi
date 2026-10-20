"""Thème visuel, composants HTML partagés et graphiques."""
import base64
from functools import lru_cache

import altair as alt
import pandas as pd
import streamlit as st

from settings import ASSETS_DIR

NAVY = "#0F1B2D"
INK = "#22324A"
OCEAN = "#0B6E99"
OCEAN_DARK = "#095B7F"
SKY = "#EAF4F9"
MUTED = "#536176"
BORDER = "#E4E8EE"
SURFACE = "#F6F8FA"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, .stApp, .stMarkdown p, h1, h2, h3, label, input, textarea, button p {{
    font-family: 'IBM Plex Sans', system-ui, sans-serif;
}}
code, pre, .stCode code {{ font-family: 'IBM Plex Mono', ui-monospace, monospace !important; }}

/* Habillage Streamlit retiré */
/* (la barre d'outils reste : elle contient le bouton qui rouvre la barre latérale) */
#MainMenu, footer, [data-testid="stMainMenu"], [data-testid="stAppDeployButton"], [data-testid="stToolbarActions"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent; }}

.block-container {{ padding-top: 1.25rem; padding-bottom: 3rem; max-width: 1180px; }}
hr {{ margin: .75rem 0 !important; border-color: {BORDER} !important; }}

/* Boutons */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, .stPopover button {{
    border-radius: 8px; font-weight: 500; min-height: 42px; transition: all .15s ease;
}}
button[data-testid="stBaseButton-primary"], button[data-testid="stBaseButton-primaryFormSubmit"] {{
    background: {OCEAN}; border-color: {OCEAN}; color: #fff;
}}
button[data-testid="stBaseButton-primary"]:hover, button[data-testid="stBaseButton-primaryFormSubmit"]:hover {{
    background: {OCEAN_DARK}; border-color: {OCEAN_DARK}; color: #fff;
}}
button[data-testid="stBaseButton-secondary"] {{ border-color: #C9D1DC; color: {NAVY}; background: #fff; }}
button[data-testid="stBaseButton-secondary"]:hover {{ border-color: {OCEAN}; color: {OCEAN}; }}
button[data-testid="stBaseButton-tertiary"] {{ color: {INK}; }}
button[data-testid="stBaseButton-tertiary"]:hover {{ color: {OCEAN}; }}

/* Champs */
.stTextInput input, .stTextArea textarea {{ border-radius: 8px; }}
[data-baseweb="input"], [data-baseweb="textarea"] {{ border-radius: 8px !important; }}

/* Onglets */
[data-baseweb="tab-list"] {{ gap: 4px; }}
[data-baseweb="tab"] {{ font-weight: 500; }}

/* Pastilles de suggestions */
[data-testid="stButtonGroup"] button {{
    border-radius: 999px !important; border: 1px solid #D5DCE5 !important; background: #fff !important;
    color: {INK} !important; font-size: 14px !important; padding: 6px 14px !important;
}}
[data-testid="stButtonGroup"] button:hover {{ border-color: {OCEAN} !important; color: {OCEAN} !important; }}
[data-testid="stButtonGroup"] [role="radiogroup"] {{ flex-wrap: wrap; overflow: visible; gap: 8px; }}
.st-key-hero_pills_box [role="radiogroup"] {{ justify-content: center; }}
/* Sélecteur Connexion / Inscription : l'option choisie est mise en évidence */
.st-key-auth_card [data-testid="stButtonGroup"] button {{ border-radius: 10px !important; flex: 1; }}
.st-key-auth_card [data-testid="stButtonGroup"] button[aria-checked="true"] {{
    background: {SKY} !important; border-color: {OCEAN} !important; color: {OCEAN} !important; font-weight: 600 !important;
}}

/* Barre latérale */
[data-testid="stSidebar"] {{ background: {SURFACE}; border-right: 1px solid {BORDER}; }}
[data-testid="stSidebar"] .block-container {{ padding-top: 1rem; }}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: .3rem; }}
[data-testid="stSidebar"] .stButton > button {{ min-height: 38px; }}
[data-testid="stSidebar"] .stButton > button > div {{ justify-content: flex-start; width: 100%; }}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {{
    background: #E1EAF2; border-color: #E1EAF2; color: {NAVY}; font-weight: 600;
}}
[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {{ background: #D6E3EE; color: {NAVY}; }}
.st-key-new_folder_btn button {{ border-style: dashed !important; color: {OCEAN} !important; border-color: #9CC3D8 !important; }}

/* Accueil : barre de question */
.st-key-hero_search {{
    background: #fff; border: 1px solid #D5DCE5; border-radius: 16px; padding: 10px 10px 10px 18px;
    box-shadow: 0 12px 36px rgba(15,27,45,.08);
}}
.st-key-hero_search [data-baseweb="input"] {{ border: 0 !important; background: transparent !important; }}
.st-key-hero_search input {{ font-size: 17px !important; background: transparent !important; }}
.st-key-hero_search [data-testid="stForm"] {{ border: 0; padding: 0; }}

/* Carte de connexion */
.st-key-auth_card {{
    background: #fff; border: 1px solid {BORDER}; border-radius: 16px; padding: 28px 28px 18px;
    box-shadow: 0 16px 48px rgba(15,27,45,.08);
}}
.st-key-auth_card [data-testid="stForm"] {{ border: 0; padding: 0; }}

/* Cartes d'exemples de l'espace d'analyse */
.st-key-example_grid .stButton > button {{
    min-height: 74px; justify-content: flex-start; text-align: left; background: #fff;
    border: 1px solid {BORDER}; border-radius: 12px; color: {INK}; padding: 12px 16px;
}}
.st-key-example_grid .stButton > button > div {{ justify-content: flex-start; width: 100%; }}
.st-key-example_grid .stButton > button:hover {{
    border-color: {OCEAN}; color: {NAVY}; box-shadow: 0 6px 18px rgba(11,110,153,.12); transform: translateY(-1px);
}}

/* Réponses */
[class*="st-key-answer_"] {{
    background: #fff; border: 1px solid {BORDER}; border-radius: 14px; padding: 18px 20px 8px;
    box-shadow: 0 2px 8px rgba(15,27,45,.04);
}}
[data-testid="stChatInput"] {{ border-radius: 14px; }}

/* Composants HTML maison */
.wwi-eyebrow {{ display: inline-block; font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: {OCEAN};
    letter-spacing: .06em; background: {SKY}; border-radius: 999px; padding: 6px 12px; }}
.wwi-muted {{ color: {MUTED}; }}
.wwi-kpi {{ border: 1px solid {BORDER}; border-radius: 12px; padding: 18px 20px; background: #fff; min-height: 106px;
    box-sizing: border-box; }}
.wwi-kpi span {{ display: block; font-size: 13px; color: {MUTED}; }}
.wwi-kpi strong {{ display: block; font-size: 28px; font-weight: 600; color: {NAVY}; margin-top: 4px; }}
.wwi-step {{ border-radius: 12px; padding: 20px; background: {SURFACE}; min-height: 150px; box-sizing: border-box; }}
.wwi-step b {{ display: inline-flex; width: 28px; height: 28px; border-radius: 14px; background: {OCEAN}; color: #fff;
    align-items: center; justify-content: center; font-size: 14px; margin-bottom: 10px; }}
.wwi-step h4 {{ margin: 0 0 4px; font-size: 16px; color: {NAVY}; }}
.wwi-step p {{ margin: 0; font-size: 14px; color: {MUTED}; line-height: 1.5; }}
.wwi-badge {{ font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #34445A; white-space: nowrap; }}
.wwi-badge i {{ display: inline-block; width: 7px; height: 7px; border-radius: 4px; background: #1F8A5B; margin-right: 6px; }}
.wwi-question {{ display: flex; justify-content: flex-end; margin: 18px 0 10px; }}
.wwi-question div {{ background: {NAVY}; color: #fff; border-radius: 16px 16px 4px 16px; padding: 10px 16px;
    max-width: 80%; font-size: 15px; line-height: 1.5; }}
.wwi-insight {{ font-size: 15px; color: {INK}; margin-bottom: 4px; }}
.wwi-insight strong {{ color: {NAVY}; }}
</style>
"""


def inject_css(background: str = "#FFFFFF", max_width: int = 1180) -> None:
    st.html(CSS + f"<style>.stApp{{background:{background}}}.block-container,"
                  f'[data-testid="stBottomBlockContainer"]{{max-width:{max_width}px;margin:0 auto}}</style>')


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


def number(value) -> str:
    if isinstance(value, (int, float)) and not pd.isna(value):
        return f"{value:,.0f}".replace(",", " ") if abs(value) >= 100 else f"{value:,.2f}".replace(".", ",")
    return str(value)


# --- Graphiques ---------------------------------------------------------------

def _as_dates(series: pd.Series) -> pd.Series | None:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    sample = series.dropna().astype(str).head(20)
    if not sample.empty and sample.str.match(r"^\d{4}-\d{2}-\d{2}").all():
        return pd.to_datetime(series, errors="coerce")
    return None


def chart(df: pd.DataFrame, height: int = 340) -> alt.Chart | None:
    """Courbe pour une date, barres pour une année ou une catégorie (mesure = dernière colonne numérique)."""
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not numeric or df.shape[1] < 2:
        return None
    y = numeric[-1]
    x = next(c for c in df.columns if c != y)
    # Comptes entiers : pas de graduations 0,1 / 0,2… sur l'axe des valeurs.
    step = 1 if pd.api.types.is_integer_dtype(df[y]) or (df[y].dropna() % 1 == 0).all() else None
    value_axis = alt.Axis(format="~s", tickMinStep=step) if step else alt.Axis(format="~s")
    tooltip_y = alt.Tooltip(f"{y}:Q", format=",.0f")
    dates = _as_dates(df[x])
    if dates is not None:
        data = df.assign(**{x: dates})
        base = alt.Chart(data).encode(x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format="%m/%Y", grid=False)))
        y_axis = alt.Y(f"{y}:Q", title=None, axis=alt.Axis(format="~s"))
        area = base.mark_area(color=OCEAN, opacity=.08).encode(y=y_axis)
        line = base.mark_line(color=OCEAN, strokeWidth=2.5).encode(
            y=y_axis, tooltip=[alt.Tooltip(f"{x}:T", format="%m/%Y"), tooltip_y])
        return (area + line).properties(height=height).configure_view(strokeWidth=0)
    if pd.api.types.is_numeric_dtype(df[x]):  # année, trimestre… : axe ordinal
        return (
            alt.Chart(df).mark_bar(color=OCEAN, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(x=alt.X(f"{x}:O", title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y(f"{y}:Q", title=None, axis=value_axis),
                    tooltip=[alt.Tooltip(f"{x}:O"), tooltip_y])
            .properties(height=height).configure_view(strokeWidth=0)
        )
    data = df.head(30)
    return (
        alt.Chart(data).mark_bar(color=OCEAN, cornerRadiusEnd=4)
        .encode(y=alt.Y(f"{x}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=260)),
                x=alt.X(f"{y}:Q", title=None, axis=value_axis), tooltip=[alt.Tooltip(f"{x}:N"), tooltip_y])
        .properties(height=max(160, 30 * len(data))).configure_view(strokeWidth=0)
    )
