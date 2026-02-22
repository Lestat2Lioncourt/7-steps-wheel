// ===================================================================
// Roue CSI - Referentiel : filtrage client-side + CRUD categories
// Depends on COL global from wheel.js
// ===================================================================

function _formatSeuil(s) {
    if (s === null || s === undefined || s === '') return '-';
    s = parseInt(s);
    if (isNaN(s) || s <= 0) return '-';
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = s % 60;
    var parts = [];
    if (h > 0) parts.push(h + 'h');
    if (m > 0) parts.push(m + 'min');
    if (sec > 0 && h === 0) parts.push(sec + 's');
    return parts.join(' ') || '0s';
}

function initReferentiel() {
    // Attach events
    var search = document.getElementById('ref-search');
    var catFilter = document.getElementById('ref-cat-filter');
    var typeFilter = document.getElementById('ref-type-filter');
    var etatFilter = document.getElementById('ref-etat-filter');

    if (search) search.addEventListener('input', filterRef);
    if (catFilter) catFilter.addEventListener('change', filterRef);
    if (typeFilter) typeFilter.addEventListener('change', filterRef);
    if (etatFilter) etatFilter.addEventListener('change', filterRef);

    // Format seuil values
    document.querySelectorAll('.ref-seuil').forEach(function(el) {
        var raw = el.getAttribute('data-seuil');
        el.textContent = _formatSeuil(raw);
    });

    updateRefStats();
}

function filterRef() {
    var search = (document.getElementById('ref-search').value || '').toLowerCase();
    var cat = document.getElementById('ref-cat-filter').value;
    var type = document.getElementById('ref-type-filter').value;
    var etat = document.getElementById('ref-etat-filter').value;

    var rows = document.querySelectorAll('#ref-body .ref-row');
    rows.forEach(function(tr) {
        var matchSearch = true;
        if (search) {
            var code = (tr.getAttribute('data-code') || '').toLowerCase();
            var desc = (tr.getAttribute('data-desc') || '').toLowerCase();
            matchSearch = code.indexOf(search) !== -1 || desc.indexOf(search) !== -1;
        }
        var matchCat = (cat === 'all' || tr.getAttribute('data-cat') === cat);
        var matchType = (type === 'all' || tr.getAttribute('data-type') === type);
        var matchEtat = (etat === 'all' || tr.getAttribute('data-etat') === etat);

        if (matchSearch && matchCat && matchType && matchEtat) {
            tr.classList.remove('hidden');
        } else {
            tr.classList.add('hidden');
        }
    });

    updateRefStats();
}

function updateRefStats() {
    var rows = document.querySelectorAll('#ref-body .ref-row');
    var counts = { green: 0, yellow: 0, orange: 0, red: 0, grey: 0 };
    var visible = 0;
    var total = rows.length;

    rows.forEach(function(tr) {
        if (!tr.classList.contains('hidden')) {
            var w = tr.getAttribute('data-worst') || 'grey';
            counts[w] = (counts[w] || 0) + 1;
            visible++;
        }
    });

    var el = document.getElementById('ref-stats');
    if (!el) return;

    el.innerHTML =
        '<span class="ref-stat"><span class="icd" style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + COL.green + '"></span><span class="n">' + counts.green + '</span> Conf.</span>' +
        '<span class="ref-stat"><span class="icd" style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + COL.yellow + '"></span><span class="n">' + counts.yellow + '</span> En cours</span>' +
        '<span class="ref-stat"><span class="icd" style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + COL.orange + '"></span><span class="n">' + counts.orange + '</span> Warn.</span>' +
        '<span class="ref-stat"><span class="icd" style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + COL.red + '"></span><span class="n">' + counts.red + '</span> Bloc.</span>' +
        '<span class="ref-stat"><span class="icd" style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + COL.grey + '"></span><span class="n">' + counts.grey + '</span> N/E</span>' +
        '<span class="ref-stat" style="margin-left:auto;color:#a0c4ff;font-weight:600">' + visible + '/' + total + '</span>';
}

function qfCat(el, cat) {
    // Quick filter from sidebar: sync the dropdown + filter
    document.getElementById('ref-cat-filter').value = cat;
    filterRef();
    // Update sidebar active state
    var items = document.querySelectorAll('.sidebar-item');
    items.forEach(function(i) { i.classList.remove('active'); });
    el.classList.add('active');
}

// -------------------------------------------------------------------
// CRUD Categories
// -------------------------------------------------------------------
function openCategoryModal(catId, catNom) {
    var overlay = document.getElementById('category-modal-overlay');
    if (!overlay) return;
    document.getElementById('category-modal-id').value = catId || '';
    document.getElementById('category-modal-nom').value = catNom || '';
    document.getElementById('category-modal-title').textContent =
        catId ? 'Renommer la categorie' : 'Ajouter une categorie';
    overlay.classList.add('open');
    document.getElementById('category-modal-nom').focus();
}

function closeCategoryModal() {
    var overlay = document.getElementById('category-modal-overlay');
    if (overlay) overlay.classList.remove('open');
}

function submitCategory() {
    var catId = document.getElementById('category-modal-id').value;
    var nom = document.getElementById('category-modal-nom').value.trim();
    if (!nom) return;

    var url, method;
    if (catId) {
        url = '/api/categories/' + catId;
        method = 'PUT';
    } else {
        url = '/api/categories';
        method = 'POST';
    }

    fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nom: nom })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok) {
            location.reload();
        } else {
            alert(data.error || 'Erreur');
        }
    })
    .catch(function() { alert('Erreur reseau'); });
}

function deleteCategory(catId, catNom) {
    if (!confirm('Supprimer la categorie "' + catNom + '" ?')) return;

    fetch('/api/categories/' + catId, { method: 'DELETE' })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok) {
            location.reload();
        } else {
            alert(data.error || 'Erreur');
        }
    })
    .catch(function() { alert('Erreur reseau'); });
}

function reorderCategory(catId, direction) {
    fetch('/api/categories/' + catId + '/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ direction: direction })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok) {
            location.reload();
        } else {
            alert(data.error || 'Erreur');
        }
    })
    .catch(function() { alert('Erreur reseau'); });
}
