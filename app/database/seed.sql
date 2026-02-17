-- ============================================
-- Roue CSI - Donnees de reference initiales
-- ============================================

-- 7 étapes de la roue CSI
INSERT INTO etapes (numero, nom, description) VALUES
(1, 'Ce qu''on VEUT',     'Définir l''objectif de mesure'),
(2, 'Ce qu''on PEUT',     'Ce qui est techniquement faisable'),
(3, 'COLLECTE',           'Collecte des données'),
(4, 'DATA PREP',          'Préparation des données'),
(5, 'DATA QUALITY',       'Qualité des données'),
(6, 'DATA VIZ & USAGE',   'Visualisation et exploitation'),
(7, 'BILAN',              'Bilan / revue');

-- 5 statuts d'étape (sévérité croissante : 0 = neutre, 4 = critique)
INSERT INTO statuts_etape (intitule, couleur, severite, ordre) VALUES
('Non évalué',  '#9E9E9E', 0, 1),
('Validé',      '#4CAF50', 1, 2),
('En cours',    '#FFEB3B', 2, 3),
('Warning',     '#FF9800', 3, 4),
('Blocage',     '#F44336', 4, 5);

-- États du cycle de vie
INSERT INTO etats_indicateur (intitule, couleur, ordre) VALUES
('Cadré',       '#6c757d', 1),
('En attente',  '#ffc107', 2),
('Réalisé',     '#28a745', 3),
('Annulé',      '#dc3545', 4),
('En cours',    '#17a2b8', 5),
('À cadrer',    '#adb5bd', 6);

-- Types d'indicateur
INSERT INTO types_indicateur (intitule, couleur, ordre) VALUES
('SLA', '#0d6efd', 1),
('KPI', '#6f42c1', 2),
('XLA', '#d63384', 3);
