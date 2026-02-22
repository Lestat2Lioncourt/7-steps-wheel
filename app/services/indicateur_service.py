"""
Couche service : requetes SQL et logique d'agregation "le pire l'emporte".
Adapte pour PostgreSQL (psycopg3).
"""

from app.database.db import get_connection, get_active_project_id, get_active_client_schema

# Mapping severite -> nom de couleur JS
_SEVERITE_TO_COLOR = {0: 'grey', 1: 'green', 2: 'yellow', 3: 'orange', 4: 'red'}
_COLOR_TO_SEVERITE = {v: k for k, v in _SEVERITE_TO_COLOR.items()}


_CC_FIELDS = ('ciblage_fonctionnel', 'ciblage_technique', 'conformite_fonctionnel', 'conformite_technique',
              'cc_commentaire', 'cc_couleur')


def _resolve_ciblage_conformite(ind_row, cat_row, projet_row):
    """Resout les 6 champs ciblage/conformite avec heritage Indicateur > Categorie > Projet.
    Retourne un dict {field: {value, origine, propre}} pour chaque champ."""
    result = {}
    for field in _CC_FIELDS:
        ind_val = ind_row.get(field) if ind_row else None
        cat_val = cat_row.get(field) if cat_row else None
        proj_val = projet_row.get(field) if projet_row else None
        if ind_val is not None:
            result[field] = {'value': ind_val, 'origine': 'indicateur', 'propre': True}
        elif cat_val is not None:
            result[field] = {'value': cat_val, 'origine': 'categorie', 'propre': False}
        elif proj_val is not None:
            result[field] = {'value': proj_val, 'origine': 'projet', 'propre': False}
        else:
            result[field] = {'value': None, 'origine': None, 'propre': False}
    return result


# -------------------------------------------------------------------
# CRUD ciblage/conformite (projet, categorie, indicateur)
# -------------------------------------------------------------------
def get_project_ciblage_conformite():
    """Retourne les 6 champs ciblage/conformite du projet actif."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT ciblage_fonctionnel, ciblage_technique, conformite_fonctionnel, conformite_technique,
                      cc_commentaire, cc_couleur FROM projets WHERE id = %s""",
            (get_active_project_id(),)
        ).fetchone()
        return dict(row) if row else {f: None for f in _CC_FIELDS}
    finally:
        conn.close()


def save_project_ciblage_conformite(data):
    """Met a jour les 6 champs ciblage/conformite du projet actif."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE projets SET ciblage_fonctionnel = %s, ciblage_technique = %s,
               conformite_fonctionnel = %s, conformite_technique = %s,
               cc_commentaire = %s, cc_couleur = %s WHERE id = %s""",
            (data.get('ciblage_fonctionnel'), data.get('ciblage_technique'),
             data.get('conformite_fonctionnel'), data.get('conformite_technique'),
             data.get('cc_commentaire'), data.get('cc_couleur'),
             get_active_project_id())
        )
        conn.commit()
    finally:
        conn.close()


def get_categorie_ciblage_conformite(cat_id):
    """Retourne les 6 champs ciblage/conformite propres d'une categorie."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT ciblage_fonctionnel, ciblage_technique, conformite_fonctionnel, conformite_technique,
                      cc_commentaire, cc_couleur FROM categories WHERE id = %s""",
            (cat_id,)
        ).fetchone()
        return dict(row) if row else {f: None for f in _CC_FIELDS}
    finally:
        conn.close()


def save_categorie_ciblage_conformite(cat_id, data):
    """Met a jour les 6 champs ciblage/conformite d'une categorie."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE categories SET ciblage_fonctionnel = %s, ciblage_technique = %s,
               conformite_fonctionnel = %s, conformite_technique = %s,
               cc_commentaire = %s, cc_couleur = %s WHERE id = %s""",
            (data.get('ciblage_fonctionnel'), data.get('ciblage_technique'),
             data.get('conformite_fonctionnel'), data.get('conformite_technique'),
             data.get('cc_commentaire'), data.get('cc_couleur'),
             cat_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_indicateur_ciblage_conformite(ind_id):
    """Retourne les 6 champs ciblage/conformite propres d'un indicateur."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT ciblage_fonctionnel, ciblage_technique, conformite_fonctionnel, conformite_technique,
                      cc_commentaire, cc_couleur FROM indicateurs WHERE id = %s""",
            (ind_id,)
        ).fetchone()
        return dict(row) if row else {f: None for f in _CC_FIELDS}
    finally:
        conn.close()


def save_indicateur_ciblage_conformite(ind_id, data):
    """Met a jour les 6 champs ciblage/conformite d'un indicateur."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE indicateurs SET ciblage_fonctionnel = %s, ciblage_technique = %s,
               conformite_fonctionnel = %s, conformite_technique = %s,
               cc_commentaire = %s, cc_couleur = %s WHERE id = %s""",
            (data.get('ciblage_fonctionnel'), data.get('ciblage_technique'),
             data.get('conformite_fonctionnel'), data.get('conformite_technique'),
             data.get('cc_commentaire'), data.get('cc_couleur'),
             ind_id)
        )
        conn.commit()
    finally:
        conn.close()


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
    conn = get_connection()
    try:
        statuts = get_statuts_map()

        cats = conn.execute("""
            SELECT c.id, c.nom, c.ordre, COUNT(i.id) as count
            FROM categories c
            LEFT JOIN indicateurs i ON i.categorie_id = c.id
            GROUP BY c.id, c.nom, c.ordre
            ORDER BY c.ordre
        """).fetchall()

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

        ind_worst = {}
        step_worst = {}
        ind_step_color = {}

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

        indicateurs = conn.execute(
            "SELECT id, categorie_id FROM indicateurs"
        ).fetchall()
        cat_inds = {}
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

        wheel_colors = []
        for step_num in range(1, 8):
            sev = step_worst.get(step_num, 0)
            wheel_colors.append(_SEVERITE_TO_COLOR.get(sev, 'grey'))

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
    conn = get_connection()
    try:
        statuts = get_statuts_map()

        cat = conn.execute(
            "SELECT id, nom FROM categories WHERE id = %s", (categorie_id,)
        ).fetchone()
        if not cat:
            return None

        all_cats_rows = conn.execute("""
            SELECT c.id, c.nom, c.ordre, COUNT(i.id) as count
            FROM categories c
            LEFT JOIN indicateurs i ON i.categorie_id = c.id
            GROUP BY c.id, c.nom, c.ordre ORDER BY c.ordre
        """).fetchall()

        inds = conn.execute("""
            SELECT i.id, i.code, i.description, t.intitule as type, e.intitule as etat,
                   t.couleur as type_couleur
            FROM indicateurs i
            JOIN types_indicateur t ON i.type_id = t.id
            JOIN etats_indicateur e ON i.etat_id = e.id
            WHERE i.categorie_id = %s
            ORDER BY i.code
        """, (categorie_id,)).fetchall()

        ind_ids = [r['id'] for r in inds]

        if ind_ids:
            ie_rows = conn.execute("""
                SELECT ie.indicateur_id, ie.etape,
                       sg.severite as sev_global,
                       sc.severite as sev_categorie,
                       si.severite as sev_indicateur
                FROM indicateur_etapes ie
                LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
                LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
                LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
                WHERE ie.indicateur_id = ANY(%s)
            """, (ind_ids,)).fetchall()
        else:
            ie_rows = []

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

        # Worst par categorie (sidebar)
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
    conn = get_connection()
    try:
        statuts = get_statuts_map()

        ind = conn.execute("""
            SELECT i.*, t.intitule as type, e.intitule as etat,
                   t.couleur as type_couleur, e.couleur as etat_couleur
            FROM indicateurs i
            JOIN types_indicateur t ON i.type_id = t.id
            JOIN etats_indicateur e ON i.etat_id = e.id
            WHERE i.id = %s
        """, (indicateur_id,)).fetchone()
        if not ind:
            return None

        cat = conn.execute(
            """SELECT id, nom, ciblage_fonctionnel, ciblage_technique,
                      conformite_fonctionnel, conformite_technique,
                      cc_commentaire, cc_couleur
               FROM categories WHERE id = %s""", (ind['categorie_id'],)
        ).fetchone()

        projet_row = conn.execute(
            """SELECT ciblage_fonctionnel, ciblage_technique,
                      conformite_fonctionnel, conformite_technique,
                      cc_commentaire, cc_couleur
               FROM projets WHERE id = %s""", (get_active_project_id(),)
        ).fetchone()

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
            WHERE ie.indicateur_id = %s
            ORDER BY ie.etape
        """, (indicateur_id,)).fetchall()

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

        # Siblings
        siblings_rows = conn.execute("""
            SELECT i.id, i.code, i.description
            FROM indicateurs i
            WHERE i.categorie_id = %s
            ORDER BY i.code
        """, (ind['categorie_id'],)).fetchall()

        sib_ids = [r['id'] for r in siblings_rows]
        sib_worst = {}
        if sib_ids:
            sib_ie = conn.execute("""
                SELECT ie.indicateur_id,
                       sg.severite as sev_global,
                       sc.severite as sev_categorie,
                       si.severite as sev_indicateur
                FROM indicateur_etapes ie
                LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
                LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
                LEFT JOIN statuts_etape si ON ie.statut_indicateur_id = si.id
                WHERE ie.indicateur_id = ANY(%s)
            """, (sib_ids,)).fetchall()
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

        # All categories (sidebar)
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

        ind_worst_sev = max(
            (_step_worst_color_sev(r) for r in ie_rows),
            default=0
        )

        resolved_cc = _resolve_ciblage_conformite(ind, cat, projet_row)

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
            'periodicite': ind.get('periodicite', 'Mensuel'),
            'sla_valeur': ind.get('sla_valeur'),
            'kpi_formule': ind.get('kpi_formule'),
            'penalite': ind.get('penalite', False),
            'seuil': ind.get('seuil'),
            'ciblage_fonctionnel': ind['ciblage_fonctionnel'],
            'ciblage_technique': ind['ciblage_technique'],
            'conformite_fonctionnel': ind['conformite_fonctionnel'],
            'conformite_technique': ind['conformite_technique'],
            'cc_commentaire': ind['cc_commentaire'],
            'cc_couleur': ind['cc_couleur'],
            'resolved': resolved_cc,
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


# -------------------------------------------------------------------
# Drill data pour la vue Globale
# -------------------------------------------------------------------
def get_global_drill_data():
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
            cat_data = {}
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
# Drill data pour la vue Categorie
# -------------------------------------------------------------------
def get_categorie_drill_data(categorie_id):
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
            WHERE i.categorie_id = %s
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
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT sg.severite as sev, ie.commentaire_global as comment
            FROM indicateur_etapes ie
            LEFT JOIN statuts_etape sg ON ie.statut_global_id = sg.id
            WHERE ie.etape = %s
            LIMIT 1
        """, (etape,)).fetchone()
        if row:
            return {'color': _SEVERITE_TO_COLOR.get(row['sev'], None) if row['sev'] is not None else None,
                    'comment': row['comment'] or ''}
        return {'color': None, 'comment': ''}
    finally:
        conn.close()


def get_step_layer_values_cat(categorie_id, etape):
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT sc.severite as sev, ie.commentaire_categorie as comment
            FROM indicateur_etapes ie
            JOIN indicateurs i ON ie.indicateur_id = i.id
            LEFT JOIN statuts_etape sc ON ie.statut_categorie_id = sc.id
            WHERE ie.etape = %s AND i.categorie_id = %s
            LIMIT 1
        """, (etape, categorie_id)).fetchone()
        if row:
            return {'color': _SEVERITE_TO_COLOR.get(row['sev'], None) if row['sev'] is not None else None,
                    'comment': row['comment'] or ''}
        return {'color': None, 'comment': ''}
    finally:
        conn.close()


# -------------------------------------------------------------------
# Sauvegarde d'une couche pour une etape
# -------------------------------------------------------------------
def save_step(context, etape, layer, color_name, commentaire,
              indicateur_id=None, categorie_id=None):
    conn = get_connection()
    try:
        statut_id = None
        if color_name:
            sev = _COLOR_TO_SEVERITE.get(color_name)
            if sev is not None:
                row = conn.execute(
                    "SELECT id FROM statuts_etape WHERE severite = %s", (sev,)
                ).fetchone()
                if row:
                    statut_id = row['id']

        statut_col = f'statut_{layer}_id'
        comment_col = f'commentaire_{layer}'

        # Determiner les indicateurs concernes
        if context == 'global':
            projet_id = get_active_project_id()
            ind_ids = [r['id'] for r in conn.execute(
                "SELECT id FROM indicateurs WHERE projet_id = %s", (projet_id,)
            ).fetchall()]
        elif context == 'categorie':
            if not categorie_id and indicateur_id:
                row = conn.execute(
                    "SELECT categorie_id FROM indicateurs WHERE id = %s", (indicateur_id,)
                ).fetchone()
                if row:
                    categorie_id = row['categorie_id']
            ind_ids = [r['id'] for r in conn.execute(
                "SELECT id FROM indicateurs WHERE categorie_id = %s", (categorie_id,)
            ).fetchall()]
        elif context == 'indicateur':
            ind_ids = [indicateur_id] if indicateur_id else []

        # UPSERT pour chaque indicateur (cree la ligne si elle n'existe pas)
        for iid in ind_ids:
            conn.execute(f"""
                INSERT INTO indicateur_etapes (indicateur_id, etape, {statut_col}, {comment_col})
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (indicateur_id, etape)
                DO UPDATE SET {statut_col} = EXCLUDED.{statut_col},
                              {comment_col} = EXCLUDED.{comment_col}
            """, (iid, etape, statut_id, commentaire or None))

        conn.commit()
    finally:
        conn.close()


# -------------------------------------------------------------------
# Vue Referentiel
# -------------------------------------------------------------------
def get_indicateur_properties(ind_id):
    """Retourne les 5 proprietes d'un indicateur."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT periodicite, sla_valeur, kpi_formule, penalite, seuil FROM indicateurs WHERE id = %s",
            (ind_id,)
        ).fetchone()
        if row:
            return dict(row)
        return {'periodicite': 'Mensuel', 'sla_valeur': None, 'kpi_formule': None, 'penalite': False, 'seuil': None}
    finally:
        conn.close()


def save_indicateur_properties(ind_id, data):
    """Met a jour les 5 proprietes d'un indicateur."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE indicateurs SET periodicite = %s, sla_valeur = %s, kpi_formule = %s,
               penalite = %s, seuil = %s WHERE id = %s""",
            (data.get('periodicite', 'Mensuel'),
             data.get('sla_valeur'),
             data.get('kpi_formule'),
             bool(data.get('penalite', False)),
             data.get('seuil'),
             ind_id)
        )
        conn.commit()
    finally:
        conn.close()


_TYPE_CLASS = {'SLA': 'type-sla', 'KPI': 'type-kpi', 'XLA': 'type-xla'}
_ETAT_CLASS = {
    'Realise': 'etat-realise', 'En cours': 'etat-encours',
    'A cadrer': 'etat-acadrer', 'Cadre': 'etat-cadre',
    'En attente': 'etat-enattente', 'Annule': 'etat-annule',
}


def get_referentiel_data():
    conn = get_connection()
    try:
        # Charger projet pour heritage ciblage/conformite
        projet_row = conn.execute(
            """SELECT ciblage_fonctionnel, ciblage_technique,
                      conformite_fonctionnel, conformite_technique,
                      cc_commentaire, cc_couleur
               FROM projets WHERE id = %s""", (get_active_project_id(),)
        ).fetchone()

        # Charger toutes les categories avec leurs champs ciblage/conformite
        all_cats_cc = {}
        for r in conn.execute(
            """SELECT id, ciblage_fonctionnel, ciblage_technique,
                      conformite_fonctionnel, conformite_technique,
                      cc_commentaire, cc_couleur
               FROM categories"""
        ).fetchall():
            all_cats_cc[r['id']] = dict(r)

        inds = conn.execute("""
            SELECT i.id, i.code, i.description, i.chapitre,
                   i.periodicite, i.sla_valeur, i.kpi_formule, i.penalite, i.seuil,
                   i.ciblage_fonctionnel, i.ciblage_technique,
                   i.conformite_fonctionnel, i.conformite_technique,
                   i.cc_commentaire, i.cc_couleur,
                   i.categorie_id, c.nom as categorie_nom,
                   t.intitule as type, e.intitule as etat
            FROM indicateurs i
            JOIN categories c ON i.categorie_id = c.id
            JOIN types_indicateur t ON i.type_id = t.id
            JOIN etats_indicateur e ON i.etat_id = e.id
            ORDER BY i.code
        """).fetchall()

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

        indicateurs = []
        for ind in inds:
            worst_sev = ind_worst.get(ind['id'], 0)
            cat_cc = all_cats_cc.get(ind['categorie_id'], {})
            resolved = _resolve_ciblage_conformite(ind, cat_cc, projet_row)
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
                'periodicite': ind.get('periodicite', 'Mensuel'),
                'sla_valeur': ind.get('sla_valeur'),
                'kpi_formule': ind.get('kpi_formule'),
                'penalite': ind.get('penalite', False),
                'seuil': ind.get('seuil'),
                'resolved': resolved,
                'worst': _SEVERITE_TO_COLOR.get(worst_sev, 'grey'),
            })

        cats_rows = conn.execute("""
            SELECT c.id, c.nom, c.ordre, COUNT(i.id) as count
            FROM categories c
            LEFT JOIN indicateurs i ON i.categorie_id = c.id
            GROUP BY c.id, c.nom, c.ordre
            ORDER BY c.ordre
        """).fetchall()

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

        etats = [{'intitule': r['intitule']} for r in
                 conn.execute("SELECT intitule FROM etats_indicateur ORDER BY ordre").fetchall()]
        types = [{'intitule': r['intitule']} for r in
                 conn.execute("SELECT intitule FROM types_indicateur ORDER BY ordre").fetchall()]

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
