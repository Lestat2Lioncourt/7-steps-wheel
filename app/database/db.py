"""
Couche d'acces a la base de donnees PostgreSQL.
Gere les connexions, les schemas (common + par client) et les migrations.
"""

import re
import unicodedata
from datetime import date
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.database.config import get_dsn

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SQL_DIR = Path(__file__).resolve().parent
SCHEMA_COMMON_PATH = SQL_DIR / "schema_common.sql"
SEED_COMMON_PATH = SQL_DIR / "seed_common.sql"
SCHEMA_CLIENT_PATH = SQL_DIR / "schema_client.sql"

# Contexte actif (module-level, mono-utilisateur)
_active_client_schema = None
_active_project_id = None


# -------------------------------------------------------------------
# Connexion
# -------------------------------------------------------------------

def get_connection():
    """Retourne une connexion PostgreSQL avec dict rows et le bon search_path."""
    conn = psycopg.connect(get_dsn(), row_factory=dict_row)
    if _active_client_schema:
        conn.execute(
            sql.SQL("SET search_path = {}, common").format(
                sql.Identifier(_active_client_schema)
            )
        )
    else:
        conn.execute("SET search_path = common")
    return conn


def get_connection_common():
    """Retourne une connexion pointant sur le schema common uniquement."""
    conn = psycopg.connect(get_dsn(), row_factory=dict_row)
    conn.execute("SET search_path = common")
    return conn


def get_connection_raw():
    """Retourne une connexion brute (autocommit, sans search_path)."""
    return psycopg.connect(get_dsn(), autocommit=True, row_factory=dict_row)


# -------------------------------------------------------------------
# Contexte actif
# -------------------------------------------------------------------

def set_active_context(client_schema=None, project_id=None):
    """Definit le client et le projet actifs."""
    global _active_client_schema, _active_project_id
    _active_client_schema = client_schema
    _active_project_id = project_id


def get_active_context():
    """Retourne (client_schema, project_id)."""
    return _active_client_schema, _active_project_id


def get_active_project_id():
    """Retourne l'id du projet actif."""
    return _active_project_id


def get_active_client_schema():
    """Retourne le schema du client actif."""
    return _active_client_schema


# -------------------------------------------------------------------
# Initialisation du schema common
# -------------------------------------------------------------------

def init_common():
    """Cree le schema common et insere les donnees de reference.
    Idempotent (IF NOT EXISTS + ON CONFLICT DO NOTHING)."""
    conn = get_connection_raw()
    try:
        with open(SCHEMA_COMMON_PATH, "r", encoding="utf-8") as f:
            conn.execute(f.read())
        with open(SEED_COMMON_PATH, "r", encoding="utf-8") as f:
            conn.execute(f.read())
        print("Schema common initialise")
    finally:
        conn.close()


# -------------------------------------------------------------------
# Gestion des clients
# -------------------------------------------------------------------

def _make_slug(name):
    """Genere un slug ASCII a partir d'un nom."""
    slug = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_").lower()
    return slug or "client"


def load_clients():
    """Retourne la liste de tous les clients."""
    conn = get_connection_common()
    try:
        rows = conn.execute(
            "SELECT id, nom, schema_name, date_creation FROM clients ORDER BY nom"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_client_by_id(client_id):
    """Retourne le client correspondant a l'id, ou None."""
    conn = get_connection_common()
    try:
        row = conn.execute(
            "SELECT id, nom, schema_name, date_creation FROM clients WHERE id = %s",
            (client_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_client_by_schema(schema_name):
    """Retourne le client correspondant au schema, ou None."""
    conn = get_connection_common()
    try:
        row = conn.execute(
            "SELECT id, nom, schema_name, date_creation FROM clients WHERE schema_name = %s",
            (schema_name,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_client(nom):
    """Cree un nouveau client : schema PostgreSQL + tables metier.
    Retourne le dict {id, nom, schema_name, date_creation}."""
    base_slug = "client_" + _make_slug(nom)

    conn = get_connection_raw()
    try:
        # Trouver un schema_name unique
        existing = {r['schema_name'] for r in conn.execute(
            "SELECT schema_name FROM common.clients"
        ).fetchall()}

        slug = base_slug
        counter = 1
        while slug in existing:
            slug = f"{base_slug}_{counter}"
            counter += 1

        # Creer le schema
        conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(
            sql.Identifier(slug)
        ))

        # Creer les tables metier dans le schema
        conn.execute(sql.SQL("SET search_path = {}, common").format(
            sql.Identifier(slug)
        ))
        with open(SCHEMA_CLIENT_PATH, "r", encoding="utf-8") as f:
            conn.execute(f.read())

        # Enregistrer dans common.clients
        conn.execute("SET search_path = common")
        row = conn.execute(
            """INSERT INTO clients (nom, schema_name, date_creation)
               VALUES (%s, %s, %s) RETURNING id, nom, schema_name, date_creation""",
            (nom, slug, date.today().isoformat())
        ).fetchone()

        print(f"Client cree : {nom} (schema: {slug})")
        return dict(row)
    finally:
        conn.close()


def update_client(client_id, nom=None):
    """Met a jour le nom d'un client."""
    conn = get_connection_common()
    try:
        if nom:
            conn.execute(
                "UPDATE clients SET nom = %s WHERE id = %s",
                (nom, client_id)
            )
            conn.commit()
    finally:
        conn.close()


def delete_client(client_id):
    """Supprime un client et son schema. Retourne True si supprime."""
    conn = get_connection_raw()
    try:
        row = conn.execute(
            "SELECT schema_name FROM common.clients WHERE id = %s",
            (client_id,)
        ).fetchone()
        if not row:
            return False

        schema_name = row['schema_name']

        # Supprimer le schema et toutes ses tables
        conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
            sql.Identifier(schema_name)
        ))

        # Supprimer l'entree dans common.clients (cascade supprime client_membres)
        conn.execute(
            "DELETE FROM common.clients WHERE id = %s",
            (client_id,)
        )

        print(f"Client supprime : {schema_name}")
        return True
    finally:
        conn.close()


# -------------------------------------------------------------------
# Gestion des membres client
# -------------------------------------------------------------------

def get_clients_for_user(user_id):
    """Retourne la liste des clients auxquels un utilisateur a acces."""
    conn = get_connection_common()
    try:
        rows = conn.execute(
            """SELECT c.id, c.nom, c.schema_name, cm.role
               FROM clients c
               JOIN client_membres cm ON cm.client_id = c.id
               WHERE cm.user_id = %s
               ORDER BY c.nom""",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_client_member(client_id, user_id, role='membre'):
    """Ajoute un utilisateur a un client."""
    conn = get_connection_common()
    try:
        conn.execute(
            """INSERT INTO client_membres (client_id, user_id, role)
               VALUES (%s, %s, %s)
               ON CONFLICT (client_id, user_id) DO NOTHING""",
            (client_id, user_id, role)
        )
        conn.commit()
    finally:
        conn.close()


# -------------------------------------------------------------------
# Gestion des projets (dans le schema client actif)
# -------------------------------------------------------------------

def load_projects(client_schema=None):
    """Retourne la liste des projets du client actif (ou du schema specifie)."""
    schema = client_schema or _active_client_schema
    if not schema:
        return []
    conn = get_connection_raw()
    try:
        conn.execute(sql.SQL("SET search_path = {}, common").format(
            sql.Identifier(schema)
        ))
        rows = conn.execute(
            "SELECT id, nom, date_creation, actif FROM projets ORDER BY nom"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_project_by_id(project_id, client_schema=None):
    """Retourne le projet correspondant a l'id dans le schema client."""
    schema = client_schema or _active_client_schema
    if not schema:
        return None
    conn = get_connection_raw()
    try:
        conn.execute(sql.SQL("SET search_path = {}, common").format(
            sql.Identifier(schema)
        ))
        row = conn.execute(
            "SELECT id, nom, date_creation, actif FROM projets WHERE id = %s",
            (project_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_project(nom, client_schema=None):
    """Cree un nouveau projet dans le schema client actif.
    Retourne le dict {id, nom, date_creation, actif}."""
    schema = client_schema or _active_client_schema
    if not schema:
        raise ValueError("Aucun client actif")
    conn = get_connection_raw()
    try:
        conn.execute(sql.SQL("SET search_path = {}, common").format(
            sql.Identifier(schema)
        ))
        row = conn.execute(
            """INSERT INTO projets (nom, date_creation)
               VALUES (%s, %s) RETURNING id, nom, date_creation, actif""",
            (nom, date.today().isoformat())
        ).fetchone()
        print(f"Projet cree : {nom}")
        return dict(row)
    finally:
        conn.close()


def update_project(project_id, nom=None, client_schema=None):
    """Met a jour le nom d'un projet."""
    schema = client_schema or _active_client_schema
    if not schema:
        return None
    conn = get_connection_raw()
    try:
        conn.execute(sql.SQL("SET search_path = {}, common").format(
            sql.Identifier(schema)
        ))
        if nom:
            conn.execute(
                "UPDATE projets SET nom = %s WHERE id = %s",
                (nom, project_id)
            )
        row = conn.execute(
            "SELECT id, nom, date_creation, actif FROM projets WHERE id = %s",
            (project_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def delete_project(project_id, client_schema=None):
    """Supprime un projet (CASCADE supprime les donnees associees)."""
    schema = client_schema or _active_client_schema
    if not schema:
        return False
    conn = get_connection_raw()
    try:
        conn.execute(sql.SQL("SET search_path = {}, common").format(
            sql.Identifier(schema)
        ))
        result = conn.execute(
            "DELETE FROM projets WHERE id = %s", (project_id,)
        )
        return result.rowcount > 0
    finally:
        conn.close()


# -------------------------------------------------------------------
# Gestion des membres projet
# -------------------------------------------------------------------

def get_projects_for_user(user_id, client_schema=None):
    """Retourne les projets auxquels un utilisateur a acces dans le client."""
    schema = client_schema or _active_client_schema
    if not schema:
        return []
    conn = get_connection_raw()
    try:
        conn.execute(sql.SQL("SET search_path = {}, common").format(
            sql.Identifier(schema)
        ))
        rows = conn.execute(
            """SELECT p.id, p.nom, p.date_creation, pm.role
               FROM projets p
               JOIN projet_membres pm ON pm.projet_id = p.id
               WHERE pm.user_id = %s AND p.actif = TRUE
               ORDER BY p.nom""",
            (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_project_member(project_id, user_id, role='membre'):
    """Ajoute un utilisateur a un projet."""
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO projet_membres (projet_id, user_id, role, date_creation)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (projet_id, user_id) DO NOTHING""",
            (project_id, user_id, role, date.today().isoformat())
        )
        conn.commit()
    finally:
        conn.close()


# -------------------------------------------------------------------
# Migrations client schemas
# -------------------------------------------------------------------

def migrate_client_schema(schema_name):
    """Applique les migrations sur un schema client existant.
    Utilise IF NOT EXISTS / ADD COLUMN IF NOT EXISTS pour etre idempotent."""
    conn = get_connection_raw()
    try:
        conn.execute(sql.SQL("SET search_path = {}, common").format(
            sql.Identifier(schema_name)
        ))

        # Verifier que les tables existent, sinon les creer
        with open(SCHEMA_CLIENT_PATH, "r", encoding="utf-8") as f:
            conn.execute(f.read())

        # Migrations futures iront ici :
        # conn.execute("ALTER TABLE actions ADD COLUMN IF NOT EXISTS new_col TEXT")

        print(f"Migration schema {schema_name} OK")
    finally:
        conn.close()


def migrate_all_schemas():
    """Applique les migrations sur tous les schemas clients."""
    conn = get_connection_common()
    try:
        schemas = conn.execute(
            "SELECT schema_name FROM clients"
        ).fetchall()
    finally:
        conn.close()

    for row in schemas:
        migrate_client_schema(row['schema_name'])


if __name__ == "__main__":
    init_common()
    print("Initialisation terminee")
