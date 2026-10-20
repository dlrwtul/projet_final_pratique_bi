"""Stockage SQLite des utilisateurs, de leurs dossiers d'analyse et de leurs analyses."""
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import bcrypt

from settings import USERS_DB_PATH

SCHEMA = """
create table if not exists users (
    id            integer primary key autoincrement,
    full_name     text not null,
    email         text not null unique,
    password_hash text not null,
    created_at    text not null
);
create table if not exists folders (
    id         integer primary key autoincrement,
    user_id    integer not null references users(id) on delete cascade,
    name       text not null,
    created_at text not null
);
create table if not exists sessions (
    token      text primary key,
    user_id    integer not null references users(id) on delete cascade,
    expires_at text not null
);
create table if not exists analyses (
    id          integer primary key autoincrement,
    folder_id   integer not null references folders(id) on delete cascade,
    question    text not null,
    sql         text not null,
    result_json text,
    row_count   integer,
    created_at  text not null
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def _connect():
    USERS_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(USERS_DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("pragma foreign_keys = on")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init() -> None:
    with _connect() as con:
        con.executescript(SCHEMA)


# --- Utilisateurs -------------------------------------------------------------

class AuthError(Exception):
    pass


def create_user(full_name: str, email: str, password: str) -> dict:
    full_name, email = full_name.strip(), email.strip().lower()
    if not full_name or "@" not in email:
        raise AuthError("Nom ou adresse e-mail invalide.")
    if len(password) < 8:
        raise AuthError("Le mot de passe doit contenir au moins 8 caractères.")
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        with _connect() as con:
            cur = con.execute(
                "insert into users (full_name, email, password_hash, created_at) values (?, ?, ?, ?)",
                (full_name, email, password_hash, _now()),
            )
            user_id = cur.lastrowid
            con.execute(
                "insert into folders (user_id, name, created_at) values (?, ?, ?)",
                (user_id, "Mes analyses", _now()),
            )
    except sqlite3.IntegrityError:
        raise AuthError("Un compte existe déjà avec cette adresse e-mail.") from None
    return {"id": user_id, "full_name": full_name, "email": email}


def authenticate(email: str, password: str) -> dict:
    with _connect() as con:
        row = con.execute(
            "select id, full_name, email, password_hash from users where email = ?",
            (email.strip().lower(),),
        ).fetchone()
    if row is None or not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        raise AuthError("E-mail ou mot de passe incorrect.")
    return {"id": row["id"], "full_name": row["full_name"], "email": row["email"]}


# --- Sessions (survivent au rechargement de la page) --------------------------

SESSION_DAYS = 7


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat(timespec="seconds")
    with _connect() as con:
        con.execute("delete from sessions where expires_at < ?", (_now(),))
        con.execute("insert into sessions (token, user_id, expires_at) values (?, ?, ?)",
                    (token, user_id, expires))
    return token


def session_user(token: str) -> dict | None:
    with _connect() as con:
        row = con.execute(
            """select u.id, u.full_name, u.email from sessions s join users u on u.id = s.user_id
               where s.token = ? and s.expires_at > ?""",
            (token, _now()),
        ).fetchone()
    return dict(row) if row else None


def delete_session(token: str) -> None:
    with _connect() as con:
        con.execute("delete from sessions where token = ?", (token,))


# --- Dossiers -----------------------------------------------------------------

def list_folders(user_id: int) -> list[dict]:
    with _connect() as con:
        rows = con.execute(
            """select f.id, f.name, count(a.id) as n
               from folders f left join analyses a on a.folder_id = f.id
               where f.user_id = ? group by f.id order by f.created_at, f.id""",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def create_folder(user_id: int, name: str) -> int:
    with _connect() as con:
        return con.execute(
            "insert into folders (user_id, name, created_at) values (?, ?, ?)",
            (user_id, name.strip(), _now()),
        ).lastrowid


def rename_folder(user_id: int, folder_id: int, name: str) -> None:
    with _connect() as con:
        con.execute(
            "update folders set name = ? where id = ? and user_id = ?",
            (name.strip(), folder_id, user_id),
        )


def delete_folder(user_id: int, folder_id: int) -> None:
    with _connect() as con:
        con.execute("delete from folders where id = ? and user_id = ?", (folder_id, user_id))


# --- Analyses -----------------------------------------------------------------

def add_analysis(user_id: int, folder_id: int, question: str, sql: str,
                 result_json: str, row_count: int) -> None:
    with _connect() as con:
        owner = con.execute(
            "select 1 from folders where id = ? and user_id = ?", (folder_id, user_id)
        ).fetchone()
        if owner is None:
            raise PermissionError("Dossier introuvable.")
        con.execute(
            """insert into analyses (folder_id, question, sql, result_json, row_count, created_at)
               values (?, ?, ?, ?, ?, ?)""",
            (folder_id, question, sql, result_json, row_count, _now()),
        )


def list_analyses(user_id: int, folder_id: int) -> list[dict]:
    with _connect() as con:
        rows = con.execute(
            """select a.* from analyses a join folders f on f.id = a.folder_id
               where a.folder_id = ? and f.user_id = ? order by a.created_at, a.id""",
            (folder_id, user_id),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_analysis(user_id: int, analysis_id: int) -> None:
    with _connect() as con:
        con.execute(
            """delete from analyses where id = ?
               and folder_id in (select id from folders where user_id = ?)""",
            (analysis_id, user_id),
        )
