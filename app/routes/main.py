"""
Blueprint principal : accueil, selection client/projet, vues.
Adapte pour PostgreSQL multi-client/multi-projet.
Authentification par email + mot de passe, invitations, SSO Microsoft (optionnel).
"""

from datetime import date
from functools import wraps
from flask import Blueprint, render_template, abort, request, jsonify, session, redirect, url_for
from app.database.db import (
    load_clients, get_client_by_id, get_client_by_schema,
    create_client, update_client, delete_client,
    load_projects, get_project_by_id, create_project, update_project, delete_project,
    set_active_context, get_active_project_id,
    get_connection, get_connection_common,
    add_client_member,
    migrate_client_schema,
    BASE_DIR,
)
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
    get_project_ciblage_conformite,
    save_project_ciblage_conformite,
    get_categorie_ciblage_conformite,
    save_categorie_ciblage_conformite,
    get_indicateur_ciblage_conformite,
    save_indicateur_ciblage_conformite,
)
from app.services.action_service import (
    get_actions_for_indicator,
    get_actions_for_categorie,
    get_actions_for_global,
    get_parent_breadcrumb,
    create_action,
    update_action_status,
    update_action,
    delete_action,
    KANBAN_COLUMNS,
    KANBAN_LABELS,
)
from app.services.identity_service import (
    ensure_user_in_db,
    add_user_to_project,
    suggest_trigramme,
    create_placeholder_user,
)
from app.services.auth_service import (
    verify_password,
    is_setup_needed,
    create_initial_admin,
    is_sso_enabled,
    get_msal_auth_url,
    complete_msal_flow,
    find_user_by_email,
    create_invitation,
    validate_invitation,
    consume_invitation,
)
from app.services.member_service import (
    get_all_members,
    add_member,
    update_member,
    update_member_role,
    update_member_emails,
    update_member_date_fin,
    remove_member,
)

main_bp = Blueprint('main', __name__)

# Cache des schemas deja migres (evite de re-executer schema_client.sql a chaque requete)
_migrated_schemas = set()


def _activate_project(client_schema, project_id):
    """Active un client + projet : positionne le contexte et applique les migrations si besoin."""
    set_active_context(client_schema, project_id)
    if client_schema not in _migrated_schemas:
        migrate_client_schema(client_schema)
        _migrated_schemas.add(client_schema)


def _get_current_user_id():
    """Retourne le user_id de l'utilisateur courant (depuis common.utilisateurs).
    Ne cree pas de compte a la volee."""
    conn = get_connection_common()
    try:
        row = conn.execute(
            "SELECT id FROM utilisateurs WHERE login = %s",
            (session['user_login'],)
        ).fetchone()
        return row['id'] if row else None
    finally:
        conn.close()


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

# Routes exclues des guards (pas besoin de client+projet actif)
_OPEN_ROUTES = (
    'main.accueil', 'main.select_project',
    'main.create_client_route', 'main.create_project_route',
    'main.update_client_route', 'main.delete_client_route',
    'main.update_project_route', 'main.delete_project_route',
    'main.login', 'main.logout',
    'main.setup', 'main.invitation',
    'main.sso_login', 'main.sso_callback',
    'main.api_trigramme_suggest', 'static',
)


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
    """Redirige vers login si pas identifie, puis vers accueil si pas de client+projet."""
    if request.endpoint in _OPEN_ROUTES:
        return
    if request.endpoint and request.endpoint.startswith('static'):
        return

    # 1. Identite requise (session uniquement, plus de fichier identity.json)
    if 'user_login' not in session:
        return redirect(url_for('main.login'))

    # 2. Client + Projet actif requis
    if 'client_schema' not in session or 'project_id' not in session:
        return redirect(url_for('main.accueil'))

    # 3. Verifier que le client existe
    client = get_client_by_schema(session['client_schema'])
    if not client:
        session.pop('client_id', None)
        session.pop('client_schema', None)
        session.pop('client_name', None)
        session.pop('project_id', None)
        session.pop('project_name', None)
        return redirect(url_for('main.accueil'))

    # 4. Activer le contexte (search_path + migration si besoin)
    _activate_project(session['client_schema'], session['project_id'])

    # 5. Verifier que le projet existe
    project = get_project_by_id(session['project_id'])
    if not project:
        session.pop('project_id', None)
        session.pop('project_name', None)
        return redirect(url_for('main.accueil'))

    # 6. Verifier que l'utilisateur est membre du projet
    role = _resolve_role(ensure_user_in_db(session['user_login'], session['user_nom'],
                             session.get('user_email', ''), session.get('user_trigramme', '')))
    if role is None or role == 'information':
        session.pop('project_id', None)
        session.pop('project_name', None)
        session.pop('user_role', None)
        session.pop('user_real_role', None)
        error = 'info_only' if role == 'information' else 'non_membre'
        return redirect(url_for('main.accueil', error=error))
    # Preserver le switch de role si actif (admin temporairement en mode membre)
    if session.get('user_real_role') == 'admin' and role == 'admin':
        pass  # Garder user_role tel quel (mode membre switche)
    else:
        session['user_role'] = role
        session.pop('user_real_role', None)


# -------------------------------------------------------------------
# Login / Logout / Setup / Invitation / SSO
# -------------------------------------------------------------------
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect vers setup si aucun utilisateur
    if is_setup_needed():
        return redirect(url_for('main.setup'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        if not email or not password:
            return render_template('login.html', error='Email et mot de passe requis.',
                                   sso_available=is_sso_enabled(), prefill_email=email)

        user = verify_password(email, password)
        if not user:
            return render_template('login.html', error='Identifiants incorrects.',
                                   sso_available=is_sso_enabled(), prefill_email=email)

        session['user_login'] = user['login']
        session['user_nom'] = user['nom']
        session['user_email'] = user['email']
        session['user_trigramme'] = user['trigramme']
        return redirect(url_for('main.accueil'))

    # GET : si deja connecte, aller a l'accueil
    if 'user_login' in session:
        return redirect(url_for('main.accueil'))

    return render_template('login.html', error=None,
                           sso_available=is_sso_enabled(), prefill_email='')


@main_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))


@main_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    """Wizard de creation du premier administrateur."""
    if not is_setup_needed():
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        nom = request.form.get('nom', '').strip()
        trigramme = request.form.get('trigramme', '').strip().upper()
        password = request.form.get('password', '').strip()
        password2 = request.form.get('password2', '').strip()

        error = None
        if not email or not nom or not password:
            error = 'Tous les champs sont requis.'
        elif len(password) < 6:
            error = 'Le mot de passe doit contenir au moins 6 caracteres.'
        elif password != password2:
            error = 'Les mots de passe ne correspondent pas.'

        if error:
            return render_template('setup.html', error=error,
                                   prefill={'email': email, 'nom': nom, 'trigramme': trigramme})

        user = create_initial_admin(email, nom, trigramme, password)
        session['user_login'] = user['login']
        session['user_nom'] = user['nom']
        session['user_email'] = user['email'] or ''
        session['user_trigramme'] = user['trigramme'] or ''
        return redirect(url_for('main.accueil'))

    return render_template('setup.html', error=None, prefill={})


@main_bp.route('/invitation/<token>', methods=['GET', 'POST'])
def invitation(token):
    """Activation de compte par lien d'invitation."""
    inv = validate_invitation(token)

    if request.method == 'POST':
        if not inv:
            return render_template('invitation.html', valid=False)

        nom = request.form.get('nom', '').strip()
        trigramme = request.form.get('trigramme', '').strip().upper()
        password = request.form.get('password', '').strip()
        password2 = request.form.get('password2', '').strip()

        error = None
        if not password:
            error = 'Le mot de passe est requis.'
        elif len(password) < 6:
            error = 'Le mot de passe doit contenir au moins 6 caracteres.'
        elif password != password2:
            error = 'Les mots de passe ne correspondent pas.'

        if error:
            return render_template('invitation.html', valid=True, inv=inv, error=error,
                                   prefill={'nom': nom, 'trigramme': trigramme})

        user = consume_invitation(inv['id'], password, nom=nom or None, trigramme=trigramme or None)
        if user:
            session['user_login'] = user['login']
            session['user_nom'] = user['nom']
            session['user_email'] = user['email'] or ''
            session['user_trigramme'] = user['trigramme'] or ''
            return redirect(url_for('main.accueil'))

        return render_template('invitation.html', valid=False)

    # GET
    if not inv:
        return render_template('invitation.html', valid=False)
    return render_template('invitation.html', valid=True, inv=inv, error=None, prefill={})


# --- SSO Microsoft ---
@main_bp.route('/sso/login')
def sso_login():
    """Initie le flow OAuth2 Microsoft."""
    if not is_sso_enabled():
        return redirect(url_for('main.login'))
    redirect_uri = url_for('main.sso_callback', _external=True)
    auth_url, flow = get_msal_auth_url(redirect_uri)
    if not auth_url:
        return redirect(url_for('main.login'))
    session['sso_flow'] = flow
    return redirect(auth_url)


@main_bp.route('/sso/callback')
def sso_callback():
    """Callback OAuth2 Microsoft."""
    if not is_sso_enabled():
        return redirect(url_for('main.login'))
    flow = session.pop('sso_flow', None)
    if not flow:
        return redirect(url_for('main.login'))

    claims = complete_msal_flow(flow, request.args)
    if not claims:
        return redirect(url_for('main.login'))

    email = claims.get('preferred_username', '').lower()
    if not email:
        return redirect(url_for('main.login'))

    user = find_user_by_email(email)
    if not user:
        return render_template('login.html', error='Aucun compte associe a cet email Microsoft.',
                               sso_available=True, prefill_email=email)

    session['user_login'] = user['login']
    session['user_nom'] = user['nom']
    session['user_email'] = user['email'] or ''
    session['user_trigramme'] = user['trigramme'] or ''
    return redirect(url_for('main.accueil'))


# -------------------------------------------------------------------
# Accueil : liste des clients et projets
# -------------------------------------------------------------------
@main_bp.route('/')
def accueil():
    if 'user_login' not in session:
        return redirect(url_for('main.login'))

    # Charger tous les clients et leurs projets
    clients = load_clients()
    for c in clients:
        c['projects'] = load_projects(c['schema_name'])

    return render_template('accueil.html', clients=clients,
                           user_nom=session.get('user_nom', ''))


# -------------------------------------------------------------------
# Gestion des clients
# -------------------------------------------------------------------
@main_bp.route('/client/nouveau', methods=['POST'])
def create_client_route():
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('main.accueil'))
    client = create_client(name)
    # Ajouter le createur comme admin du client
    user_id = _get_current_user_id()
    if user_id:
        add_client_member(client['id'], user_id, 'admin')
    return redirect(url_for('main.accueil'))


@main_bp.route('/client/<int:client_id>/modifier', methods=['POST'])
def update_client_route(client_id):
    name = request.form.get('name', '').strip()
    if not name:
        return redirect(url_for('main.accueil'))
    update_client(client_id, nom=name)
    if session.get('client_id') == client_id:
        session['client_name'] = name
    return redirect(url_for('main.accueil'))


@main_bp.route('/client/<int:client_id>/supprimer', methods=['POST'])
def delete_client_route(client_id):
    delete_client(client_id)
    if session.get('client_id') == client_id:
        session.pop('client_id', None)
        session.pop('client_schema', None)
        session.pop('client_name', None)
        session.pop('project_id', None)
        session.pop('project_name', None)
    return redirect(url_for('main.accueil'))


# -------------------------------------------------------------------
# Gestion des projets
# -------------------------------------------------------------------
@main_bp.route('/client/<int:client_id>/projet/nouveau', methods=['POST'])
def create_project_route(client_id):
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip() or None
    if not name:
        return redirect(url_for('main.accueil'))

    client = get_client_by_id(client_id)
    if not client:
        return redirect(url_for('main.accueil'))

    project = create_project(name, client['schema_name'], description=description)

    # Activer le contexte pour le nouveau projet
    _activate_project(client['schema_name'], project['id'])

    # Le createur est automatiquement admin du projet
    add_user_to_project(session['user_login'], session['user_nom'],
                        session.get('user_email', ''), session.get('user_trigramme', ''),
                        role='admin')

    session['client_id'] = client_id
    session['client_schema'] = client['schema_name']
    session['client_name'] = client['nom']
    session['project_id'] = project['id']
    session['project_name'] = project['nom']
    session['user_role'] = 'admin'
    return redirect(url_for('main.vue_globale'))


@main_bp.route('/client/<int:client_id>/projet/<int:project_id>')
def select_project(client_id, project_id):
    client = get_client_by_id(client_id)
    if not client:
        abort(404)
    project = get_project_by_id(project_id, client['schema_name'])
    if not project:
        abort(404)

    _activate_project(client['schema_name'], project_id)

    # Verifier si l'utilisateur est membre
    role = _resolve_role(ensure_user_in_db(session['user_login'], session['user_nom'],
                             session.get('user_email', ''), session.get('user_trigramme', '')))
    if role is None:
        return redirect(url_for('main.accueil', error='non_membre'))

    session['client_id'] = client_id
    session['client_schema'] = client['schema_name']
    session['client_name'] = client['nom']
    session['project_id'] = project_id
    session['project_name'] = project['nom']
    session['user_role'] = role
    return redirect(url_for('main.vue_globale'))


@main_bp.route('/client/<int:client_id>/projet/<int:project_id>/modifier', methods=['POST'])
def update_project_route(client_id, project_id):
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    if not name:
        return redirect(url_for('main.accueil'))
    client = get_client_by_id(client_id)
    if not client:
        return redirect(url_for('main.accueil'))
    update_project(project_id, nom=name, description=description, client_schema=client['schema_name'])
    if session.get('project_id') == project_id:
        session['project_name'] = name
    return redirect(url_for('main.accueil'))


@main_bp.route('/client/<int:client_id>/projet/<int:project_id>/supprimer', methods=['POST'])
def delete_project_route(client_id, project_id):
    client = get_client_by_id(client_id)
    if client:
        delete_project(project_id, client_schema=client['schema_name'])
    if session.get('project_id') == project_id:
        session.pop('project_id', None)
        session.pop('project_name', None)
    return redirect(url_for('main.accueil'))


# -------------------------------------------------------------------
# Vues metier : Global, Categorie, Indicateur, Referentiel
# -------------------------------------------------------------------
@main_bp.route('/global')
def vue_globale():
    data = get_global_data()
    drill_data = get_global_drill_data()
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
    color = d.get('color')
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
# Ciblage / Conformite — 3 niveaux (projet, categorie, indicateur)
# -------------------------------------------------------------------
@main_bp.route('/api/projet/ciblage', methods=['GET'])
def api_get_projet_ciblage():
    return jsonify(get_project_ciblage_conformite())


@main_bp.route('/api/projet/ciblage', methods=['POST'])
@require_write
def api_save_projet_ciblage():
    d = request.get_json()
    save_project_ciblage_conformite(d)
    return jsonify({'ok': True})


@main_bp.route('/api/categorie/<int:cat_id>/ciblage', methods=['GET'])
def api_get_categorie_ciblage(cat_id):
    return jsonify(get_categorie_ciblage_conformite(cat_id))


@main_bp.route('/api/categorie/<int:cat_id>/ciblage', methods=['POST'])
@require_write
def api_save_categorie_ciblage(cat_id):
    d = request.get_json()
    save_categorie_ciblage_conformite(cat_id, d)
    return jsonify({'ok': True})


@main_bp.route('/api/indicateur/<int:ind_id>/ciblage', methods=['GET'])
def api_get_indicateur_ciblage(ind_id):
    return jsonify(get_indicateur_ciblage_conformite(ind_id))


@main_bp.route('/api/indicateur/<int:ind_id>/ciblage', methods=['POST'])
@require_write
def api_save_indicateur_ciblage(ind_id):
    d = request.get_json()
    save_indicateur_ciblage_conformite(ind_id, d)
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


def _render_kanban(data, actions, kanban_level, etapes, parent_id=None, parent_breadcrumb=None):
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
        parent_id=parent_id,
        parent_breadcrumb=parent_breadcrumb or [],
    )


@main_bp.route('/global/kanban')
def vue_kanban_global():
    parent_id = request.args.get('parent', type=int)
    data = get_global_data()
    actions = get_actions_for_global(parent_id=parent_id)
    breadcrumb = get_parent_breadcrumb(parent_id) if parent_id else []
    return _render_kanban(data, actions, 'global', _kanban_common(),
                          parent_id=parent_id, parent_breadcrumb=breadcrumb)


@main_bp.route('/categorie/<int:id>/kanban')
def vue_kanban_categorie(id):
    parent_id = request.args.get('parent', type=int)
    data = get_categorie_data(id)
    if data is None:
        abort(404)
    actions = get_actions_for_categorie(id, parent_id=parent_id)
    breadcrumb = get_parent_breadcrumb(parent_id) if parent_id else []
    return _render_kanban(data, actions, 'categorie', _kanban_common(),
                          parent_id=parent_id, parent_breadcrumb=breadcrumb)


@main_bp.route('/indicateur/<int:id>/kanban')
def vue_kanban(id):
    parent_id = request.args.get('parent', type=int)
    data = get_indicateur_data(id)
    if data is None:
        abort(404)
    actions = get_actions_for_indicator(id, data['categorie']['id'], parent_id=parent_id)
    breadcrumb = get_parent_breadcrumb(parent_id) if parent_id else []
    return _render_kanban(data, actions, 'indicateur', _kanban_common(),
                          parent_id=parent_id, parent_breadcrumb=breadcrumb)


@main_bp.route('/api/action/create', methods=['POST'])
@require_write
def api_action_create():
    d = request.get_json()
    if not d or not d.get('titre') or not d.get('assignee_login') or not d.get('etape'):
        return jsonify({'ok': False, 'error': 'Missing parameters'}), 400
    # Si assignee_login contient @ → creer un placeholder
    if '@' in d['assignee_login']:
        d['assignee_login'] = create_placeholder_user(d['assignee_login'])
    # parent_id pour sous-taches
    if d.get('parent_id'):
        d['parent_id'] = int(d['parent_id'])
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
    projet_id = get_active_project_id()
    conn = get_connection()
    try:
        if q:
            like = f"%{q}%"
            users = conn.execute("""
                SELECT u.login, u.nom, u.email, u.trigramme
                FROM utilisateurs u
                JOIN projet_membres pm ON pm.user_id = u.id
                WHERE pm.projet_id = %s
                    AND (u.login ILIKE %s OR u.nom ILIKE %s
                         OR u.email ILIKE %s OR u.trigramme ILIKE %s)
                ORDER BY u.nom LIMIT 20
            """, (projet_id, like, like, like, like)).fetchall()
        else:
            users = conn.execute("""
                SELECT u.login, u.nom, u.email, u.trigramme
                FROM utilisateurs u
                JOIN projet_membres pm ON pm.user_id = u.id
                WHERE pm.projet_id = %s
                ORDER BY u.nom LIMIT 20
            """, (projet_id,)).fetchall()
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
def vue_membres():
    members = get_all_members()
    return render_template(
        'membres.html',
        members=members,
        active_tab='membres',
        global_counts=get_global_counts(),
        COL=COL,
        COL_LABEL=COL_LABEL,
        project_name=session.get('project_name', 'ROUE CSI'),
        client_name=session.get('client_name', ''),
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
    want_invite = d.get('generate_invitation', False)
    try:
        add_member(login, nom, email, trigramme, role)
        invitation_url = None
        if want_invite:
            # Recuperer le user_id du membre nouvellement cree
            conn = get_connection()
            try:
                row = conn.execute(
                    "SELECT id FROM utilisateurs WHERE login = %s OR email = %s",
                    (login, email)
                ).fetchone()
            finally:
                conn.close()
            if row:
                created_by = _get_current_user_id()
                token = create_invitation(row['id'], created_by)
                invitation_url = url_for('main.invitation', token=token, _external=True)
        return jsonify({'ok': True, 'invitation_url': invitation_url})
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


@main_bp.route('/api/membres/<int:id>', methods=['PUT'])
@require_admin
def api_update_member(id):
    data = request.get_json(force=True)
    try:
        update_member(id, data)
        return jsonify({'ok': True})
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400


@main_bp.route('/api/membres/<int:id>/invitation', methods=['POST'])
@require_admin
def api_generate_invitation(id):
    """Genere un lien d'invitation pour un membre."""
    projet_id = get_active_project_id()
    conn = get_connection()
    try:
        pm = conn.execute(
            "SELECT user_id FROM projet_membres WHERE id = %s AND projet_id = %s",
            (id, projet_id)
        ).fetchone()
        if not pm:
            return jsonify({'ok': False, 'error': 'Membre introuvable.'}), 404
        user_id = pm['user_id']
    finally:
        conn.close()

    created_by = _get_current_user_id()
    token = create_invitation(user_id, created_by)
    inv_url = url_for('main.invitation', token=token, _external=True)
    return jsonify({'ok': True, 'url': inv_url})


@main_bp.route('/api/switch-role', methods=['POST'])
def api_switch_role():
    real_role = session.get('user_real_role') or session.get('user_role')
    if real_role != 'admin':
        return jsonify({'ok': False, 'error': 'Reserve aux administrateurs'}), 403
    current = session.get('user_role')
    if current == 'admin':
        session['user_real_role'] = 'admin'
        session['user_role'] = 'membre'
    else:
        session['user_role'] = session.pop('user_real_role', 'admin')
    return jsonify({'ok': True, 'role': session['user_role']})
