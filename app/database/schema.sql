-- ============================================
-- Roue CSI - Schema SQLite
-- ============================================

PRAGMA foreign_keys = ON;

-- --------------------------------------------
-- Tables de reference
-- --------------------------------------------

-- 7 etapes fixes de la roue CSI
CREATE TABLE etapes (
    numero      INTEGER PRIMARY KEY,
    nom         TEXT NOT NULL,
    description TEXT,
    tooltip     TEXT
);

-- 5 statuts d'evaluation par etape (Gris -> Rouge)
CREATE TABLE statuts_etape (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    intitule    TEXT UNIQUE NOT NULL,
    couleur     TEXT NOT NULL,
    severite    INTEGER NOT NULL,   -- 0=le moins grave, 4=le plus grave (pour "le pire l'emporte")
    ordre       INTEGER DEFAULT 0
);

-- Etats du cycle de vie d'un indicateur
CREATE TABLE etats_indicateur (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    intitule    TEXT UNIQUE NOT NULL,
    couleur     TEXT NOT NULL,
    ordre       INTEGER DEFAULT 0
);

-- Types d'indicateur
CREATE TABLE types_indicateur (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    intitule    TEXT UNIQUE NOT NULL,
    couleur     TEXT,
    ordre       INTEGER DEFAULT 0
);

-- --------------------------------------------
-- Tables metier
-- --------------------------------------------

CREATE TABLE utilisateurs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    login       TEXT UNIQUE NOT NULL,
    nom         TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('admin', 'intervenant'))
);

CREATE TABLE categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT UNIQUE NOT NULL,
    ordre       INTEGER DEFAULT 0
);

CREATE TABLE indicateurs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT UNIQUE NOT NULL,
    description     TEXT,
    chapitre        TEXT,
    categorie_id    INTEGER NOT NULL REFERENCES categories(id),
    etat_id         INTEGER NOT NULL REFERENCES etats_indicateur(id),
    type_id         INTEGER NOT NULL REFERENCES types_indicateur(id),
    ciblage         TEXT,
    conformite      TEXT
);

-- Coeur du modele : 3 couches (Global / Categorie / Indicateur) par etape
CREATE TABLE indicateur_etapes (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    indicateur_id           INTEGER NOT NULL REFERENCES indicateurs(id),
    etape                   INTEGER NOT NULL REFERENCES etapes(numero),
    statut_global_id        INTEGER REFERENCES statuts_etape(id),
    commentaire_global      TEXT,
    statut_categorie_id     INTEGER REFERENCES statuts_etape(id),
    commentaire_categorie   TEXT,
    statut_indicateur_id    INTEGER REFERENCES statuts_etape(id),
    commentaire_indicateur  TEXT,
    UNIQUE(indicateur_id, etape)
);

-- Actions Kanban (rattachement a 2 niveaux)
CREATE TABLE actions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    titre               TEXT NOT NULL,
    description         TEXT,
    niveau              TEXT NOT NULL CHECK (niveau IN ('indicateur', 'categorie')),
    indicateur_id       INTEGER REFERENCES indicateurs(id),
    categorie_id        INTEGER REFERENCES categories(id),
    etape               INTEGER NOT NULL REFERENCES etapes(numero),
    assignee_login      TEXT NOT NULL REFERENCES utilisateurs(login),
    statut              TEXT NOT NULL DEFAULT 'a_faire'
                        CHECK (statut IN ('a_faire', 'en_cours', 'a_valider', 'termine', 'rejete')),
    commentaire         TEXT,
    cree_par            TEXT NOT NULL REFERENCES utilisateurs(login),
    date_creation       TEXT NOT NULL,
    date_modification   TEXT,
    CHECK (
        (niveau = 'indicateur' AND indicateur_id IS NOT NULL) OR
        (niveau = 'categorie' AND categorie_id IS NOT NULL)
    )
);

-- --------------------------------------------
-- Historique : snapshots par revue
-- --------------------------------------------

CREATE TABLE revues (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT UNIQUE NOT NULL,   -- datetime ISO 8601 de l'enregistrement
    cree_par    TEXT NOT NULL REFERENCES utilisateurs(login),
    commentaire TEXT
);

-- Snapshot des proprietes indicateur
CREATE TABLE revue_indicateurs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    revue_id        INTEGER NOT NULL REFERENCES revues(id),
    indicateur_id   INTEGER NOT NULL REFERENCES indicateurs(id),
    code            TEXT,
    description     TEXT,
    chapitre        TEXT,
    categorie_id    INTEGER REFERENCES categories(id),
    etat_id         INTEGER REFERENCES etats_indicateur(id),
    type_id         INTEGER REFERENCES types_indicateur(id),
    ciblage         TEXT,
    conformite      TEXT,
    UNIQUE(revue_id, indicateur_id)
);

-- Snapshot des statuts/commentaires par etape
CREATE TABLE revue_indicateur_etapes (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    revue_id                INTEGER NOT NULL REFERENCES revues(id),
    indicateur_id           INTEGER NOT NULL REFERENCES indicateurs(id),
    etape                   INTEGER NOT NULL,
    statut_global_id        INTEGER REFERENCES statuts_etape(id),
    commentaire_global      TEXT,
    statut_categorie_id     INTEGER REFERENCES statuts_etape(id),
    commentaire_categorie   TEXT,
    statut_indicateur_id    INTEGER REFERENCES statuts_etape(id),
    commentaire_indicateur  TEXT,
    UNIQUE(revue_id, indicateur_id, etape)
);
