/* Gestion des membres du projet */

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

function changeRole(userId, newRole) {
    fetch('/api/membres/' + userId + '/role', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role: newRole })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (!data.ok) {
            alert(data.error || 'Erreur');
            location.reload();
        }
    });
}

function removeMember(userId, name) {
    if (!confirm('Retirer ' + name + ' du projet ?')) return;

    fetch('/api/membres/' + userId + '/remove', {
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

function copyInvitation() {
    var name = window._projectName || 'Roue CSI';
    var dbPath = window._dbPath || '(chemin non disponible)';
    var appPath = window._appPath || '(chemin non disponible)';
    var text = 'Vous avez ete ajoute au projet "' + name + '".\n\n'
             + 'Pour y acceder :\n'
             + '1. Double-cliquez sur :\n'
             + '   ' + appPath + '\n'
             + '2. Dans l\'accueil, cliquez "Rattacher existant"\n'
             + '3. Donnez un nom au projet et collez ce chemin :\n'
             + '   ' + dbPath + '\n\n'
             + '(Etape 2-3 uniquement a la premiere utilisation.)';
    navigator.clipboard.writeText(text).then(function() {
        var btn = document.querySelector('[onclick="copyInvitation()"]');
        if (btn) {
            var orig = btn.textContent;
            btn.textContent = 'Copie !';
            setTimeout(function() { btn.textContent = orig; }, 2000);
        }
    });
}

function updateEmails(userId, emails) {
    fetch('/api/membres/' + userId + '/emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ emails_secondaires: emails })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (!data.ok) {
            alert(data.error || 'Erreur');
            location.reload();
        }
    });
}

function updateDateFin(userId, dateFin) {
    fetch('/api/membres/' + userId + '/date_fin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ date_fin: dateFin })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (!data.ok) {
            alert(data.error || 'Erreur');
        }
    });
}

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
