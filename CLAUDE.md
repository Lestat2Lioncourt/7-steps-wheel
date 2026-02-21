# CLAUDE.md - Contexte projet Roue CSI

## Resume du projet

Application web Python (Flask + PostgreSQL) pour le suivi de la maturite des indicateurs de service (SLA/KPI/XLA) selon la methodologie CSI (Continual Service Improvement) a 7 etapes. Remplace un fichier Excel macro (`Roue CSI.xlsm`). Application generique, multi-clients, multi-projets.

## Etat d'avancement

**Phase actuelle : Authentification implementee** - Application fonctionnelle :
1. Analyse du fichier Excel original (`Roue CSI.xlsm` + `Roue CSI.accdb`)
2. Concepts metier et architecture definis
3. Prototypes HTML interactifs valides
4. Modele de donnees PostgreSQL (schema `common` + schemas par client)
5. Framework choisi : **Flask** + **psycopg3** + **python-dotenv**
6. Structure projet Python creee
7. Composant SVG de la roue (3 niveaux Global/Categorie/Indicateur)
8. Backend API complet (routes Flask : step save, actions CRUD, user search)
9. Vues : Global, Categorie, Indicateur, Kanban (3 niveaux), Referentiel, Login, Accueil
10. Authentification : login email + mot de passe (hash PBKDF2), invitations par lien, setup wizard premier admin, SSO Microsoft prepare (MSAL conditionnel)
11. Kanban : drag & drop, autocomplete assignee, assignation par email (placeholder user), taches chapeau (parent/enfant)
12. Gestion multi-clients / multi-projets : chaque client a son schema PostgreSQL (`client_<slug>`)
13. Script de lancement `start.py` (detection port, ouverture navigateur unique)
14. Gestion des membres : 4 roles (admin/membre/lecteur/information), controle d'acces, page admin, invitation
15. Bulles commentaires sur roues globale et categorie (drawIndicatorWheel avec couches G/C visibles)
16. Edition directe des commentaires par clic sur bulle ou bouton "+" (sans descendre au niveau indicateur)
17. Heritage couleurs : la couche globale se propage sur les vues categorie (worstColor + wheelColors backend)
18. Modale edition : onglets couche [C]/[G] au-dessus du textarea (style tabs), couleur obligatoire avant commentaire
19. Kanban : dates de debut et fin previsionnelle sur les actions (schema, migration auto, CRUD, affichage cartes)
20. Dates membres : date_creation (auto a l'ajout), date_derniere_connexion (auto au login), date_fin previsionnelle (manuelle)
21. Emails secondaires par membre : connexion transparente via n'importe quel compte O365 (recherche email principal + secondaires)
22. Accueil : structure clients > projets, CRUD clients et projets
23. Migration auto des schemas client a chaque activation projet (idempotente, cachee par `_migrated_schemas`)
24. **Migration SQLite → PostgreSQL** : toute la couche donnees reecrite (db.py, 4 services, routes, templates accueil/membres)
25. **Authentification** : login email+mdp (werkzeug PBKDF2), setup wizard, invitations par lien (token 7j), SSO Microsoft (MSAL conditionnel), suppression detection registre Windows/identity.json

**Prochaines etapes** : Docker, deploiement VPS, historique/snapshots, generation CR.

## Architecture PostgreSQL

### Schemas

- **`common`** : tables partagees entre tous les clients
  - `utilisateurs` : tous les utilisateurs (login, nom, email, trigramme, emails_secondaires)
  - `clients` : liste des clients (nom, slug, date_creation)
  - `client_membres` : appartenance utilisateur ↔ client (role)
  - `invitations` : activation de compte par lien (token, expiration, user_id)
  - `etapes`, `statuts_etape`, `etats_indicateur`, `types_indicateur` : tables de reference
- **`client_<slug>`** : un schema par client, contient les donnees metier
  - `projets`, `projet_membres` : projets du client et membres par projet
  - `categories`, `indicateurs`, `indicateur_etapes` : donnees de la roue CSI
  - `actions` : kanban (avec `parent_id` pour hierarchie chapeau)
  - `revues` : historique (futur)

### Connexion et search_path

- `get_connection()` → `SET search_path = client_schema, common` (resout `utilisateurs` vers `common`, `actions` vers le schema client)
- `get_connection_common()` → `SET search_path = common`
- Contexte actif : `_active_client_schema` + `_active_project_id` (globals module-level dans db.py)
- `set_active_context(schema, project_id)` appele par `_activate_project()` dans les routes

### Modele utilisateurs (deux tables)

- `common.utilisateurs` : donnees identitaire (login, nom, email, trigramme, emails_secondaires)
- `client_schema.projet_membres` : appartenance projet (user_id, projet_id, role, date_creation, date_derniere_connexion, date_fin)
- Le frontend utilise `projet_membres.id` comme ID membre (pas `utilisateurs.id`)

### Migration idempotente

- `init_common()` : execute `schema_common.sql` + `seed_common.sql` au demarrage Flask
- `migrate_client_schema(schema)` : execute `schema_client.sql` (IF NOT EXISTS) a la premiere activation du schema dans le process
- Cache `_migrated_schemas` dans les routes pour eviter les re-executions

## Fichiers du projet

| Fichier | Role |
|---------|------|
| `ROADMAP.md` | Documentation complete du projet : concepts, fonctionnalites, architecture, decisions |
| `CLAUDE.md` | Ce fichier - contexte pour Claude Code |
| `start.py` | Script de lancement : demarre Flask + ouvre le navigateur (detection port, reloader-safe, compatible pythonw) |
| `Roue CSI.vbs` | Lanceur silencieux (pas de fenetre console) — appelle pythonw + start.py |
| `installer-raccourci.bat` | Cree un raccourci bureau "Roue CSI" — a executer une fois par utilisateur |
| `requirements.txt` | Dependances Python (flask, psycopg[binary], python-dotenv) |
| `.env` | Variables d'environnement PostgreSQL (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD) — hors git |
| `.env.example` | Template .env sans credentials (commite) |
| **`app/`** | **Code source Python (Flask)** |
| `app/main.py` | Point d'entree Flask (app factory, init_common, ouverture navigateur auto) |
| `app/database/config.py` | Configuration PostgreSQL (lit .env via python-dotenv, expose get_dsn()) |
| `app/database/db.py` | Connexion PostgreSQL (psycopg3), gestion contexte schema/projet, CRUD clients/projets, migration schemas |
| `app/database/schema_common.sql` | DDL PostgreSQL schema `common` (utilisateurs, clients, client_membres, tables de reference) |
| `app/database/schema_client.sql` | DDL PostgreSQL schema client (projets, projet_membres, categories, indicateurs, actions, revues) |
| `app/database/seed_common.sql` | Donnees de reference initiales (7 etapes, 5 statuts, etats, types) |
| `app/database/schema.sql` | *Legacy* — ancien schema SQLite (conserve pour reference) |
| `app/database/seed.sql` | *Legacy* — ancien seed SQLite |
| `app/database/seed_demo.sql` | *Legacy* — donnees demo SQLite |
| `app/routes/main.py` | Blueprint principal : login, vues, API step/actions/users, gestion clients/projets/membres |
| `app/services/auth_service.py` | Authentification : verify_password, set_password, invitations (create/validate/consume), setup wizard, SSO MSAL (conditionnel) |
| `app/services/identity_service.py` | Trigramme, placeholder user, fusion, reconnaissance emails secondaires (PostgreSQL). Detection registre Windows supprimee |
| `app/services/action_service.py` | CRUD actions Kanban, regroupement par statut, hierarchie parent/enfant (PostgreSQL) |
| `app/services/member_service.py` | CRUD membres projet via modele deux tables utilisateurs + projet_membres (PostgreSQL) |
| `app/services/indicateur_service.py` | Donnees roue (3 niveaux), save_step (UPSERT), referentiel (PostgreSQL) |
| `app/templates/` | Templates Jinja2 : base, login, setup, invitation, accueil, global, categorie, indicateur, kanban, referentiel, membres |
| `app/static/js/wheel.js` | Composant SVG roue (drawSimpleWheel + drawIndicatorWheel avec bulles commentaires, bouton "+"), modale edition statuts/commentaires |
| `app/static/js/kanban.js` | Kanban drag & drop, autocomplete assignee, taches chapeau (drill-down parent/enfant) |
| `app/static/js/membres.js` | CRUD membres, copie invitation (URL), auto-trigramme, emails secondaires, date_fin |
| `app/static/js/referentiel.js` | Interactions page referentiel |
| `app/static/js/sortable.min.js` | Bibliotheque SortableJS (drag & drop) |
| `app/static/css/style.css` | Theme sombre complet |
| **`data/`** | **Donnees locales (hors git)** |
| `data/identity.json` | *Supprime* — ancien stockage identite locale (remplace par sessions Flask + auth) |
| **`prototype/`** | **Prototypes HTML (reference)** |
| `prototype/prototype-consolide.html` | **Prototype de reference** - consolide toutes les fonctionnalites validees |
| **`_old_version/`** | **Fichiers originaux Excel/Access (hors git)** |

## Decisions cles prises

- **Stack** : Python Flask, PostgreSQL (psycopg3), HTML/CSS/JS + SVG
- **Base de donnees** : PostgreSQL serveur (remplace SQLite fichier). Un schema `common` partage + un schema par client (`client_<slug>`)
- **Configuration** : `.env` pour les credentials PostgreSQL, `.env.example` commite
- **Deploiement** : Standalone local actuellement, migration vers Docker + VPS prevue
- **Interface** : 2 onglets (Roue CSI / Referentiel), fiche fixe verticale au niveau indicateur
- **Commentaires** : Systeme a 3 couches (Global/Categorie/Indicateur) par etape, "le pire l'emporte". Bulles visibles aux 3 niveaux de roue. Edition directe par clic bulle ou bouton "+". Couleur obligatoire avant saisie commentaire
- **Kanban** : 5 colonnes, rattachement a 3 niveaux (global, categorie+etape, indicateur+etape), dates debut/fin previsionnelles, taches chapeau (parent/enfant avec drill-down)
- **Assignation** : Autocomplete par nom/login/email/trigramme + assignation a un email inconnu (placeholder user fusionne a la connexion)
- **Trigramme** : Auto-suggere depuis le nom (initiale prenom + 2 lettres nom), affiche sur cartes et topbar
- **Multi-clients / Multi-projets** : Chaque client a son schema PostgreSQL. L'accueil affiche les clients avec leurs projets imbriques
- **Historique** : Snapshots par revue, consultation en lecture seule uniquement
- **Notifications** : Power Automate (l'utilisateur aura besoin d'accompagnement)
- **Compteurs** : Inline dans la barre de titre (pastilles compactes)
- **Authentification** : Login email + mot de passe (hash werkzeug PBKDF2). Setup wizard au premier lancement (creation admin initial). Invitations par lien (token 7j, generation par admin dans la modale membre). SSO Microsoft prepare (MSAL, actif seulement si AZURE_CLIENT_ID/TENANT_ID/CLIENT_SECRET dans .env). Detection registre Windows supprimee (code mort sur Raspberry Pi). Emails secondaires : un membre peut avoir plusieurs adresses, connexion transparente via n'importe laquelle
- **Roles** : 4 niveaux — admin (tout + gestion membres), membre (consulter + modifier), lecteur (consulter uniquement), information (pas d'acces app, destinataire CR uniquement). Createur d'un projet = admin automatique
- **Migration auto** : `migrate_client_schema()` applique les DDL (IF NOT EXISTS) a chaque activation de schema, garantissant la compatibilite

## Concepts metier essentiels

- **Roue CSI** : 7 etapes fixes parcourues en sens horaire (Ce qu'on VEUT, Ce qu'on PEUT, COLLECTE, DATA PREP, DATA QUALITY, DATA VIZ & USAGE, BILAN)
- **5 statuts couleur** : Gris (Non evalue), Vert (Valide), Jaune (En cours), Orange (Warning), Rouge (Blocage)
- **Hierarchie** : Global > Categorie > Indicateur, drill-down recursif, meme composant roue aux 3 niveaux
- **Propagation** : Saisie au niveau Global propage a tous les indicateurs, au niveau Categorie propage a ceux de la categorie
- **Deblocage partiel** : Vider la couche Global ou Categorie d'un indicateur specifique sans toucher les autres
- **Taches chapeau** : Une action avec des sous-taches (parent_id). Statut et dates calcules dynamiquement depuis les enfants. Drill-down au clic, non draggable

## Conventions techniques

- **Parametres SQL** : `%s` (psycopg3), jamais `?` (SQLite)
- **Recherche case-insensitive** : `ILIKE` (PostgreSQL)
- **Recherche emails secondaires** : `%s = ANY(string_to_array(u.emails_secondaires, ','))`
- **UPSERT** : `INSERT ... ON CONFLICT ... DO UPDATE SET ...` (save_step, etc.)
- **ID retour** : `RETURNING id` (PostgreSQL), jamais `last_insert_rowid()` (SQLite)
- **Resultats requetes** : `dict_row` factory (acces par cle, ex: `row['id']`)
- **Connexion** : `psycopg.connect(get_dsn(), row_factory=dict_row)` + autocommit=False par defaut

## Taches restantes

- [x] Modele de donnees (PostgreSQL multi-schema)
- [x] Framework : Flask + psycopg3
- [x] Structure du projet Python
- [x] Composant SVG de la roue (reutilisable aux 3 niveaux)
- [x] Backend API (routes Flask : step save, actions CRUD, user search, clients/projets)
- [x] Vues : Global, Categorie, Indicateur, Kanban, Referentiel, Login, Accueil
- [x] Gestion utilisateurs : auto-detection O365 multi-comptes, identite verrouillee
- [x] Kanban : drag & drop, autocomplete assignee, assignation par email, dates debut/fin, taches chapeau
- [x] Gestion multi-clients / multi-projets (schemas PostgreSQL)
- [x] Script de lancement start.py
- [x] Gestion membres : 4 roles, controle d'acces, page admin, invitation
- [x] Bulles commentaires sur roues globale/categorie + edition directe
- [x] Heritage couleurs global → categorie, modale avec onglets couche
- [x] Dates membres + emails secondaires O365
- [x] Edition client/projet depuis l'accueil + migration auto schemas
- [x] **Migration SQLite → PostgreSQL** (db.py, 4 services, routes, templates)
- [x] Authentification (login email+mdp, invitations par lien, setup wizard, SSO Microsoft prepare)
- [ ] Dockerisation (Dockerfile + docker-compose)
- [ ] Deploiement VPS
- [ ] Historique et enregistrement global (snapshots)
- [ ] Generation du CR (compte-rendu diff)
- [ ] Notifications Power Automate
- [ ] Import des donnees existantes (Excel → PostgreSQL)
- [ ] Tests et packaging
- [ ] Nettoyage fichiers legacy SQLite (schema.sql, seed.sql, seed_demo.sql)

## Points en attente cote utilisateur

- Textes detailles des tooltips pour chaque etape de la roue ("je te fournirai le detail")

## Langue

L'utilisateur communique en francais. Les noms de variables/code peuvent etre en francais ou anglais selon le contexte.

## Repository GitHub

https://github.com/Lestat2Lioncourt/7-steps-wheel
