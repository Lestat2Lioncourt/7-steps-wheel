// ===================================================================
// Roue CSI - Referentiel : filtrage client-side
// Depends on COL global from wheel.js
// ===================================================================

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
