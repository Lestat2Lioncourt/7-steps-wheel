-- ============================================
-- Roue CSI - Schema client (PostgreSQL)
-- Tables metier dediees a un client
-- Execute dans le schema du client (search_path deja positionne)
-- Les references vers common.* sont explicites
-- ============================================

-- Projets du client
CREATE TABLE IF NOT EXISTS projets (
    id                      SERIAL PRIMARY KEY,
    nom                     TEXT NOT NULL,
    description             TEXT,
    ciblage_fonctionnel     TEXT,
    ciblage_technique       TEXT,
    conformite_fonctionnel  TEXT,
    conformite_technique    TEXT,
    cc_commentaire          TEXT,
    cc_couleur              TEXT,
    date_creation           TEXT NOT NULL,
    actif                   BOOLEAN DEFAULT TRUE
);

-- Membres d'un projet (role specifique au projet)
CREATE TABLE IF NOT EXISTS projet_membres (
    id          SERIAL PRIMARY KEY,
    projet_id   INTEGER NOT NULL REFERENCES projets(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES common.utilisateurs(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('admin', 'membre', 'lecteur', 'information')),
    date_creation           TEXT,
    date_derniere_connexion TEXT,
    date_fin                TEXT,
    UNIQUE(projet_id, user_id)
);

-- Categories d'indicateurs
CREATE TABLE IF NOT EXISTS categories (
    id                      SERIAL PRIMARY KEY,
    projet_id               INTEGER NOT NULL REFERENCES projets(id) ON DELETE CASCADE,
    nom                     TEXT NOT NULL,
    ordre                   INTEGER DEFAULT 0,
    ciblage_fonctionnel     TEXT,
    ciblage_technique       TEXT,
    conformite_fonctionnel  TEXT,
    conformite_technique    TEXT,
    cc_commentaire          TEXT,
    cc_couleur              TEXT,
    UNIQUE(projet_id, nom)
);

-- Indicateurs
CREATE TABLE IF NOT EXISTS indicateurs (
    id                      SERIAL PRIMARY KEY,
    projet_id               INTEGER NOT NULL REFERENCES projets(id) ON DELETE CASCADE,
    code                    TEXT NOT NULL,
    description             TEXT,
    chapitre                TEXT,
    categorie_id            INTEGER NOT NULL REFERENCES categories(id),
    etat_id                 INTEGER NOT NULL REFERENCES common.etats_indicateur(id),
    type_id                 INTEGER NOT NULL REFERENCES common.types_indicateur(id),
    periodicite             TEXT DEFAULT 'Mensuel',
    sla_valeur              REAL,
    kpi_formule             TEXT,
    penalite                BOOLEAN DEFAULT FALSE,
    seuil                   INTEGER,
    ciblage_fonctionnel     TEXT,
    ciblage_technique       TEXT,
    conformite_fonctionnel  TEXT,
    conformite_technique    TEXT,
    cc_commentaire          TEXT,
    cc_couleur              TEXT,
    UNIQUE(projet_id, code)
);

-- Coeur du modele : 3 couches (Global / Categorie / Indicateur) par etape
CREATE TABLE IF NOT EXISTS indicateur_etapes (
    id                      SERIAL PRIMARY KEY,
    indicateur_id           INTEGER NOT NULL REFERENCES indicateurs(id) ON DELETE CASCADE,
    etape                   INTEGER NOT NULL REFERENCES common.etapes(numero),
    statut_global_id        INTEGER REFERENCES common.statuts_etape(id),
    commentaire_global      TEXT,
    statut_categorie_id     INTEGER REFERENCES common.statuts_etape(id),
    commentaire_categorie   TEXT,
    statut_indicateur_id    INTEGER REFERENCES common.statuts_etape(id),
    commentaire_indicateur  TEXT,
    UNIQUE(indicateur_id, etape)
);

-- Actions Kanban
CREATE TABLE IF NOT EXISTS actions (
    id                  SERIAL PRIMARY KEY,
    projet_id           INTEGER NOT NULL REFERENCES projets(id) ON DELETE CASCADE,
    titre               TEXT NOT NULL,
    description         TEXT,
    niveau              TEXT NOT NULL CHECK (niveau IN ('global', 'indicateur', 'categorie')),
    indicateur_id       INTEGER REFERENCES indicateurs(id),
    categorie_id        INTEGER REFERENCES categories(id),
    etape               INTEGER NOT NULL REFERENCES common.etapes(numero),
    assignee_login      TEXT NOT NULL REFERENCES common.utilisateurs(login),
    statut              TEXT NOT NULL DEFAULT 'a_faire'
                        CHECK (statut IN ('a_faire', 'en_cours', 'a_valider', 'termine', 'rejete')),
    commentaire         TEXT,
    date_debut          TEXT,
    date_fin            TEXT,
    parent_id           INTEGER REFERENCES actions(id),
    cree_par            TEXT NOT NULL REFERENCES common.utilisateurs(login),
    date_creation       TEXT NOT NULL,
    date_modification   TEXT,
    CHECK (
        (niveau = 'global') OR
        (niveau = 'indicateur' AND indicateur_id IS NOT NULL) OR
        (niveau = 'categorie' AND categorie_id IS NOT NULL)
    )
);

-- Historique : snapshots par revue
CREATE TABLE IF NOT EXISTS revues (
    id          SERIAL PRIMARY KEY,
    projet_id   INTEGER NOT NULL REFERENCES projets(id) ON DELETE CASCADE,
    date        TEXT NOT NULL,
    cree_par    TEXT NOT NULL REFERENCES common.utilisateurs(login),
    commentaire TEXT
);

CREATE TABLE IF NOT EXISTS revue_indicateurs (
    id                      SERIAL PRIMARY KEY,
    revue_id                INTEGER NOT NULL REFERENCES revues(id) ON DELETE CASCADE,
    indicateur_id           INTEGER NOT NULL REFERENCES indicateurs(id),
    code                    TEXT,
    description             TEXT,
    chapitre                TEXT,
    categorie_id            INTEGER REFERENCES categories(id),
    etat_id                 INTEGER REFERENCES common.etats_indicateur(id),
    type_id                 INTEGER REFERENCES common.types_indicateur(id),
    periodicite             TEXT,
    sla_valeur              REAL,
    kpi_formule             TEXT,
    penalite                BOOLEAN,
    seuil                   INTEGER,
    ciblage_fonctionnel     TEXT,
    ciblage_technique       TEXT,
    conformite_fonctionnel  TEXT,
    conformite_technique    TEXT,
    UNIQUE(revue_id, indicateur_id)
);

CREATE TABLE IF NOT EXISTS revue_indicateur_etapes (
    id                      SERIAL PRIMARY KEY,
    revue_id                INTEGER NOT NULL REFERENCES revues(id) ON DELETE CASCADE,
    indicateur_id           INTEGER NOT NULL REFERENCES indicateurs(id),
    etape                   INTEGER NOT NULL,
    statut_global_id        INTEGER REFERENCES common.statuts_etape(id),
    commentaire_global      TEXT,
    statut_categorie_id     INTEGER REFERENCES common.statuts_etape(id),
    commentaire_categorie   TEXT,
    statut_indicateur_id    INTEGER REFERENCES common.statuts_etape(id),
    commentaire_indicateur  TEXT,
    UNIQUE(revue_id, indicateur_id, etape)
);
