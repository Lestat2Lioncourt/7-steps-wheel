/**
 * Kanban board — drag & drop + modale CRUD + assignee autocomplete
 * Supporte les 3 niveaux : global, categorie, indicateur
 */

var _saving = false;
var _acTimer = null;

function initKanban() {
    var isLecteur = window._userRole === 'lecteur';

    document.querySelectorAll('.kanban-cards').forEach(function(el) {
        new Sortable(el, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'sortable-ghost',
            disabled: isLecteur,
            onEnd: function(evt) {
                var cardEl = evt.item;
                var actionId = cardEl.getAttribute('data-id');
                var newStatus = evt.to.closest('.kanban-column').getAttribute('data-status');
                var oldStatus = evt.from.closest('.kanban-column').getAttribute('data-status');

                if (newStatus === oldStatus) return;

                fetch('/api/action/' + actionId + '/status', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({statut: newStatus})
                })
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (!data.ok) {
                        evt.from.appendChild(cardEl);
                    }
                    updateCounts();
                })
                .catch(function() {
                    evt.from.appendChild(cardEl);
                });
            }
        });
    });

    // Click on cards to edit
    document.querySelectorAll('.kanban-card').forEach(function(card) {
        card.addEventListener('click', function() {
            openActionModal(card.getAttribute('data-id'));
        });
    });

    initAssigneeAutocomplete();

    // Auto-open creation modal si ?new=1&etape=X dans l'URL
    var params = new URLSearchParams(location.search);
    if (params.get('new') === '1') {
        openActionModal(null);
        var etape = params.get('etape');
        if (etape) {
            document.getElementById('km-etape').value = etape;
        }
        // Nettoyer l'URL sans recharger
        history.replaceState(null, '', location.pathname);
    }
}

function updateCounts() {
    document.querySelectorAll('.kanban-column').forEach(function(col) {
        var count = col.querySelectorAll('.kanban-card').length;
        var badge = col.querySelector('.kcount');
        if (badge) badge.textContent = count;
        var empty = col.querySelector('.kanban-empty');
        if (empty) empty.style.display = count === 0 ? '' : 'none';
    });
}

/* ---- Assignee autocomplete ---- */

function initAssigneeAutocomplete() {
    var input = document.getElementById('km-assignee-input');
    var hidden = document.getElementById('km-assignee');
    var dropdown = document.getElementById('km-assignee-dropdown');
    if (!input || !hidden || !dropdown) return;

    input.addEventListener('input', function() {
        hidden.value = '';
        clearTimeout(_acTimer);
        _acTimer = setTimeout(function() { _searchUsers(input.value.trim()); }, 200);
    });

    input.addEventListener('focus', function() {
        _searchUsers(input.value.trim());
    });

    // Close dropdown on outside click
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.style.display = 'none';
        }
    });
}

function _searchUsers(q) {
    var dropdown = document.getElementById('km-assignee-dropdown');
    fetch('/api/users/search?q=' + encodeURIComponent(q))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            _renderDropdown(data.users, q);
        });
}

function _renderDropdown(users, query) {
    var dropdown = document.getElementById('km-assignee-dropdown');
    dropdown.innerHTML = '';

    users.forEach(function(u) {
        var opt = document.createElement('div');
        opt.className = 'assignee-option';
        var triHtml = u.trigramme ? '<span class="ao-tri">' + _esc(u.trigramme) + '</span>' : '';
        var emailHtml = u.email ? '<span class="ao-email">' + _esc(u.email) + '</span>' : '';
        opt.innerHTML = triHtml + '<span class="ao-nom">' + _esc(u.nom) + '</span>' + emailHtml;
        opt.addEventListener('click', function() {
            _selectAssignee(u.login, u.nom, u.trigramme);
        });
        dropdown.appendChild(opt);
    });

    // If query looks like an email and no exact email match, offer "nouveau"
    if (query && query.indexOf('@') !== -1) {
        var exactMatch = users.some(function(u) { return u.email === query || u.login === query; });
        if (!exactMatch) {
            var opt = document.createElement('div');
            opt.className = 'assignee-option new-email';
            opt.innerHTML = '<span class="ao-nom">Assigner a ' + _esc(query) + ' (nouveau)</span>';
            opt.addEventListener('click', function() {
                _selectAssignee(query, query, '');
            });
            dropdown.appendChild(opt);
        }
    }

    dropdown.style.display = dropdown.children.length > 0 ? '' : 'none';
}

function _selectAssignee(login, nom, tri) {
    document.getElementById('km-assignee').value = login;
    var label = (tri ? '[' + tri + '] ' : '') + nom;
    document.getElementById('km-assignee-input').value = label;
    document.getElementById('km-assignee-dropdown').style.display = 'none';
}

function _esc(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

/* ---- Niveau tabs ---- */

function selectNiveau(tab) {
    var tabs = document.getElementById('km-niveau-tabs');
    tabs.querySelectorAll('.modal-tab').forEach(function(t) { t.classList.remove('active'); });
    tab.classList.add('active');
    document.getElementById('km-niveau').value = tab.getAttribute('data-niveau');
}

function _getSelectedNiveau() {
    return document.getElementById('km-niveau').value;
}

function _resetNiveauTabs() {
    var tabs = document.getElementById('km-niveau-tabs');
    if (!tabs) return;
    var allTabs = tabs.querySelectorAll('.modal-tab');
    allTabs.forEach(function(t) { t.classList.remove('active'); });
    // Select the first tab (= current kanban level) by default
    if (allTabs.length > 0) allTabs[0].classList.add('active');
    document.getElementById('km-niveau').value = allTabs.length > 0
        ? allTabs[0].getAttribute('data-niveau')
        : window._kanbanLevel;
}

/* ---- Modal ---- */

function openActionModal(actionId) {
    var overlay = document.getElementById('kanban-modal-overlay');
    var title = document.getElementById('km-title');
    var form = document.getElementById('km-form');
    var deleteBtn = document.getElementById('km-delete');
    var saveBtn = document.getElementById('km-save');
    var inheritInfo = document.getElementById('km-inherit-info');
    var niveauTabs = document.getElementById('km-niveau-tabs');

    // Reset
    form.reset();
    document.getElementById('km-action-id').value = '';
    document.getElementById('km-assignee').value = '';
    document.getElementById('km-assignee-input').value = '';
    document.getElementById('km-assignee-dropdown').style.display = 'none';
    inheritInfo.style.display = 'none';
    saveBtn.disabled = false;
    saveBtn.textContent = 'Enregistrer';
    _saving = false;

    if (actionId) {
        // Edition: hide niveau tabs, show info if inherited
        var card = document.querySelector('.kanban-card[data-id="' + actionId + '"]');
        if (!card) return;
        title.textContent = 'Modifier l\'action';
        niveauTabs.style.display = 'none';
        document.getElementById('km-action-id').value = actionId;
        document.getElementById('km-titre').value = card.getAttribute('data-titre') || '';
        document.getElementById('km-etape').value = card.getAttribute('data-etape') || '1';
        document.getElementById('km-commentaire').value = card.getAttribute('data-commentaire') || '';
        document.getElementById('km-description').value = card.getAttribute('data-description') || '';
        document.getElementById('km-date-debut').value = card.getAttribute('data-date-debut') || '';
        document.getElementById('km-date-fin').value = card.getAttribute('data-date-fin') || '';

        // Pre-fill assignee autocomplete
        var assigneeLogin = card.getAttribute('data-assignee') || '';
        var assigneeNom = card.getAttribute('data-assignee-nom') || assigneeLogin;
        var assigneeTri = card.getAttribute('data-assignee-tri') || '';
        document.getElementById('km-assignee').value = assigneeLogin;
        var label = (assigneeTri ? '[' + assigneeTri + '] ' : '') + assigneeNom;
        document.getElementById('km-assignee-input').value = label;

        var niveau = card.getAttribute('data-niveau');
        document.getElementById('km-niveau').value = niveau;
        if (niveau !== window._kanbanLevel) {
            var labels = {global: 'Action globale', categorie: 'Action de categorie'};
            inheritInfo.textContent = (labels[niveau] || niveau) + ' — heritee. Modifiez-la depuis son niveau d\'origine.';
            inheritInfo.style.display = '';
        }
        deleteBtn.style.display = '';
    } else {
        // Creation: show niveau tabs
        title.textContent = 'Nouvelle action';
        deleteBtn.style.display = 'none';
        // Show tabs only if there are multiple choices (not global-level kanban)
        if (niveauTabs.querySelectorAll('.modal-tab').length > 1) {
            niveauTabs.style.display = '';
        } else {
            niveauTabs.style.display = 'none';
        }
        _resetNiveauTabs();
    }

    overlay.classList.add('open');
}

function closeActionModal() {
    document.getElementById('kanban-modal-overlay').classList.remove('open');
    document.getElementById('km-assignee-dropdown').style.display = 'none';
}

function _setLoading(loading) {
    var saveBtn = document.getElementById('km-save');
    _saving = loading;
    saveBtn.disabled = loading;
    saveBtn.textContent = loading ? 'Enregistrement...' : 'Enregistrer';
}

function saveAction() {
    if (_saving) return;

    var actionId = document.getElementById('km-action-id').value;
    var titre = document.getElementById('km-titre').value.trim();
    if (!titre) {
        document.getElementById('km-titre').focus();
        return;
    }

    // Assignee: prefer hidden value, fallback to input if it looks like an email
    var assignee = document.getElementById('km-assignee').value;
    if (!assignee) {
        var inputVal = document.getElementById('km-assignee-input').value.trim();
        if (inputVal && inputVal.indexOf('@') !== -1) {
            assignee = inputVal;
        }
    }
    if (!assignee) {
        document.getElementById('km-assignee-input').focus();
        return;
    }

    _setLoading(true);

    var payload = {
        titre: titre,
        etape: parseInt(document.getElementById('km-etape').value),
        assignee_login: assignee,
        commentaire: document.getElementById('km-commentaire').value.trim() || null,
        description: document.getElementById('km-description').value.trim() || null,
        date_debut: document.getElementById('km-date-debut').value || null,
        date_fin: document.getElementById('km-date-fin').value || null,
    };

    if (actionId) {
        fetch('/api/action/' + actionId + '/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.ok) location.reload();
            else _setLoading(false);
        })
        .catch(function() { _setLoading(false); });
    } else {
        var niveau = _getSelectedNiveau();
        payload.niveau = niveau;
        if (niveau === 'indicateur') {
            payload.indicateur_id = window._kanbanIndicateurId;
        } else if (niveau === 'categorie') {
            payload.categorie_id = window._kanbanCategorieId;
        }
        payload.cree_par = window._kanbanUserLogin || 'admin';
        fetch('/api/action/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.ok) location.reload();
            else _setLoading(false);
        })
        .catch(function() { _setLoading(false); });
    }
}

function deleteAction() {
    if (_saving) return;
    var actionId = document.getElementById('km-action-id').value;
    if (!actionId) return;
    if (!confirm('Supprimer cette action ?')) return;

    _setLoading(true);

    fetch('/api/action/' + actionId + '/delete', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok) location.reload();
        else _setLoading(false);
    })
    .catch(function() { _setLoading(false); });
}
