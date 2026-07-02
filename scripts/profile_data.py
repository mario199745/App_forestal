"""Perfil reproducible de las fuentes Excel del proyecto forestal.

Uso:
    conda run -n sigexpert python App_forestal/scripts/profile_data.py
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "DATA"
OUTPUT = ROOT / "DOCS" / "perfil_datos.json"

# Alcance aprobado para la base y el aplicativo.
SOURCE_FILES = (
    "Data_ProduccionArbol_FINAL.xlsx",
    "Data_MorfotipoMedidas_FINAL.xlsx",
    "Data_TaninosVainas_FINAL.xlsx",
)

NA_MARKERS = ["", "-", "--", "NA", "N/A", "na", "n/a", "s/d", "S/D"]


def slug(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def scalar(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def meaningful_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Quita filas/columnas totalmente vacías y cabeceras sin nombre vacías."""
    result = frame.replace(NA_MARKERS, pd.NA).dropna(axis=0, how="all")
    empty_unnamed = [
        col
        for col in result.columns
        if str(col).startswith("Unnamed:") and result[col].isna().all()
    ]
    return result.drop(columns=empty_unnamed).dropna(axis=1, how="all")


def column_profile(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna()
    numeric = pd.to_numeric(non_null, errors="coerce")
    numeric_ratio = float(numeric.notna().mean()) if len(non_null) else 0.0
    examples = [scalar(value) for value in non_null.drop_duplicates().head(8)]
    result: dict[str, Any] = {
        "dtype_lectura": str(series.dtype),
        "nulos": int(series.isna().sum()),
        "porcentaje_nulos": round(float(series.isna().mean() * 100), 2),
        "unicos": int(non_null.nunique(dropna=True)),
        "porcentaje_unicidad": round(
            float(non_null.nunique() / len(non_null) * 100), 2
        ) if len(non_null) else 0.0,
        "ratio_numerico": round(numeric_ratio, 4),
        "ejemplos": examples,
    }
    if len(non_null) and numeric_ratio >= 0.95:
        valid = numeric.dropna()
        result["estadisticas"] = {
            "min": scalar(valid.min()),
            "max": scalar(valid.max()),
            "media": scalar(valid.mean()),
            "mediana": scalar(valid.median()),
        }
    elif 0 < non_null.nunique() <= 20:
        result["frecuencias"] = {
            str(scalar(key)): int(value)
            for key, value in non_null.value_counts().head(20).items()
        }
    return result


def sheet_profile(frame: pd.DataFrame) -> dict[str, Any]:
    clean = meaningful_frame(frame)
    normalized = [slug(col) for col in clean.columns]
    duplicates = [name for name, count in Counter(normalized).items() if count > 1]
    exact_duplicates = int(clean.duplicated().sum()) if len(clean.columns) else 0
    unique_candidates = [
        str(col)
        for col in clean.columns
        if clean[col].notna().all() and clean[col].is_unique
    ]
    return {
        "filas": int(len(clean)),
        "columnas": int(len(clean.columns)),
        "duplicados_exactos": exact_duplicates,
        "columnas_normalizadas_duplicadas": duplicates,
        "candidatas_clave_unica": unique_candidates,
        "nombres_originales": [str(col) for col in clean.columns],
        "nombres_normalizados": normalized,
        "perfil_columnas": {
            str(col): column_profile(clean[col]) for col in clean.columns
        },
    }


def main() -> None:
    report: dict[str, Any] = {
        "generado": datetime.now().astimezone().isoformat(),
        "directorio_fuente": str(DATA_DIR),
        "archivos": {},
    }
    for filename in SOURCE_FILES:
        workbook = DATA_DIR / filename
        if not workbook.exists():
            raise FileNotFoundError(f"No se encontró la fuente requerida: {workbook}")
        excel = pd.ExcelFile(workbook, engine="openpyxl")
        book = {"tamano_bytes": workbook.stat().st_size, "hojas": {}}
        for sheet in excel.sheet_names:
            frame = pd.read_excel(excel, sheet_name=sheet, engine="openpyxl")
            book["hojas"][sheet] = sheet_profile(frame)
        report["archivos"][workbook.name] = book

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=scalar),
        encoding="utf-8",
    )
    print(f"Perfil guardado en {OUTPUT}")


if __name__ == "__main__":
    main()
