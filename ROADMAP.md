# ROADMAP - Roue CSI

## 1. Contexte

Application generique de suivi de la maturite des indicateurs de service (SLA/KPI) basee sur la methodologie CSI (Continual Service Improvement). Remplace un outil Excel macro par une application Python web standalone, adaptable a tout contexte de suivi d'indicateurs.

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
- Chapitre (optionnel, informatif) - reference documentaire libre, peut etre modifiee sans impact sur le fonctionnement de l'app. N'est PAS utilise comme cle ou identifiant.
- Description
- Categorie
- Etat (Cadre, En attente, Realise, Annule, En cours, A cadrer) — valeurs dans table de reference `etats_indicateur`
- Type (SLA, KPI, XLA) — valeurs dans table de reference `types_indicateur`
- Condition de ciblage (texte descriptif, consultable/modifiable sous la roue)
- Condition de conformite (texte descriptif, consultable/modifiable sous la roue)

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
- Survol d'une etape de la roue : affiche le texte detaille de l'etape en tooltip (textes a definir)
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
  - Conditions de ciblage et conformite (consultables/modifiables, retirees de sous la roue)
  - Lien vers le Kanban (actions)
- Roue individuelle avec les 7 etapes et leurs couleurs
- Commentaires affiches dans des blocs SVG autour de la roue, relies par des lignes pointillees a leur etape (jamais de chevauchement avec la roue)
- Les 3 couches de commentaires visibles (G/C/I) quand elles existent, avec indication d'origine
- Panneau statut a droite de la roue
- Panneau historique a droite : liste des dates de revue, clic pour voir l'etat a cette date
- Clic sur une etape : modale d'edition avec 3 onglets ou sections (couche Global / Categorie / Indicateur), possibilite de vider une couche pour debloquer
- La fiche apparait/disparait avec une transition animee lors du changement de niveau

**Panneau filtre par statut (present sur toutes les vues avec roue) :**
- Affiche a droite de la roue, sur les vues Global, Categorie et Indicateur
- Liste les 5 statuts avec le nombre d'elements concernes entre parentheses
- Clic sur un statut : affiche une liste a 2 niveaux cliquables :
  - Niveau 1 : Categories (cliquables → navigation vers vue categorie)
  - Niveau 2 : Indicateurs par categorie (cliquables → navigation vers vue indicateur), avec les etapes concernees et leurs commentaires
- Au niveau vue Indicateur : liste les etapes ayant ce statut avec leurs commentaires
- Complementaire au drill-down par etape : deux axes de lecture (par etape vs par statut)

### 3.3 Onglet Referentiel

Vue dediee au design et parametrage des indicateurs :

- **Barre de recherche** : recherche par code, description, ciblage
- **Filtres** : 3 selecteurs (categorie, type SLA/KPI/XLA, etat)
- **Compteurs dynamiques** : nombre d'indicateurs par statut CSI, mis a jour en fonction des filtres actifs
- **Tableau complet** avec colonnes : Statut CSI, Chapitre, Code, Description, Categorie, Type, Etat, Ciblage, Conformite
- Colonnes ciblage/conformite avec tooltip pour le texte integral
- Lien "Voir roue" par ligne : bascule vers l'onglet Roue CSI avec navigation directe vers l'indicateur
- Clic sur une ligne : navigation vers la vue Indicateur (roue + fiche)
- **Sidebar contextuelle** : filtres rapides par categorie et par etat

### 3.4 Vue Actions (Kanban)

**Rattachement des actions :**
- Une action peut etre rattachee a **2 niveaux** :
  - **Indicateur + Etape** : cas standard, action specifique a un indicateur pour une etape donnee (ex: "Obtenir les referentiels" pour ITR_QUAL_REF_TECH / etape COLLECTE)
  - **Categorie + Etape** : action transverse concernant tous les indicateurs d'une categorie pour une etape (ex: "Obtenir les acces a la BDD de supervision" pour Process Incident / etape Ce qu'on PEUT)
- Les actions de niveau categorie sont visibles dans le Kanban de chaque indicateur de la categorie (en tant qu'actions heritees, distinguees visuellement)

**Board Kanban :**
- 5 colonnes : A faire / En cours / A valider / Termine / Rejete
- Chaque carte : titre, assignee, etape rattachee, niveau (indicateur ou categorie)
- Les cartes de niveau categorie sont marquees visuellement (badge "C" ou bordure distincte) pour les distinguer des cartes specifiques a l'indicateur
- Statut "A valider" : l'intervenant propose, le chef de projet valide ou rejette

**Acces au Kanban :**
- Depuis la fiche indicateur (lien "Actions / Kanban")
- Depuis la vue categorie (pour voir les actions transverses de la categorie)
- Vue "Mes taches" pour chaque intervenant (toutes ses taches, tous niveaux confondus)

### 3.5 Gestion de l'historique et revues

- **Enregistrement global (snapshot)** : en fin de reunion, le chef de projet enregistre l'etat de tous les indicateurs a la date du jour
- Les modifications entre deux revues sont du "travail en cours", figees lors de l'enregistrement
- Navigation historique : clic sur une date de revue pour voir l'etat complet a cette date
- **Lecture seule** : les donnees historiques sont strictement non modifiables. L'affichage d'un snapshot passe sert uniquement a la consultation et a la comparaison avec l'etat actuel

### 3.6 Compte-rendu d'avancement (CR)

Genere automatiquement lors de l'enregistrement global :
- Vue globale : etapes ayant evolue (intitules avec fond couleur, pas les noms de couleurs)
- Categories modifiees : statut avant/apres
- Indicateurs modifies : etapes modifiees, commentaires, nouvelles actions
- Actions terminees depuis la derniere revue
- Format : HTML/PDF
- Envoi : au chef de projet pour validation et redirection, ou directement a une liste de diffusion

### 3.7 Workflow des taches

Complement a la section 3.4 (Vue Actions / Kanban) concernant le flux de travail :

- Une action est creee par un admin, assignee a un intervenant
- L'intervenant peut modifier le statut et le commentaire de ses taches (via fichier inbox)
- Flux : A faire -> En cours -> A valider -> Termine / Rejete
- Vue "Mes taches" pour chaque intervenant (filtree sur son login)

---

## 4. Architecture technique

### 4.1 Stack

- **Backend** : Python Flask
- **Frontend** : HTML/CSS/JS + SVG pour les roues
- **Base de donnees** : SQLite (fichier unique `.db`)
- **Deploiement** : Standalone (serveur local, ouverture navigateur auto)
- **Hebergement** : OneDrive/SharePoint (sources + executable + DB + dossiers inbox/outbox)

### 4.2 Gestion des utilisateurs

- Identification automatique par login Windows/O365 (pas d'authentification manuelle)
- Table `utilisateurs` avec login et role

| Role | Droits |
|------|--------|
| Admin | Tout : evaluer, creer des taches, valider inbox, enregistrer revues, gerer utilisateurs, generer CR |
| Intervenant | Consulter toutes les vues, mettre a jour ses taches (via fichier inbox) |

- Plusieurs admins possibles (chef de projet principal + suppleants)
- Pas de mecanisme de verrou : les admins ne sont jamais deux a ecrire simultanement

### 4.3 Pattern Inbox/Outbox (echanges via OneDrive)

```
OneDrive partage/
  |
  +-- app/                     <- Application (tout le monde)
  +-- data/
  |     +-- roue_csi.db        <- Base SQLite (ecriture admin uniquement)
  +-- inbox/                   <- Modifications des intervenants
  |     +-- 2026-02-16_dupont_IQ_INC_1.json
  |     +-- ...
  +-- outbox/                  <- Notifications vers les intervenants
        +-- dupont/
        |     +-- task_2026-02-16_IQ_INC_1.json
        +-- martin/
              +-- ...
```

**Flux intervenant -> admin :**
1. L'intervenant met a jour une tache dans l'app
2. L'app genere un fichier JSON dans `inbox/`
3. Power Automate notifie le chef de projet (email)
4. Le chef de projet ouvre l'app, voit les modifications en attente
5. Ecran de validation avec diff : valide ou rejette chaque modification
6. Les fichiers traites sont archives

**Flux admin -> intervenant :**
1. Le chef de projet cree/assigne une tache
2. Un fichier est genere dans `outbox/{login_intervenant}/`
3. Power Automate peut envoyer un email memo a l'intervenant
4. L'intervenant voit ses taches dans la vue "Mes taches"

### 4.4 Format des fichiers d'echange (JSON)

**Mise a jour de tache :**
```json
{
  "auteur": "p.dupont",
  "date": "2026-02-16T14:30:00",
  "type": "task_update",
  "indicateur": "IQ_INC_1",
  "etape": 3,
  "task_id": 42,
  "statut": "a_valider",
  "commentaire": "Extraction SCCM mise en place"
}
```

**Nouvelle tache assignee :**
```json
{
  "auteur": "chef.projet",
  "date": "2026-02-16T10:00:00",
  "type": "task_assign",
  "indicateur": "IQ_INC_1",
  "etape": 3,
  "titre": "Mettre en place l'extraction SCCM",
  "assignee": "p.dupont",
  "commentaire": "A faire avant la prochaine revue"
}
```

### 4.5 Notifications (Power Automate)

- Declencheur : creation d'un fichier dans le dossier `inbox/` sur OneDrive
- Action : email au(x) chef(s) de projet
- Optionnel : declencheur sur `outbox/{intervenant}/` pour email memo a l'intervenant
- Configuration a faire avec accompagnement (l'utilisateur ne maitrise pas Power Automate)

---

## 5. Decisions prises

| Sujet | Decision | Justification |
|-------|----------|---------------|
| Framework | Flask | Templates Jinja2 natifs, ideal pour rendu serveur HTML/SVG, simple pour app standalone |
| Base de donnees | SQLite | Natif Python, portable, un seul fichier, fiable |
| Interface | Web (HTML/SVG/JS) | SVG ideal pour la roue, drill-down naturel en web |
| Deploiement | Standalone | Pas de serveur disponible |
| Hebergement | OneDrive | Seul stockage partage disponible |
| Ecriture DB | Admin uniquement | Evite les problemes de concurrence SQLite |
| Echanges | Fichiers JSON inbox/outbox | Compatible OneDrive, tracable, validable |
| Verrou DB | Non | Risque de conflit negligeable (~1/10000) |
| Commentaires SVG | Blocs autour de la roue avec lignes | Fidelite avec l'Excel original, pas de chevauchement |
| Kanban | 5 statuts avec validation | A faire / En cours / A valider / Termine / Rejete |
| Historique | Enregistrement global par revue | Snapshot complet de tous les indicateurs a une date |
| CR | Generation auto a l'enregistrement | Diff avec revue precedente, format HTML/PDF |
| Notifications | Power Automate | Ecosysteme Microsoft deja en place |
| Multi-admin | Oui, par role | Suppleance en cas d'absence |
| Identification | Login Windows/O365 auto | Pas de mot de passe a gerer |
| Commentaires 3 couches | Global / Categorie / Indicateur par etape | Saisie unique propagee, deblocage partiel possible |
| Tooltips | Sur indicateurs et etapes | Lisibilite, acces rapide a l'intitule complet |
| Referentiels externes | Tables statuts_etape, etats_indicateur, types_indicateur | Modifiable sans toucher au code, extensible |
| Snapshots | indicateur_etapes + proprietes indicateurs | Photo complete a chaque revue, pas de snapshot Kanban |
| Tri indicateurs | Alphabetique par code | Pas de champ ordre, tri naturel |

---

## 6. Etapes de realisation (a affiner)

- [x] Modele de donnees detaille (12 tables, schema.sql + seed.sql)
- [x] Choix framework : Flask
- [x] Structure du projet Python (app/, data/, tests/)
- [ ] Composant SVG de la roue (reutilisable aux 3 niveaux)
- [ ] Backend API
- [ ] Vues : Global, Categorie, Indicateur, Kanban
- [ ] Systeme inbox/outbox
- [ ] Gestion utilisateurs et roles
- [ ] Historique et enregistrement global
- [ ] Generation du CR
- [ ] Notifications Power Automate
- [ ] Import des donnees existantes (Excel -> SQLite)
- [ ] Tests et packaging

---

## 7. Prototypes

Plusieurs prototypes HTML interactifs ont ete crees dans le dossier `prototype/` :

| Fichier | Description | Statut |
|---------|-------------|--------|
| `prototype.html` | Roue SVG avec systeme 3 couches (G/C/I), commentaires SVG, modale d'edition, Kanban | Prototype de reference pour la roue |
| `proto-1-toggle-panel.html` | Approche toggle [Roue][Tableau] + panneau lateral glissant | Explore, non retenu |
| `proto-2-referentiel-panel.html` | Approche 2 onglets topbar + panneau lateral glissant | Explore, non retenu |
| **`proto-3-fiche-fixe.html`** | **Approche retenue** : 2 onglets topbar (Roue CSI / Referentiel) + fiche fixe verticale + compteurs inline | **Approche retenue** |

**Approche retenue (proto-3)** illustre :
- 2 onglets : Roue CSI / Referentiel
- Layout a 3 colonnes (Sidebar | Fiche fixe | Roue) au niveau indicateur
- Fiche verticale avec proprietes, ciblage, conformite, lien Kanban
- Compteurs inline dans la barre de titre
- Referentiel avec recherche, filtres (categorie, type, etat) et statistiques dynamiques
- Roue SVG avec systeme 3 couches, commentaires SVG relies par lignes pointillees
- Drill-down recursif et navigation par breadcrumb
