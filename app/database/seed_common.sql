-- ============================================
-- Roue CSI - Donnees de reference (common)
-- ============================================

SET search_path = common;

-- 7 etapes de la roue CSI
INSERT INTO etapes (numero, nom, description) VALUES
(1, 'Ce qu''on VEUT',     'Definir l''objectif de mesure'),
(2, 'Ce qu''on PEUT',     'Ce qui est techniquement faisable'),
(3, 'COLLECTE',           'Collecte des donnees'),
(4, 'DATA PREP',          'Preparation des donnees'),
(5, 'DATA QUALITY',       'Qualite des donnees'),
(6, 'DATA VIZ & USAGE',   'Visualisation et exploitation'),
(7, 'BILAN',              'Bilan / revue')
ON CONFLICT DO NOTHING;

-- 5 statuts d'etape (severite croissante : 0 = neutre, 4 = critique)
INSERT INTO statuts_etape (intitule, couleur, severite, ordre) VALUES
('Non evalue',  '#9E9E9E', 0, 1),
('Valide',      '#4CAF50', 1, 2),
('En cours',    '#FFEB3B', 2, 3),
('Warning',     '#FF9800', 3, 4),
('Blocage',     '#F44336', 4, 5)
ON CONFLICT DO NOTHING;

-- Etats du cycle de vie
INSERT INTO etats_indicateur (intitule, couleur, ordre) VALUES
('Cadre',       '#6c757d', 1),
('En attente',  '#ffc107', 2),
('Realise',     '#28a745', 3),
('Annule',      '#dc3545', 4),
('En cours',    '#17a2b8', 5),
('A cadrer',    '#adb5bd', 6)
ON CONFLICT DO NOTHING;

-- Types d'indicateur
INSERT INTO types_indicateur (intitule, couleur, ordre) VALUES
('SLA', '#0d6efd', 1),
('KPI', '#6f42c1', 2),
('XLA', '#d63384', 3)
ON CONFLICT DO NOTHING;
