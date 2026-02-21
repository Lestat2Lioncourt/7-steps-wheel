"""
CRUD pour la gestion des membres d'un projet.
Adapte pour PostgreSQL (psycopg3) avec modele deux tables :
  - common.utilisateurs : donnees globales utilisateur
  - client_schema.projet_membres : rattachement au projet (role, dates)
L'ID retourne au frontend est projet_membres.id (= membership ID).
"""

from app.database.db import get_connection, get_active_project_id


def get_all_members():
    """Liste tous les membres du projet actif, ordonnes par role puis nom."""
    projet_id = get_active_project_id()
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT pm.id, u.id AS user_id, u.login, u.nom, u.email, u.trigramme,
                   pm.role, u.emails_secondaires,
                   pm.date_creation, pm.date_derniere_connexion, pm.date_fin,
                   (u.hash_mdp IS NULL OR u.hash_mdp = '') AS invitation_pending
            FROM projet_membres pm
            JOIN utilisateurs u ON u.id = pm.user_id
            WHERE pm.projet_id = %s
            ORDER BY
                CASE pm.role WHEN 'admin' THEN 0 WHEN 'membre' THEN 1
                     WHEN 'lecteur' THEN 2 WHEN 'information' THEN 3 END,
                u.nom
        """, (projet_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_member(login, nom, email="", trigramme="", role="membre"):
    """Ajoute un membre au projet. Cree l'utilisateur dans common si necessaire.
    Leve ValueError si deja membre du projet."""
    from datetime import datetime
    projet_id = get_active_project_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_connection()
    try:
        # Verifier si deja membre du projet (par login ou email)
        existing = conn.execute("""
            SELECT pm.id FROM projet_membres pm
            JOIN utilisateurs u ON u.id = pm.user_id
            WHERE pm.projet_id = %s
                  AND (u.login = %s
                       OR (u.email IS NOT NULL AND u.email = %s AND u.email != '')
                       OR %s = ANY(string_to_array(u.emails_secondaires, ',')))
        """, (projet_id, login, email, email)).fetchone()
        if existing:
            raise ValueError("Cet utilisateur est deja membre du projet.")

        # Trouver ou creer l'utilisateur dans common.utilisateurs
        user_row = conn.execute(
            "SELECT id FROM utilisateurs WHERE login = %s", (login,)
        ).fetchone()
        if not user_row and email:
            user_row = conn.execute(
                "SELECT id FROM utilisateurs WHERE email = %s", (email,)
            ).fetchone()

        if user_row:
            user_id = user_row['id']
        else:
            user_row = conn.execute("""
                INSERT INTO utilisateurs (login, nom, email, trigramme, date_creation)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (login, nom, email or None, trigramme or None, now)).fetchone()
            user_id = user_row['id']

        # Ajouter au projet
        conn.execute("""
            INSERT INTO projet_membres (projet_id, user_id, role, date_creation)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (projet_id, user_id) DO NOTHING
        """, (projet_id, user_id, role, now))
        conn.commit()
    finally:
        conn.close()


def update_member_role(member_id, new_role):
    """Change le role d'un membre. Protege le dernier admin."""
    if new_role not in ('admin', 'membre', 'lecteur', 'information'):
        raise ValueError(f"Role invalide : {new_role}")
    projet_id = get_active_project_id()
    conn = get_connection()
    try:
        pm = conn.execute(
            "SELECT id, role FROM projet_membres WHERE id = %s AND projet_id = %s",
            (member_id, projet_id)
        ).fetchone()
        if not pm:
            raise ValueError("Membre introuvable.")
        if pm["role"] == "admin" and new_role != "admin":
            admin_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM projet_membres WHERE projet_id = %s AND role = 'admin'",
                (projet_id,)
            ).fetchone()["cnt"]
            if admin_count <= 1:
                raise ValueError("Impossible : c'est le dernier administrateur du projet.")
        conn.execute(
            "UPDATE projet_membres SET role = %s WHERE id = %s",
            (new_role, member_id)
        )
        conn.commit()
    finally:
        conn.close()


def remove_member(member_id, current_user_login):
    """Retire un membre du projet.
    Gardes : pas soi-meme, pas le dernier admin, pas si actions liees."""
    projet_id = get_active_project_id()
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT pm.id, pm.role, u.login
            FROM projet_membres pm
            JOIN utilisateurs u ON u.id = pm.user_id
            WHERE pm.id = %s AND pm.projet_id = %s
        """, (member_id, projet_id)).fetchone()
        if not row:
            raise ValueError("Membre introuvable.")
        if row["login"] == current_user_login:
            raise ValueError("Vous ne pouvez pas vous retirer vous-meme.")
        if row["role"] == "admin":
            admin_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM projet_membres WHERE projet_id = %s AND role = 'admin'",
                (projet_id,)
            ).fetchone()["cnt"]
            if admin_count <= 1:
                raise ValueError("Impossible : c'est le dernier administrateur du projet.")
        # Verifier les actions liees
        action_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM actions WHERE projet_id = %s AND (assignee_login = %s OR cree_par = %s)",
            (projet_id, row["login"], row["login"]),
        ).fetchone()["cnt"]
        if action_count > 0:
            raise ValueError(
                f"Impossible : cet utilisateur est lie a {action_count} action(s). "
                "Reassignez-les d'abord."
            )
        conn.execute("DELETE FROM projet_membres WHERE id = %s", (member_id,))
        conn.commit()
    finally:
        conn.close()


def update_member_emails(member_id, emails_secondaires):
    """Met a jour les emails secondaires d'un membre.
    Les emails secondaires sont stockes sur common.utilisateurs (global)."""
    conn = get_connection()
    try:
        pm = conn.execute(
            "SELECT user_id FROM projet_membres WHERE id = %s", (member_id,)
        ).fetchone()
        if not pm:
            raise ValueError("Membre introuvable.")
        user_id = pm['user_id']

        if emails_secondaires:
            emails = [e.strip().lower() for e in emails_secondaires.split(",") if e.strip()]
            for em in emails:
                conflict = conn.execute(
                    "SELECT id, nom FROM utilisateurs WHERE email = %s AND id != %s",
                    (em, user_id),
                ).fetchone()
                if conflict:
                    raise ValueError(f"L'email {em} est deja l'email principal de {conflict['nom']}.")
                conflict2 = conn.execute(
                    "SELECT id, nom FROM utilisateurs WHERE id != %s AND %s = ANY(string_to_array(emails_secondaires, ','))",
                    (user_id, em),
                ).fetchone()
                if conflict2:
                    raise ValueError(f"L'email {em} est deja un email secondaire de {conflict2['nom']}.")
            clean = ",".join(emails)
        else:
            clean = None
        conn.execute(
            "UPDATE utilisateurs SET emails_secondaires = %s WHERE id = %s",
            (clean, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_member_date_fin(member_id, date_fin):
    """Met a jour la date de fin previsionnelle d'un membre (sur le projet)."""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE projet_membres SET date_fin = %s WHERE id = %s",
            (date_fin or None, member_id),
        )
        conn.commit()
    finally:
        conn.close()


def update_member(member_id, data):
    """Mise a jour complete d'un membre.
    Champs utilisateur (nom, trigramme, emails_secondaires) -> common.utilisateurs
    Champs membership (role, date_fin) -> projet_membres"""
    projet_id = get_active_project_id()
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT pm.id, pm.role, pm.user_id
            FROM projet_membres pm
            WHERE pm.id = %s AND pm.projet_id = %s
        """, (member_id, projet_id)).fetchone()
        if not row:
            raise ValueError("Membre introuvable.")
        user_id = row['user_id']

        # Verifier dernier admin
        new_role = data.get('role')
        if new_role:
            if new_role not in ('admin', 'membre', 'lecteur', 'information'):
                raise ValueError(f"Role invalide : {new_role}")
            if row['role'] == 'admin' and new_role != 'admin':
                admin_count = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM projet_membres WHERE projet_id = %s AND role = 'admin'",
                    (projet_id,)
                ).fetchone()['cnt']
                if admin_count <= 1:
                    raise ValueError("Impossible : c'est le dernier administrateur du projet.")

        # Validation emails secondaires
        emails_sec = data.get('emails_secondaires', '').strip() or None
        if emails_sec:
            emails = [e.strip().lower() for e in emails_sec.split(",") if e.strip()]
            for em in emails:
                conflict = conn.execute(
                    "SELECT id, nom FROM utilisateurs WHERE email = %s AND id != %s",
                    (em, user_id),
                ).fetchone()
                if conflict:
                    raise ValueError(f"L'email {em} est deja l'email principal de {conflict['nom']}.")
                conflict2 = conn.execute(
                    "SELECT id, nom FROM utilisateurs WHERE id != %s AND %s = ANY(string_to_array(emails_secondaires, ','))",
                    (user_id, em),
                ).fetchone()
                if conflict2:
                    raise ValueError(f"L'email {em} est deja un email secondaire de {conflict2['nom']}.")
            emails_sec = ",".join(emails)

        # Mise a jour utilisateur (common.utilisateurs)
        nom = data.get('nom', '').strip()
        trigramme = data.get('trigramme', '').strip().upper()

        user_updates = []
        user_params = []
        if nom:
            user_updates.append("nom = %s")
            user_params.append(nom)
        if trigramme is not None:
            user_updates.append("trigramme = %s")
            user_params.append(trigramme or None)
        user_updates.append("emails_secondaires = %s")
        user_params.append(emails_sec)

        if user_updates:
            user_params.append(user_id)
            conn.execute(
                f"UPDATE utilisateurs SET {', '.join(user_updates)} WHERE id = %s",
                user_params,
            )

        # Mise a jour membership (projet_membres)
        pm_updates = []
        pm_params = []
        if new_role:
            pm_updates.append("role = %s")
            pm_params.append(new_role)
        date_fin = data.get('date_fin', '').strip() or None
        pm_updates.append("date_fin = %s")
        pm_params.append(date_fin)

        if pm_updates:
            pm_params.append(member_id)
            conn.execute(
                f"UPDATE projet_membres SET {', '.join(pm_updates)} WHERE id = %s",
                pm_params,
            )

        conn.commit()
    finally:
        conn.close()
