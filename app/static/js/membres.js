/* Gestion des membres du projet */

/* ---- Modale ajout membre ---- */
function openAddMemberModal() {
    document.getElementById('am-email').value = '';
    document.getElementById('am-nom').value = '';
    document.getElementById('am-trigramme').value = '';
    document.getElementById('am-role').value = 'membre';
    document.getElementById('add-member-overlay').classList.add('open');
    setTimeout(function() { document.getElementById('am-email').focus(); }, 100);
}

function closeAddMemberModal() {
    document.getElementById('add-member-overlay').classList.remove('open');
}

function submitAddMember() {
    var email = document.getElementById('am-email').value.trim();
    var nom = document.getElementById('am-nom').value.trim();
    var trigramme = document.getElementById('am-trigramme').value.trim().toUpperCase();
    var role = document.getElementById('am-role').value;
    if (!email || !nom) return;

    fetch('/api/membres/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, nom: nom, trigramme: trigramme, role: role })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok) {
            location.reload();
        } else {
            alert(data.error || 'Erreur');
        }
    });
}

/* ---- Modale detail membre ---- */
var _currentMember = null;

function openMemberDetail(member) {
    _currentMember = member;
    var isAdmin = window._userRole === 'admin';
    var isSelf = member.login === window._currentUserLogin;

    document.getElementById('md-id').value = member.id;
    document.getElementById('md-login').value = member.login;
    document.getElementById('md-title').textContent = member.nom;
    document.getElementById('md-nom').value = member.nom || '';
    document.getElementById('md-trigramme').value = member.trigramme || '';
    document.getElementById('md-email').value = member.email || '';
    document.getElementById('md-role').value = member.role || 'membre';
    document.getElementById('md-emails-sec').value = member.emails_secondaires || '';
    document.getElementById('md-date-creation').textContent = member.date_creation || '-';
    document.getElementById('md-date-connexion').textContent = member.date_derniere_connexion || '-';
    document.getElementById('md-date-fin').value = member.date_fin || '';

    // Lecture seule pour non-admins
    var fields = ['md-nom', 'md-trigramme', 'md-emails-sec', 'md-date-fin'];
    fields.forEach(function(id) {
        document.getElementById(id).readOnly = !isAdmin;
    });
    var roleSelect = document.getElementById('md-role');
    roleSelect.disabled = !isAdmin;

    // Boutons d'action
    var actionsDiv = document.getElementById('md-actions');
    if (isAdmin) {
        var retireBtn = '';
        if (!isSelf) {
            retireBtn = '<button type="button" class="btn-clear" onclick="removeMemberFromDetail()">Retirer</button>';
        }
        var inviteBtn = '';
        if (!isSelf) {
            inviteBtn = '<button type="button" class="btn btn-secondary" onclick="generateInvitation(' + member.id + ')" id="md-invite-btn">'
                + (member.invitation_pending ? 'Renvoyer l\'invitation' : 'Lien d\'invitation')
                + '</button>';
        }
        actionsDiv.innerHTML = retireBtn
            + inviteBtn
            + '<span style="flex:1"></span>'
            + '<button type="button" class="btn btn-secondary" onclick="closeMemberDetail()">Annuler</button>'
            + '<button type="button" class="btn btn-primary" onclick="saveMember()">Enregistrer</button>';
    } else {
        actionsDiv.innerHTML = '<span style="flex:1"></span>'
            + '<button type="button" class="btn btn-secondary" onclick="closeMemberDetail()">Fermer</button>';
    }

    document.getElementById('member-detail-overlay').classList.add('open');
}

function closeMemberDetail() {
    document.getElementById('member-detail-overlay').classList.remove('open');
    _currentMember = null;
}

function saveMember() {
    var id = document.getElementById('md-id').value;
    var data = {
        nom: document.getElementById('md-nom').value.trim(),
        trigramme: document.getElementById('md-trigramme').value.trim(),
        role: document.getElementById('md-role').value,
        emails_secondaires: document.getElementById('md-emails-sec').value.trim(),
        date_fin: document.getElementById('md-date-fin').value
    };
    if (!data.nom) {
        alert('Le nom est requis.');
        return;
    }
    fetch('/api/membres/' + id, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(function(r) { return r.json(); })
    .then(function(resp) {
        if (resp.ok) {
            location.reload();
        } else {
            alert(resp.error || 'Erreur');
        }
    });
}

function removeMemberFromDetail() {
    var id = document.getElementById('md-id').value;
    var nom = document.getElementById('md-nom').value;
    if (!confirm('Retirer ' + nom + ' du projet ?')) return;

    fetch('/api/membres/' + id + '/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok) {
            location.reload();
        } else {
            alert(data.error || 'Erreur');
        }
    });
}

/* ---- Invitation par lien ---- */
function generateInvitation(memberId) {
    var btn = document.getElementById('md-invite-btn');
    if (btn) btn.textContent = 'Generation...';

    fetch('/api/membres/' + memberId + '/invitation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.ok && data.url) {
            navigator.clipboard.writeText(data.url).then(function() {
                if (btn) {
                    btn.textContent = 'Lien copie !';
                    setTimeout(function() { btn.textContent = 'Lien d\'invitation'; }, 2500);
                }
            }).catch(function() {
                prompt('Copiez ce lien :', data.url);
                if (btn) btn.textContent = 'Lien d\'invitation';
            });
        } else {
            alert(data.error || 'Erreur');
            if (btn) btn.textContent = 'Lien d\'invitation';
        }
    });
}

/* ---- Trigramme suggestion (modale ajout) ---- */
var _triSuggestTimer = null;
function suggestTrigramme() {
    clearTimeout(_triSuggestTimer);
    _triSuggestTimer = setTimeout(function() {
        var nom = document.getElementById('am-nom').value;
        if (!nom) return;
        fetch('/api/trigramme/suggest?nom=' + encodeURIComponent(nom))
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.trigramme && !document.getElementById('am-trigramme').value) {
                document.getElementById('am-trigramme').value = data.trigramme;
            }
        });
    }, 300);
}
