"""
Couche service : requetes SQL et logique d'agregation "le pire l'emporte".
"""

from app.database.db import get_connection

# Mapping severite -> nom de couleur JS
_SEVERITE_TO_COLOR = {0: 'grey', 1: 'green', 2: 'yellow', 3: 'orange', 4: 'red'}
_COLOR_TO_SEVERITE = {v: k for k, v in _SEVERITE_TO_COLOR.items()}


def _row_to_dict(row):
    """Convertit un sqlite3.Row en dict."""
    return dict(row) if row else None


def _worst(severities):
    """Retourne la couleur la pire (severite max) d'une liste de severites."""
    if not severities:
        return 'grey'
    return _SEVERITE_TO_COLOR.get(max(severities), 'grey')


def _step_worst_color(ie_row):
    """Calcule la couleur effective d'une ligne indicateur_etapes (pire des 3 couches)."""
    sevs = []
    for col in ('sev_global', 'sev_categorie', 'sev_indicateur'):
        v = ie_row[col]
        if v is not None:
            sevs.append(v)
    return _worst(sevs) if sevs else 'grey'


def _color_name(statut_id, statuts_map):
    """Retourne le nom de couleur JS pour un statut_id donne."""
    if statut_id is None:
        return None
    info = statuts_map.get(statut_id)
    if info:
        return _SEVERITE_TO_COLOR.get(info['severite'], 'grey')
    return None


# -------------------------------------------------------------------
# Chargement de la table de reference statuts_etape
# -------------------------------------------------------------------
def get_statuts_map():
    """Retourne {id: {intitule, couleur, severite, color_name}}."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, intitule, couleur, severite FROM statuts_etape").fetchall()
        return {
            r['id']: {
                'intitule': r['intitule'],
                'couleur': r['couleur'],
                'severite': r['severite'],
                'color_name': _SEVERITE_TO_COLOR.get(r['severite'], 'grey')
            }
            for r in rows
        }
    finally:
        conn.close()


# -------------------------------------------------------------------
# Vue Globale
# -------------------------------------------------------------------
def get_global_data():
    """
    Retourne les donnees pour la vue globale :
    - categories : liste de {id, nom, count, worst}
    - wheel_colors : array de 7 couleurs (pire de tous les indicateurs par etape)
    - status_counts : {green: N, ...}
    - total : nombre total d'indicateurs
    """
    conn = get_connection()
    try:
        statuts = get_statuts_map()

        # Categories avec comptage
        cats = conn.execute("""
            SELECT c.id, c.nom, c.ordre, COUNT(i.id) as count
            FROM categories c
            LEFT JOIN indicateurs i ON i.categorie_id = c.id
            GROUP BY c.id
            ORDER BY c.ordre
        """).fetchall()

        # Toutes les indicateur_etapes avec severites jointes
        ie_rows = conn.execute("""
            SELECT ie.indicateur_id, ie.etape,
                   sg.severite as sev_global,
                   sc.severite as sev_categorie,
                   si.severite as sev_indicateur
            FROM indicateur_etapes ie
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
        """).fetchall()

        # Couleur pire par indicateur (sur toutes ses etapes)
        ind_worst = {}  # indicateur_id -> max severite
        # Couleur pire par etape (sur tous les indicateurs)
        step_worst = {}  # etape -> max severite
        # Couleur pire par indicateur par etape
        ind_step_color = {}  # (indicateur_id, etape) -> color

        for row in ie_rows:
            sev = _step_worst_color_sev(row)
            color = _SEVERITE_TO_COLOR.get(sev, 'grey')

            iid = row['indicateur_id']
            step = row['etape']

            ind_step_color[(iid, step)] = color

            if iid not in ind_worst or sev > ind_worst[iid]:
                ind_worst[iid] = sev
            if step not in step_worst or sev > step_worst[step]:
                step_worst[step] = sev

        # Couleur pire par categorie
        indicateurs = conn.execute(
            "SELECT id, categorie_id FROM indicateurs"
        ).fetchall()
        cat_inds = {}  # categorie_id -> [indicateur_ids]
        for ind in indicateurs:
            cat_inds.setdefault(ind['categorie_id'], []).append(ind['id'])

        categories = []
        for cat in cats:
            inds = cat_inds.get(cat['id'], [])
            if inds:
                worst_sev = max(ind_worst.get(iid, 0) for iid in inds)
            else:
                worst_sev = 0
            categories.append({
                'id': cat['id'],
                'nom': cat['nom'],
                'count': cat['count'],
                'worst': _SEVERITE_TO_COLOR.get(worst_sev, 'grey')
            })

        # Wheel : 7 couleurs
        wheel_colors = []
        for step_num in range(1, 8):
            sev = step_worst.get(step_num, 0)
            wheel_colors.append(_SEVERITE_TO_COLOR.get(sev, 'grey'))

        # Compteurs globaux : compter les indicateurs par leur pire couleur
        status_counts = {'green': 0, 'yellow': 0, 'orange': 0, 'red': 0, 'grey': 0}
        for iid, sev in ind_worst.items():
            c = _SEVERITE_TO_COLOR.get(sev, 'grey')
            status_counts[c] = status_counts.get(c, 0) + 1

        total = len(ind_worst)

        return {
            'categories': categories,
            'wheel_colors': wheel_colors,
            'status_counts': status_counts,
            'total': total
        }
    finally:
        conn.close()


def _step_worst_color_sev(ie_row):
    """Retourne la severite max d'une ligne indicateur_etapes."""
    sevs = []
    for col in ('sev_global', 'sev_categorie', 'sev_indicateur'):
        v = ie_row[col]
        if v is not None:
            sevs.append(v)
    return max(sevs) if sevs else 0


# -------------------------------------------------------------------
# Vue Categorie
# -------------------------------------------------------------------
def get_categorie_data(categorie_id):
    """
    Retourne les donnees pour la vue categorie :
    - categorie : {id, nom}
    - categories : toutes les categories (pour sidebar)
    - indicateurs : liste de {id, code, description, type, etat, worst}
    - wheel_colors : 7 couleurs (pire des indicateurs de cette categorie par etape)
    - status_counts : {green: N, ...}
    """
    conn = get_connection()
    try:
        statuts = get_statuts_map()

        cat = conn.execute(
            "SELECT id, nom FROM categories WHERE id = ?", (categorie_id,)
        ).fetchone()
        if not cat:
            return None

        # Toutes les categories (sidebar)
        all_cats_rows = conn.execute("""
            SELECT c.id, c.nom, c.ordre, COUNT(i.id) as count
            FROM categories c
            LEFT JOIN indicateurs i ON i.categorie_id = c.id
            GROUP BY c.id ORDER BY c.ordre
        """).fetchall()

        # Indicateurs de la categorie
        inds = conn.execute("""
            SELECT i.id, i.code, i.description, t.intitule as type, e.intitule as etat,
                   t.couleur as type_couleur
            FROM indicateurs i
            JOIN types_indicateur t ON i.type_id = t.id
            JOIN etats_indicateur e ON i.etat_id = e.id
            WHERE i.categorie_id = ?
            ORDER BY i.code
        """, (categorie_id,)).fetchall()

        ind_ids = [r['id'] for r in inds]

        # indicateur_etapes pour ces indicateurs
        if ind_ids:
            placeholders = ','.join('?' * len(ind_ids))
            ie_rows = conn.execute(f"""
                SELECT ie.indicateur_id, ie.etape,
                       sg.severite as sev_global,
                       sc.severite as sev_categorie,
                       si.severite as sev_indicateur
                FROM indicateur_etapes ie
                LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
                LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
                LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
                WHERE ie.indicateur_id IN ({placeholders})
            """, ind_ids).fetchall()
        else:
            ie_rows = []

        # Couleur pire par indicateur et par etape
        ind_worst = {}
        step_worst = {}
        for row in ie_rows:
            sev = _step_worst_color_sev(row)
            iid = row['indicateur_id']
            step = row['etape']
            if iid not in ind_worst or sev > ind_worst[iid]:
                ind_worst[iid] = sev
            if step not in step_worst or sev > step_worst[step]:
                step_worst[step] = sev

        indicateurs = []
        for ind in inds:
            worst_sev = ind_worst.get(ind['id'], 0)
            indicateurs.append({
                'id': ind['id'],
                'code': ind['code'],
                'description': ind['description'],
                'type': ind['type'],
                'etat': ind['etat'],
                'type_couleur': ind['type_couleur'],
                'worst': _SEVERITE_TO_COLOR.get(worst_sev, 'grey')
            })

        wheel_colors = []
        for step_num in range(1, 8):
            sev = step_worst.get(step_num, 0)
            wheel_colors.append(_SEVERITE_TO_COLOR.get(sev, 'grey'))

        status_counts = {'green': 0, 'yellow': 0, 'orange': 0, 'red': 0, 'grey': 0}
        for iid, sev in ind_worst.items():
            c = _SEVERITE_TO_COLOR.get(sev, 'grey')
            status_counts[c] = status_counts.get(c, 0) + 1

        # Calculer worst par categorie (pour sidebar)
        # On a besoin des indicateur_etapes de toutes les categories
        all_ie = conn.execute("""
            SELECT ie.indicateur_id, i.categorie_id,
                   sg.severite as sev_global,
                   sc.severite as sev_categorie,
                   si.severite as sev_indicateur
            FROM indicateur_etapes ie
            JOIN indicateurs i ON ie.indicateur_id = i.id
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
        """).fetchall()

        cat_worst = {}
        for row in all_ie:
            sev = _step_worst_color_sev(row)
            cid = row['categorie_id']
            if cid not in cat_worst or sev > cat_worst[cid]:
                cat_worst[cid] = sev

        all_cats = []
        for c in all_cats_rows:
            all_cats.append({
                'id': c['id'],
                'nom': c['nom'],
                'count': c['count'],
                'worst': _SEVERITE_TO_COLOR.get(cat_worst.get(c['id'], 0), 'grey')
            })

        return {
            'categorie': {'id': cat['id'], 'nom': cat['nom']},
            'categories': all_cats,
            'indicateurs': indicateurs,
            'wheel_colors': wheel_colors,
            'status_counts': status_counts,
            'total': len(indicateurs)
        }
    finally:
        conn.close()


# -------------------------------------------------------------------
# Vue Indicateur
# -------------------------------------------------------------------
def get_indicateur_data(indicateur_id):
    """
    Retourne les donnees pour la vue indicateur :
    - indicateur : proprietes completes
    - categorie : {id, nom}
    - step_data : array de 7 objets avec les 3 couches
    - wheel_colors : 7 couleurs (pire des 3 couches par etape)
    - status_counts : compteur par couleur sur les 7 etapes
    - siblings : indicateurs de la meme categorie (pour sidebar)
    - categories : toutes les categories (pour sidebar)
    """
    conn = get_connection()
    try:
        statuts = get_statuts_map()

        ind = conn.execute("""
            SELECT i.*, t.intitule as type, e.intitule as etat,
                   t.couleur as type_couleur, e.couleur as etat_couleur
            FROM indicateurs i
            JOIN types_indicateur t ON i.type_id = t.id
            JOIN etats_indicateur e ON i.etat_id = e.id
            WHERE i.id = ?
        """, (indicateur_id,)).fetchone()
        if not ind:
            return None

        cat = conn.execute(
            "SELECT id, nom FROM categories WHERE id = ?", (ind['categorie_id'],)
        ).fetchone()

        # 7 etapes de cet indicateur
        ie_rows = conn.execute("""
            SELECT ie.etape,
                   ie.statut_global_id, ie.commentaire_global,
                   ie.statut_categorie_id, ie.commentaire_categorie,
                   ie.statut_indicateur_id, ie.commentaire_indicateur,
                   sg.severite as sev_global,
                   sc.severite as sev_categorie,
                   si.severite as sev_indicateur
            FROM indicateur_etapes ie
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
            WHERE ie.indicateur_id = ?
            ORDER BY ie.etape
        """, (indicateur_id,)).fetchall()

        # Construire step_data pour JS (7 objets avec 3 couches)
        step_data = []
        wheel_colors = []
        status_counts = {'green': 0, 'yellow': 0, 'orange': 0, 'red': 0, 'grey': 0}

        for step_num in range(1, 8):
            row = None
            for r in ie_rows:
                if r['etape'] == step_num:
                    row = r
                    break

            if row:
                sd = {
                    'global': {
                        'color': _color_name(row['statut_global_id'], statuts),
                        'comment': row['commentaire_global'] or ''
                    },
                    'categorie': {
                        'color': _color_name(row['statut_categorie_id'], statuts),
                        'comment': row['commentaire_categorie'] or ''
                    },
                    'indicateur': {
                        'color': _color_name(row['statut_indicateur_id'], statuts),
                        'comment': row['commentaire_indicateur'] or ''
                    }
                }
                sev = _step_worst_color_sev(row)
                wc = _SEVERITE_TO_COLOR.get(sev, 'grey')
            else:
                sd = {
                    'global': {'color': None, 'comment': ''},
                    'categorie': {'color': None, 'comment': ''},
                    'indicateur': {'color': None, 'comment': ''}
                }
                wc = 'grey'

            step_data.append(sd)
            wheel_colors.append(wc)
            status_counts[wc] += 1

        # Indicateurs de la meme categorie (sidebar)
        siblings_rows = conn.execute("""
            SELECT i.id, i.code, i.description
            FROM indicateurs i
            WHERE i.categorie_id = ?
            ORDER BY i.code
        """, (ind['categorie_id'],)).fetchall()

        # Calculer worst pour chaque sibling
        sib_ids = [r['id'] for r in siblings_rows]
        sib_worst = {}
        if sib_ids:
            placeholders = ','.join('?' * len(sib_ids))
            sib_ie = conn.execute(f"""
                SELECT ie.indicateur_id,
                       sg.severite as sev_global,
                       sc.severite as sev_categorie,
                       si.severite as sev_indicateur
                FROM indicateur_etapes ie
                LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
                LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
                LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
                WHERE ie.indicateur_id IN ({placeholders})
            """, sib_ids).fetchall()
            for r in sib_ie:
                sev = _step_worst_color_sev(r)
                iid = r['indicateur_id']
                if iid not in sib_worst or sev > sib_worst[iid]:
                    sib_worst[iid] = sev

        siblings = []
        for s in siblings_rows:
            siblings.append({
                'id': s['id'],
                'code': s['code'],
                'description': s['description'],
                'worst': _SEVERITE_TO_COLOR.get(sib_worst.get(s['id'], 0), 'grey')
            })

        # Toutes categories (sidebar)
        all_cats_rows = conn.execute("""
            SELECT c.id, c.nom, c.ordre
            FROM categories c ORDER BY c.ordre
        """).fetchall()

        all_ie = conn.execute("""
            SELECT ie.indicateur_id, i.categorie_id,
                   sg.severite as sev_global,
                   sc.severite as sev_categorie,
                   si.severite as sev_indicateur
            FROM indicateur_etapes ie
            JOIN indicateurs i ON ie.indicateur_id = i.id
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
        """).fetchall()

        cat_worst = {}
        for r in all_ie:
            sev = _step_worst_color_sev(r)
            cid = r['categorie_id']
            if cid not in cat_worst or sev > cat_worst[cid]:
                cat_worst[cid] = sev

        all_cats = []
        for c in all_cats_rows:
            all_cats.append({
                'id': c['id'],
                'nom': c['nom'],
                'worst': _SEVERITE_TO_COLOR.get(cat_worst.get(c['id'], 0), 'grey')
            })

        # Worst global de l'indicateur
        ind_worst_sev = max(
            (_step_worst_color_sev(r) for r in ie_rows),
            default=0
        )

        indicateur = {
            'id': ind['id'],
            'code': ind['code'],
            'description': ind['description'],
            'chapitre': ind['chapitre'],
            'categorie_id': ind['categorie_id'],
            'type': ind['type'],
            'type_couleur': ind['type_couleur'],
            'etat': ind['etat'],
            'etat_couleur': ind['etat_couleur'],
            'ciblage': ind['ciblage'],
            'conformite': ind['conformite'],
            'worst': _SEVERITE_TO_COLOR.get(ind_worst_sev, 'grey')
        }

        return {
            'indicateur': indicateur,
            'categorie': {'id': cat['id'], 'nom': cat['nom']},
            'step_data': step_data,
            'wheel_colors': wheel_colors,
            'status_counts': status_counts,
            'siblings': siblings,
            'categories': all_cats
        }
    finally:
        conn.close()


# -------------------------------------------------------------------
# Compteurs globaux (pour topbar)
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# Drill data pour la vue Globale (clic etape)
# -------------------------------------------------------------------
def get_global_drill_data():
    """
    Retourne {1: [{cat_id, cat_nom, worst, count}], ...} pour les 7 etapes.
    Worst par categorie calcule uniquement sur l'etape concernee.
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT ie.etape, i.categorie_id, c.nom as cat_nom,
                   sg.severite as sev_global,
                   sc.severite as sev_categorie,
                   si.severite as sev_indicateur
            FROM indicateur_etapes ie
            JOIN indicateurs i ON ie.indicateur_id = i.id
            JOIN categories c ON i.categorie_id = c.id
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
        """).fetchall()

        result = {}
        for step_num in range(1, 8):
            # Group by categorie for this step
            cat_data = {}  # cat_id -> {cat_nom, worst_sev, count}
            for r in rows:
                if r['etape'] != step_num:
                    continue
                cid = r['categorie_id']
                sev = _step_worst_color_sev(r)
                if cid not in cat_data:
                    cat_data[cid] = {'cat_nom': r['cat_nom'], 'worst_sev': sev, 'count': 0}
                cat_data[cid]['count'] += 1
                if sev > cat_data[cid]['worst_sev']:
                    cat_data[cid]['worst_sev'] = sev

            result[step_num] = [
                {
                    'cat_id': cid,
                    'cat_nom': d['cat_nom'],
                    'worst': _SEVERITE_TO_COLOR.get(d['worst_sev'], 'grey'),
                    'count': d['count']
                }
                for cid, d in sorted(cat_data.items())
            ]
        return result
    finally:
        conn.close()


# -------------------------------------------------------------------
# Drill data pour la vue Categorie (clic etape)
# -------------------------------------------------------------------
def get_categorie_drill_data(categorie_id):
    """
    Retourne {1: [{ind_id, ind_code, ind_desc, worst}], ...} pour les 7 etapes.
    """
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT ie.etape, ie.indicateur_id, i.code, i.description,
                   sg.severite as sev_global,
                   sc.severite as sev_categorie,
                   si.severite as sev_indicateur
            FROM indicateur_etapes ie
            JOIN indicateurs i ON ie.indicateur_id = i.id
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
            WHERE i.categorie_id = ?
        """, (categorie_id,)).fetchall()

        result = {}
        for step_num in range(1, 8):
            step_inds = []
            for r in rows:
                if r['etape'] != step_num:
                    continue
                sev = _step_worst_color_sev(r)
                step_inds.append({
                    'ind_id': r['indicateur_id'],
                    'ind_code': r['code'],
                    'ind_desc': r['description'],
                    'worst': _SEVERITE_TO_COLOR.get(sev, 'grey')
                })
            step_inds.sort(key=lambda x: x['ind_code'])
            result[step_num] = step_inds
        return result
    finally:
        conn.close()


# -------------------------------------------------------------------
# Valeurs couche pour la modale (lecture)
# -------------------------------------------------------------------
def get_step_layer_values(etape):
    """
    Retourne les valeurs de la couche globale pour cette etape.
    Lue depuis n'importe quel indicateur (identique pour tous).
    {color: 'green', comment: '...'}
    """
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT sg.severite as sev, ie.commentaire_global as comment
            FROM indicateur_etapes ie
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            WHERE ie.etape = ?
            LIMIT 1
        """, (etape,)).fetchone()
        if row and row['sev'] is not None:
            return {'color': _SEVERITE_TO_COLOR.get(row['sev'], None), 'comment': row['comment'] or ''}
        return {'color': None, 'comment': ''}
    finally:
        conn.close()


def get_step_layer_values_cat(categorie_id, etape):
    """
    Retourne les valeurs de la couche categorie pour cette etape et categorie.
    {color: 'green', comment: '...'}
    """
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT sc.severite as sev, ie.commentaire_categorie as comment
            FROM indicateur_etapes ie
            JOIN indicateurs i ON ie.indicateur_id = i.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            WHERE ie.etape = ? AND i.categorie_id = ?
            LIMIT 1
        """, (etape, categorie_id)).fetchone()
        if row and row['sev'] is not None:
            return {'color': _SEVERITE_TO_COLOR.get(row['sev'], None), 'comment': row['comment'] or ''}
        return {'color': None, 'comment': ''}
    finally:
        conn.close()


# -------------------------------------------------------------------
# Sauvegarde d'une couche pour une etape
# -------------------------------------------------------------------
def save_step(context, etape, layer, color_name, commentaire,
              indicateur_id=None, categorie_id=None):
    """
    Sauvegarde un statut/commentaire pour une couche d'une etape.

    context: 'global' | 'categorie' | 'indicateur'
    layer: 'global' | 'categorie' | 'indicateur' (quelle couche ecrire)
    color_name: 'green', 'red', ... ou None pour vider
    commentaire: texte ou ''
    """
    conn = get_connection()
    try:
        # Mapping color_name -> statut_id via severite
        statut_id = None
        if color_name:
            sev = _COLOR_TO_SEVERITE.get(color_name)
            if sev is not None:
                row = conn.execute(
                    "SELECT id FROM statuts_etape WHERE severite = ?", (sev,)
                ).fetchone()
                if row:
                    statut_id = row['id']

        # Determine column names
        statut_col = f'statut_{layer}_id'
        comment_col = f'commentaire_{layer}'

        if context == 'global':
            # Propage a tous les indicateurs
            conn.execute(f"""
                UPDATE indicateur_etapes
                SET {statut_col} = ?, {comment_col} = ?
                WHERE etape = ?
            """, (statut_id, commentaire or None, etape))

        elif context == 'categorie':
            # Deriver categorie_id depuis indicateur_id si manquant
            if not categorie_id and indicateur_id:
                row = conn.execute(
                    "SELECT categorie_id FROM indicateurs WHERE id = ?", (indicateur_id,)
                ).fetchone()
                if row:
                    categorie_id = row['categorie_id']
            # Propage aux indicateurs de la categorie
            conn.execute(f"""
                UPDATE indicateur_etapes
                SET {statut_col} = ?, {comment_col} = ?
                WHERE etape = ? AND indicateur_id IN (
                    SELECT id FROM indicateurs WHERE categorie_id = ?
                )
            """, (statut_id, commentaire or None, etape, categorie_id))

        elif context == 'indicateur':
            # Ne touche que cet indicateur
            conn.execute(f"""
                UPDATE indicateur_etapes
                SET {statut_col} = ?, {comment_col} = ?
                WHERE etape = ? AND indicateur_id = ?
            """, (statut_id, commentaire or None, etape, indicateur_id))

        conn.commit()
    finally:
        conn.close()


# -------------------------------------------------------------------
# Vue Referentiel
# -------------------------------------------------------------------

# Mappings pour les classes CSS des types et etats
_TYPE_CLASS = {'SLA': 'type-sla', 'KPI': 'type-kpi', 'XLA': 'type-xla'}
_ETAT_CLASS = {
    'Réalisé': 'etat-realise', 'En cours': 'etat-encours',
    'À cadrer': 'etat-acadrer', 'Cadré': 'etat-cadre',
    'En attente': 'etat-enattente', 'Annulé': 'etat-annule',
}


def get_referentiel_data():
    """
    Retourne les donnees pour la vue referentiel :
    - categories : [{id, nom, count, worst}]
    - indicateurs : [{id, code, description, chapitre, categorie_nom, type, etat,
                      etat_class, type_class, ciblage, conformite, worst}]
    - etats : [{intitule}]
    - types : [{intitule}]
    - status_counts : {green: N, ...}
    - total : nombre total d'indicateurs
    """
    conn = get_connection()
    try:
        # Indicateurs joints avec categories, types, etats
        inds = conn.execute("""
            SELECT i.id, i.code, i.description, i.chapitre, i.ciblage, i.conformite,
                   i.categorie_id, c.nom as categorie_nom,
                   t.intitule as type, e.intitule as etat
            FROM indicateurs i
            JOIN categories c ON i.categorie_id = c.id
            JOIN types_indicateur t ON i.type_id = t.id
            JOIN etats_indicateur e ON i.etat_id = e.id
            ORDER BY i.code
        """).fetchall()

        # indicateur_etapes pour calculer worst color par indicateur
        ie_rows = conn.execute("""
            SELECT ie.indicateur_id,
                   sg.severite as sev_global,
                   sc.severite as sev_categorie,
                   si.severite as sev_indicateur
            FROM indicateur_etapes ie
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
        """).fetchall()

        ind_worst = {}  # indicateur_id -> max severite
        for row in ie_rows:
            sev = _step_worst_color_sev(row)
            iid = row['indicateur_id']
            if iid not in ind_worst or sev > ind_worst[iid]:
                ind_worst[iid] = sev

        # Construire la liste d'indicateurs
        indicateurs = []
        for ind in inds:
            worst_sev = ind_worst.get(ind['id'], 0)
            indicateurs.append({
                'id': ind['id'],
                'code': ind['code'],
                'description': ind['description'],
                'chapitre': ind['chapitre'] or '',
                'categorie_nom': ind['categorie_nom'],
                'type': ind['type'],
                'etat': ind['etat'],
                'type_class': _TYPE_CLASS.get(ind['type'], ''),
                'etat_class': _ETAT_CLASS.get(ind['etat'], ''),
                'ciblage': ind['ciblage'] or '',
                'conformite': ind['conformite'] or '',
                'worst': _SEVERITE_TO_COLOR.get(worst_sev, 'grey'),
            })

        # Categories avec count et worst
        cats_rows = conn.execute("""
            SELECT c.id, c.nom, c.ordre, COUNT(i.id) as count
            FROM categories c
            LEFT JOIN indicateurs i ON i.categorie_id = c.id
            GROUP BY c.id
            ORDER BY c.ordre
        """).fetchall()

        # Worst par categorie = max severite de ses indicateurs
        cat_inds = {}
        for ind in inds:
            cat_inds.setdefault(ind['categorie_id'], []).append(ind['id'])

        categories = []
        for cat in cats_rows:
            cat_ind_ids = cat_inds.get(cat['id'], [])
            if cat_ind_ids:
                worst_sev = max(ind_worst.get(iid, 0) for iid in cat_ind_ids)
            else:
                worst_sev = 0
            categories.append({
                'id': cat['id'],
                'nom': cat['nom'],
                'count': cat['count'],
                'worst': _SEVERITE_TO_COLOR.get(worst_sev, 'grey'),
            })

        # Listes pour les selects de filtre
        etats = [{'intitule': r['intitule']} for r in
                 conn.execute("SELECT intitule FROM etats_indicateur ORDER BY ordre").fetchall()]
        types = [{'intitule': r['intitule']} for r in
                 conn.execute("SELECT intitule FROM types_indicateur ORDER BY ordre").fetchall()]

        # Compteurs globaux
        status_counts = {'green': 0, 'yellow': 0, 'orange': 0, 'red': 0, 'grey': 0}
        for iid, sev in ind_worst.items():
            c = _SEVERITE_TO_COLOR.get(sev, 'grey')
            status_counts[c] = status_counts.get(c, 0) + 1

        return {
            'categories': categories,
            'indicateurs': indicateurs,
            'etats': etats,
            'types': types,
            'status_counts': status_counts,
            'total': len(indicateurs),
        }
    finally:
        conn.close()


def get_global_counts():
    """Retourne {green: N, yellow: N, ...} sur tous les indicateurs."""
    conn = get_connection()
    try:
        ie_rows = conn.execute("""
            SELECT ie.indicateur_id,
                   sg.severite as sev_global,
                   sc.severite as sev_categorie,
                   si.severite as sev_indicateur
            FROM indicateur_etapes ie
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
        """).fetchall()

        ind_worst = {}
        for row in ie_rows:
            sev = _step_worst_color_sev(row)
            iid = row['indicateur_id']
            if iid not in ind_worst or sev > ind_worst[iid]:
                ind_worst[iid] = sev

        counts = {'green': 0, 'yellow': 0, 'orange': 0, 'red': 0, 'grey': 0}
        for sev in ind_worst.values():
            c = _SEVERITE_TO_COLOR.get(sev, 'grey')
            counts[c] += 1
        return counts
    finally:
        conn.close()
