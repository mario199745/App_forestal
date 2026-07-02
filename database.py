"""Acceso de solo lectura a la base analítica."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


DB_PATH = Path(__file__).resolve().parent / "data" / "forestal.db"


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError("No existe la base. Ejecute etl/build_database.py.")
    return sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, check_same_thread=False)


@st.cache_data(show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, get_connection(), params=params)


def table(name: str) -> pd.DataFrame:
    allowed = {
        "fact_arbol",
        "fact_morfologia",
        "fact_tanino_repeticion",
        "fact_tanino_reporte",
        "vw_cobertura_dominios",
    }
    if name not in allowed:
        raise ValueError(f"Tabla no permitida: {name}")
    return query(f"SELECT * FROM {name}")
