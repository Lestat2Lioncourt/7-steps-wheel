-- ============================================
-- Roue CSI - Donnees de demonstration
-- ============================================
-- 7 categories, 14 indicateurs, 98 lignes indicateur_etapes
-- statut_*_id : 1=Non evalue, 2=Valide, 3=En cours, 4=Warning, 5=Blocage

-- Categories
INSERT INTO categories (id, nom, ordre) VALUES
(1, 'SLA Transverse',      1),
(2, 'Service Desk',        2),
(3, 'Process Incident',    3),
(4, 'Process Demande',     4),
(5, 'Gestion des stocks',  5),
(6, 'Marche de location',  6),
(7, 'Pilotage',            7);

-- Indicateurs (14)
-- etat_id : 1=Cadre, 2=En attente, 3=Realise, 4=Annule, 5=En cours, 6=A cadrer
-- type_id : 1=SLA, 2=KPI, 3=XLA
INSERT INTO indicateurs (id, code, description, chapitre, categorie_id, etat_id, type_id, ciblage, conformite) VALUES
( 1, 'ITR_QUAL_REF_TECH',   'Qualite gestion referentiels techniques',           '4.1.3',   1, 5, 1, 'Liste des donnees des referentiels techniques',       'Nombre d''erreurs <= 5'),
( 2, 'ITR_REP_PROJET_TSD',  'Reporting projet et TSD',                           '4.1.4',   1, 6, 1, 'Rapports mensuels de pilotage',                       'Livraison avant le 5 du mois'),
( 3, 'ISD_APPEL_DECROCHE',  'Taux appels decroches',                             '4.3.1',   2, 3, 1, 'Appels entrants sur la plage horaire',                'Taux decroche >= 95%'),
( 4, 'ISD_QUAL_TICKET',     'Qualite de saisie des tickets',                     '4.3.2',   2, 5, 2, 'Tickets crees par le Service Desk',                   'Taux de conformite saisie >= 90%'),
( 5, 'IQ_INC_1',            'Resolution incident Bloque',                        '4.2.1',   3, 3, 1, 'Tous les incidents de priorite Bloquant',             'Delai de resolution <= 4h ouvrees'),
( 6, 'IQ_INC_1A',           'Resolution Bloque (4h)',                            '4.2.1.1', 3, 3, 1, 'Incidents P1 hors maintenance programmee',             '95% resolus en moins de 4h'),
( 7, 'IQ_INC_2',            'Resolution incident Gene',                          '4.2.2',   3, 3, 1, 'Tous les incidents de priorite Gene',                 'Delai de resolution <= 12h ouvrees'),
( 8, 'IQ_INC_NON_RES',      'Non-resolution des tickets',                        '4.2.5',   3, 5, 2, 'Tickets ouverts depuis plus de 30 jours',             'Taux de non-resolution < 5%'),
( 9, 'IQ_INC_ESCAL',        'Delais et qualite de l''escalade',                  '4.2.6',   3, 5, 1, 'Escalades techniques et hierarchiques',               '100% des escalades notifiees sous 1h'),
(10, 'IQ_INC_PROP',         'Propositions amelioration',                         '4.2.7',   3, 6, 2, 'Propositions emises par les equipes',                 'Au moins 2 propositions par trimestre'),
(11, 'IQ_REQ_TRAITEMENT',   'Delai traitement des demandes',                     '4.4.1',   4, 5, 1, 'Demandes standard catalogue',                         '80% traitees en 5 jours'),
(12, 'IQ_PARC_STOCK',       'Gestion du stock',                                  '4.5.1',   5, 3, 2, 'Materiel en stock actif',                             'Ecart inventaire < 2%'),
(13, 'IQ_LOC_RESTIT',       'Restitution materiel location',                     '4.6.1',   6, 6, 2, 'Materiel en fin de contrat de location',              '100% restitue sous 30 jours'),
(14, 'IP_TENUE_COMITE',     'Tenue des comites de pilotage',                     '4.7.1',   7, 5, 2, 'Comites mensuels et trimestriels',                    '100% des comites tenus');

-- ============================================
-- indicateur_etapes : 14 indicateurs x 7 etapes = 98 lignes
--
-- La couche "global" est utilisee uniquement sur ITR_QUAL_REF_TECH
-- pour illustrer le systeme 3 couches dans la vue indicateur.
-- Les autres indicateurs n'ont que des statuts indicateur/categorie.
-- ============================================

-- Indicateur 1: ITR_QUAL_REF_TECH (worst=orange, cat=SLA Transverse)
-- Seul indicateur avec les 3 couches remplies (demo du systeme)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(1, 1, NULL, NULL, NULL, NULL, 2, NULL),
(1, 2, NULL, NULL, NULL, NULL, 4, 'Pas d''appareil de mesure dedie. Calcul manuel.'),
(1, 3, 5, 'Blocage acces BDD pour tous les indicateurs', NULL, NULL, 4, 'Mesures dans fichiers Excel. Referentiels a fournir.'),
(1, 4, NULL, NULL, 3, 'Outils de preparation en cours de deploiement', NULL, NULL),
(1, 5, NULL, NULL, NULL, NULL, 1, NULL),
(1, 6, NULL, NULL, NULL, NULL, 3, NULL),
(1, 7, NULL, NULL, 4, 'Chantier patrimoine documentaire en cours', 4, 'Voir dates avec equipe. Planification a affiner.');

-- Indicateur 2: ITR_REP_PROJET_TSD (worst=yellow)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(2, 1, NULL, NULL, NULL, NULL, 3, 'Objectifs en cours de definition'),
(2, 2, NULL, NULL, NULL, NULL, 3, NULL),
(2, 3, NULL, NULL, NULL, NULL, 3, 'Sources de donnees a identifier'),
(2, 4, NULL, NULL, 3, 'Outils de preparation en cours de deploiement', NULL, NULL),
(2, 5, NULL, NULL, NULL, NULL, 1, NULL),
(2, 6, NULL, NULL, NULL, NULL, 1, NULL),
(2, 7, NULL, NULL, 4, 'Chantier patrimoine documentaire en cours', NULL, NULL);

-- Indicateur 3: ISD_APPEL_DECROCHE (worst=orange)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(3, 1, NULL, NULL, NULL, NULL, 2, NULL),
(3, 2, NULL, NULL, NULL, NULL, 2, NULL),
(3, 3, NULL, NULL, NULL, NULL, 2, 'Extraction via outil telephonie OK'),
(3, 4, NULL, NULL, NULL, NULL, 2, NULL),
(3, 5, NULL, NULL, NULL, NULL, 4, 'Temps plancher en attente de validation'),
(3, 6, NULL, NULL, NULL, NULL, 2, NULL),
(3, 7, NULL, NULL, NULL, NULL, 2, NULL);

-- Indicateur 4: ISD_QUAL_TICKET (worst=orange)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(4, 1, NULL, NULL, NULL, NULL, 2, NULL),
(4, 2, NULL, NULL, NULL, NULL, 3, 'Criteres de saisie a preciser'),
(4, 3, NULL, NULL, NULL, NULL, 3, NULL),
(4, 4, NULL, NULL, NULL, NULL, 3, NULL),
(4, 5, NULL, NULL, NULL, NULL, 4, 'Champs obligatoires non remplis regulierement'),
(4, 6, NULL, NULL, NULL, NULL, 1, NULL),
(4, 7, NULL, NULL, NULL, NULL, 1, NULL);

-- Indicateur 5: IQ_INC_1 (worst=green)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(5, 1, NULL, NULL, NULL, NULL, 2, NULL),
(5, 2, NULL, NULL, NULL, NULL, 2, NULL),
(5, 3, NULL, NULL, NULL, NULL, 2, 'Extraction ITSM fonctionnelle'),
(5, 4, NULL, NULL, NULL, NULL, 2, NULL),
(5, 5, NULL, NULL, NULL, NULL, 2, NULL),
(5, 6, NULL, NULL, NULL, NULL, 2, NULL),
(5, 7, NULL, NULL, NULL, NULL, 2, NULL);

-- Indicateur 6: IQ_INC_1A (worst=green)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(6, 1, NULL, NULL, NULL, NULL, 2, NULL),
(6, 2, NULL, NULL, NULL, NULL, 2, NULL),
(6, 3, NULL, NULL, NULL, NULL, 2, 'Meme source que IQ_INC_1'),
(6, 4, NULL, NULL, NULL, NULL, 2, NULL),
(6, 5, NULL, NULL, NULL, NULL, 2, NULL),
(6, 6, NULL, NULL, NULL, NULL, 2, NULL),
(6, 7, NULL, NULL, NULL, NULL, 2, NULL);

-- Indicateur 7: IQ_INC_2 (worst=green)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(7, 1, NULL, NULL, NULL, NULL, 2, NULL),
(7, 2, NULL, NULL, NULL, NULL, 2, NULL),
(7, 3, NULL, NULL, NULL, NULL, 2, NULL),
(7, 4, NULL, NULL, NULL, NULL, 2, NULL),
(7, 5, NULL, NULL, NULL, NULL, 2, NULL),
(7, 6, NULL, NULL, NULL, NULL, 2, NULL),
(7, 7, NULL, NULL, NULL, NULL, 2, NULL);

-- Indicateur 8: IQ_INC_NON_RES (worst=red)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(8, 1, NULL, NULL, NULL, NULL, 3, 'Criteres de non-resolution a definir'),
(8, 2, NULL, NULL, NULL, NULL, 4, 'Requete complexe a valider'),
(8, 3, NULL, NULL, NULL, NULL, 5, 'Aucune source identifiee'),
(8, 4, NULL, NULL, NULL, NULL, 1, NULL),
(8, 5, NULL, NULL, NULL, NULL, 1, NULL),
(8, 6, NULL, NULL, NULL, NULL, 1, NULL),
(8, 7, NULL, NULL, NULL, NULL, 1, NULL);

-- Indicateur 9: IQ_INC_ESCAL (worst=orange)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(9, 1, NULL, NULL, NULL, NULL, 2, NULL),
(9, 2, NULL, NULL, NULL, NULL, 3, 'Niveaux escalade a formaliser'),
(9, 3, NULL, NULL, NULL, NULL, 4, 'Consolidation requise'),
(9, 4, NULL, NULL, NULL, NULL, 3, NULL),
(9, 5, NULL, NULL, NULL, NULL, 1, NULL),
(9, 6, NULL, NULL, NULL, NULL, 1, NULL),
(9, 7, NULL, NULL, NULL, NULL, 1, NULL);

-- Indicateur 10: IQ_INC_PROP (worst=grey)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(10, 1, NULL, NULL, NULL, NULL, 1, NULL),
(10, 2, NULL, NULL, NULL, NULL, 1, NULL),
(10, 3, NULL, NULL, NULL, NULL, 1, NULL),
(10, 4, NULL, NULL, NULL, NULL, 1, NULL),
(10, 5, NULL, NULL, NULL, NULL, 1, NULL),
(10, 6, NULL, NULL, NULL, NULL, 1, NULL),
(10, 7, NULL, NULL, NULL, NULL, 1, NULL);

-- Indicateur 11: IQ_REQ_TRAITEMENT (worst=yellow)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(11, 1, NULL, NULL, NULL, NULL, 2, NULL),
(11, 2, NULL, NULL, NULL, NULL, 3, 'Sources multiples a consolider'),
(11, 3, NULL, NULL, NULL, NULL, 3, 'Requetes en cours de dev'),
(11, 4, NULL, NULL, NULL, NULL, 3, NULL),
(11, 5, NULL, NULL, NULL, NULL, 1, NULL),
(11, 6, NULL, NULL, NULL, NULL, 1, NULL),
(11, 7, NULL, NULL, NULL, NULL, 1, NULL);

-- Indicateur 12: IQ_PARC_STOCK (worst=green)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(12, 1, NULL, NULL, NULL, NULL, 2, NULL),
(12, 2, NULL, NULL, NULL, NULL, 2, NULL),
(12, 3, NULL, NULL, NULL, NULL, 2, 'Inventaire SCCM disponible'),
(12, 4, NULL, NULL, NULL, NULL, 2, NULL),
(12, 5, NULL, NULL, NULL, NULL, 2, NULL),
(12, 6, NULL, NULL, NULL, NULL, 2, NULL),
(12, 7, NULL, NULL, NULL, NULL, 2, NULL);

-- Indicateur 13: IQ_LOC_RESTIT (worst=grey)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(13, 1, NULL, NULL, NULL, NULL, 1, NULL),
(13, 2, NULL, NULL, NULL, NULL, 1, NULL),
(13, 3, NULL, NULL, NULL, NULL, 1, NULL),
(13, 4, NULL, NULL, NULL, NULL, 1, NULL),
(13, 5, NULL, NULL, NULL, NULL, 1, NULL),
(13, 6, NULL, NULL, NULL, NULL, 1, NULL),
(13, 7, NULL, NULL, NULL, NULL, 1, NULL);

-- Indicateur 14: IP_TENUE_COMITE (worst=yellow)
INSERT INTO indicateur_etapes (indicateur_id, etape, statut_global_id, commentaire_global, statut_categorie_id, commentaire_categorie, statut_indicateur_id, commentaire_indicateur) VALUES
(14, 1, NULL, NULL, NULL, NULL, 2, NULL),
(14, 2, NULL, NULL, NULL, NULL, 2, NULL),
(14, 3, NULL, NULL, NULL, NULL, 2, NULL),
(14, 4, NULL, NULL, NULL, NULL, 3, NULL),
(14, 5, NULL, NULL, NULL, NULL, 3, NULL),
(14, 6, NULL, NULL, NULL, NULL, 3, 'Solution Excel en cours de deploiement'),
(14, 7, NULL, NULL, NULL, NULL, 1, NULL);

-- ============================================
-- Utilisateurs demo
-- ============================================
INSERT INTO utilisateurs (login, nom, email, trigramme, role) VALUES
('admin', 'Administrateur', NULL, 'ADM', 'admin'),
('amin', 'KOUYATE, Amin', 'amin.kouyate@example.com', 'AKO', 'membre'),
('pascal.g', 'GARNIER, Pascal', 'pascal.garnier@example.com', 'PGA', 'membre'),
('gisele', 'MARTIN, Gisele', 'gisele.martin@example.com', 'GMA', 'membre'),
('p.dupont', 'DUPONT, Pierre', 'p.dupont@example.com', 'PDU', 'membre');

-- ============================================
-- Actions demo (liees a ITR_QUAL_REF_TECH id=1, cat SLA Transverse id=1)
-- ============================================
INSERT INTO actions (titre, description, niveau, indicateur_id, categorie_id, etape, assignee_login, statut, commentaire, cree_par, date_creation) VALUES
('Obtenir la liste exhaustive des referentiels', NULL, 'indicateur', 1, NULL, 3, 'amin', 'a_faire', NULL, 'admin', '2026-01-05'),
('Definir le format de remontee', NULL, 'indicateur', 1, NULL, 4, 'pascal.g', 'a_faire', NULL, 'admin', '2026-01-05'),
('Controle qualite des donnees', NULL, 'indicateur', 1, NULL, 5, 'amin', 'a_faire', NULL, 'admin', '2026-01-06'),
('Obtenir les acces a la BDD supervision', NULL, 'categorie', NULL, 1, 2, 'p.dupont', 'a_faire', NULL, 'admin', '2026-01-05'),
('Cadrage patrimoine documentaire', NULL, 'indicateur', 1, NULL, 2, 'gisele', 'en_cours', NULL, 'admin', '2026-01-03'),
('Mise a jour referentiels contrat', NULL, 'categorie', NULL, 1, 1, 'pascal.g', 'en_cours', NULL, 'admin', '2026-01-02'),
('Identifier les sources de donnees', NULL, 'indicateur', 1, NULL, 2, 'p.dupont', 'a_valider', NULL, 'admin', '2026-01-01'),
('Definir criteres de conformite', NULL, 'indicateur', 1, NULL, 1, 'p.dupont', 'termine', NULL, 'admin', '2025-12-15'),
('Export automatise SCCM', NULL, 'indicateur', 1, NULL, 3, 'amin', 'rejete', 'Hors perimetre actuel', 'admin', '2025-12-10');

-- Actions globales (visibles depuis tous les indicateurs)
INSERT INTO actions (titre, description, niveau, indicateur_id, categorie_id, etape, assignee_login, statut, commentaire, cree_par, date_creation) VALUES
('Obtenir acces BDD central', 'Blocage acces base de donnees pour tous les indicateurs', 'global', NULL, NULL, 3, 'p.dupont', 'en_cours', NULL, 'admin', '2026-01-04'),
('Valider la gouvernance des donnees', NULL, 'global', NULL, NULL, 1, 'gisele', 'a_faire', NULL, 'admin', '2026-01-07');
