"""
Couche service : CRUD actions pour le Kanban.
Supporte la hierarchie parent/enfant (taches chapeau).
Adapte pour PostgreSQL (psycopg3) avec schema client + common.
"""

from datetime import date
from app.database.db import get_connection, get_active_project_id

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
    projet_id = get_active_project_id()
    rows = conn.execute(f"""
        SELECT a.id, a.titre, a.description, a.niveau,
               a.indicateur_id, a.categorie_id,
               a.etape, e.nom AS etape_nom,
               a.assignee_login, u.nom AS assignee_nom, u.trigramme AS assignee_trigramme,
               a.statut, a.commentaire,
               a.date_debut, a.date_fin,
               a.parent_id,
               (SELECT COUNT(*) FROM actions ch WHERE ch.parent_id = a.id) AS children_count,
               a.cree_par, a.date_creation, a.date_modification,
               c.nom AS categorie_nom
        FROM actions a
        JOIN etapes e ON a.etape = e.numero
        JOIN utilisateurs u ON a.assignee_login = u.login
        LEFT JOIN categories c ON a.categorie_id = c.id
        WHERE a.projet_id = %s AND ({where_clause})
        ORDER BY a.date_creation DESC
    """, (projet_id, *params)).fetchall()
    return [dict(r) for r in rows]


def _aggregate_status(child_statuses):
    """Calcule le statut parent depuis les statuts enfants."""
    s = set(child_statuses)
    if len(s) == 1:
        return s.pop()
    return 'en_cours'


def compute_parent_status_dates(actions_list):
    """Pour chaque action chapeau, recalcule statut et dates depuis ses enfants.
    Travaille recursivement : feuilles d'abord, puis remontee vers les parents."""
    if not actions_list:
        return actions_list

    by_id = {a['id']: a for a in actions_list}
    children_by_parent = {}
    for a in actions_list:
        pid = a.get('parent_id')
        if pid and pid in by_id:
            children_by_parent.setdefault(pid, []).append(a)

    computed = {}

    def compute(action_id):
        if action_id in computed:
            return computed[action_id]
        a = by_id[action_id]
        kids = children_by_parent.get(action_id, [])
        if not kids and a.get('children_count', 0) == 0:
            result = (a['statut'], a.get('date_debut'), a.get('date_fin'))
            computed[action_id] = result
            return result
        if not kids and a.get('children_count', 0) > 0:
            result = _compute_from_db(action_id)
            computed[action_id] = result
            return result
        child_results = [compute(c['id']) for c in kids]
        statuses = [r[0] for r in child_results]
        dates_debut = [r[1] for r in child_results if r[1]]
        dates_fin = [r[2] for r in child_results if r[2]]
        agg_status = _aggregate_status(statuses)
        agg_debut = min(dates_debut) if dates_debut else None
        agg_fin = max(dates_fin) if dates_fin else None
        result = (agg_status, agg_debut, agg_fin)
        computed[action_id] = result
        return result

    for a in actions_list:
        if a.get('children_count', 0) > 0:
            status, d_debut, d_fin = compute(a['id'])
            a['statut_computed'] = status
            a['date_debut_computed'] = d_debut
            a['date_fin_computed'] = d_fin
        else:
            a['statut_computed'] = a['statut']
            a['date_debut_computed'] = a.get('date_debut')
            a['date_fin_computed'] = a.get('date_fin')

    return actions_list


def _compute_from_db(action_id):
    """Calcule statut/dates d'un parent en lisant tous ses descendants depuis la DB."""
    conn = get_connection()
    try:
        leaves = _collect_leaf_statuses(conn, action_id)
        if not leaves:
            row = conn.execute(
                "SELECT statut, date_debut, date_fin FROM actions WHERE id = %s",
                (action_id,)
            ).fetchone()
            if row:
                return (row['statut'], row['date_debut'], row['date_fin'])
            return ('a_faire', None, None)
        statuses = [l[0] for l in leaves]
        dates_debut = [l[1] for l in leaves if l[1]]
        dates_fin = [l[2] for l in leaves if l[2]]
        return (
            _aggregate_status(statuses),
            min(dates_debut) if dates_debut else None,
            max(dates_fin) if dates_fin else None,
        )
    finally:
        conn.close()


def _collect_leaf_statuses(conn, parent_id):
    """Collecte recursivement les (statut, date_debut, date_fin) des feuilles sous parent_id."""
    children = conn.execute(
        "SELECT id, statut, date_debut, date_fin FROM actions WHERE parent_id = %s",
        (parent_id,)
    ).fetchall()
    if not children:
        return []
    results = []
    for child in children:
        grandchildren = conn.execute(
            "SELECT COUNT(*) AS cnt FROM actions WHERE parent_id = %s", (child['id'],)
        ).fetchone()['cnt']
        if grandchildren == 0:
            results.append((child['statut'], child['date_debut'], child['date_fin']))
        else:
            results.extend(_collect_leaf_statuses(conn, child['id']))
    return results


def _group_by_status(actions_list):
    """Groupe une liste d'actions par statut et retourne columns + counts + users."""
    projet_id = get_active_project_id()
    conn = get_connection()
    try:
        users = conn.execute("""
            SELECT u.login, u.nom, u.email, u.trigramme
            FROM utilisateurs u
            JOIN projet_membres pm ON pm.user_id = u.id
            WHERE pm.projet_id = %s
            ORDER BY u.nom
        """, (projet_id,)).fetchall()
        users = [dict(u) for u in users]
    finally:
        conn.close()

    columns = {s: [] for s in KANBAN_COLUMNS}
    for action in actions_list:
        st = action.get('statut_computed', action['statut'])
        columns[st].append(action)

    counts = {s: len(columns[s]) for s in KANBAN_COLUMNS}

    return {
        'columns': columns,
        'counts': counts,
        'users': users,
    }


def get_actions_for_indicator(indicateur_id, categorie_id, parent_id=None):
    """Retourne les actions de l'indicateur + categorie heritee + global heritees."""
    conn = get_connection()
    try:
        if parent_id is not None:
            actions = _fetch_actions(conn,
                "a.parent_id = %s",
                (parent_id,))
        else:
            actions = _fetch_actions(conn,
                """((a.niveau = 'indicateur' AND a.indicateur_id = %s)
                OR (a.niveau = 'categorie' AND a.categorie_id = %s)
                OR (a.niveau = 'global'))
                AND a.parent_id IS NULL""",
                (indicateur_id, categorie_id))
    finally:
        conn.close()
    compute_parent_status_dates(actions)
    return _group_by_status(actions)


def get_actions_for_categorie(categorie_id, parent_id=None):
    """Retourne les actions de la categorie + global heritees."""
    conn = get_connection()
    try:
        if parent_id is not None:
            actions = _fetch_actions(conn,
                "a.parent_id = %s",
                (parent_id,))
        else:
            actions = _fetch_actions(conn,
                """((a.niveau = 'categorie' AND a.categorie_id = %s)
                OR (a.niveau = 'global'))
                AND a.parent_id IS NULL""",
                (categorie_id,))
    finally:
        conn.close()
    compute_parent_status_dates(actions)
    return _group_by_status(actions)


def get_actions_for_global(parent_id=None):
    """Retourne uniquement les actions globales."""
    conn = get_connection()
    try:
        if parent_id is not None:
            actions = _fetch_actions(conn,
                "a.parent_id = %s",
                (parent_id,))
        else:
            actions = _fetch_actions(conn,
                "a.niveau = 'global' AND a.parent_id IS NULL", ())
    finally:
        conn.close()
    compute_parent_status_dates(actions)
    return _group_by_status(actions)


def get_parent_breadcrumb(action_id):
    """Retourne la liste [{'id': ..., 'titre': ...}, ...] du parent le plus haut vers action_id."""
    conn = get_connection()
    try:
        chain = []
        current_id = action_id
        while current_id is not None:
            row = conn.execute(
                "SELECT id, titre, parent_id FROM actions WHERE id = %s",
                (current_id,)
            ).fetchone()
            if not row:
                break
            chain.append({'id': row['id'], 'titre': row['titre']})
            current_id = row['parent_id']
        chain.reverse()
        return chain
    finally:
        conn.close()


def create_action(data):
    """Cree une action. data = {titre, niveau, indicateur_id, categorie_id,
       etape, assignee_login, cree_par, description, commentaire, parent_id}"""
    projet_id = get_active_project_id()
    conn = get_connection()
    try:
        row = conn.execute("""
            INSERT INTO actions
                (projet_id, titre, description, niveau, indicateur_id, categorie_id,
                 etape, assignee_login, statut, commentaire,
                 date_debut, date_fin, parent_id, cree_par, date_creation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'a_faire', %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            projet_id,
            data['titre'],
            data.get('description'),
            data['niveau'],
            data.get('indicateur_id'),
            data.get('categorie_id'),
            data['etape'],
            data['assignee_login'],
            data.get('commentaire'),
            data.get('date_debut') or None,
            data.get('date_fin') or None,
            data.get('parent_id') or None,
            data.get('cree_par', 'admin'),
            date.today().isoformat(),
        )).fetchone()
        conn.commit()
        return row['id']
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
            SET statut = %s, date_modification = %s
            WHERE id = %s
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
            SET titre = %s, description = %s, assignee_login = %s,
                etape = %s, commentaire = %s,
                date_debut = %s, date_fin = %s,
                date_modification = %s
            WHERE id = %s
        """, (
            data['titre'],
            data.get('description'),
            data['assignee_login'],
            data['etape'],
            data.get('commentaire'),
            data.get('date_debut') or None,
            data.get('date_fin') or None,
            date.today().isoformat(),
            action_id,
        ))
        conn.commit()
    finally:
        conn.close()


def delete_action(action_id):
    """Supprime une action. Refuse si elle a des enfants."""
    conn = get_connection()
    try:
        count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM actions WHERE parent_id = %s", (action_id,)
        ).fetchone()['cnt']
        if count > 0:
            raise ValueError("Supprimez d'abord les sous-taches")
        conn.execute("DELETE FROM actions WHERE id = %s", (action_id,))
        conn.commit()
    finally:
        conn.close()
