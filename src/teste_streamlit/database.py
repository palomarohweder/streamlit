from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import streamlit as st
from sqlalchemy import Engine, URL, create_engine
from streamlit.errors import StreamlitSecretNotFoundError

from teste_streamlit.models import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOCAL_DATABASE = PROJECT_ROOT / "laboratorio.db"


def setting(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value

    try:
        value = st.secrets.get(name)
    except StreamlitSecretNotFoundError:
        return default
    return str(value) if value is not None else default


def make_engine(database_url: str | URL) -> Engine:
    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection: sqlite3.Connection, _: object) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

    return engine


@st.cache_resource
def get_engine() -> Engine:
    environment = (setting("APP_ENV", "development") or "development").lower()
    if environment in {"production", "prod"}:
        mysql_url = setting("MYSQL_DATABASE_URL")
        if not mysql_url:
            raise RuntimeError(
                "Defina MYSQL_DATABASE_URL nas variáveis de ambiente ou nos secrets."
            )
        return make_engine(mysql_url)

    database_url = setting("DATABASE_URL")
    if database_url:
        return make_engine(database_url)
    return make_engine(URL.create("sqlite", database=str(LOCAL_DATABASE)))


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
