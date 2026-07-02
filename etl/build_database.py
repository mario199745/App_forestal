"""Construye la base analítica SQLite a partir de las tres fuentes aprobadas."""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "DATA"
APP_DIR = ROOT / "App_forestal"
DB_PATH = APP_DIR / "data" / "forestal.db"
REPORT_PATH = ROOT / "DOCS" / "reporte_validacion.json"


def slug(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def canon_region(value: object) -> str | None:
    return None if pd.isna(value) else " ".join(part.capitalize() for part in slug(value).split("_"))


def canon_manejo(value: object) -> str | None:
    if pd.isna(value):
        return None
    key = slug(value)
    if key.startswith("plantacion"):
        return "Plantación"
    if key.startswith("bosque"):
        return "Bosque"
    if key.startswith("saf"):
        return "SAF"
    return str(value).strip()


def canon_clase(value: object) -> str | None:
    if pd.isna(value):
        return None
    key = slug(value)
    if key.startswith("inf"):
        return "Inferior"
    if key.startswith("med"):
        return "Media"
    if key.startswith("sup"):
        return "Superior"
    return str(value).strip()


def canon_morfotipo(value: object) -> str | None:
    if pd.isna(value):
        return None
    key = slug(value)
    known = {
        "almidon_blanca": "Almidón-Blanca",
        "roja": "Roja",
        "jancos": "Jancos",
    }
    return known.get(key, str(value).strip().replace("_", " "))


def read_sheet(filename: str, sheet: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    frame = pd.read_excel(path, sheet_name=sheet, engine="openpyxl")
    frame = frame.replace(["-", "--", "NA", "N/A", ""], pd.NA).dropna(how="all")
    frame = frame.dropna(axis=1, how="all")
    frame.columns = [slug(column) for column in frame.columns]
    frame.insert(0, "source_row", range(2, len(frame) + 2))
    frame["source_file"] = filename
    frame["source_sheet"] = sheet
    frame["loaded_at"] = datetime.now().astimezone().isoformat()
    frame["is_exact_duplicate"] = frame.drop(
        columns=["source_row", "source_file", "source_sheet", "loaded_at"]
    ).duplicated(keep=False).astype(int)
    return frame


def add_common_dimensions(
    frame: pd.DataFrame, region: str, manejo: str, clase: str, morfotipo: str
) -> pd.DataFrame:
    frame["region_original"] = frame[region]
    frame["manejo_original"] = frame[manejo]
    frame["clase_original"] = frame[clase]
    frame["morfotipo_original"] = frame[morfotipo]
    frame["region"] = frame[region].map(canon_region)
    frame["manejo"] = frame[manejo].map(canon_manejo)
    frame["clase"] = frame[clase].map(canon_clase)
    frame["morfotipo"] = frame[morfotipo].map(canon_morfotipo)
    removable = {region, manejo, clase, morfotipo} - {
        "region", "manejo", "clase", "morfotipo"
    }
    return frame.drop(columns=list(removable))


def infer_clase_from_code(code: object) -> str | None:
    if pd.isna(code):
        return None
    parts = str(code).split("-")
    if len(parts) >= 3:
        return {"I": "Inferior", "M": "Media", "S": "Superior"}.get(parts[2].upper())
    return None


def prepare_tables() -> dict[str, pd.DataFrame]:
    production = read_sheet("Data_ProduccionArbol_FINAL.xlsx", "DataBase")
    production = add_common_dimensions(
        production, "region", "aprovechamiento", "clase", "morfotipo"
    )
    production.insert(0, "arbol_id", range(1, len(production) + 1))

    morphology = read_sheet("Data_MorfotipoMedidas_FINAL.xlsx", "Hoja1")
    morphology = add_common_dimensions(
        morphology, "region", "manejo", "clase", "morfotipo"
    )
    morphology.insert(0, "morfologia_id", range(1, len(morphology) + 1))

    tannin_rep = read_sheet("Data_TaninosVainas_FINAL.xlsx", "Valores_R1 & R2")
    tannin_rep = add_common_dimensions(
        tannin_rep, "region", "manejo", "clase", "morfotipo"
    )
    if "fecha_result" in tannin_rep:
        raw_date = tannin_rep["fecha_result"].copy()
        numeric_date = pd.to_numeric(raw_date, errors="coerce")
        converted = pd.to_datetime(
            numeric_date, unit="D", origin="1899-12-30", errors="coerce"
        )
        tannin_rep["fecha_result_original"] = raw_date
        tannin_rep["fecha_result"] = converted.dt.strftime("%Y-%m-%d")
    tannin_rep.insert(0, "tanino_repeticion_id", range(1, len(tannin_rep) + 1))

    tannin_report = read_sheet("Data_TaninosVainas_FINAL.xlsx", "Valores_Reporte")
    tannin_report["clase_inferida"] = tannin_report["codigo_dei"].map(infer_clase_from_code)
    tannin_report = add_common_dimensions(
        tannin_report, "region", "manejo", "clase_inferida", "morfotipo"
    )
    tannin_report.insert(0, "tanino_reporte_id", range(1, len(tannin_report) + 1))

    return {
        "fact_arbol": production,
        "fact_morfologia": morphology,
        "fact_tanino_repeticion": tannin_rep,
        "fact_tanino_reporte": tannin_report,
    }


def dimension(values: list[pd.Series], id_name: str, value_name: str) -> pd.DataFrame:
    series = pd.concat(values, ignore_index=True).dropna().drop_duplicates().sort_values()
    result = pd.DataFrame({value_name: series.reset_index(drop=True)})
    result.insert(0, id_name, range(1, len(result) + 1))
    return result


def create_views(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE VIEW vw_cobertura_dominios AS
        WITH grupos AS (
          SELECT region, manejo, clase FROM fact_arbol
          UNION SELECT region, manejo, clase FROM fact_morfologia
          UNION SELECT region, manejo, clase FROM fact_tanino_repeticion
        )
        SELECT g.region, g.manejo, g.clase,
          EXISTS(SELECT 1 FROM fact_arbol a WHERE a.region=g.region AND a.manejo=g.manejo AND a.clase=g.clase) AS tiene_produccion,
          EXISTS(SELECT 1 FROM fact_morfologia m WHERE m.region=g.region AND m.manejo=g.manejo AND m.clase=g.clase) AS tiene_morfologia,
          EXISTS(SELECT 1 FROM fact_tanino_repeticion t WHERE t.region=g.region AND t.manejo=g.manejo AND t.clase=g.clase) AS tiene_taninos
        FROM grupos g;

        CREATE VIEW vw_resumen_produccion AS
        SELECT region, manejo, clase, morfotipo, COUNT(*) AS n,
          AVG(alt_total) AS altura_media, AVG(dap_ms) AS dap_medio,
          AVG(biomasa_alom) AS biomasa_media, AVG(peso_cosfin) AS cosecha_media
        FROM fact_arbol GROUP BY region, manejo, clase, morfotipo;

        CREATE VIEW vw_resumen_morfologia AS
        SELECT region, manejo, clase, morfotipo, COUNT(*) AS n,
          AVG(long_vaina) AS longitud_vaina_media, AVG(anch_vaina) AS ancho_vaina_medio,
          AVG(peso_vaina) AS peso_vaina_medio, AVG(n_semilla) AS semillas_media,
          AVG(peso_semilla) AS peso_semilla_medio
        FROM fact_morfologia GROUP BY region, manejo, clase, morfotipo;

        CREATE VIEW vw_resumen_taninos AS
        SELECT region, manejo, clase, morfotipo, COUNT(*) AS n,
          AVG(taninos) AS taninos_media, MIN(taninos) AS taninos_min,
          MAX(taninos) AS taninos_max, AVG(humedad) AS humedad_media
        FROM fact_tanino_repeticion GROUP BY region, manejo, clase, morfotipo;
        """
    )


def validation_report(tables: dict[str, pd.DataFrame]) -> dict[str, object]:
    result: dict[str, object] = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "database": str(DB_PATH),
        "tables": {},
    }
    for name, frame in tables.items():
        result["tables"][name] = {
            "rows": len(frame),
            "columns": len(frame.columns),
            "duplicate_rows_flagged": int(frame["is_exact_duplicate"].sum()),
            "null_cells": int(frame.isna().sum().sum()),
            "regions": int(frame["region"].nunique()),
            "management_types": int(frame["manejo"].nunique()),
            "classes": int(frame["clase"].nunique()),
        }
    return result


def build_database() -> Path:
    tables = prepare_tables()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    with sqlite3.connect(DB_PATH) as connection:
        for name, frame in tables.items():
            frame.to_sql(name, connection, index=False, if_exists="replace")

        dimensions = {
            "dim_region": dimension([f["region"] for f in tables.values()], "region_id", "region"),
            "dim_manejo": dimension([f["manejo"] for f in tables.values()], "manejo_id", "manejo"),
            "dim_clase": dimension([f["clase"] for f in tables.values()], "clase_id", "clase"),
            "dim_morfotipo": dimension(
                [f["morfotipo"] for f in tables.values()], "morfotipo_id", "morfotipo"
            ),
        }
        for name, frame in dimensions.items():
            frame.to_sql(name, connection, index=False, if_exists="replace")

        for table in tables:
            connection.execute(
                f"CREATE INDEX idx_{table}_filtros ON {table}(region, manejo, clase, morfotipo)"
            )
        create_views(connection)
        connection.execute("ANALYZE")

    report = validation_report(tables)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Base creada: {DB_PATH}")
    print(json.dumps({name: len(frame) for name, frame in tables.items()}, ensure_ascii=False))
    return DB_PATH


if __name__ == "__main__":
    build_database()
