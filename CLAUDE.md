# CLAUDE.md - Contexte projet Roue CSI

## Resume du projet

Application web Python standalone remplacant un fichier Excel macro (`Roue CSI.xlsm`) pour le suivi de la maturite des indicateurs de service (SLA/KPI/XLA) selon la methodologie CSI (Continual Service Improvement) a 7 etapes. Application generique, non liee a un contrat ou client specifique.

## Etat d'avancement

**Phase actuelle : Developpement** - Fondations posees :
1. Analyse du fichier Excel original (`Roue CSI.xlsm` + `Roue CSI.accdb`)
2. Concepts metier et architecture definis
3. Prototypes HTML interactifs valides
4. Modele de donnees SQLite implemente (12 tables, donnees de reference)
5. Framework choisi : **Flask**
6. Structure projet Python creee

**Prochaines etapes** : Composant SVG de la roue, backend API (routes Flask), vues HTML.

## Fichiers du projet

| Fichier | Role |
|---------|------|
| `ROADMAP.md` | Documentation complete du projet : concepts, fonctionnalites, architecture, decisions |
| `CLAUDE.md` | Ce fichier - contexte pour Claude Code |
| `_old_version/Roue CSI.xlsm` | Fichier Excel original a remplacer (4 onglets, macros VBA) |
| `_old_version/Roue CSI.accdb` | Base Access originale |
| `_old_version/Rendu.png` | Screenshot de la roue Excel pour reference visuelle |
| `prototype/prototype.html` | Prototype v3 : roue SVG avec systeme 3 couches G/C/I, modale, Kanban |
| `prototype/proto-1-toggle-panel.html` | Exploration : toggle Roue/Tableau + panneau lateral (non retenu) |
| `prototype/proto-2-referentiel-panel.html` | Exploration : 2 onglets topbar + panneau lateral (non retenu) |
| `prototype/proto-3-fiche-fixe.html` | Exploration : fiche fixe + referentiel (approche retenue, inspire le consolide) |
| `prototype/prototype-consolide.html` | **Prototype de reference** - consolide toutes les fonctionnalites validees |
| `app/` | Code source Python (Flask) : database, models, routes, services, static, templates |
| `app/database/schema.sql` | Schema SQLite complet (12 tables) |
| `app/database/seed.sql` | Donnees de reference initiales (etapes, statuts, etats, types) |
| `app/database/db.py` | init_db() + get_connection() |
| `app/main.py` | Point d'entree Flask (app factory + ouverture navigateur auto) |
| `data/roue_csi.db` | Base SQLite initialisee |
| `requirements.txt` | Dependances Python (flask) |

## Decisions cles prises

- **Stack** : Python Flask, SQLite, HTML/CSS/JS + SVG
- **Deploiement** : Standalone (serveur local, ouverture navigateur auto), heberge sur OneDrive
- **Interface** : 2 onglets (Roue CSI / Referentiel), fiche fixe verticale au niveau indicateur
- **Commentaires** : Systeme a 3 couches (Global/Categorie/Indicateur) par etape, "le pire l'emporte"
- **Kanban** : 5 colonnes, rattachement a 2 niveaux (indicateur+etape OU categorie+etape)
- **Historique** : Snapshots par revue, consultation en lecture seule uniquement
- **Echanges multi-utilisateurs** : Pattern inbox/outbox JSON via OneDrive
- **Notifications** : Power Automate (l'utilisateur aura besoin d'accompagnement)
- **Compteurs** : Inline dans la barre de titre (pastilles compactes)
- **Identification** : Login Windows/O365 automatique

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
- [ ] Composant SVG de la roue (reutilisable aux 3 niveaux)
- [ ] Backend API
- [ ] Vues : Global, Categorie, Indicateur, Kanban, Referentiel
- [ ] Systeme inbox/outbox
- [ ] Gestion utilisateurs et roles
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
