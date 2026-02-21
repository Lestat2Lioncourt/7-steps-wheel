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


def set_active_project(db_file: str = None, db_path: str = None) -> None:
    """Definit le projet actif. db_path (absolu) a priorite sur db_file (relatif a data/)."""
    global _active_db_path
    if db_path:
        _active_db_path = Path(db_path)
    else:
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


def update_project(project_id: str, name: str = None, db_path: str = None) -> dict | None:
    """Met a jour le nom et/ou le chemin d'un projet. Retourne le projet mis a jour."""
    projects = load_projects()
    updated = None
    for p in projects:
        if p["id"] == project_id:
            if name:
                p["name"] = name
            if db_path is not None and "db_path" in p:
                p["db_path"] = db_path
            updated = p
            break
    if updated:
        _save_projects(projects)
    return updated


def delete_project(project_id: str) -> bool:
    """Retire un projet de la liste (ne supprime pas le fichier DB). Retourne True si supprime."""
    projects = load_projects()
    new_list = [p for p in projects if p["id"] != project_id]
    if len(new_list) == len(projects):
        return False
    _save_projects(new_list)
    return True


def _save_projects(projects: list[dict]) -> None:
    """Ecrit la liste des projets dans projects.json."""
    PROJECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROJECTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"projects": projects}, f, ensure_ascii=False, indent=2)


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
            # Migration : ajouter les colonnes email/trigramme/dates si absentes
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(utilisateurs)").fetchall()}
            for col_name in ("email", "trigramme", "emails_secondaires", "date_creation", "date_derniere_connexion", "date_fin"):
                if col_name not in cols:
                    try:
                        conn.execute(f"ALTER TABLE utilisateurs ADD COLUMN {col_name} TEXT")
                        print(f"Migration : colonne '{col_name}' ajoutee a utilisateurs")
                    except sqlite3.OperationalError:
                        pass  # colonne deja ajoutee par un autre processus
            # Migration : ajouter date_debut/date_fin a actions si absentes
            action_cols = {row["name"] for row in conn.execute("PRAGMA table_info(actions)").fetchall()}
            for col_name in ("date_debut", "date_fin"):
                if col_name not in action_cols:
                    try:
                        conn.execute(f"ALTER TABLE actions ADD COLUMN {col_name} TEXT")
                        print(f"Migration : colonne '{col_name}' ajoutee a actions")
                    except sqlite3.OperationalError:
                        pass

            # Migration : renommer role 'intervenant' -> 'membre' + ajouter 'lecteur'
            schema_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='utilisateurs'"
            ).fetchone()
            needs_rebuild = False
            rename_intervenant = False
            if schema_sql and 'intervenant' in schema_sql[0]:
                needs_rebuild = True
                rename_intervenant = True
            elif schema_sql and 'information' not in schema_sql[0]:
                needs_rebuild = True

            if needs_rebuild:
                role_expr = ("CASE WHEN role = 'intervenant' THEN 'membre' ELSE role END"
                             if rename_intervenant else "role")
                conn.executescript(f"""
                    PRAGMA foreign_keys = OFF;
                    DROP TABLE IF EXISTS utilisateurs_new;
                    CREATE TABLE utilisateurs_new (
                        id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                        login                   TEXT UNIQUE NOT NULL,
                        nom                     TEXT NOT NULL,
                        email                   TEXT,
                        trigramme               TEXT,
                        role                    TEXT NOT NULL CHECK (role IN ('admin', 'membre', 'lecteur', 'information')),
                        emails_secondaires      TEXT,
                        date_creation           TEXT,
                        date_derniere_connexion TEXT,
                        date_fin                TEXT
                    );
                    INSERT INTO utilisateurs_new (id, login, nom, email, trigramme, role,
                                                  emails_secondaires, date_creation, date_derniere_connexion, date_fin)
                        SELECT id, login, nom, email, trigramme, {role_expr},
                               emails_secondaires, date_creation, date_derniere_connexion, date_fin
                        FROM utilisateurs;
                    DROP TABLE utilisateurs;
                    ALTER TABLE utilisateurs_new RENAME TO utilisateurs;
                    PRAGMA foreign_keys = ON;
                """)
                print("Migration : table utilisateurs reconstruite (roles: admin/membre/lecteur/information)")

            conn.commit()
            print(f"Base existante : {db_path}")
    finally:
        conn.close()


def create_project(name: str) -> dict:
    """Cree un nouveau projet : DB vierge (schema + ref) + entree dans projects.json.
    Retourne le dict {id, name, db_file}."""
    import re
    import unicodedata

    # Generer un slug a partir du nom
    slug = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()
    if not slug:
        slug = "projet"

    # S'assurer que l'id et le fichier sont uniques
    existing = load_projects()
    existing_ids = {p["id"] for p in existing}
    existing_files = {p["db_file"] for p in existing}

    base_slug = slug
    counter = 1
    while slug in existing_ids or f"{slug}.db" in existing_files:
        slug = f"{base_slug}-{counter}"
        counter += 1

    db_file = f"{slug}.db"
    db_path = DATA_DIR / db_file

    # Creer la DB (schema + donnees de reference, sans demo)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    finally:
        conn.close()

    # Ajouter dans projects.json
    project = {"id": slug, "name": name, "db_file": db_file}
    existing.append(project)
    PROJECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROJECTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"projects": existing}, f, ensure_ascii=False, indent=2)

    print(f"Projet cree : {name} ({db_file})")
    return project


def attach_project(name: str, source_path: str) -> dict:
    """Rattache un projet existant par reference directe (sans copie).
    Retourne le dict {id, name, db_path}."""
    import re
    import unicodedata

    source = Path(source_path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"Fichier introuvable : {source_path}")

    # Generer un slug pour l'id
    slug = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug).strip("-").lower()
    if not slug:
        slug = "projet"

    existing = load_projects()
    existing_ids = {p["id"] for p in existing}

    base_slug = slug
    counter = 1
    while slug in existing_ids:
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Appliquer les migrations sur la DB distante
    init_db(source)

    # Ajouter dans projects.json avec db_path (chemin absolu)
    project = {"id": slug, "name": name, "db_path": str(source)}
    existing.append(project)
    PROJECTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROJECTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"projects": existing}, f, ensure_ascii=False, indent=2)

    print(f"Projet rattache : {name} -> {source}")
    return project


if __name__ == "__main__":
    init_db(force=True)
