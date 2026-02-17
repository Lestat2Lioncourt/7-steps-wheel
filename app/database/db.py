"""
Initialisation et acces a la base de donnees SQLite.
"""

import json
import os
import sqlite3
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "roue_csi.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SEED_PATH = Path(__file__).resolve().parent / "seed.sql"
SEED_DEMO_PATH = Path(__file__).resolve().parent / "seed_demo.sql"
PROJECTS_PATH = DATA_DIR / "projects.json"

# Projet actif (module-level, mono-utilisateur)
_active_db_path = None


def set_active_project(db_file: str) -> None:
    """Definit le projet actif via le nom du fichier DB."""
    global _active_db_path
    _active_db_path = DATA_DIR / db_file


def get_active_db_path() -> Path | None:
    """Retourne le chemin de la DB active, ou None si aucun projet selectionne."""
    return _active_db_path


def load_projects() -> list[dict]:
    """Charge la liste des projets depuis projects.json."""
    if not PROJECTS_PATH.exists():
        return []
    with open(PROJECTS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("projects", [])


def get_project_by_id(project_id: str) -> dict | None:
    """Retourne le projet correspondant a l'id, ou None."""
    for p in load_projects():
        if p["id"] == project_id:
            return p
    return None


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Retourne une connexion SQLite avec foreign keys activees.

    Utilise db_path si fourni, sinon _active_db_path, sinon DB_PATH (fallback).
    """
    path = db_path or _active_db_path or DB_PATH
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path = DB_PATH, force: bool = False) -> None:
    """Cree la base, applique le schema et insere les donnees de reference + demo."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if force and db_path.exists():
        db_path.unlink()
        print(f"Base supprimee : {db_path}")

    already_exists = db_path.exists()

    conn = get_connection(db_path)
    try:
        if not already_exists:
            # Schema
            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            # Donnees de reference
            with open(SEED_PATH, "r", encoding="utf-8") as f:
                conn.executescript(f.read())
            # Donnees de demonstration
            if SEED_DEMO_PATH.exists():
                with open(SEED_DEMO_PATH, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
                print(f"Donnees demo chargees")
            print(f"Base creee : {db_path}")
        else:
            print(f"Base existante : {db_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db(force=True)
