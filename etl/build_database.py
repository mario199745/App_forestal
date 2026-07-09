"""Construye la base analitica SQLite Tara + INIA."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.prepare_tara_inia_data import build_database  # noqa: E402


if __name__ == "__main__":
    build_database()
