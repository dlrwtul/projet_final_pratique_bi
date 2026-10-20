import html
import time
from datetime import datetime
from io import StringIO

import pandas as pd
import streamlit as st

import session
import ui
import users_db
import warehouse

ENGINE_LABELS = {"exemple": "SQL de référence", "cortex": "généré par Cortex",
                 "ollama": "généré par Ollama", "manuel": "SQL écrit à la main"}
GROUP_ICONS = {"Ventes": ":material/trending_up:", "Produits": ":material/inventory_2:",
               "Rentabilité": ":material/savings:"}


def _initials(name: str) -> str:
    return "".join(p[0] for p in name.split()[:2]).upper() or "?"


# --- Dossiers (boîtes de dialogue) --------------------------------------------

@st.dialog("Nouveau dossier")
def _new_folder(user: dict) -> None:
    with st.form("new_folder_form", border=False):
        name = st.text_input("Nom du dossier", placeholder="Ex. : Ventes 2015", max_chars=60)
        if st.form_submit_button("Créer le dossier", type="primary", width="stretch") and name.strip():
            st.session_state.folder_id = users_db.create_folder(user["id"], name)
            st.rerun()


@st.dialog("Renommer le dossier")
def _rename_folder(user: dict, folder: dict) -> None:
    with st.form("rename_folder_form", border=False):
        name = st.text_input("Nouveau nom", value=folder["name"], max_chars=60)
        if st.form_submit_button("Enregistrer", type="primary", width="stretch") and name.strip():
            users_db.rename_folder(user["id"], folder["id"], name)
            st.rerun()


@st.dialog("Supprimer le dossier")
def _delete_folder(user: dict, folder: dict) -> None:
    st.write(f"Le dossier **{folder['name']}** et ses {folder['n']} analyse(s) seront supprimés.")
    cancel, confirm = st.columns(2)
    if cancel.button("Annuler", width="stretch"):
        st.rerun()
    if confirm.button("Supprimer", type="primary", width="stretch", icon=":material/delete:"):
        users_db.delete_folder(user["id"], folder["id"])
        st.session_state.pop("folder_id", None)
        st.rerun()


# --- Barre latérale et en-tête ------------------------------------------------

def _sidebar(user: dict, folders: list[dict], active: dict) -> None:
    with st.sidebar:
        st.html(f'<div style="padding:4px 2px 10px">{ui.brand(size=28, subtitle=False)}</div>')
        if st.button("Nouveau dossier", key="new_folder_btn", icon=":material/create_new_folder:", width="stretch"):
            _new_folder(user)

        st.html(f'<div style="font-size:12px;font-weight:600;letter-spacing:.06em;color:{ui.MUTED};'
                'margin:14px 0 2px">MES DOSSIERS</div>')
        for f in folders:
            is_active = f["id"] == active["id"]
            if st.button(f"{f['name']}  ·  {f['n']}", key=f"folder_{f['id']}",
                         icon=":material/folder_open:" if is_active else ":material/folder:",
                         type="primary" if is_active else "tertiary", width="stretch"):
                st.session_state.folder_id = f["id"]
                st.rerun()

        st.divider()
        if st.button("Accueil", icon=":material/home:", type="tertiary", width="stretch"):
            session.go("landing")
        if st.button("À propos du projet", icon=":material/info:", type="tertiary", width="stretch"):
            session.go("about")
        st.divider()
        st.html(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:2px 0">
              <span style="width:36px;height:36px;border-radius:18px;background:{ui.NAVY};color:#fff;font-size:13px;
                           font-weight:600;display:inline-flex;align-items:center;justify-content:center;flex:none">
                {html.escape(_initials(user['full_name']))}</span>
              <span style="display:flex;flex-direction:column;min-width:0">
                <span style="font-size:14px;font-weight:600;color:{ui.NAVY}">{html.escape(user['full_name'])}</span>
                <span style="font-size:12px;color:{ui.MUTED};overflow:hidden;text-overflow:ellipsis">
                  {html.escape(user['email'])}</span>
              </span>
            </div>""")
        if st.button("Se déconnecter", icon=":material/logout:", type="tertiary", width="stretch"):
            session.sign_out()


def _header(user: dict, active: dict, folders: list[dict]) -> None:
    title, badge, options = st.columns([4.6, 3.2, 1.7], vertical_alignment="center")
    title.html(f'<div style="font-size:24px;font-weight:600;color:{ui.NAVY}">{html.escape(active["name"])}</div>'
               f'<div class="wwi-muted" style="font-size:13px">{active["n"]} analyse(s)</div>')
    badge.html(f'<div class="wwi-badge" style="text-align:right"><i></i>{warehouse.backend_label()}</div>')
    with options.popover("Gérer", icon=":material/tune:", width="stretch"):
        if st.button("Renommer", icon=":material/edit:", type="tertiary", width="stretch"):
            _rename_folder(user, active)
        if len(folders) > 1 and st.button("Supprimer", icon=":material/delete:", type="tertiary", width="stretch"):
            _delete_folder(user, active)
    st.divider()


# --- Analyses -----------------------------------------------------------------

def _load(result_json: str | None) -> pd.DataFrame:
    if not result_json:
        return pd.DataFrame()
    df = pd.read_json(StringIO(result_json), orient="split")
    for col in df.columns:
        is_text = pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])
        dates = ui._as_dates(df[col]) if is_text else None
        if dates is not None:
            df[col] = dates
    return df


def _insight(df: pd.DataFrame) -> str:
    if df.empty:
        return "Aucune ligne ne correspond à cette question."
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if len(df) == 1 and numeric:
        return f"Résultat : <strong>{ui.number(df.iloc[0][numeric[-1]])}</strong>"
    # Libellé = première colonne non mesurée (une année numérique compte comme libellé).
    labels = [c for c in df.columns if c not in numeric] or numeric[:-1]
    text = f"<strong>{len(df)}</strong> lignes"
    if numeric and labels:
        first = df.iloc[0]
        label = first[labels[0]]
        label = label.strftime("%m/%Y") if isinstance(label, pd.Timestamp) else html.escape(str(label))
        text += f" · première : <strong>{label}</strong> ({ui.number(first[numeric[-1]])})"
    return text


def _analysis(user: dict, a: dict) -> None:
    st.html(f'<div class="wwi-question"><div>{html.escape(a["question"])}</div></div>')
    df = _load(a["result_json"])
    figure = ui.chart(df) if not df.empty else None
    with st.container(key=f"answer_{a['id']}"):
        st.html(f'<div class="wwi-insight">{_insight(df)}</div>')
        names = (["Graphique"] if figure is not None else []) + (["Tableau"] if not df.empty else []) + ["SQL"]
        for name, tab in zip(names, st.tabs(names)):
            with tab:
                if name == "Graphique":
                    st.altair_chart(figure, width="stretch")
                elif name == "Tableau":
                    numbers = {c: st.column_config.NumberColumn(format="localized")
                               for c in df.columns if pd.api.types.is_float_dtype(df[c])}
                    dates = {c: st.column_config.DateColumn(format="DD/MM/YYYY")
                             for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])}
                    st.dataframe(df, hide_index=True, width="stretch", column_config=numbers | dates)
                else:
                    st.code(a["sql"], language="sql")
        when = datetime.fromisoformat(a["created_at"]).strftime("%d/%m/%Y %H:%M")
        details = [f"{when} UTC"]
        if a.get("engine"):
            details.append(ENGINE_LABELS.get(a["engine"], a["engine"]))
        if a.get("duration_ms") is not None:
            details.append(f"{a['duration_ms'] / 1000:.1f} s".replace(".", ","))
        meta, csv, delete = st.columns([5, 1.4, 1.4], vertical_alignment="center")
        meta.html(f'<span class="wwi-muted" style="font-size:12px">{" · ".join(details)}</span>')
        csv.download_button("CSV", df.to_csv(index=False).encode(), f"analyse_{a['id']}.csv", "text/csv",
                            icon=":material/download:", key=f"csv_{a['id']}", type="tertiary", width="stretch")
        if delete.button("Supprimer", key=f"del_{a['id']}", icon=":material/delete:", type="tertiary", width="stretch"):
            users_db.delete_analysis(user["id"], a["id"])
            st.rerun()


def _ask(user: dict, folder_id: int, question: str, sql: str | None = None) -> None:
    # La question s'affiche tout de suite pendant que le SQL est généré puis exécuté.
    st.html(f'<div class="wwi-question"><div>{html.escape(question)}</div></div>')
    start = time.perf_counter()
    engine = "manuel" if sql else None
    try:
        with st.spinner("Génération du SQL et exécution sur la couche Gold…"):
            if not sql:
                sql, engine = warehouse.generate_sql(question)
            sql = warehouse.clean_sql(sql)
            df = warehouse.run_sql(sql)
    except warehouse.QueryError as exc:
        st.session_state.last_error = (question, str(exc), sql)
        st.rerun()
    st.session_state.pop("last_error", None)
    users_db.add_analysis(user["id"], folder_id, question, sql,
                          df.to_json(orient="split", date_format="iso", index=False), len(df),
                          engine, int((time.perf_counter() - start) * 1000))
    st.rerun()


def _queue_suggestion() -> None:
    if question := st.session_state.get("suggestions"):
        st.session_state.pending_question = question
        st.session_state.suggestions = None


def _empty_state(user: dict, folder_id: int) -> None:
    st.html(f'<div style="text-align:center;padding:28px 0 18px">'
            f'<div style="font-size:30px;font-weight:600;color:{ui.NAVY}">Que voulez-vous savoir ?</div>'
            f'<div class="wwi-muted" style="margin-top:6px">Choisissez une question ou écrivez la vôtre en bas.</div>'
            "</div>")
    with st.container(key="example_grid"):
        for group, questions in warehouse.EXAMPLE_GROUPS.items():
            st.html(f'<div style="font-size:12px;font-weight:600;letter-spacing:.06em;color:{ui.MUTED};'
                    f'margin:10px 0 0">{group.upper()}</div>')
            cols = st.columns(2)
            for i, question in enumerate(questions):
                if cols[i % 2].button(question, key=f"ex_{group}_{i}", icon=GROUP_ICONS[group], width="stretch"):
                    _ask(user, folder_id, question)


def _error_block(user: dict, folder_id: int) -> None:
    question, message, failed_sql = st.session_state.last_error
    st.html(f'<div class="wwi-question"><div>{html.escape(question)}</div></div>')
    with st.container(key="answer_error"):
        st.warning(message, icon=":material/warning:")
        with st.form("manual_sql", border=False):
            sql = st.text_area("Écrire ou corriger le SQL", value=failed_sql or "select ", height=140)
            if st.form_submit_button("Exécuter", type="primary", icon=":material/play_arrow:"):
                _ask(user, folder_id, question, sql)


def render() -> None:
    user = session.user()
    folders = users_db.list_folders(user["id"])
    if not folders:
        users_db.create_folder(user["id"], "Mes analyses")
        folders = users_db.list_folders(user["id"])
    active = next((f for f in folders if f["id"] == st.session_state.get("folder_id")), folders[0])
    st.session_state.folder_id = active["id"]

    _sidebar(user, folders, active)
    _header(user, active, folders)

    if pending := st.session_state.pop("pending_question", None):
        _ask(user, active["id"], pending)

    analyses = users_db.list_analyses(user["id"], active["id"])
    if not analyses and "last_error" not in st.session_state:
        _empty_state(user, active["id"])
    for a in analyses:
        _analysis(user, a)
    if "last_error" in st.session_state:
        _error_block(user, active["id"])

    if analyses:
        asked = {a["question"] for a in analyses}
        ideas = [q for q in warehouse.EXAMPLES if q not in asked][:4]
        if ideas:
            st.html('<div style="height:8px"></div>')
            st.pills("Suggestions", ideas, key="suggestions", on_change=_queue_suggestion,
                     label_visibility="collapsed")
    if question := st.chat_input("Posez une question sur les données Wide World Importers…"):
        _ask(user, active["id"], question)
