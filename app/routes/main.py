"""
Blueprint principal : accueil, selection de projet, vues Globale, Categorie, Indicateur.
"""

from datetime import date
from flask import Blueprint, render_template, abort, request, jsonify, session, redirect, url_for
from app.database.db import load_projects, get_project_by_id, set_active_project
from app.services.indicateur_service import (
    get_global_data,
    get_categorie_data,
    get_indicateur_data,
    get_global_counts,
    get_global_drill_data,
    get_categorie_drill_data,
    get_step_layer_values,
    get_step_layer_values_cat,
    save_step as svc_save_step,
)

main_bp = Blueprint('main', __name__)

# Couleurs JS disponibles dans tous les templates
COL = {
    'grey': '#6b7280', 'green': '#22c55e', 'yellow': '#eab308',
    'orange': '#f97316', 'red': '#dc2626'
}
COL_LABEL = {
    'grey': 'Aucun', 'green': 'Validé', 'yellow': 'En cours',
    'orange': 'Warning', 'red': 'Blocage'
}

# Routes exclues du guard projet actif
_OPEN_ROUTES = ('main.accueil', 'main.select_project', 'static')


@main_bp.before_request
def require_active_project():
    """Redirige vers l'accueil si aucun projet n'est selectionne."""
    if request.endpoint in _OPEN_ROUTES:
        return
    if request.endpoint and request.endpoint.startswith('static'):
        return
    if 'project_id' not in session:
        return redirect(url_for('main.accueil'))
    # Re-armer le module db avec le bon chemin (apres redemarrage serveur)
    project = get_project_by_id(session['project_id'])
    if project is None:
        session.clear()
        return redirect(url_for('main.accueil'))
    set_active_project(project['db_file'])


@main_bp.route('/')
def accueil():
    projects = load_projects()
    return render_template('accueil.html', projects=projects)


@main_bp.route('/projet/<project_id>')
def select_project(project_id):
    project = get_project_by_id(project_id)
    if project is None:
        abort(404)
    set_active_project(project['db_file'])
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
