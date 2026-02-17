"""
Couche service : CRUD actions pour le Kanban.
"""

from datetime import date
from app.database.db import get_connection

# Colonnes Kanban ordonnees
KANBAN_COLUMNS = ['a_faire', 'en_cours', 'a_valider', 'termine', 'rejete']

KANBAN_LABELS = {
    'a_faire': 'A faire',
    'en_cours': 'En cours',
    'a_valider': 'A valider',
    'termine': 'Termine',
    'rejete': 'Rejete',
}


def _fetch_actions(conn, where_clause, params):
    """Requete commune pour recuperer des actions avec JOIN etapes + utilisateurs."""
    rows = conn.execute(f"""
        SELECT a.id, a.titre, a.description, a.niveau,
               a.indicateur_id, a.categorie_id,
               a.etape, e.nom as etape_nom,
               a.assignee_login, u.nom as assignee_nom, u.trigramme as assignee_trigramme,
               a.statut, a.commentaire, a.cree_par,
               a.date_creation, a.date_modification,
               c.nom as categorie_nom
        FROM actions a
        JOIN etapes e ON a.etape = e.numero
        JOIN utilisateurs u ON a.assignee_login = u.login
        LEFT JOIN categories c ON a.categorie_id = c.id
        WHERE {where_clause}
        ORDER BY a.date_creation DESC
    """, params).fetchall()
    return [dict(r) for r in rows]


def _group_by_status(actions_list):
    """Groupe une liste d'actions par statut et retourne columns + counts + users."""
    conn = get_connection()
    try:
        users = conn.execute(
            "SELECT login, nom, email, trigramme FROM utilisateurs ORDER BY nom"
        ).fetchall()
        users = [dict(u) for u in users]
    finally:
        conn.close()

    columns = {s: [] for s in KANBAN_COLUMNS}
    for action in actions_list:
        columns[action['statut']].append(action)

    counts = {s: len(columns[s]) for s in KANBAN_COLUMNS}

    return {
        'columns': columns,
        'counts': counts,
        'users': users,
    }


def get_actions_for_indicator(indicateur_id, categorie_id):
    """Retourne les actions de l'indicateur + categorie heritee + global heritees."""
    conn = get_connection()
    try:
        actions = _fetch_actions(conn,
            """(a.niveau = 'indicateur' AND a.indicateur_id = ?)
            OR (a.niveau = 'categorie' AND a.categorie_id = ?)
            OR (a.niveau = 'global')""",
            (indicateur_id, categorie_id))
    finally:
        conn.close()
    return _group_by_status(actions)


def get_actions_for_categorie(categorie_id):
    """Retourne les actions de la categorie + global heritees."""
    conn = get_connection()
    try:
        actions = _fetch_actions(conn,
            """(a.niveau = 'categorie' AND a.categorie_id = ?)
            OR (a.niveau = 'global')""",
            (categorie_id,))
    finally:
        conn.close()
    return _group_by_status(actions)


def get_actions_for_global():
    """Retourne uniquement les actions globales."""
    conn = get_connection()
    try:
        actions = _fetch_actions(conn,
            "a.niveau = 'global'", ())
    finally:
        conn.close()
    return _group_by_status(actions)


def create_action(data):
    """Cree une action. data = {titre, niveau, indicateur_id, categorie_id,
       etape, assignee_login, cree_par, description, commentaire}"""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO actions
                (titre, description, niveau, indicateur_id, categorie_id,
                 etape, assignee_login, statut, commentaire, cree_par, date_creation)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'a_faire', ?, ?, ?)
        """, (
            data['titre'],
            data.get('description'),
            data['niveau'],
            data.get('indicateur_id'),
            data.get('categorie_id'),
            data['etape'],
            data['assignee_login'],
            data.get('commentaire'),
            data.get('cree_par', 'admin'),
            date.today().isoformat(),
        ))
        conn.commit()
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    finally:
        conn.close()


def update_action_status(action_id, new_status):
    """Change le statut + met a jour date_modification."""
    if new_status not in KANBAN_COLUMNS:
        raise ValueError(f"Statut invalide: {new_status}")
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE actions
            SET statut = ?, date_modification = ?
            WHERE id = ?
        """, (new_status, date.today().isoformat(), action_id))
        conn.commit()
    finally:
        conn.close()


def update_action(action_id, data):
    """Met a jour titre, description, assignee_login, etape, commentaire."""
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE actions
            SET titre = ?, description = ?, assignee_login = ?,
                etape = ?, commentaire = ?, date_modification = ?
            WHERE id = ?
        """, (
            data['titre'],
            data.get('description'),
            data['assignee_login'],
            data['etape'],
            data.get('commentaire'),
            date.today().isoformat(),
            action_id,
        ))
        conn.commit()
    finally:
        conn.close()


def delete_action(action_id):
    """Supprime une action."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM actions WHERE id = ?", (action_id,))
        conn.commit()
    finally:
        conn.close()
