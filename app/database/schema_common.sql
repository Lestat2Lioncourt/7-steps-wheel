-- ============================================
-- Roue CSI - Schema common (PostgreSQL)
-- Tables partagees entre tous les clients
-- ============================================

CREATE SCHEMA IF NOT EXISTS common;

SET search_path = common;

-- --------------------------------------------
-- Tables de reference (nomenclatures)
-- --------------------------------------------

-- 7 etapes fixes de la roue CSI
CREATE TABLE IF NOT EXISTS etapes (
    numero      INTEGER PRIMARY KEY,
    nom         TEXT NOT NULL,
    description TEXT,
    tooltip     TEXT
);

-- 5 statuts d'evaluation par etape (Gris -> Rouge)
CREATE TABLE IF NOT EXISTS statuts_etape (
    id          SERIAL PRIMARY KEY,
    intitule    TEXT UNIQUE NOT NULL,
    couleur     TEXT NOT NULL,
    severite    INTEGER NOT NULL,
    ordre       INTEGER DEFAULT 0
);

-- Etats du cycle de vie d'un indicateur
CREATE TABLE IF NOT EXISTS etats_indicateur (
    id          SERIAL PRIMARY KEY,
    intitule    TEXT UNIQUE NOT NULL,
    couleur     TEXT NOT NULL,
    ordre       INTEGER DEFAULT 0
);

-- Types d'indicateur
CREATE TABLE IF NOT EXISTS types_indicateur (
    id          SERIAL PRIMARY KEY,
    intitule    TEXT UNIQUE NOT NULL,
    couleur     TEXT,
    ordre       INTEGER DEFAULT 0
);

-- --------------------------------------------
-- Utilisateurs (tous clients confondus)
-- --------------------------------------------

CREATE TABLE IF NOT EXISTS utilisateurs (
    id                      SERIAL PRIMARY KEY,
    login                   TEXT UNIQUE NOT NULL,
    nom                     TEXT NOT NULL,
    email                   TEXT,
    trigramme               TEXT,
    hash_mdp                TEXT,
    emails_secondaires      TEXT,
    date_creation           TEXT,
    date_derniere_connexion TEXT,
    date_fin                TEXT
);

-- --------------------------------------------
-- Clients et rattachement utilisateurs
-- --------------------------------------------

CREATE TABLE IF NOT EXISTS clients (
    id              SERIAL PRIMARY KEY,
    nom             TEXT NOT NULL,
    schema_name     TEXT UNIQUE NOT NULL,
    date_creation   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS client_membres (
    id          SERIAL PRIMARY KEY,
    client_id   INTEGER NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('admin', 'membre', 'lecteur', 'information')),
    UNIQUE(client_id, user_id)
);

-- --------------------------------------------
-- Invitations (activation de compte par lien)
-- --------------------------------------------

CREATE TABLE IF NOT EXISTS invitations (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    token       TEXT UNIQUE NOT NULL,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    used_at     TEXT,
    created_by  INTEGER REFERENCES utilisateurs(id)
);
