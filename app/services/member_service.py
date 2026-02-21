"""
CRUD pour la gestion des membres d'un projet.
"""

from app.database.db import get_connection


def get_all_members():
    """Liste tous les membres du projet, ordonnes par role puis nom."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT id, login, nom, email, trigramme, role
            FROM utilisateurs
            ORDER BY
                CASE role WHEN 'admin' THEN 0 WHEN 'membre' THEN 1 WHEN 'lecteur' THEN 2 WHEN 'information' THEN 3 END,
                nom
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_member(login, nom, email="", trigramme="", role="membre"):
    """Ajoute un membre au projet. Leve ValueError si doublon."""
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM utilisateurs WHERE login = ? OR (email IS NOT NULL AND email = ? AND email != '')",
            (login, email),
        ).fetchone()
        if existing:
            raise ValueError("Cet utilisateur est deja membre du projet.")
        conn.execute(
            "INSERT INTO utilisateurs (login, nom, email, trigramme, role) VALUES (?, ?, ?, ?, ?)",
            (login, nom, email or None, trigramme or None, role),
        )
        conn.commit()
    finally:
        conn.close()


def update_member_role(user_id, new_role):
    """Change le role d'un membre. Protege le dernier admin."""
    if new_role not in ('admin', 'membre', 'lecteur', 'information'):
        raise ValueError(f"Role invalide : {new_role}")
    conn = get_connection()
    try:
        user = conn.execute("SELECT role FROM utilisateurs WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise ValueError("Utilisateur introuvable.")
        if user["role"] == "admin" and new_role != "admin":
            admin_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM utilisateurs WHERE role = 'admin'"
            ).fetchone()["cnt"]
            if admin_count <= 1:
                raise ValueError("Impossible : c'est le dernier administrateur du projet.")
        conn.execute("UPDATE utilisateurs SET role = ? WHERE id = ?", (new_role, user_id))
        conn.commit()
    finally:
        conn.close()


def remove_member(user_id, current_user_login):
    """Retire un membre du projet.
    Gardes : pas soi-meme, pas le dernier admin, pas si actions liees."""
    conn = get_connection()
    try:
        user = conn.execute("SELECT login, role FROM utilisateurs WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise ValueError("Utilisateur introuvable.")
        if user["login"] == current_user_login:
            raise ValueError("Vous ne pouvez pas vous retirer vous-meme.")
        if user["role"] == "admin":
            admin_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM utilisateurs WHERE role = 'admin'"
            ).fetchone()["cnt"]
            if admin_count <= 1:
                raise ValueError("Impossible : c'est le dernier administrateur du projet.")
        # Verifier les actions liees
        action_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM actions WHERE assignee_login = ? OR cree_par = ?",
            (user["login"], user["login"]),
        ).fetchone()["cnt"]
        if action_count > 0:
            raise ValueError(
                f"Impossible : cet utilisateur est lie a {action_count} action(s). "
                "Reassignez-les d'abord."
            )
        conn.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
