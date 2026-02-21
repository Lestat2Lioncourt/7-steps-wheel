"""
Detection et memorisation de l'identite utilisateur.
Sources : registre Windows (WorkplaceJoin, OneDrive Business), fichier local.
"""

import json
import os
import sys
from pathlib import Path

from app.database.db import DATA_DIR, get_connection

IDENTITY_PATH = DATA_DIR / "identity.json"


# -------------------------------------------------------------------
# Detection depuis le registre Windows
# -------------------------------------------------------------------
def detect_from_registry():
    """Detecte les identites O365 depuis le registre Windows.
    Retourne une liste de {email, nom} (peut etre vide)."""
    if sys.platform != "win32":
        return []
    try:
        import winreg
    except ImportError:
        return []

    accounts = []
    seen_emails = set()

    # 1. OneDrive Business (Business1, Business2, ...)
    i = 1
    while True:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                rf"Software\Microsoft\OneDrive\Accounts\Business{i}",
            )
            email = None
            nom = None
            try:
                email, _ = winreg.QueryValueEx(key, "UserEmail")
            except OSError:
                pass
            try:
                nom, _ = winreg.QueryValueEx(key, "UserName")
            except OSError:
                pass
            winreg.CloseKey(key)
            if email and email.lower() not in seen_emails:
                seen_emails.add(email.lower())
                accounts.append({"email": email, "nom": nom or email.split("@")[0]})
            i += 1
        except OSError:
            break

    # 2. Fallback : WorkplaceJoin
    try:
        base = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows NT\CurrentVersion\WorkplaceJoin\JoinInfo",
        )
        j = 0
        while True:
            try:
                subname = winreg.EnumKey(base, j)
                sub = winreg.OpenKey(base, subname)
                email = None
                try:
                    email, _ = winreg.QueryValueEx(sub, "UserEmail")
                except OSError:
                    pass
                winreg.CloseKey(sub)
                if email and email.lower() not in seen_emails:
                    seen_emails.add(email.lower())
                    nom = os.environ.get("USERNAME", email.split("@")[0])
                    accounts.append({"email": email, "nom": nom})
                j += 1
            except OSError:
                break
        winreg.CloseKey(base)
    except OSError:
        pass

    return accounts


# -------------------------------------------------------------------
# Stockage fichier local
# -------------------------------------------------------------------
def get_stored_identity():
    """Lit l'identite memorisee depuis identity.json.
    Retourne {login, nom, email} ou None."""
    if not IDENTITY_PATH.exists():
        return None
    try:
        with open(IDENTITY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("login") and data.get("nom"):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def save_identity(login, nom, email="", trigramme=""):
    """Sauvegarde l'identite dans identity.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {"login": login, "nom": nom, "email": email, "trigramme": trigramme}
    with open(IDENTITY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def clear_identity():
    """Supprime l'identite memorisee."""
    if IDENTITY_PATH.exists():
        IDENTITY_PATH.unlink()


# -------------------------------------------------------------------
# Trigramme
# -------------------------------------------------------------------
import re

def suggest_trigramme(nom_str):
    """Genere un trigramme a partir du nom.
    "NOM, Prenom" -> initiale prenom + 2 premieres lettres du nom (ex: PNO)
    "Prenom Nom" -> idem (ex: PNO)
    Mot seul -> 3 premieres lettres."""
    if not nom_str:
        return ""
    s = nom_str.strip()
    # Format "NOM, Prenom"
    if "," in s:
        parts = s.split(",", 1)
        nom_part = re.sub(r"[^A-Za-zÀ-ÿ]", "", parts[0].strip())
        prenom_part = re.sub(r"[^A-Za-zÀ-ÿ]", "", parts[1].strip())
        if prenom_part and nom_part:
            return (prenom_part[0] + nom_part[:2]).upper()
        if nom_part:
            return nom_part[:3].upper()
        return ""
    # Format "Prenom Nom" (au moins 2 mots)
    words = s.split()
    if len(words) >= 2:
        prenom_part = re.sub(r"[^A-Za-zÀ-ÿ]", "", words[0])
        nom_part = re.sub(r"[^A-Za-zÀ-ÿ]", "", words[-1])
        if prenom_part and nom_part:
            return (prenom_part[0] + nom_part[:2]).upper()
    # Mot seul
    clean = re.sub(r"[^A-Za-zÀ-ÿ]", "", s)
    return clean[:3].upper()


# -------------------------------------------------------------------
# Placeholder user (assignation par email)
# -------------------------------------------------------------------
def create_placeholder_user(email):
    """Cree un utilisateur placeholder a partir d'un email.
    login = partie avant @, nom = email, trigramme = NULL.
    Si le login ou l'email existe deja, retourne le login existant."""
    conn = get_connection()
    try:
        # Verifier si un utilisateur avec cet email existe deja
        row = conn.execute(
            "SELECT login FROM utilisateurs WHERE email = ?", (email,)
        ).fetchone()
        if row:
            return row["login"]

        login = email.split("@")[0].lower()
        # Verifier si le login existe deja
        row = conn.execute(
            "SELECT login FROM utilisateurs WHERE login = ?", (login,)
        ).fetchone()
        if row:
            return row["login"]

        conn.execute(
            "INSERT INTO utilisateurs (login, nom, email, trigramme, role) VALUES (?, ?, ?, NULL, 'membre')",
            (login, email, email),
        )
        conn.commit()
        return login
    finally:
        conn.close()


# -------------------------------------------------------------------
# Synchronisation avec la table utilisateurs du projet actif
# -------------------------------------------------------------------
def ensure_user_in_db(login, nom, email="", trigramme=""):
    """Verifie si l'utilisateur est membre du projet.
    - Si login existe : UPDATE nom/email/trigramme, retourne le role.
    - Si email match un placeholder (login different) : fusion, retourne le role.
    - Si n'existe pas : retourne None (pas d'auto-insert)."""
    conn = get_connection()
    try:
        # Fusion placeholder : chercher un utilisateur avec cet email mais un login different
        if email:
            placeholder = conn.execute(
                "SELECT login, role FROM utilisateurs WHERE email = ? AND login != ?",
                (email, login),
            ).fetchone()
            if placeholder:
                old_login = placeholder["login"]
                role = placeholder["role"]
                # Mettre a jour les FK dans actions
                conn.execute(
                    "UPDATE actions SET assignee_login = ? WHERE assignee_login = ?",
                    (login, old_login),
                )
                conn.execute(
                    "UPDATE actions SET cree_par = ? WHERE cree_par = ?",
                    (login, old_login),
                )
                # Mettre a jour le placeholder lui-meme
                conn.execute(
                    "UPDATE utilisateurs SET login = ?, nom = ?, trigramme = ? WHERE email = ? AND login = ?",
                    (login, nom, trigramme or None, email, old_login),
                )
                conn.commit()
                return role

        # Chercher par login
        row = conn.execute(
            "SELECT role FROM utilisateurs WHERE login = ?", (login,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE utilisateurs SET nom = ?, email = ?, trigramme = ? WHERE login = ?",
                (nom, email or None, trigramme or None, login),
            )
            conn.commit()
            return row["role"]

        # Pas membre de ce projet
        return None
    finally:
        conn.close()


def add_user_to_project(login, nom, email="", trigramme="", role="membre"):
    """Insere un utilisateur dans la table utilisateurs du projet actif."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO utilisateurs (login, nom, email, trigramme, role) VALUES (?, ?, ?, ?, ?)",
            (login, nom, email or None, trigramme or None, role),
        )
        conn.commit()
    finally:
        conn.close()
