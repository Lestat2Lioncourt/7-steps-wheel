"""
CRUD pour la gestion des membres d'un projet.
"""

from app.database.db import get_connection


def get_all_members():
    """Liste tous les membres du projet, ordonnes par role puis nom."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT id, login, nom, email, trigramme, role,
                   emails_secondaires, date_creation, date_derniere_connexion, date_fin
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
    from datetime import datetime
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM utilisateurs WHERE login = ? OR (email IS NOT NULL AND email = ? AND email != '') OR (',' || emails_secondaires || ',') LIKE '%,' || ? || ',%'",
            (login, email, email),
        ).fetchone()
        if existing:
            raise ValueError("Cet utilisateur est deja membre du projet.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute(
            "INSERT INTO utilisateurs (login, nom, email, trigramme, role, date_creation) VALUES (?, ?, ?, ?, ?, ?)",
            (login, nom, email or None, trigramme or None, role, now),
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


def update_member_emails(user_id, emails_secondaires):
    """Met a jour les emails secondaires d'un membre.
    Valide qu'aucun email n'est deja utilise par un autre membre (principal ou secondaire)."""
    conn = get_connection()
    try:
        if emails_secondaires:
            emails = [e.strip().lower() for e in emails_secondaires.split(",") if e.strip()]
            for em in emails:
                # Verifier email principal d'un autre membre
                conflict = conn.execute(
                    "SELECT id, nom FROM utilisateurs WHERE email = ? AND id != ?",
                    (em, user_id),
                ).fetchone()
                if conflict:
                    raise ValueError(f"L'email {em} est deja l'email principal de {conflict['nom']}.")
                # Verifier email secondaire d'un autre membre
                conflict2 = conn.execute(
                    "SELECT id, nom FROM utilisateurs WHERE id != ? AND (',' || emails_secondaires || ',') LIKE '%,' || ? || ',%'",
                    (user_id, em),
                ).fetchone()
                if conflict2:
                    raise ValueError(f"L'email {em} est deja un email secondaire de {conflict2['nom']}.")
            clean = ",".join(emails)
        else:
            clean = None
        conn.execute(
            "UPDATE utilisateurs SET emails_secondaires = ? WHERE id = ?",
            (clean, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_member_date_fin(user_id, date_fin):
    """Met a jour la date de fin previsionnelle d'un membre."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE utilisateurs SET date_fin = ? WHERE id = ?",
            (date_fin or None, user_id),
        )
        conn.commit()
    finally:
        conn.close()
