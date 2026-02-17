// ===================================================================
// Roue CSI - Fonctions SVG
// Extrait et parametrise depuis prototype-consolide.html
// ===================================================================

const COL = {
    grey: '#6b7280', green: '#22c55e', yellow: '#eab308',
    orange: '#f97316', red: '#dc2626'
};
const COL_LABEL = {
    grey: 'Aucun', green: 'Valid\u00e9', yellow: 'En cours',
    orange: 'Warning', red: 'Blocage'
};
const STATUS_ORDER = ['green', 'yellow', 'orange', 'red', 'grey'];

const STEPS = [
    { label: "Ce qu'on\nVEUT",   short: "Ce qu'on VEUT",   tip: "Definir l'objectif de mesure" },
    { label: "Ce qu'on\nPEUT",   short: "Ce qu'on PEUT",   tip: "Ce qui est techniquement faisable" },
    { label: "COLLECTE",          short: "COLLECTE",         tip: "Collecte des donnees" },
    { label: "DATA\nPREP",       short: "DATA PREP",        tip: "Preparation des donnees" },
    { label: "DATA\nQUALITY",   short: "DATA QUALITY",     tip: "Qualite des donnees" },
    { label: "DATA VIZ\n& USAGE", short: "DATA VIZ & USAGE", tip: "Visualisation et exploitation" },
    { label: "BILAN",             short: "BILAN",            tip: "Bilan / revue" }
];

const LAYERS = {
    global:     { b: 'G', c: '#e94560', label: 'Global' },
    categorie:  { b: 'C', c: '#3a7bd5', label: 'Categorie' },
    indicateur: { b: 'I', c: '#8b5cf6', label: 'Indicateur' }
};

const svgNS = 'http://www.w3.org/2000/svg';
function mk(t) { return document.createElementNS(svgNS, t); }

// -------------------------------------------------------------------
// Couleur la pire parmi les 3 couches d'une etape
// -------------------------------------------------------------------
function worstColor(stepData) {
    const o = { grey: 0, green: 1, yellow: 2, orange: 3, red: 4 };
    let w = -1, wc = 'grey';
    ['global', 'categorie', 'indicateur'].forEach(k => {
        const c = stepData[k] ? stepData[k].color : null;
        if (c && o[c] > w) { w = o[c]; wc = c; }
    });
    return wc;
}

// -------------------------------------------------------------------
// Commentaires existants d'une etape (pour les bulles)
// -------------------------------------------------------------------
function layerComments(stepData) {
    const r = [];
    ['global', 'categorie', 'indicateur'].forEach(k => {
        const d = stepData[k];
        if (d && d.comment) {
            r.push({
                key: k,
                badge: LAYERS[k].b,
                bc: LAYERS[k].c,
                sc: d.color ? COL[d.color] : '#333',
                lines: d.comment.split('\n')
            });
        }
    });
    return r;
}

// -------------------------------------------------------------------
// Roue simple (vue globale / categorie)
// data : array de 7 noms de couleur ('green', 'red', ...)
// opts : { c1, c2, onClick(stepIndex) }
// -------------------------------------------------------------------
function drawSimpleWheel(svgId, data, opts) {
    opts = opts || {};
    const svg = document.getElementById(svgId);
    svg.innerHTML = '';
    const cx = 220, cy = 220, R = 155, rx = 48, ry = 33, sa = -90;

    // Arrow marker
    const defs = mk('defs');
    defs.innerHTML = '<marker id="a-' + svgId + '" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#3a7bd5"/></marker>';
    svg.appendChild(defs);

    // Positions
    const pos = [];
    for (let i = 0; i < 7; i++) {
        const a = (sa + i * 360 / 7) * Math.PI / 180;
        pos.push({ x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) });
    }

    // Arrow arcs
    for (let i = 0; i < 7; i++) {
        const a1 = (sa + i * 360 / 7 + 19) * Math.PI / 180;
        const a2 = (sa + (i + 1) * 360 / 7 - 19) * Math.PI / 180;
        const p = mk('path');
        p.setAttribute('d', 'M' + (cx + R * Math.cos(a1)) + ' ' + (cy + R * Math.sin(a1)) +
            ' A' + R + ' ' + R + ' 0 0 1 ' + (cx + R * Math.cos(a2)) + ' ' + (cy + R * Math.sin(a2)));
        p.setAttribute('class', 'arrow-path');
        p.setAttribute('marker-end', 'url(#a-' + svgId + ')');
        svg.appendChild(p);
    }

    // Ellipses + labels
    for (let i = 0; i < 7; i++) {
        const g = mk('g');
        g.setAttribute('class', 'step-ellipse');

        const ti = mk('title');
        ti.textContent = STEPS[i].short + ': ' + STEPS[i].tip;
        g.appendChild(ti);

        if (opts.onClick) {
            (function(idx) { g.onclick = function() { opts.onClick(idx); }; })(i);
        }

        const el = mk('ellipse');
        el.setAttribute('cx', pos[i].x);
        el.setAttribute('cy', pos[i].y);
        el.setAttribute('rx', rx);
        el.setAttribute('ry', ry);
        el.setAttribute('fill', COL[data[i]] || COL.grey);
        el.setAttribute('stroke', 'rgba(255,255,255,0.12)');
        el.setAttribute('stroke-width', '2');
        g.appendChild(el);

        const lines = STEPS[i].label.split('\n');
        const txt = mk('text');
        txt.setAttribute('class', 'step-label');
        txt.setAttribute('x', pos[i].x);
        txt.setAttribute('y', pos[i].y - (lines.length - 1) * 7);
        lines.forEach(function(l, li) {
            const ts = mk('tspan');
            ts.setAttribute('x', pos[i].x);
            ts.setAttribute('dy', li ? '14' : '0');
            ts.textContent = l;
            txt.appendChild(ts);
        });
        g.appendChild(txt);
        svg.appendChild(g);
    }

    // Center text
    if (opts.c1) {
        const t = mk('text');
        t.setAttribute('class', 'center-title');
        t.setAttribute('x', cx);
        t.setAttribute('y', cy - 8);
        t.textContent = opts.c1;
        svg.appendChild(t);
    }
    if (opts.c2) {
        const t = mk('text');
        t.setAttribute('class', 'center-date');
        t.setAttribute('x', cx);
        t.setAttribute('y', cy + 14);
        t.textContent = opts.c2;
        svg.appendChild(t);
    }
}

// -------------------------------------------------------------------
// Roue indicateur (avec bulles commentaires 3 couches)
// indData : array de 7 objets { global:{color,comment}, categorie:{...}, indicateur:{...} }
// opts : { centerCode, centerDate }
// -------------------------------------------------------------------
function drawIndicatorWheel(svgId, indData, opts) {
    opts = opts || {};
    const svg = document.getElementById(svgId);
    svg.innerHTML = '';
    const cx = 370, cy = 245, R = 150, rx = 48, ry = 33, sa = -90;

    // Arrow marker
    const defs = mk('defs');
    defs.innerHTML = '<marker id="a-ind-' + svgId + '" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#3a7bd5"/></marker>';
    svg.appendChild(defs);

    // Positions
    const pos = [];
    for (let i = 0; i < 7; i++) {
        const a = (sa + i * 360 / 7) * Math.PI / 180;
        pos.push({ x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) });
    }

    // Arrow arcs
    for (let i = 0; i < 7; i++) {
        const a1 = (sa + i * 360 / 7 + 19) * Math.PI / 180;
        const a2 = (sa + (i + 1) * 360 / 7 - 19) * Math.PI / 180;
        const p = mk('path');
        p.setAttribute('d', 'M' + (cx + R * Math.cos(a1)) + ' ' + (cy + R * Math.sin(a1)) +
            ' A' + R + ' ' + R + ' 0 0 1 ' + (cx + R * Math.cos(a2)) + ' ' + (cy + R * Math.sin(a2)));
        p.setAttribute('class', 'arrow-path');
        p.setAttribute('marker-end', 'url(#a-ind-' + svgId + ')');
        svg.appendChild(p);
    }

    // Comment slots layout
    var slotDefs = {
        6: { x: 4, w: 165, s: 'left' },
        5: { x: 4, w: 165, s: 'left' },
        0: { x: 4, w: 165, s: 'left' },
        1: { x: 590, w: 165, s: 'right' },
        2: { x: 590, w: 165, s: 'right' },
        3: { x: 590, w: 165, s: 'right' }
    };

    function calcH(si) {
        var ls = layerComments(indData[si]);
        if (!ls.length) return 0;
        var h = 16;
        ls.forEach(function(l, i) {
            h += 14;
            h += (l.lines.length - 1) * 12;
            if (i < ls.length - 1) h += 3;
        });
        return h + 6;
    }

    function posSlots(list) {
        var y = 8, r = [];
        list.forEach(function(si) {
            var h = calcH(si);
            if (h > 0) { r.push({ si: si, y: y, h: h }); y += h + 8; }
        });
        return r;
    }

    var allSlots = posSlots([6, 5, 0]).concat(posSlots([1, 2, 3]));

    // Draw comment boxes
    allSlots.forEach(function(slot) {
        var si = slot.si, sd = slotDefs[si];
        if (!sd) return;
        var ls = layerComments(indData[si]);
        if (!ls.length) return;

        var bx = sd.x, by = slot.y, bw = sd.w, bh = slot.h;

        // Connector line
        var ln = mk('line');
        var ax = sd.s === 'left' ? bx + bw : bx;
        ln.setAttribute('x1', ax);
        ln.setAttribute('y1', by + bh / 2);
        ln.setAttribute('x2', pos[si].x);
        ln.setAttribute('y2', pos[si].y);
        ln.setAttribute('class', 'comment-line');
        svg.appendChild(ln);

        // Group
        var grp = mk('g');
        grp.style.cursor = 'pointer';

        var gt = mk('title');
        var tps = [];
        ls.forEach(function(l) { tps.push('[' + l.badge + '] ' + l.lines.join(' ')); });
        gt.textContent = STEPS[si].short + '\n' + tps.join('\n');
        grp.appendChild(gt);

        // Box
        var r = mk('rect');
        r.setAttribute('x', bx);
        r.setAttribute('y', by);
        r.setAttribute('width', bw);
        r.setAttribute('height', bh);
        r.setAttribute('class', 'comment-box-bg');
        r.setAttribute('rx', '5');
        grp.appendChild(r);

        // Color bar
        var wc = worstColor(indData[si]);
        var bar = mk('rect');
        bar.setAttribute('x', bx);
        bar.setAttribute('y', by);
        bar.setAttribute('width', 3);
        bar.setAttribute('height', bh);
        bar.setAttribute('fill', COL[wc]);
        bar.setAttribute('rx', '1');
        grp.appendChild(bar);

        // Step label
        var sl = mk('text');
        sl.setAttribute('class', 'comment-step-label');
        sl.setAttribute('x', bx + 10);
        sl.setAttribute('y', by + 12);
        sl.textContent = STEPS[si].short;
        grp.appendChild(sl);

        // Layer comments
        var cy2 = by + 24;
        var maxL = Math.floor((bw - 34) / 5.5);
        ls.forEach(function(layer) {
            var br2 = mk('rect');
            br2.setAttribute('x', bx + 8);
            br2.setAttribute('y', cy2 - 9);
            br2.setAttribute('width', 15);
            br2.setAttribute('height', 12);
            br2.setAttribute('rx', '2');
            br2.setAttribute('fill', layer.bc);
            grp.appendChild(br2);

            var bt = mk('text');
            bt.setAttribute('class', 'comment-badge-text');
            bt.setAttribute('x', bx + 15.5);
            bt.setAttribute('y', cy2 - 3);
            bt.textContent = layer.badge;
            grp.appendChild(bt);

            layer.lines.forEach(function(line) {
                var tx = mk('text');
                tx.setAttribute('class', 'comment-text');
                tx.setAttribute('x', bx + 27);
                tx.setAttribute('y', cy2);
                tx.textContent = line.length > maxL ? line.substring(0, maxL - 2) + '..' : line;
                grp.appendChild(tx);
                cy2 += 12;
            });
            cy2 += 3;
        });
        svg.appendChild(grp);
    });

    // Ellipses on top (after comment boxes)
    for (var i = 0; i < 7; i++) {
        var wc = worstColor(indData[i]);
        var g = mk('g');
        g.setAttribute('class', 'step-ellipse');

        var ti = mk('title');
        ti.textContent = STEPS[i].short + ': ' + STEPS[i].tip;
        g.appendChild(ti);

        if (opts.onClick) {
            (function(idx) { g.onclick = function() { opts.onClick(idx); }; })(i);
        }

        var el = mk('ellipse');
        el.setAttribute('cx', pos[i].x);
        el.setAttribute('cy', pos[i].y);
        el.setAttribute('rx', rx);
        el.setAttribute('ry', ry);
        el.setAttribute('fill', COL[wc]);
        el.setAttribute('stroke', 'rgba(255,255,255,0.12)');
        el.setAttribute('stroke-width', '2');
        g.appendChild(el);

        var lines = STEPS[i].label.split('\n');
        var txt = mk('text');
        txt.setAttribute('class', 'step-label');
        txt.setAttribute('x', pos[i].x);
        txt.setAttribute('y', pos[i].y - (lines.length - 1) * 7);
        lines.forEach(function(l, li) {
            var ts = mk('tspan');
            ts.setAttribute('x', pos[i].x);
            ts.setAttribute('dy', li ? '14' : '0');
            ts.textContent = l;
            txt.appendChild(ts);
        });
        g.appendChild(txt);
        svg.appendChild(g);
    }

    // Center text
    if (opts.centerCode) {
        var ct = mk('text');
        ct.setAttribute('class', 'center-title');
        ct.setAttribute('x', cx);
        ct.setAttribute('y', cy - 6);
        ct.textContent = opts.centerCode;
        svg.appendChild(ct);
    }
    if (opts.centerDate) {
        var cd = mk('text');
        cd.setAttribute('class', 'center-date');
        cd.setAttribute('x', cx);
        cd.setAttribute('y', cy + 14);
        cd.textContent = opts.centerDate;
        svg.appendChild(cd);
    }
}

// -------------------------------------------------------------------
// Panneau de statuts (compteurs par couleur)
// containerId : id du div
// counts : { green: N, yellow: N, ... }
// -------------------------------------------------------------------
function buildStatusPanel(containerId, counts) {
    var el = document.getElementById(containerId);
    el.innerHTML = STATUS_ORDER.map(function(c) {
        return '<div class="status-filter-item" data-color="' + c + '">' +
            '<span class="sf-dot" style="background:' + COL[c] + '"></span>' +
            '<span class="sf-label">' + COL_LABEL[c] + '</span>' +
            '<span class="sf-count">' + (counts[c] || 0) + '</span>' +
            '</div>';
    }).join('');
}

// ===================================================================
// MODAL - Edition des statuts/commentaires
// ===================================================================

var _modal = {
    stepIdx: null,       // 0-based
    context: null,       // 'global' | 'categorie' | 'indicateur'
    activeTab: null,     // 'global' | 'categorie' | 'indicateur'
    selectedColor: null, // 'green', 'red', ... or null
    opts: null,          // {stepData, categorie_id, indicateur_id, layerValues}
    tabs: []             // available tabs for this context
};

function openModal(stepIdx, context, opts) {
    _modal.stepIdx = stepIdx;
    _modal.context = context;
    _modal.opts = opts || {};

    var etape = stepIdx + 1;
    document.getElementById('modal-title').textContent =
        'Etape ' + etape + ' : ' + STEPS[stepIdx].short;

    // Determine available tabs
    var tabsEl = document.getElementById('modal-tabs');
    tabsEl.innerHTML = '';

    if (context === 'indicateur') {
        _modal.tabs = ['indicateur', 'categorie', 'global'];
    } else if (context === 'categorie') {
        _modal.tabs = ['categorie'];
    } else {
        _modal.tabs = ['global'];
    }

    _modal.tabs.forEach(function(t) {
        var btn = document.createElement('div');
        btn.className = 'modal-tab';
        btn.setAttribute('data-tab', t);
        btn.innerHTML = '<span class="tab-badge" style="background:' + LAYERS[t].c + '">' +
            LAYERS[t].b + '</span> ' + LAYERS[t].label;
        btn.onclick = function() { switchTab(t); };
        tabsEl.appendChild(btn);
    });

    // Show/hide clear button
    var clearBtn = document.getElementById('modal-clear');
    clearBtn.style.display = (context === 'indicateur') ? '' : 'none';

    // Set note text
    var noteEl = document.getElementById('modal-note');
    if (context === 'indicateur' && _modal.tabs.length > 1) {
        noteEl.textContent = 'G propage a tous, C propage a la categorie, I ne touche que cet indicateur.';
    } else if (context === 'global') {
        noteEl.textContent = 'Ce statut sera propage a TOUS les indicateurs.';
    } else if (context === 'categorie') {
        noteEl.textContent = 'Ce statut sera propage a tous les indicateurs de cette categorie.';
    } else {
        noteEl.textContent = '';
    }

    // Default tab: 'indicateur' when editing from indicator view, first tab otherwise
    switchTab(context === 'indicateur' ? 'indicateur' : _modal.tabs[0]);

    document.getElementById('modal-overlay').classList.add('open');
}

function closeModal() {
    document.getElementById('modal-overlay').classList.remove('open');
}

function switchTab(layer) {
    _modal.activeTab = layer;

    // Update tab active state
    var tabs = document.querySelectorAll('#modal-tabs .modal-tab');
    tabs.forEach(function(t) {
        t.classList.toggle('active', t.getAttribute('data-tab') === layer);
    });

    // Update note for indicateur context
    var noteEl = document.getElementById('modal-note');
    if (_modal.context === 'indicateur') {
        if (layer === 'global') noteEl.textContent = 'Propage a TOUS les indicateurs.';
        else if (layer === 'categorie') noteEl.textContent = 'Propage aux indicateurs de cette categorie.';
        else noteEl.textContent = 'Ne modifie que cet indicateur.';
    }

    // Show/hide clear button only for indicateur context
    var clearBtn = document.getElementById('modal-clear');
    clearBtn.style.display = (_modal.context === 'indicateur') ? '' : 'none';

    loadTabData();
}

function loadTabData() {
    var layer = _modal.activeTab;
    var color = null;
    var comment = '';

    // Try to load from layerValues passed via opts
    if (_modal.opts.layerValues && _modal.opts.layerValues[layer]) {
        var lv = _modal.opts.layerValues[layer];
        color = lv.color || null;
        comment = lv.comment || '';
    }
    // For indicateur context, stepData has the 3 layers
    else if (_modal.opts.stepData && _modal.opts.stepData[layer]) {
        var sd = _modal.opts.stepData[layer];
        color = sd.color || null;
        comment = sd.comment || '';
    }

    // Set color picker
    _modal.selectedColor = color;
    var btns = document.querySelectorAll('#modal-colors .color-btn');
    btns.forEach(function(b) {
        b.classList.toggle('selected', b.getAttribute('data-color') === color);
    });

    // Set comment
    document.getElementById('modal-comment').value = comment;
}

function selColor(btn) {
    _modal.selectedColor = btn.getAttribute('data-color');
    var btns = document.querySelectorAll('#modal-colors .color-btn');
    btns.forEach(function(b) { b.classList.remove('selected'); });
    btn.classList.add('selected');
}

function clearLayer() {
    // Vider cette couche = enregistrer null pour cet indicateur uniquement
    var etape = _modal.stepIdx + 1;
    var body = {
        context: 'indicateur',
        etape: etape,
        layer: _modal.activeTab,
        color: null,
        commentaire: '',
        indicateur_id: _modal.opts.indicateur_id
    };
    fetch('/api/step/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    }).then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.ok) location.reload();
    });
}

function saveModal() {
    var etape = _modal.stepIdx + 1;
    var layer = _modal.activeTab;

    // Determine the save context based on the active tab and original context
    var saveContext;
    if (_modal.context === 'indicateur') {
        saveContext = layer;  // G→global, C→categorie, I→indicateur
    } else {
        saveContext = _modal.context;
    }

    var body = {
        context: saveContext,
        etape: etape,
        layer: layer,
        color: _modal.selectedColor,
        commentaire: document.getElementById('modal-comment').value,
        indicateur_id: _modal.opts.indicateur_id || null,
        categorie_id: _modal.opts.categorie_id || null
    };

    fetch('/api/step/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    }).then(function(r) { return r.json(); })
    .then(function(d) {
        if (d.ok) location.reload();
    });
}

// ===================================================================
// DRILL TABLES - Vue Globale / Categorie
// ===================================================================

function showGlobalDrill(stepIdx, drillData, globalLayerValues) {
    var el = document.getElementById('drill-area');
    if (!el) return;

    var etape = stepIdx + 1;
    var items = drillData[etape] || [];

    var html = '<div class="drill-edit-header">' +
        '<h3>Etape ' + etape + ' : ' + STEPS[stepIdx].short + '</h3>' +
        '<span class="drill-edit-link" onclick="openModal(' + stepIdx +
        ', \'global\', {layerValues:{global:' +
        JSON.stringify(globalLayerValues[etape] || {color:null,comment:''}) +
        '}})">Modifier statut global</span>' +
        '</div>';

    html += '<table class="drill-table"><tr><th>Categorie</th><th>Statut</th><th>Indicateurs</th></tr>';
    items.forEach(function(item) {
        html += '<tr onclick="location.href=\'/categorie/' + item.cat_id + '\'">' +
            '<td>' + item.cat_nom + '</td>' +
            '<td><span class="status-dot c-' + item.worst + '"></span>' + COL_LABEL[item.worst] + '</td>' +
            '<td>' + item.count + '</td></tr>';
    });
    html += '</table>';

    el.innerHTML = html;
    el.classList.add('open');
}

function showCatDrill(stepIdx, drillData, catLayerValues, categorie_id) {
    var el = document.getElementById('drill-area');
    if (!el) return;

    var etape = stepIdx + 1;
    var items = drillData[etape] || [];

    var html = '<div class="drill-edit-header">' +
        '<h3>Etape ' + etape + ' : ' + STEPS[stepIdx].short + '</h3>' +
        '<span class="drill-edit-link" onclick="openModal(' + stepIdx +
        ', \'categorie\', {categorie_id:' + categorie_id +
        ', layerValues:{categorie:' +
        JSON.stringify(catLayerValues[etape] || {color:null,comment:''}) +
        '}})">Modifier statut categorie</span>' +
        '</div>';

    html += '<table class="drill-table"><tr><th>Code</th><th>Description</th><th>Statut</th></tr>';
    items.forEach(function(item) {
        html += '<tr onclick="location.href=\'/indicateur/' + item.ind_id + '\'">' +
            '<td>' + item.ind_code + '</td>' +
            '<td>' + item.ind_desc + '</td>' +
            '<td><span class="status-dot c-' + item.worst + '"></span>' + COL_LABEL[item.worst] + '</td></tr>';
    });
    html += '</table>';

    el.innerHTML = html;
    el.classList.add('open');
}

// -------------------------------------------------------------------
// Compteurs inline (topbar)
// containerId : id du div
// counts : { green: N, yellow: N, ... }
// -------------------------------------------------------------------
function buildInlineCounters(containerId, counts) {
    var el = document.getElementById(containerId);
    el.innerHTML = STATUS_ORDER.map(function(c) {
        return '<span class="ic" title="' + COL_LABEL[c] + '">' +
            '<span class="icd" style="background:' + COL[c] + '"></span>' +
            (counts[c] || 0) + '</span>';
    }).join('');
}
