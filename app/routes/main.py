"""
Blueprint principal : accueil, selection de projet, vues Globale, Categorie, Indicateur.
"""

from datetime import date
from functools import wraps
from flask import Blueprint, render_template, abort, request, jsonify, session, redirect, url_for
from app.database.db import load_projects, get_project_by_id, set_active_project, get_active_db_path, get_connection, create_project, attach_project, update_project, delete_project, init_db
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
    add_user_to_project,
    suggest_trigramme,
    create_placeholder_user,
)
from app.services.member_service import (
    get_all_members,
    add_member,
    update_member_role,
    update_member_emails,
    update_member_date_fin,
    remove_member,
)

main_bp = Blueprint('main', __name__)


def _activate_project(project):
    """Active un projet (local ou distant) et applique les migrations si necessaire."""
    if project.get('db_path'):
        set_active_project(db_path=project['db_path'])
    else:
        set_active_project(db_file=project['db_file'])
    # Appliquer les migrations sur la base du projet
    init_db(get_active_db_path())


def _resolve_role(result):
    """Traite le retour de ensure_user_in_db.
    Si c'est un dict (connexion via email secondaire), met a jour la session
    avec les infos du membre principal et retourne le role.
    Si c'est une string, retourne directement le role."""
    if result is None:
        return None
    if isinstance(result, dict):
        session['user_login'] = result['login']
        session['user_nom'] = result['nom']
        session['user_email'] = result['email'] or ''
        session['user_trigramme'] = result['trigramme'] or ''
        return result['role']
    return result

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


# -------------------------------------------------------------------
# Decorateurs de controle d'acces
# -------------------------------------------------------------------
def require_write(f):
    """Refuse l'acces en ecriture aux lecteurs (403 JSON)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_role') == 'lecteur':
            return jsonify({'ok': False, 'error': 'Acces en lecture seule'}), 403
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    """Refuse l'acces si pas admin (403 JSON)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return jsonify({'ok': False, 'error': 'Acces reserve aux administrateurs'}), 403
        return f(*args, **kwargs)
    return decorated


def require_admin_page(f):
    """Refuse l'acces si pas admin (redirect pour pages HTML)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('user_role') != 'admin':
            return redirect(url_for('main.vue_globale'))
        return f(*args, **kwargs)
    return decorated


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

    # 3. Verifier que l'utilisateur est membre du projet
    role = _resolve_role(ensure_user_in_db(session['user_login'], session['user_nom'],
                             session.get('user_email', ''), session.get('user_trigramme', '')))
    if role is None or role == 'information':
        session.pop('project_id', None)
        session.pop('project_name', None)
        session.pop('user_role', None)
        error = 'info_only' if role == 'information' else 'non_membre'
        return redirect(url_for('main.accueil', error=error))
    session['user_role'] = role


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        nom = request.form.get('nom', '').strip()
        trigramme = request.form.get('trigramme', '').strip().upper()
        if not email or not nom:
            return render_template('login.html', accounts=[], prefill={'email': email, 'nom': nom, 'trigramme': trigramme},
                                   detected=False, error='Email et nom requis.')
        # login = partie avant @ de l'email
        login_id = email.split('@')[0].lower()
        identity = save_identity(login_id, nom, email, trigramme)
        session['user_login'] = identity['login']
        session['user_nom'] = identity['nom']
        session['user_email'] = identity['email']
        session['user_trigramme'] = identity.get('trigramme', '')
        return redirect(url_for('main.accueil'))

    # GET: auto-login depuis fichier ou registre
    stored = get_stored_identity()
    if stored:
        session['user_login'] = stored['login']
        session['user_nom'] = stored['nom']
        session['user_email'] = stored.get('email', '')
        session['user_trigramme'] = stored.get('trigramme', '')
        return redirect(url_for('main.accueil'))

    accounts = detect_from_registry()
    if len(accounts) == 1:
        # Un seul compte detecte → connexion automatique
        email = accounts[0]['email']
        nom = accounts[0].get('nom', email.split('@')[0])
        login_id = email.split('@')[0].lower()
        trigramme = suggest_trigramme(nom)
        identity = save_identity(login_id, nom, email, trigramme)
        session['user_login'] = identity['login']
        session['user_nom'] = identity['nom']
        session['user_email'] = identity['email']
        session['user_trigramme'] = identity.get('trigramme', '')
        return redirect(url_for('main.accueil'))

    if len(accounts) > 1:
        # Plusieurs comptes → ecran de selection
        return render_template('login.html', accounts=accounts, prefill={}, detected=False, error=None)

    # Aucun compte detecte → formulaire manuel
    return render_template('login.html', accounts=[], prefill={}, detected=False, error=None)


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
    # Le createur est automatiquement admin
    add_user_to_project(session['user_login'], session['user_nom'],
                        session.get('user_email', ''), session.get('user_trigramme', ''),
                        role='admin')
    session['user_role'] = 'admin'
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
    # Verifier si deja membre, sinon ajouter comme admin
    role = _resolve_role(ensure_user_in_db(session['user_login'], session['user_nom'],
                             session.get('user_email', ''), session.get('user_trigramme', '')))
    if role is None:
        add_user_to_project(session['user_login'], session['user_nom'],
                            session.get('user_email', ''), session.get('user_trigramme', ''),
                            role='admin')
        role = 'admin'
    session['user_role'] = role
    return redirect(url_for('main.vue_globale'))


@main_bp.route('/projet/<project_id>/modifier', methods=['POST'])
def update_project_route(project_id):
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('main.accueil'))
    update_project(project_id, name=name)
    return redirect(url_for('main.accueil'))


@main_bp.route('/projet/<project_id>/supprimer', methods=['POST'])
def delete_project_route(project_id):
    delete_project(project_id)
    # Si le projet supprime etait le projet actif, nettoyer la session
    if session.get('project_id') == project_id:
        session.pop('project_id', None)
        session.pop('project_name', None)
    return redirect(url_for('main.accueil'))


@main_bp.route('/projet/<project_id>')
def select_project(project_id):
    project = get_project_by_id(project_id)
    if project is None:
        abort(404)
    _activate_project(project)
    # Verifier si l'utilisateur est membre
    role = _resolve_role(ensure_user_in_db(session['user_login'], session['user_nom'],
                             session.get('user_email', ''), session.get('user_trigramme', '')))
    if role is None:
        return redirect(url_for('main.accueil', error='non_membre'))
    session['project_id'] = project['id']
    session['project_name'] = project['name']
    session['user_role'] = role
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
    global_layer_values = {}
    for step_num in range(1, 8):
        cat_layer_values[step_num] = get_step_layer_values_cat(id, step_num)
        global_layer_values[step_num] = get_step_layer_values(step_num)
    return render_template(
        'categorie.html',
        data=data,
        drill_data=drill_data,
        cat_layer_values=cat_layer_values,
        global_layer_values=global_layer_values,
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
@require_write
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
@require_write
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
@require_write
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
@require_write
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
@require_write
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


# -------------------------------------------------------------------
# Gestion des membres
# -------------------------------------------------------------------
@main_bp.route('/membres')
@require_admin_page
def vue_membres():
    from app.database.db import get_active_db_path, BASE_DIR
    members = get_all_members()
    db_path = get_active_db_path()
    app_path = str(BASE_DIR / 'start.py')
    return render_template(
        'membres.html',
        members=members,
        active_tab='membres',
        global_counts=get_global_counts(),
        COL=COL,
        COL_LABEL=COL_LABEL,
        project_name=session.get('project_name', 'ROUE CSI'),
        db_path=str(db_path) if db_path else '',
        app_path=app_path,
    )


@main_bp.route('/api/membres/add', methods=['POST'])
@require_admin
def api_add_member():
    d = request.get_json()
    if not d or not d.get('email') or not d.get('nom'):
        return jsonify({'ok': False, 'error': 'Email et nom requis'}), 400
    email = d['email'].strip()
    nom = d['nom'].strip()
    trigramme = d.get('trigramme', '').strip().upper()
    role = d.get('role', 'membre')
    if role not in ('admin', 'membre', 'lecteur', 'information'):
        return jsonify({'ok': False, 'error': 'Role invalide'}), 400
    login = email.split('@')[0].lower()
    try:
        add_member(login, nom, email, trigramme, role)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@main_bp.route('/api/membres/<int:id>/role', methods=['POST'])
@require_admin
def api_change_role(id):
    d = request.get_json()
    new_role = d.get('role') if d else None
    if not new_role:
        return jsonify({'ok': False, 'error': 'Role requis'}), 400
    try:
        update_member_role(id, new_role)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@main_bp.route('/api/membres/<int:id>/emails', methods=['POST'])
@require_admin
def api_update_member_emails(id):
    data = request.get_json(force=True)
    try:
        update_member_emails(id, data.get('emails_secondaires', '').strip() or None)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@main_bp.route('/api/membres/<int:id>/date_fin', methods=['POST'])
@require_admin
def api_update_member_date_fin(id):
    data = request.get_json(force=True)
    update_member_date_fin(id, data.get('date_fin', '').strip() or None)
    return jsonify({'ok': True})


@main_bp.route('/api/membres/<int:id>/remove', methods=['POST'])
@require_admin
def api_remove_member(id):
    try:
        remove_member(id, session.get('user_login', ''))
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
