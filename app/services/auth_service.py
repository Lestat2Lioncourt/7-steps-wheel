"""
Service d'authentification : login/mdp, invitations, setup wizard, SSO Microsoft (optionnel).
Hash via werkzeug (PBKDF2, inclus avec Flask).
MSAL importe conditionnellement : absence = SSO silencieusement desactive.
"""

import os
import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash, check_password_hash

from app.database.db import get_connection_common

try:
    import msal
    _MSAL_AVAILABLE = True
except ImportError:
    _MSAL_AVAILABLE = False


# -------------------------------------------------------------------
# Verification mot de passe
# -------------------------------------------------------------------

def verify_password(login_or_email, password):
    """Cherche par email/login/emails_secondaires, verifie le hash.
    Retourne dict user {id, login, nom, email, trigramme} ou None."""
    conn = get_connection_common()
    try:
        row = conn.execute("""
            SELECT id, login, nom, email, trigramme, hash_mdp
            FROM utilisateurs
            WHERE login = %s OR email = %s
               OR %s = ANY(string_to_array(emails_secondaires, ','))
        """, (login_or_email, login_or_email, login_or_email)).fetchone()
        if not row or not row['hash_mdp']:
            return None
        if not check_password_hash(row['hash_mdp'], password):
            return None
        return {
            'id': row['id'],
            'login': row['login'],
            'nom': row['nom'],
            'email': row['email'] or '',
            'trigramme': row['trigramme'] or '',
        }
    finally:
        conn.close()


def set_password(user_id, password):
    """Hash + UPDATE hash_mdp."""
    h = generate_password_hash(password)
    conn = get_connection_common()
    try:
        conn.execute(
            "UPDATE utilisateurs SET hash_mdp = %s WHERE id = %s",
            (h, user_id)
        )
        conn.commit()
    finally:
        conn.close()


# -------------------------------------------------------------------
# Invitations
# -------------------------------------------------------------------

def create_invitation(user_id, created_by, expiry_days=7):
    """Genere un token d'invitation pour un utilisateur.
    Invalide les anciens tokens non utilises du meme user.
    Retourne le token."""
    token = secrets.token_urlsafe(32)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expires = (datetime.now() + timedelta(days=expiry_days)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection_common()
    try:
        # Invalider les anciens tokens non utilises
        conn.execute(
            "DELETE FROM invitations WHERE user_id = %s AND used_at IS NULL",
            (user_id,)
        )
        conn.execute("""
            INSERT INTO invitations (user_id, token, created_at, expires_at, created_by)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, token, now, expires, created_by))
        conn.commit()
        return token
    finally:
        conn.close()


def validate_invitation(token):
    """Verifie token existe, non utilise, non expire.
    Retourne dict {id, user_id, user_nom, user_email, user_trigramme} ou None."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection_common()
    try:
        row = conn.execute("""
            SELECT i.id, i.user_id, u.nom, u.email, u.trigramme
            FROM invitations i
            JOIN utilisateurs u ON u.id = i.user_id
            WHERE i.token = %s AND i.used_at IS NULL AND i.expires_at > %s
        """, (token, now)).fetchone()
        if not row:
            return None
        return {
            'id': row['id'],
            'user_id': row['user_id'],
            'user_nom': row['nom'] or '',
            'user_email': row['email'] or '',
            'user_trigramme': row['trigramme'] or '',
        }
    finally:
        conn.close()


def consume_invitation(invitation_id, password, nom=None, trigramme=None):
    """Marque l'invitation comme utilisee, set le mot de passe,
    met a jour nom/trigramme si fournis. Retourne dict user."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    h = generate_password_hash(password)
    conn = get_connection_common()
    try:
        inv = conn.execute(
            "SELECT user_id FROM invitations WHERE id = %s", (invitation_id,)
        ).fetchone()
        if not inv:
            return None
        user_id = inv['user_id']

        # Marquer comme utilisee
        conn.execute(
            "UPDATE invitations SET used_at = %s WHERE id = %s",
            (now, invitation_id)
        )

        # Mettre a jour l'utilisateur
        updates = ["hash_mdp = %s"]
        params = [h]
        if nom:
            updates.append("nom = %s")
            params.append(nom)
        if trigramme:
            updates.append("trigramme = %s")
            params.append(trigramme.upper())
        params.append(user_id)
        conn.execute(
            f"UPDATE utilisateurs SET {', '.join(updates)} WHERE id = %s",
            params
        )
        conn.commit()

        row = conn.execute(
            "SELECT id, login, nom, email, trigramme FROM utilisateurs WHERE id = %s",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# -------------------------------------------------------------------
# Setup wizard (premier lancement)
# -------------------------------------------------------------------

def is_setup_needed():
    """True si aucun utilisateur n'existe dans la base."""
    conn = get_connection_common()
    try:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM utilisateurs").fetchone()
        return row['cnt'] == 0
    finally:
        conn.close()


def create_initial_admin(email, nom, trigramme, password):
    """Cree le premier utilisateur avec mot de passe.
    Retourne dict user {id, login, nom, email, trigramme}."""
    h = generate_password_hash(password)
    login = email.split('@')[0].lower()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_connection_common()
    try:
        row = conn.execute("""
            INSERT INTO utilisateurs (login, nom, email, trigramme, hash_mdp, date_creation)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, login, nom, email, trigramme
        """, (login, nom, email, trigramme or None, h, now)).fetchone()
        conn.commit()
        return dict(row)
    finally:
        conn.close()


# -------------------------------------------------------------------
# SSO Microsoft (MSAL) — actif seulement si variables Azure presentes
# -------------------------------------------------------------------

def is_sso_enabled():
    """True si AZURE_CLIENT_ID, AZURE_TENANT_ID et AZURE_CLIENT_SECRET sont definis."""
    return bool(
        _MSAL_AVAILABLE
        and os.environ.get('AZURE_CLIENT_ID')
        and os.environ.get('AZURE_TENANT_ID')
        and os.environ.get('AZURE_CLIENT_SECRET')
    )


def _get_msal_app():
    """Cree une instance ConfidentialClientApplication."""
    if not is_sso_enabled():
        return None
    return msal.ConfidentialClientApplication(
        client_id=os.environ['AZURE_CLIENT_ID'],
        client_credential=os.environ['AZURE_CLIENT_SECRET'],
        authority=f"https://login.microsoftonline.com/{os.environ['AZURE_TENANT_ID']}",
    )


def get_msal_auth_url(redirect_uri, state=None):
    """Initie le flow OAuth2 authorization code.
    Retourne (auth_url, flow) ou (None, None) si SSO desactive."""
    app = _get_msal_app()
    if not app:
        return None, None
    flow = app.initiate_auth_code_flow(
        scopes=["User.Read"],
        redirect_uri=redirect_uri,
        state=state,
    )
    return flow.get("auth_uri"), flow


def complete_msal_flow(flow, auth_response):
    """Complete le flow OAuth2. Retourne les claims Microsoft ou None."""
    app = _get_msal_app()
    if not app:
        return None
    result = app.acquire_token_by_auth_code_flow(flow, auth_response)
    if "id_token_claims" in result:
        return result["id_token_claims"]
    return None


def find_user_by_email(email):
    """Cherche dans common.utilisateurs par email ou emails_secondaires.
    Retourne dict user ou None."""
    conn = get_connection_common()
    try:
        row = conn.execute("""
            SELECT id, login, nom, email, trigramme
            FROM utilisateurs
            WHERE email = %s
               OR %s = ANY(string_to_array(emails_secondaires, ','))
        """, (email, email)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()
