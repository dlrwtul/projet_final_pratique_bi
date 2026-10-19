from io import StringIO

import pandas as pd
import streamlit as st

import ui
import users_db
import warehouse


def _initials(name: str) -> str:
    return "".join(p[0] for p in name.split()[:2]).upper() or "?"


def _sidebar(user: dict, folders: list[dict], active: dict) -> None:
    with st.sidebar:
        st.html(ui.brand(size=26, subtitle=False))

        with st.popover("Nouveau dossier", icon=":material/create_new_folder:", width="stretch"):
            with st.form("new_folder", border=False, clear_on_submit=True):
                name = st.text_input("Nom du dossier", placeholder="Ex. : Ventes 2015")
                if st.form_submit_button("Créer", type="primary") and name.strip():
                    st.session_state.folder_id = users_db.create_folder(user["id"], name)
                    st.rerun()

        st.caption("DOSSIERS")
        for f in folders:
            is_active = f["id"] == active["id"]
            label = f"{f['name']}  ·  {f['n']}"
            if st.button(label, key=f"folder_{f['id']}", icon=":material/folder:",
                         type="primary" if is_active else "tertiary", width="stretch"):
                st.session_state.folder_id = f["id"]
                st.rerun()

        st.divider()
        if st.button("À propos du projet", icon=":material/info:", type="tertiary", width="stretch"):
            ui.go("about")
        st.html(f"""
            <div style="display:flex;align-items:center;gap:10px;padding:4px 0">
              <span style="width:34px;height:34px;border-radius:17px;background:{ui.NAVY};color:#fff;font-size:13px;
                           font-weight:600;display:inline-flex;align-items:center;justify-content:center">
                {_initials(user['full_name'])}</span>
              <span style="display:flex;flex-direction:column;min-width:0">
                <span style="font-size:14px;font-weight:500;color:{ui.NAVY}">{user['full_name']}</span>
                <span style="font-size:12px;color:{ui.MUTED}">{user['email']}</span>
              </span>
            </div>""")
        if st.button("Se déconnecter", icon=":material/logout:", type="tertiary", width="stretch"):
            st.session_state.clear()
            ui.go("landing")


def _folder_header(user: dict, active: dict, folders: list[dict]) -> None:
    title, badge, manage = st.columns([4, 3, 1], vertical_alignment="center")
    title.html(f'<span class="wwi-muted" style="font-size:14px">Dossiers /</span> '
               f'<span style="font-size:20px;font-weight:600;color:{ui.NAVY}">{active["name"]}</span>')
    badge.html(f'<div class="wwi-badge" style="text-align:right"><i></i>{warehouse.backend_label()}</div>')
    with manage.popover("Gérer", icon=":material/more_horiz:", width="stretch"):
        with st.form("rename_folder", border=False):
            new_name = st.text_input("Renommer", value=active["name"])
            if st.form_submit_button("Enregistrer") and new_name.strip():
                users_db.rename_folder(user["id"], active["id"], new_name)
                st.rerun()
        if len(folders) > 1 and st.button("Supprimer le dossier", icon=":material/delete:"):
            users_db.delete_folder(user["id"], active["id"])
            st.session_state.pop("folder_id", None)
            st.rerun()
    st.divider()


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


def _summary(df: pd.DataFrame) -> str:
    if df.empty:
        return "Aucune ligne ne correspond à cette question."
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    text = f"{len(df)} ligne{'s' if len(df) > 1 else ''} renvoyée{'s' if len(df) > 1 else ''}."
    labels = [c for c in df.columns if c not in numeric]
    if numeric and labels and len(df) > 1:
        first = df.iloc[0]
        label = first[labels[0]]
        if isinstance(label, pd.Timestamp):
            label = label.strftime("%d/%m/%Y")
        text += f" Première ligne : **{label}** ({first[numeric[0]]:,.0f}).".replace(",", " ")
    return text


def _analysis(user: dict, a: dict) -> None:
    with st.chat_message("user", avatar=":material/person:"):
        st.markdown(f"**{a['question']}**")
    with st.chat_message("assistant", avatar=":material/public:"):
        df = _load(a["result_json"])
        st.markdown(_summary(df))
        with st.expander("Requête SQL générée", icon=":material/code:"):
            st.code(a["sql"], language="sql")
        if not df.empty:
            table_tab, chart_tab = st.tabs(["Tableau", "Graphique"])
            with table_tab:
                numbers = {c: st.column_config.NumberColumn(format="localized")
                           for c in df.columns if pd.api.types.is_float_dtype(df[c])}
                dates = {c: st.column_config.DateColumn(format="DD/MM/YYYY")
                         for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])}
                st.dataframe(df, hide_index=True, width="stretch", column_config=numbers | dates)
            with chart_tab:
                figure = ui.chart(df)
                if figure is None:
                    st.caption("Pas de graphique pour ce résultat (aucune colonne numérique).")
                else:
                    st.altair_chart(figure, width="stretch")
        c1, c2, _ = st.columns([1.2, 1, 4])
        c1.download_button("Exporter CSV", df.to_csv(index=False).encode(), f"analyse_{a['id']}.csv",
                           "text/csv", icon=":material/download:", key=f"csv_{a['id']}")
        if c2.button("Supprimer", key=f"del_{a['id']}", icon=":material/delete:", type="tertiary"):
            users_db.delete_analysis(user["id"], a["id"])
            st.rerun()


def _ask(user: dict, folder_id: int, question: str, sql: str | None = None) -> None:
    try:
        with st.spinner("Génération et exécution de la requête…"):
            sql = warehouse.clean_sql(sql or warehouse.generate_sql(question))
            df = warehouse.run_sql(sql)
    except warehouse.QueryError as exc:
        st.session_state.last_error = (question, str(exc), sql)
        st.rerun()
    st.session_state.pop("last_error", None)
    users_db.add_analysis(user["id"], folder_id, question, sql,
                          df.to_json(orient="split", date_format="iso", index=False), len(df))
    st.rerun()


def _empty_state(user: dict, folder_id: int) -> None:
    st.html(f'<div style="padding:32px 0 12px"><h2 style="margin:0;font-size:24px;font-weight:600;color:{ui.NAVY}">'
            "Que voulez-vous savoir ?</h2><p class='wwi-muted' style='margin:6px 0 0'>"
            "Posez une question en bas de page, ou commencez par un exemple.</p></div>")
    for i, question in enumerate(warehouse.EXAMPLES):
        if st.button(question, key=f"example_{i}", icon=":material/arrow_forward:"):
            _ask(user, folder_id, question)


def render() -> None:
    user = st.session_state.user
    folders = users_db.list_folders(user["id"])
    if not folders:
        users_db.create_folder(user["id"], "Mes analyses")
        folders = users_db.list_folders(user["id"])
    active = next((f for f in folders if f["id"] == st.session_state.get("folder_id")), folders[0])
    st.session_state.folder_id = active["id"]

    _sidebar(user, folders, active)
    _folder_header(user, active, folders)

    analyses = users_db.list_analyses(user["id"], active["id"])
    if not analyses:
        _empty_state(user, active["id"])
    for a in analyses:
        _analysis(user, a)

    error = st.session_state.get("last_error")
    if error:
        question, message, failed_sql = error
        with st.chat_message("assistant", avatar=":material/public:"):
            st.markdown(f"**{question}**")
            st.warning(message)
            with st.form("manual_sql", border=False):
                sql = st.text_area("Écrire ou corriger le SQL", value=failed_sql or "select ", height=140)
                if st.form_submit_button("Exécuter", type="primary"):
                    _ask(user, active["id"], question, sql)

    if not warehouse.IS_SNOWFLAKE:
        st.caption("Mode local DuckDB : seules les questions d'exemple sont traduites automatiquement. "
                   "Configurez Snowflake (SF_ACCOUNT…) pour activer Cortex AI.")
    question = st.chat_input("Posez une question sur les données Wide World Importers…")
    if question:
        _ask(user, active["id"], question)
