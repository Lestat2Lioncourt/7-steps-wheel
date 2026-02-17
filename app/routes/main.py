"""
Blueprint principal : accueil, selection de projet, vues Globale, Categorie, Indicateur.
"""

from datetime import date
from flask import Blueprint, render_template, abort, request, jsonify, session, redirect, url_for
from app.database.db import load_projects, get_project_by_id, set_active_project, get_connection, create_project, attach_project
from app.services.indicateur_service import (
    get_global_data,
    get_categorie_data,
    get_indicateur_data,
    get_global_counts,
    get_global_drill_data,
    get_categorie_drill_data,
    get_step_layer_values,
    get_step_layer_values_cat,
    get_referentiel_data,
    save_step as svc_save_step,
)
from app.services.action_service import (
    get_actions_for_indicator,
    get_actions_for_categorie,
    get_actions_for_global,
    create_action,
    update_action_status,
    update_action,
    delete_action,
    KANBAN_COLUMNS,
    KANBAN_LABELS,
)
from app.services.identity_service import (
    detect_from_registry,
    get_stored_identity,
    save_identity,
    clear_identity,
    ensure_user_in_db,
    suggest_trigramme,
    create_placeholder_user,
)

main_bp = Blueprint('main', __name__)


def _activate_project(project):
    """Active un projet (local ou distant)."""
    if project.get('db_path'):
        set_active_project(db_path=project['db_path'])
    else:
        set_active_project(db_file=project['db_file'])

# Couleurs JS disponibles dans tous les templates
COL = {
    'grey': '#6b7280', 'green': '#22c55e', 'yellow': '#eab308',
    'orange': '#f97316', 'red': '#dc2626'
}
COL_LABEL = {
    'grey': 'Aucun', 'green': 'Validé', 'yellow': 'En cours',
    'orange': 'Warning', 'red': 'Blocage'
}

# Routes exclues des guards
_OPEN_ROUTES = ('main.accueil', 'main.select_project', 'main.create_project_route', 'main.attach_project_route', 'main.login', 'main.logout', 'main.api_trigramme_suggest', 'static')


@main_bp.before_request
def require_identity_and_project():
    """Redirige vers login si pas identifie, puis vers accueil si pas de projet."""
    if request.endpoint in _OPEN_ROUTES:
        return
    if request.endpoint and request.endpoint.startswith('static'):
        return

    # 1. Identite requise
    if 'user_login' not in session:
        # Tenter de restaurer depuis le fichier memorise
        stored = get_stored_identity()
        if stored:
            session['user_login'] = stored['login']
            session['user_nom'] = stored['nom']
            session['user_email'] = stored.get('email', '')
            session['user_trigramme'] = stored.get('trigramme', '')
        else:
            return redirect(url_for('main.login'))

    # 2. Projet actif requis
    if 'project_id' not in session:
        return redirect(url_for('main.accueil'))
    project = get_project_by_id(session['project_id'])
    if project is None:
        session.pop('project_id', None)
        session.pop('project_name', None)
        return redirect(url_for('main.accueil'))
    _activate_project(project)

    # 3. S'assurer que l'utilisateur existe dans la DB du projet
    ensure_user_in_db(session['user_login'], session['user_nom'],
                      session.get('user_email', ''), session.get('user_trigramme', ''))


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        nom = request.form.get('nom', '').strip()
        trigramme = request.form.get('trigramme', '').strip().upper()
        if not email or not nom:
            return render_template('login.html', prefill={'email': email, 'nom': nom, 'trigramme': trigramme},
                                   detected=False, error='Email et nom requis.')
        # login = partie avant @ de l'email
        login_id = email.split('@')[0].lower()
        identity = save_identity(login_id, nom, email, trigramme)
        session['user_login'] = identity['login']
        session['user_nom'] = identity['nom']
        session['user_email'] = identity['email']
        session['user_trigramme'] = identity.get('trigramme', '')
        return redirect(url_for('main.accueil'))

    # GET: pre-remplir depuis registre ou fichier
    stored = get_stored_identity()
    if stored:
        session['user_login'] = stored['login']
        session['user_nom'] = stored['nom']
        session['user_email'] = stored.get('email', '')
        return redirect(url_for('main.accueil'))

    detected = detect_from_registry()
    return render_template('login.html', prefill=detected or {},
                           detected=detected is not None, error=None)


@main_bp.route('/logout')
def logout():
    clear_identity()
    session.clear()
    return redirect(url_for('main.login'))


@main_bp.route('/')
def accueil():
    # Si pas identifie, renvoyer au login
    if 'user_login' not in session:
        stored = get_stored_identity()
        if stored:
            session['user_login'] = stored['login']
            session['user_nom'] = stored['nom']
            session['user_email'] = stored.get('email', '')
            session['user_trigramme'] = stored.get('trigramme', '')
        else:
            return redirect(url_for('main.login'))

    projects = load_projects()
    return render_template('accueil.html', projects=projects,
                           user_nom=session.get('user_nom', ''))


@main_bp.route('/projet/nouveau', methods=['POST'])
def create_project_route():
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('main.accueil'))
    project = create_project(name)
    # Selectionner le nouveau projet directement
    _activate_project(project)
    session['project_id'] = project['id']
    session['project_name'] = project['name']
    # S'assurer que l'utilisateur existe dans la nouvelle DB
    ensure_user_in_db(session['user_login'], session['user_nom'],
                      session.get('user_email', ''), session.get('user_trigramme', ''))
    return redirect(url_for('main.vue_globale'))


@main_bp.route('/projet/rattacher', methods=['POST'])
def attach_project_route():
    name = request.form.get('name', '').strip()
    path = request.form.get('path', '').strip()
    if not name or not path:
        return redirect(url_for('main.accueil'))
    try:
        project = attach_project(name, path)
    except FileNotFoundError:
        # Recharger l'accueil avec un message d'erreur
        projects = load_projects()
        return render_template('accueil.html', projects=projects,
                               user_nom=session.get('user_nom', ''),
                               attach_error=f'Fichier introuvable : {path}')
    _activate_project(project)
    session['project_id'] = project['id']
    session['project_name'] = project['name']
    ensure_user_in_db(session['user_login'], session['user_nom'],
                      session.get('user_email', ''), session.get('user_trigramme', ''))
    return redirect(url_for('main.vue_globale'))


@main_bp.route('/projet/<project_id>')
def select_project(project_id):
    project = get_project_by_id(project_id)
    if project is None:
        abort(404)
    _activate_project(project)
    session['project_id'] = project['id']
    session['project_name'] = project['name']
    return redirect(url_for('main.vue_globale'))


@main_bp.route('/global')
def vue_globale():
    data = get_global_data()
    drill_data = get_global_drill_data()
    # Layer values for global layer at each step
    global_layer_values = {}
    for step_num in range(1, 8):
        global_layer_values[step_num] = get_step_layer_values(step_num)
    return render_template(
        'global.html',
        data=data,
        drill_data=drill_data,
        global_layer_values=global_layer_values,
        active_tab='roue',
        global_counts=get_global_counts(),
        COL=COL,
        COL_LABEL=COL_LABEL,
        project_name=session.get('project_name', 'ROUE CSI'),
    )


@main_bp.route('/categorie/<int:id>')
def vue_categorie(id):
    data = get_categorie_data(id)
    if data is None:
        abort(404)
    drill_data = get_categorie_drill_data(id)
    cat_layer_values = {}
    for step_num in range(1, 8):
        cat_layer_values[step_num] = get_step_layer_values_cat(id, step_num)
    return render_template(
        'categorie.html',
        data=data,
        drill_data=drill_data,
        cat_layer_values=cat_layer_values,
        active_tab='roue',
        global_counts=get_global_counts(),
        COL=COL,
        COL_LABEL=COL_LABEL,
        project_name=session.get('project_name', 'ROUE CSI'),
    )


@main_bp.route('/indicateur/<int:id>')
def vue_indicateur(id):
    data = get_indicateur_data(id)
    if data is None:
        abort(404)
    return render_template(
        'indicateur.html',
        data=data,
        active_tab='roue',
        global_counts=get_global_counts(),
        COL=COL,
        COL_LABEL=COL_LABEL,
        today=date.today().strftime('%d/%m/%Y'),
        project_name=session.get('project_name', 'ROUE CSI'),
    )


@main_bp.route('/referentiel')
def vue_referentiel():
    data = get_referentiel_data()
    return render_template(
        'referentiel.html',
        data=data,
        active_tab='referentiel',
        global_counts=get_global_counts(),
        COL=COL,
        COL_LABEL=COL_LABEL,
        project_name=session.get('project_name', 'ROUE CSI'),
    )


@main_bp.route('/api/step/save', methods=['POST'])
def save_step():
    d = request.get_json()
    context = d.get('context')
    etape = d.get('etape')
    layer = d.get('layer')
    color = d.get('color')  # 'green', 'red', ... or None
    commentaire = d.get('commentaire', '')
    indicateur_id = d.get('indicateur_id')
    categorie_id = d.get('categorie_id')

    valid_contexts = ('global', 'categorie', 'indicateur')
    valid_layers = ('global', 'categorie', 'indicateur')
    if not context or not etape or not layer:
        return jsonify({'ok': False, 'error': 'Missing parameters'}), 400
    if context not in valid_contexts or layer not in valid_layers:
        return jsonify({'ok': False, 'error': 'Invalid context or layer'}), 400

    svc_save_step(
        context=context,
        etape=etape,
        layer=layer,
        color_name=color,
        commentaire=commentaire,
        indicateur_id=indicateur_id,
        categorie_id=categorie_id,
    )
    return jsonify({'ok': True})


# -------------------------------------------------------------------
# Kanban — 3 niveaux
# -------------------------------------------------------------------
def _kanban_common():
    """Charge les etapes (pour le select de la modale)."""
    conn = get_connection()
    try:
        etapes = conn.execute("SELECT numero, nom FROM etapes ORDER BY numero").fetchall()
        return [dict(e) for e in etapes]
    finally:
        conn.close()


def _render_kanban(data, actions, kanban_level, etapes):
    return render_template(
        'kanban.html',
        data=data,
        actions=actions,
        kanban_level=kanban_level,
        kanban_columns=KANBAN_COLUMNS,
        kanban_labels=KANBAN_LABELS,
        etapes=etapes,
        active_tab='roue',
        global_counts=get_global_counts(),
        COL=COL,
        COL_LABEL=COL_LABEL,
        project_name=session.get('project_name', 'ROUE CSI'),
    )


@main_bp.route('/global/kanban')
def vue_kanban_global():
    data = get_global_data()
    actions = get_actions_for_global()
    return _render_kanban(data, actions, 'global', _kanban_common())


@main_bp.route('/categorie/<int:id>/kanban')
def vue_kanban_categorie(id):
    data = get_categorie_data(id)
    if data is None:
        abort(404)
    actions = get_actions_for_categorie(id)
    return _render_kanban(data, actions, 'categorie', _kanban_common())


@main_bp.route('/indicateur/<int:id>/kanban')
def vue_kanban(id):
    data = get_indicateur_data(id)
    if data is None:
        abort(404)
    actions = get_actions_for_indicator(id, data['categorie']['id'])
    return _render_kanban(data, actions, 'indicateur', _kanban_common())


@main_bp.route('/api/action/create', methods=['POST'])
def api_action_create():
    d = request.get_json()
    if not d or not d.get('titre') or not d.get('assignee_login') or not d.get('etape'):
        return jsonify({'ok': False, 'error': 'Missing parameters'}), 400
    # Si assignee_login contient @ → creer un placeholder
    if '@' in d['assignee_login']:
        d['assignee_login'] = create_placeholder_user(d['assignee_login'])
    try:
        action_id = create_action(d)
        return jsonify({'ok': True, 'id': action_id})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@main_bp.route('/api/action/<int:id>/status', methods=['POST'])
def api_action_status(id):
    d = request.get_json()
    new_status = d.get('statut') if d else None
    if not new_status:
        return jsonify({'ok': False, 'error': 'Missing statut'}), 400
    try:
        update_action_status(id, new_status)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@main_bp.route('/api/action/<int:id>/update', methods=['POST'])
def api_action_update(id):
    d = request.get_json()
    if not d or not d.get('titre') or not d.get('assignee_login') or not d.get('etape'):
        return jsonify({'ok': False, 'error': 'Missing parameters'}), 400
    # Si assignee_login contient @ → creer un placeholder
    if '@' in d['assignee_login']:
        d['assignee_login'] = create_placeholder_user(d['assignee_login'])
    try:
        update_action(id, d)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@main_bp.route('/api/action/<int:id>/delete', methods=['POST'])
def api_action_delete(id):
    try:
        delete_action(id)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@main_bp.route('/api/users/search')
def api_users_search():
    q = request.args.get('q', '').strip()
    conn = get_connection()
    try:
        if q:
            like = f"%{q}%"
            users = conn.execute(
                """SELECT login, nom, email, trigramme FROM utilisateurs
                   WHERE login LIKE ? OR nom LIKE ? OR email LIKE ? OR trigramme LIKE ?
                   ORDER BY nom LIMIT 20""",
                (like, like, like, like),
            ).fetchall()
        else:
            users = conn.execute(
                "SELECT login, nom, email, trigramme FROM utilisateurs ORDER BY nom LIMIT 20"
            ).fetchall()
        return jsonify({'users': [dict(u) for u in users]})
    finally:
        conn.close()


@main_bp.route('/api/trigramme/suggest')
def api_trigramme_suggest():
    nom = request.args.get('nom', '')
    return jsonify({'trigramme': suggest_trigramme(nom)})
