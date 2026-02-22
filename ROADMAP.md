# ROADMAP - Roue CSI

## 1. Contexte

Application generique de suivi de la maturite des indicateurs de service (SLA/KPI/XLA) basee sur la methodologie CSI (Continual Service Improvement). Remplace un outil Excel macro par une application web Python (Flask + PostgreSQL), multi-clients, multi-projets, deployable en Docker.

---

## 2. Concepts metier

### 2.1 La Roue CSI (7-Step Improvement Process)

Roue a 7 etapes fixes, parcourues dans le sens horaire lors de chaque reunion de revue :

| # | Etape | Description |
|---|-------|-------------|
| 1 | Ce qu'on VEUT | Definir l'objectif de mesure |
| 2 | Ce qu'on PEUT | Ce qui est techniquement faisable |
| 3 | COLLECTE | Collecte des donnees |
| 4 | DATA PREP | Preparation des donnees |
| 5 | DATA QUALITY | Qualite des donnees |
| 6 | DATA VIZ & USAGE | Visualisation et exploitation |
| 7 | BILAN | Bilan / revue |

### 2.2 Statuts (5 couleurs)

| Couleur | Intitule | Usage |
|---------|----------|-------|
| Gris | Non evalue | Etape pas encore evaluee |
| Vert | Valide / Conforme | Etape validee |
| Jaune | En cours | Travail en cours |
| Orange | Warning | Alerte, attention requise |
| Rouge | Blocage | Bloque, action critique necessaire |

### 2.3 Hierarchie a 3 niveaux

```
GLOBAL (tous les indicateurs)
  |
  +-- Categorie (ex: SLA Transverse, Service Desk, Process Incident...)
  |     |
  |     +-- Indicateur (ex: IQ_INC_1, ITR_QUAL_REF_TECH...)
  |           |
  |           +-- 7 Etapes (chacune : 3 couches statut/commentaire + actions)
```

Propagation du statut du bas vers le haut : "le pire l'emporte" a chaque niveau.

### 2.4 Systeme de commentaires a 3 couches

Chaque etape d'un indicateur porte 3 couches independantes de statut + commentaire :

| Couche | Origine | Exemple |
|--------|---------|---------|
| Global | Saisie au niveau vue Globale | "Blocage acces BDD pour tous" |
| Categorie | Saisie au niveau vue Categorie | "En attente livraison outil monitoring" |
| Indicateur | Saisie au niveau vue Indicateur | "Script d'extraction en cours de dev" |

**Comportement de saisie :**
- Saisie au niveau **Global** (etape N) → propage `statut_global` + `commentaire_global` a l'etape N de **tous** les indicateurs
- Saisie au niveau **Categorie** (etape N) → propage `statut_categorie` + `commentaire_categorie` a l'etape N de tous les indicateurs **de cette categorie**
- Saisie au niveau **Indicateur** (etape N) → met a jour uniquement `statut_indicateur` + `commentaire_indicateur` de cet indicateur

**Calcul du statut affiche :**
- Le statut affiche pour une etape = le pire parmi les 3 couches (global, categorie, indicateur)
- Permet de saisir un blocage une seule fois au lieu de le repeter sur N indicateurs

**Cas de deblocage partiel :**
- Si un indicateur n'est plus concerne par un blocage categorie/global, l'admin va sur l'indicateur et vide le commentaire/statut de la couche concernee
- Le statut se recalcule avec les couches restantes
- Les autres indicateurs conservent leur couche intacte

**Affichage dans la vue Indicateur :**
- Les 3 commentaires sont visibles (quand ils existent) avec indication de leur origine (pastille G / C / I ou equivalent)
- L'utilisateur voit d'un coup d'oeil d'ou vient chaque statut

**Modele de donnees :**
```
indicateur_etapes
  - indicateur_id          (FK -> indicateurs)
  - etape                  (FK -> etapes, 1-7)
  - statut_global_id       (FK nullable -> statuts_etape)
  - commentaire_global     (nullable)
  - statut_categorie_id    (FK nullable -> statuts_etape)
  - commentaire_categorie  (nullable)
  - statut_indicateur_id   (FK nullable -> statuts_etape)
  - commentaire_indicateur (nullable)
  UNIQUE(indicateur_id, etape)
```

**Tables de reference externalisees :**
- `statuts_etape` : 5 statuts CSI (intitule, couleur, severite) — permet le calcul "le pire l'emporte" par severite
- `etats_indicateur` : etats du cycle de vie (intitule, couleur)
- `types_indicateur` : types SLA/KPI/XLA (intitule, couleur)

### 2.5 Categories d'indicateurs

Les categories sont definies librement par l'utilisateur admin (exemples : "Suivi des incidents", "Gestion des stocks", "Pilotage"...). Elles regroupent les indicateurs par domaine fonctionnel.

### 2.6 Proprietes d'un indicateur

- Code (ex: IQ_INC_1) - identifiant unique
- Chapitre (optionnel, informatif) - reference documentaire libre
- Description
- Categorie
- Etat (Cadre, En attente, Realise, Annule, En cours, A cadrer) — valeurs dans table de reference `etats_indicateur`
- Type (SLA, KPI, XLA) — valeurs dans table de reference `types_indicateur`
- Periodicite de mesure (Quotidien, Hebdomadaire, Mensuel, Trimestriel, Semestriel, Annuel) — defaut Mensuel
- Valeur SLA cible (decimal, ex: 0.95 → affiche 95%)
- Formule KPI (texte libre decrivant le calcul)
- Penalite applicable (oui/non)
- Seuil (en secondes, affiche en format lisible : 3600 → 1h, 90 → 1min 30s)
- Condition de ciblage (texte descriptif) — heritable depuis la categorie ou le niveau global
- Condition de conformite (texte descriptif) — heritable depuis la categorie ou le niveau global

### 2.7 Ciblage et conformite heritables

Les regles de ciblage et conformite peuvent etre definies a 3 niveaux, avec heritage du haut vers le bas :

| Niveau | Porte | Exemple |
|--------|-------|---------|
| Global | Tous les indicateurs du projet | "Periode de reference : mois M-1" |
| Categorie | Tous les indicateurs de la categorie | "Incidents de priorite P1 a P3 sur la periode" |
| Indicateur | Cet indicateur uniquement | "Taux de resolution dans les SLA contractuels" |

**Heritage :** un indicateur sans ciblage propre herite de sa categorie ; une categorie sans ciblage propre herite du global.

**Double definition :** chaque regle peut avoir une definition fonctionnelle (comprehensible metier) et une definition technique (requete, source de donnees, outil).

---

## 3. Fonctionnalites

### 3.1 Organisation generale de l'interface

L'application comporte **2 espaces principaux**, accessibles via des onglets dans la barre de titre :

| Onglet | Usage |
|--------|-------|
| **Roue CSI** | Vue operationnelle : suivi de l'avancement des indicateurs via la roue (Global, Categorie, Indicateur) |
| **Referentiel** | Vue design : consultation et parametrage des indicateurs (tableau complet avec toutes les proprietes) |

**Compteurs inline** dans la barre de titre : pastilles colorees compactes (nb Conformes, En cours, Warning, Blocage, Non evalues) visibles en permanence.

### 3.2 Onglet Roue CSI - Navigation et vues (drill-down recursif)

**Tooltips :**
- Survol d'un indicateur (sidebar, tableaux) : affiche l'intitule/description complet en tooltip
- Survol d'une etape de la roue : affiche le texte detaille de l'etape en tooltip (textes definis par le pattern)
- Survol d'un bloc commentaire : affiche le texte integral de toutes les couches (G/C/I) en tooltip

**Layout general :**
- Sidebar gauche (220px) : navigation categories + indicateurs
- Fiche indicateur fixe (235px) : visible uniquement au niveau Indicateur, entre la sidebar et la roue
- Zone roue (flexible) : roue SVG + panneau statut + historique

**Vue Globale :**
- Layout : Sidebar | Roue pleine largeur (pas de fiche)
- Roue agregee de tous les indicateurs
- Sidebar gauche : liste des categories avec pastille couleur et nombre d'indicateurs
- Clic sur une etape de la roue : tableau de repartition par categorie pour cette etape
- Clic sur une categorie (sidebar ou tableau) : navigation vers la vue categorie
- Clic sur une etape pour editer : modale de saisie statut + commentaire **couche Global** (propage a tous les indicateurs)

**Vue Categorie :**
- Layout : Sidebar | Roue pleine largeur (pas de fiche)
- Roue agregee des indicateurs de la categorie
- Sidebar gauche : categories (active surlignee) + liste des indicateurs de la categorie
- Clic sur une etape : tableau de repartition par indicateur pour cette etape
- Clic sur un indicateur : navigation vers la vue indicateur
- Clic sur une etape pour editer : modale de saisie statut + commentaire **couche Categorie** (propage aux indicateurs de cette categorie)

**Vue Indicateur :**
- Layout : Sidebar | **Fiche fixe** | Roue (decalee a droite)
- **Fiche fixe verticale** (bandeau permanent entre sidebar et roue) affichant :
  - Code, description, badges (type, etat, statut CSI)
  - Chapitre, categorie
  - Conditions de ciblage et conformite (avec heritage visible)
  - Lien vers le Kanban (actions)
- Roue individuelle avec les 7 etapes et leurs couleurs
- Commentaires affiches dans des blocs SVG autour de la roue, relies par des lignes pointillees a leur etape
- Les 3 couches de commentaires visibles (G/C/I) quand elles existent, avec indication d'origine
- Panneau statut a droite de la roue
- Panneau historique a droite : liste des dates de revue, clic pour voir l'etat a cette date
- Clic sur une etape : modale d'edition avec onglets (couche Global / Categorie / Indicateur), possibilite de vider une couche pour debloquer

**Panneau filtre par statut (present sur toutes les vues avec roue) :**
- Affiche a droite de la roue, sur les vues Global, Categorie et Indicateur
- Liste les 5 statuts avec le nombre d'elements concernes entre parentheses
- Clic sur un statut : affiche une liste a 2 niveaux cliquables :
  - Niveau 1 : Categories (cliquables → navigation vers vue categorie)
  - Niveau 2 : Indicateurs par categorie (cliquables → navigation vers vue indicateur), avec les etapes concernees et leurs commentaires
- Au niveau vue Indicateur : liste les etapes ayant ce statut avec leurs commentaires

### 3.3 Onglet Referentiel

Vue dediee au design et parametrage des indicateurs :

- **Barre de recherche** : recherche par code, description, ciblage
- **Filtres** : 3 selecteurs (categorie, type SLA/KPI/XLA, etat)
- **Compteurs dynamiques** : nombre d'indicateurs par statut CSI, mis a jour en fonction des filtres actifs
- **Tableau complet** avec colonnes : Statut CSI, Chapitre, Code, Description, Categorie, Type, Etat, Periodicite, SLA, KPI, Penalite, Seuil, Ciblage, Conformite
- Colonnes ciblage/conformite avec tooltip pour le texte integral
- Lien "Voir roue" par ligne : bascule vers l'onglet Roue CSI avec navigation directe vers l'indicateur
- Clic sur une ligne : navigation vers la vue Indicateur (roue + fiche)
- **Sidebar contextuelle** : filtres rapides par categorie et par etat

### 3.4 Vue Actions (Kanban)

**Rattachement des actions :**
- Une action peut etre rattachee a **3 niveaux** :
  - **Global** : action transverse concernant l'ensemble du projet
  - **Categorie + Etape** : action transverse concernant tous les indicateurs d'une categorie pour une etape
  - **Indicateur + Etape** : action specifique a un indicateur pour une etape donnee
- Les actions de niveau superieur sont visibles dans les Kanban de niveau inferieur (en tant qu'actions heritees, distinguees visuellement)

**Proprietes d'une action :**
- Titre, description
- Responsable (assignee)
- Etape rattachee
- Statut : A faire / En cours / A valider / Termine / Rejete
- Date de debut previsionnelle
- Date de fin previsionnelle
- Predecesseurs (actions qui doivent etre terminees avant que celle-ci puisse demarrer)
- Commentaire
- Tache chapeau : une action peut avoir des sous-taches (parent/enfant)

**Dependances entre actions :**
- Une action peut declarer des predecesseurs (autres actions du meme projet)
- Une action avec des predecesseurs non termines est visuellement marquee comme "bloquee"
- Permet de modeliser des enchainements : "obtenir les acces" doit etre termine avant "configurer l'extraction"
- Distinct de la hierarchie parent/enfant (decomposition vs sequencement)

**Taches chapeau (parent/enfant) :**
- Une action chapeau regroupe des sous-taches
- Son statut et ses dates sont calcules dynamiquement depuis ses enfants
- Drill-down au clic pour voir les sous-taches
- Non draggable (statut derive)

**Board Kanban :**
- 5 colonnes : A faire / En cours / A valider / Termine / Rejete
- Drag & drop pour changer le statut
- Chaque carte : titre, assignee (trigramme), etape rattachee, dates, badge niveau
- Les cartes de niveau categorie sont marquees visuellement (badge "C")
- Statut "A valider" : l'intervenant propose, le chef de projet valide ou rejette

**Acces au Kanban :**
- Depuis la fiche indicateur (lien "Actions / Kanban")
- Depuis la vue categorie (actions transverses de la categorie)
- Vue globale (toutes les actions du projet)

### 3.5 Gestion de l'historique et revues

- **Enregistrement global (snapshot)** : en fin de reunion, le chef de projet enregistre l'etat de tous les indicateurs a la date du jour
- Les modifications entre deux revues sont du "travail en cours", figees lors de l'enregistrement
- Navigation historique : clic sur une date de revue pour voir l'etat complet a cette date
- **Lecture seule** : les donnees historiques sont strictement non modifiables

### 3.6 Compte-rendu d'avancement (CR)

Genere automatiquement lors de l'enregistrement global (snapshot) :
- Vue globale : etapes ayant evolue (intitules avec fond couleur)
- Categories modifiees : statut avant/apres
- Indicateurs modifies : etapes modifiees, commentaires, nouvelles actions
- Actions terminees depuis la derniere revue
- Format : HTML/PDF
- Envoi automatique aux membres de role "information" (et optionnellement aux autres membres)
- Le template du CR peut etre defini par le pattern du projet (sections, niveau de detail)

### 3.7 Patterns de projet

Systeme de modeles pre-configures permettant d'adapter la roue CSI a differents types de projets. Le moteur (7 etapes, couleurs, categories, actions) reste identique, seul le contenu initial change.

**Un pattern definit :**
- Un nom (ex: "Suivi indicateurs", "Migration technique", ...)
- Les textes des tooltips des 7 etapes adaptes au contexte du pattern
- Un catalogue de categories possibles (ex: Service Desk, Help-Desk, Proximite, N2, N3, Gestion stocks, Suivi CMDB, Supply Chain...)
- Des indicateurs pre-definis dans chaque categorie du catalogue
- Des regles de ciblage/conformite par defaut (au niveau categorie et indicateur)
- Des actions recurrentes pre-definies (optionnel)
- Un template de CR (sections, niveau de detail)

**A la creation d'un projet :**
1. L'utilisateur choisit un pattern (ou "projet vide")
2. Il selectionne les categories pertinentes dans le catalogue du pattern
3. Le projet est cree avec les categories, indicateurs et regles selectionnes

**Apres creation :**
- Le projet vit sa vie independamment du pattern (tout est modifiable librement)
- Le pattern n'est qu'une reference d'origine

**Scope :** Les patterns sont globaux (disponibles pour tous les clients).

### 3.8 Vues de reporting

Trois vues complementaires au Kanban pour le pilotage du projet :

**Vue PERT / Jalons :**
- Vue temporelle des actions avec leurs dependances (predecesseurs)
- Affichage des grands jalons (taches chapeau) sur une timeline
- Possibilite de developper un jalon pour voir ses sous-taches
- Chemin critique mis en evidence (enchainement d'actions le plus long)
- Visualisation des actions bloquees par des predecesseurs non termines

**Vue Intervenant ("Mes actions") :**
- Filtree sur un intervenant (par defaut : l'utilisateur connecte)
- Actions realisees (historique) et actions a venir
- Groupees par statut et/ou par projet
- Accessible par chaque membre pour suivre sa charge

**Vue Manager (charge des intervenants) :**
- Vue synthetique de la charge active de chaque intervenant
- Nombre d'actions par statut et par intervenant
- Identification des surcharges et des intervenants disponibles
- Filtrable par periode (actions en cours, a venir)

### 3.9 Gestion des membres et authentification

**Roles :**

| Role | Droits |
|------|--------|
| Admin | Tout : evaluer, creer des actions, valider, enregistrer revues, gerer membres, generer CR |
| Membre | Consulter toutes les vues, modifier ses actions, mettre a jour les statuts |
| Lecteur | Consulter toutes les vues en lecture seule |
| Information | Pas d'acces a l'application, destinataire des CR par email uniquement |

- Plusieurs admins possibles (chef de projet principal + suppleants)
- Createur d'un projet = admin automatique

**Authentification :**
- Login par email + mot de passe (hash werkzeug PBKDF2)
- Setup wizard au premier lancement (creation admin initial)
- Invitations par lien (token 7j, generation par admin, email mailto pre-rempli)
- SSO Microsoft (MSAL, actif si variables Azure dans .env)
- Emails secondaires : un membre peut avoir plusieurs adresses, connexion transparente via n'importe laquelle

**Circuit d'ajout d'un membre :**
1. Admin ajoute le membre (email, nom, trigramme, role)
2. Si role admin/membre : invitation generee automatiquement (lien copie + mailto)
3. Si role lecteur/information : enregistrement direct sans invitation (configurable)
4. Le membre recoit le lien, definit son mot de passe → compte active

### 3.10 Notifications

- **Invitation** : email mailto pre-rempli a l'ajout d'un membre (actuel)
- **CR apres snapshot** : envoi automatique aux membres "information" et optionnellement aux autres
- **Actions assignees** : notification a l'intervenant quand une action lui est assignee
- **Evolution future** : envoi SMTP automatique quand configure (variables .env), mailto en fallback

---

## 4. Architecture technique

### 4.1 Stack

- **Backend** : Python Flask + gunicorn
- **Frontend** : HTML/CSS/JS + SVG pour les roues
- **Base de donnees** : PostgreSQL 16 (schema `common` + un schema par client)
- **Deploiement** : Docker (Dockerfile + docker-compose) ou standalone local
- **Authentification** : email+mdp (PBKDF2), SSO Microsoft (MSAL optionnel)

### 4.2 Architecture PostgreSQL

**Schemas :**
- `common` : tables partagees (utilisateurs, clients, client_membres, invitations, tables de reference)
- `client_<slug>` : un schema par client (projets, projet_membres, categories, indicateurs, actions, revues)

**Connexion :** `SET search_path = client_schema, common` — resout les tables metier dans le schema client et les references dans common.

**Migration idempotente :** `migrate_client_schema()` applique les DDL (IF NOT EXISTS) + ALTER TABLE (ADD COLUMN IF NOT EXISTS) a chaque demarrage, garantissant la compatibilite.

### 4.3 Notifications

- **Court terme** : mailto pre-rempli (zero config, fonctionne immediatement)
- **Moyen terme** : envoi SMTP automatique (variables SMTP_HOST, SMTP_PORT, etc. dans .env)
- **Long terme** : integration Power Automate pour workflows avances

---

## 5. Decisions prises

| Sujet | Decision | Justification |
|-------|----------|---------------|
| Framework | Flask | Templates Jinja2, ideal pour rendu serveur HTML/SVG |
| Base de donnees | PostgreSQL | Multi-schema, robuste, deploiement Docker |
| Interface | Web (HTML/SVG/JS) | SVG ideal pour la roue, drill-down naturel |
| Deploiement | Docker + standalone | Docker pour VPS, standalone pour dev local |
| Commentaires SVG | Blocs autour de la roue avec lignes | Fidelite avec l'Excel original |
| Kanban | 5 statuts avec validation | A faire / En cours / A valider / Termine / Rejete |
| Dependances actions | Predecesseurs bloquants | Distinct de parent/enfant (sequencement vs decomposition) |
| Historique | Enregistrement global par revue | Snapshot complet de tous les indicateurs a une date |
| CR | Generation auto a l'enregistrement | Diff avec revue precedente, template defini par pattern |
| Ciblage/Conformite | Heritable (Global → Categorie → Indicateur) | Evite la repetition, double definition fonc/tech |
| Notifications | Mailto → SMTP → Power Automate | Progression par paliers de complexite |
| Commentaires 3 couches | Global / Categorie / Indicateur par etape | Saisie unique propagee, deblocage partiel possible |
| Referentiels externes | Tables statuts, etats, types | Modifiable sans toucher au code |
| Snapshots | indicateur_etapes + proprietes indicateurs | Photo complete, pas de snapshot Kanban |
| Patterns | Globaux, catalogue de categories selectionnable | Template de demarrage, projet independant ensuite |
| Authentification | Email+mdp, invitations lien, SSO Microsoft optionnel | Compatible local et cloud |
| Roles | 4 niveaux (admin/membre/lecteur/information) | Information = destinataire CR, pas d'acces app |

---

## 6. Etapes de realisation

### Realise

- [x] Analyse du fichier Excel original
- [x] Modele de donnees (PostgreSQL multi-schema)
- [x] Framework : Flask + psycopg3
- [x] Structure du projet Python
- [x] Composant SVG de la roue (reutilisable aux 3 niveaux)
- [x] Backend API (routes Flask : step save, actions CRUD, user search, clients/projets)
- [x] Vues : Global, Categorie, Indicateur, Kanban (3 niveaux), Referentiel, Login, Accueil
- [x] Gestion multi-clients / multi-projets (schemas PostgreSQL)
- [x] Kanban : drag & drop, autocomplete assignee, assignation par email, dates debut/fin, taches chapeau
- [x] Gestion membres : 4 roles, controle d'acces, page admin, invitation (lien + mailto)
- [x] Bulles commentaires sur roues globale/categorie + edition directe
- [x] Heritage couleurs global → categorie, modale avec onglets couche
- [x] Dates membres + emails secondaires
- [x] Edition client/projet depuis l'accueil + description projet
- [x] Migration SQLite → PostgreSQL (db.py, 4 services, routes, templates)
- [x] Authentification (email+mdp, invitations par lien, setup wizard, SSO Microsoft prepare)
- [x] Dockerisation (Dockerfile + docker-compose + gunicorn)
- [x] Migration auto des schemas au demarrage (migrate_all_schemas)
- [x] CRUD categories dans le referentiel (ajout, renommage, reordonnancement, suppression)
- [x] Proprietes indicateur (periodicite, SLA, KPI, penalite, seuil) — schema, migration, API, fiche, referentiel

### A faire — Priorite haute

- [ ] Dependances entre actions (predecesseurs bloquants)
- [ ] Ciblage/conformite heritables (global → categorie → indicateur)
- [ ] Double definition ciblage : fonctionnelle + technique
- [ ] Historique et snapshots (backend + integration UI)
- [ ] Generation du CR (diff entre snapshots, template par pattern)

### A faire — Priorite moyenne

- [ ] Patterns de projet (modeles pre-configures avec categories/indicateurs/actions/CR)
- [ ] Vue PERT / Jalons (timeline des actions avec dependances)
- [ ] Vue Intervenant ("Mes actions" : realisees et a venir)
- [ ] Vue Manager (charge active des intervenants)
- [ ] Envoi SMTP automatique (emails invitation, CR, notifications)
- [ ] Deploiement VPS

### A faire — Priorite basse

- [ ] Import des donnees existantes (Excel → PostgreSQL)
- [ ] Notifications Power Automate (workflows avances)
- [ ] Tests et packaging
- [ ] Nettoyage fichiers legacy SQLite (schema.sql, seed.sql, seed_demo.sql)

---

## 7. Prototypes

Plusieurs prototypes HTML interactifs ont ete crees dans le dossier `prototype/` :

| Fichier | Description | Statut |
|---------|-------------|--------|
| `prototype.html` | Roue SVG avec systeme 3 couches (G/C/I), commentaires SVG, modale d'edition, Kanban | Prototype de reference pour la roue |
| `proto-1-toggle-panel.html` | Approche toggle [Roue][Tableau] + panneau lateral glissant | Explore, non retenu |
| `proto-2-referentiel-panel.html` | Approche 2 onglets topbar + panneau lateral glissant | Explore, non retenu |
| **`proto-3-fiche-fixe.html`** | **Approche retenue** : 2 onglets topbar (Roue CSI / Referentiel) + fiche fixe verticale + compteurs inline | **Approche retenue** |
| **`prototype-consolide.html`** | **Prototype de reference** : consolide toutes les fonctionnalites validees (roue, historique, lecture seule) | **Reference** |
