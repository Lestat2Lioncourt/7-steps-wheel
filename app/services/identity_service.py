"""
Utilitaires d'identite : trigramme, placeholder user, rattachement projet.
Adapte pour PostgreSQL (psycopg3) avec modele deux tables :
  - common.utilisateurs : donnees globales utilisateur
  - client_schema.projet_membres : rattachement au projet (role, dates)
"""

import re

from app.database.db import get_connection, get_active_project_id


# -------------------------------------------------------------------
# Trigramme
# -------------------------------------------------------------------
def suggest_trigramme(nom_str):
    """Genere un trigramme a partir du nom.
    "NOM, Prenom" -> initiale prenom + 2 premieres lettres du nom (ex: PNO)
    "Prenom Nom" -> idem (ex: PNO)
    Mot seul -> 3 premieres lettres."""
    if not nom_str:
        return ""
    s = nom_str.strip()
    if "," in s:
        parts = s.split(",", 1)
        nom_part = re.sub(r"[^A-Za-z\u00C0-\u00FF]", "", parts[0].strip())
        prenom_part = re.sub(r"[^A-Za-z\u00C0-\u00FF]", "", parts[1].strip())
        if prenom_part and nom_part:
            return (prenom_part[0] + nom_part[:2]).upper()
        if nom_part:
            return nom_part[:3].upper()
        return ""
    words = s.split()
    if len(words) >= 2:
        prenom_part = re.sub(r"[^A-Za-z\u00C0-\u00FF]", "", words[0])
        nom_part = re.sub(r"[^A-Za-z\u00C0-\u00FF]", "", words[-1])
        if prenom_part and nom_part:
            return (prenom_part[0] + nom_part[:2]).upper()
    clean = re.sub(r"[^A-Za-z\u00C0-\u00FF]", "", s)
    return clean[:3].upper()


# -------------------------------------------------------------------
# Placeholder user (assignation par email)
# -------------------------------------------------------------------
def create_placeholder_user(email):
    """Cree un utilisateur placeholder a partir d'un email.
    login = partie avant @, nom = email, trigramme = NULL.
    Si l'utilisateur existe deja, retourne le login existant.
    Ajoute aussi au projet actif si pas deja membre."""
    from datetime import datetime
    projet_id = get_active_project_id()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_connection()
    try:
        # Verifier si un utilisateur avec cet email existe deja
        row = conn.execute(
            "SELECT id, login FROM utilisateurs WHERE email = %s", (email,)
        ).fetchone()
        if row:
            user_id = row['id']
            login = row['login']
        else:
            login = email.split("@")[0].lower()
            # Verifier si le login existe deja
            row = conn.execute(
                "SELECT id, login FROM utilisateurs WHERE login = %s", (login,)
            ).fetchone()
            if row:
                user_id = row['id']
                login = row['login']
            else:
                row = conn.execute("""
                    INSERT INTO utilisateurs (login, nom, email, date_creation)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """, (login, email, email, now)).fetchone()
                user_id = row['id']

        # Ajouter au projet si pas deja membre
        if projet_id:
            conn.execute("""
                INSERT INTO projet_membres (projet_id, user_id, role, date_creation)
                VALUES (%s, %s, 'membre', %s)
                ON CONFLICT (projet_id, user_id) DO NOTHING
            """, (projet_id, user_id, now))

        conn.commit()
        return login
    finally:
        conn.close()


# -------------------------------------------------------------------
# Synchronisation avec la base (common.utilisateurs + projet_membres)
# -------------------------------------------------------------------
def ensure_user_in_db(login, nom, email="", trigramme=""):
    """Verifie si l'utilisateur est membre du projet actif.
    Ne met plus a jour nom/email/trigramme (fixe par l'auth).
    Seule date_derniere_connexion est mise a jour.
    - Si login existe ET est membre : UPDATE date + retourne le role.
    - Si email match un placeholder (login different) : fusion, retourne le role.
    - Si email match un email secondaire : reconnait l'utilisateur, retourne le role.
    - Si n'existe pas ou pas membre : retourne None."""
    from datetime import datetime
    projet_id = get_active_project_id()
    if not projet_id:
        return None
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_connection()
    try:
        # Fusion placeholder : chercher un utilisateur avec cet email mais un login different
        if email:
            placeholder = conn.execute("""
                SELECT u.id AS user_id, u.login, pm.role, pm.id AS pm_id
                FROM utilisateurs u
                JOIN projet_membres pm ON pm.user_id = u.id
                WHERE u.email = %s AND u.login != %s AND pm.projet_id = %s
            """, (email, login, projet_id)).fetchone()
            if placeholder:
                old_login = placeholder["login"]
                role = placeholder["role"]
                user_id = placeholder["user_id"]
                # Mettre a jour les FK dans actions
                conn.execute(
                    "UPDATE actions SET assignee_login = %s WHERE assignee_login = %s AND projet_id = %s",
                    (login, old_login, projet_id),
                )
                conn.execute(
                    "UPDATE actions SET cree_par = %s WHERE cree_par = %s AND projet_id = %s",
                    (login, old_login, projet_id),
                )
                # Mettre a jour le login + date connexion (pas nom/email/trigramme)
                conn.execute("""
                    UPDATE utilisateurs SET login = %s,
                           date_derniere_connexion = %s, date_creation = COALESCE(date_creation, %s)
                    WHERE id = %s
                """, (login, now, now, user_id))
                conn.execute(
                    "UPDATE projet_membres SET date_derniere_connexion = %s WHERE id = %s",
                    (now, placeholder["pm_id"])
                )
                conn.commit()
                return role

        # Chercher par login
        row = conn.execute("""
            SELECT u.id AS user_id, pm.role, pm.id AS pm_id
            FROM utilisateurs u
            JOIN projet_membres pm ON pm.user_id = u.id
            WHERE u.login = %s AND pm.projet_id = %s
        """, (login, projet_id)).fetchone()
        if row:
            conn.execute("""
                UPDATE utilisateurs SET date_derniere_connexion = %s,
                       date_creation = COALESCE(date_creation, %s)
                WHERE id = %s
            """, (now, now, row["user_id"]))
            conn.execute(
                "UPDATE projet_membres SET date_derniere_connexion = %s WHERE id = %s",
                (now, row["pm_id"])
            )
            conn.commit()
            return row["role"]

        # Chercher par email secondaire
        if email:
            secondary = conn.execute("""
                SELECT u.id AS user_id, u.login, u.nom, u.email, u.trigramme,
                       pm.role, pm.id AS pm_id
                FROM utilisateurs u
                JOIN projet_membres pm ON pm.user_id = u.id
                WHERE %s = ANY(string_to_array(u.emails_secondaires, ','))
                      AND pm.projet_id = %s
            """, (email, projet_id)).fetchone()
            if secondary:
                conn.execute("""
                    UPDATE utilisateurs SET date_derniere_connexion = %s,
                           date_creation = COALESCE(date_creation, %s)
                    WHERE id = %s
                """, (now, now, secondary["user_id"]))
                conn.execute(
                    "UPDATE projet_membres SET date_derniere_connexion = %s WHERE id = %s",
                    (now, secondary["pm_id"])
                )
                conn.commit()
                return {
                    "role": secondary["role"],
                    "login": secondary["login"],
                    "nom": secondary["nom"],
                    "email": secondary["email"],
                    "trigramme": secondary["trigramme"] or "",
                }

        # Pas membre de ce projet
        return None
    finally:
        conn.close()


def add_user_to_project(login, nom, email="", trigramme="", role="membre"):
    """Insere un utilisateur dans common.utilisateurs (si necessaire) et l'ajoute au projet actif."""
    from datetime import datetime
    projet_id = get_active_project_id()
    if not projet_id:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_connection()
    try:
        # Trouver ou creer l'utilisateur
        row = conn.execute(
            "SELECT id FROM utilisateurs WHERE login = %s", (login,)
        ).fetchone()
        if row:
            user_id = row['id']
            conn.execute("""
                UPDATE utilisateurs SET nom = %s, email = %s, trigramme = %s,
                       date_derniere_connexion = %s, date_creation = COALESCE(date_creation, %s)
                WHERE id = %s
            """, (nom, email or None, trigramme or None, now, now, user_id))
        else:
            row = conn.execute("""
                INSERT INTO utilisateurs (login, nom, email, trigramme, date_creation, date_derniere_connexion)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (login, nom, email or None, trigramme or None, now, now)).fetchone()
            user_id = row['id']

        # Ajouter au projet
        conn.execute("""
            INSERT INTO projet_membres (projet_id, user_id, role, date_creation, date_derniere_connexion)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (projet_id, user_id) DO NOTHING
        """, (projet_id, user_id, role, now, now))
        conn.commit()
    finally:
        conn.close()
