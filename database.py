"""Acceso de solo lectura a la base analítica."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


DB_PATH = Path(__file__).resolve().parent / "data" / "forestal.db"
REQUIRED_OBJECTS = {
    "tara_sitios",
    "tara_clima",
    "tara_suelos",
    "tara_integrada",
    "inia_resumen",
    "inia_eea",
    "inia_lineas",
    "inia_secciones",
    "vw_tara_resumen_region",
    "vw_tara_cobertura",
    "vw_inia_resumen_departamento",
}


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError("No existe la base. Ejecute etl/build_database.py.")
    return sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True, check_same_thread=False)


def database_objects() -> set[str]:
    if not DB_PATH.exists():
        return set()
    with sqlite3.connect(DB_PATH) as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')"
            )
        }


def missing_required_objects() -> set[str]:
    return REQUIRED_OBJECTS - database_objects()


@st.cache_data(show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, get_connection(), params=params)


def table(name: str) -> pd.DataFrame:
    if name not in REQUIRED_OBJECTS:
        raise ValueError(f"Tabla no permitida: {name}")
    return query(f"SELECT * FROM {name}")
