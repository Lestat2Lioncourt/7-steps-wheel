# CLAUDE.md - Contexte projet Roue CSI

## Resume du projet

Application web Python standalone remplacant un fichier Excel macro (`Roue CSI.xlsm`) pour le suivi de la maturite des indicateurs de service (SLA/KPI/XLA) selon la methodologie CSI (Continual Service Improvement) a 7 etapes. Application generique, non liee a un contrat ou client specifique.

## Etat d'avancement

**Phase actuelle : Developpement** - Application fonctionnelle :
1. Analyse du fichier Excel original (`Roue CSI.xlsm` + `Roue CSI.accdb`)
2. Concepts metier et architecture definis
3. Prototypes HTML interactifs valides
4. Modele de donnees SQLite implemente (12 tables, donnees de reference)
5. Framework choisi : **Flask**
6. Structure projet Python creee
7. Composant SVG de la roue (3 niveaux Global/Categorie/Indicateur)
8. Backend API complet (routes Flask : step save, actions CRUD, user search)
9. Vues : Global, Categorie, Indicateur, Kanban (3 niveaux), Referentiel, Login, Accueil
10. Systeme d'identification : login par email O365, trigramme auto-suggere
11. Kanban : drag & drop, autocomplete assignee, assignation par email (placeholder user)
12. Gestion multi-projets : creation, rattachement distant par reference directe
13. Script de lancement `start.py` (detection port, ouverture navigateur unique)

**Prochaines etapes** : Systeme inbox/outbox, historique/snapshots, generation CR, import Excel.

## Fichiers du projet

| Fichier | Role |
|---------|------|
| `ROADMAP.md` | Documentation complete du projet : concepts, fonctionnalites, architecture, decisions |
| `CLAUDE.md` | Ce fichier - contexte pour Claude Code |
| `start.py` | Script de lancement : demarre Flask + ouvre le navigateur (detection port, reloader-safe) |
| `requirements.txt` | Dependances Python (flask) |
| **`app/`** | **Code source Python (Flask)** |
| `app/main.py` | Point d'entree Flask (app factory + ouverture navigateur auto) |
| `app/database/schema.sql` | Schema SQLite complet (12 tables, colonnes email/trigramme sur utilisateurs) |
| `app/database/seed.sql` | Donnees de reference initiales (etapes, statuts, etats, types) |
| `app/database/seed_demo.sql` | Donnees de demonstration (categories, indicateurs, actions, utilisateurs) |
| `app/database/db.py` | init_db(), get_connection(), migration auto, create_project(), attach_project() |
| `app/routes/main.py` | Blueprint principal : login, vues, API step/actions/users, gestion projets |
| `app/services/identity_service.py` | Detection identite (registre Windows/O365), trigramme, placeholder user, fusion |
| `app/services/action_service.py` | CRUD actions Kanban, regroupement par statut |
| `app/services/indicateur_service.py` | Donnees roue (3 niveaux), save_step, referentiel |
| `app/templates/` | Templates Jinja2 : base, login, accueil, global, categorie, indicateur, kanban, referentiel |
| `app/static/js/wheel.js` | Composant SVG roue + modale edition statuts/commentaires |
| `app/static/js/kanban.js` | Kanban drag & drop + autocomplete assignee |
| `app/static/css/style.css` | Theme sombre complet |
| **`data/`** | **Donnees utilisateur (hors git)** |
| `data/projects.json` | Liste des projets (locaux et distants) |
| `data/roue_csi.db` | Base SQLite projet demo |
| `data/identity.json` | Identite utilisateur memorisee |
| **`prototype/`** | **Prototypes HTML (reference)** |
| `prototype/prototype-consolide.html` | **Prototype de reference** - consolide toutes les fonctionnalites validees |
| **`_old_version/`** | **Fichiers originaux Excel/Access** |

## Decisions cles prises

- **Stack** : Python Flask, SQLite, HTML/CSS/JS + SVG
- **Deploiement** : Standalone (serveur local, ouverture navigateur auto), heberge sur OneDrive
- **Interface** : 2 onglets (Roue CSI / Referentiel), fiche fixe verticale au niveau indicateur
- **Commentaires** : Systeme a 3 couches (Global/Categorie/Indicateur) par etape, "le pire l'emporte"
- **Kanban** : 5 colonnes, rattachement a 3 niveaux (global, categorie+etape, indicateur+etape)
- **Assignation** : Autocomplete par nom/login/email/trigramme + assignation a un email inconnu (placeholder user fusionne a la connexion)
- **Trigramme** : Auto-suggere depuis le nom (initiale prenom + 2 lettres nom), affiche sur cartes et topbar
- **Multi-projets** : Projets locaux (DB dans data/) ou distants (reference directe vers .db partage, sans copie)
- **Historique** : Snapshots par revue, consultation en lecture seule uniquement
- **Echanges multi-utilisateurs** : Pattern inbox/outbox JSON via OneDrive
- **Notifications** : Power Automate (l'utilisateur aura besoin d'accompagnement)
- **Compteurs** : Inline dans la barre de titre (pastilles compactes)
- **Identification** : Login par email O365, trigramme, detection registre Windows en fallback

## Concepts metier essentiels

- **Roue CSI** : 7 etapes fixes parcourues en sens horaire (Ce qu'on VEUT, Ce qu'on PEUT, COLLECTE, DATA PREP, DATA QUALITY, DATA VIZ & USAGE, BILAN)
- **5 statuts couleur** : Gris (Non evalue), Vert (Valide), Jaune (En cours), Orange (Warning), Rouge (Blocage)
- **Hierarchie** : Global > Categorie > Indicateur, drill-down recursif, meme composant roue aux 3 niveaux
- **Propagation** : Saisie au niveau Global propage a tous les indicateurs, au niveau Categorie propage a ceux de la categorie
- **Deblocage partiel** : Vider la couche Global ou Categorie d'un indicateur specifique sans toucher les autres

## Taches restantes (a affiner)

- [x] Modele de donnees detaille (12 tables SQLite, tables de reference externalisees)
- [x] Choix framework : Flask
- [x] Structure du projet Python
- [x] Composant SVG de la roue (reutilisable aux 3 niveaux)
- [x] Backend API (routes Flask : step save, actions CRUD, user search, projets)
- [x] Vues : Global, Categorie, Indicateur, Kanban, Referentiel, Login, Accueil
- [x] Gestion utilisateurs : login email, trigramme, placeholder user, fusion
- [x] Kanban : drag & drop, autocomplete assignee, assignation par email
- [x] Gestion multi-projets : creation vierge + rattachement distant
- [x] Script de lancement start.py
- [ ] Systeme inbox/outbox
- [ ] Historique et enregistrement global (snapshots)
- [ ] Generation du CR (compte-rendu diff)
- [ ] Notifications Power Automate
- [ ] Import des donnees existantes (Excel -> SQLite)
- [ ] Tests et packaging

## Points en attente cote utilisateur

- Textes detailles des tooltips pour chaque etape de la roue ("je te fournirai le detail")
- Choix mecanisme inbox tracking (table en base vs gestion par fichiers)

## Langue

L'utilisateur communique en francais. Les noms de variables/code peuvent etre en francais ou anglais selon le contexte.

## Repository GitHub

https://github.com/Lestat2Lioncourt/7-steps-wheel
