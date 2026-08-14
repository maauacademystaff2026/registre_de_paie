-- Schéma SQLite du registre de paie (§8.3, §11).
-- Un seul fichier local (registre_paie.db), sauvegardable comme un document normal.

PRAGMA foreign_keys = ON;

-- §5 : les 5 tarifs du barème, modifiables dans l'application, jamais codés en dur.
CREATE TABLE IF NOT EXISTS parametres_bareme (
    categorie TEXT PRIMARY KEY,
    tarif_horaire REAL NOT NULL
);

-- §7-A : case "Exclu" par personne (remplace la liste figée d'exclusions).
-- Ce statut est un réglage courant ; sa valeur au moment de chaque calcul est
-- figée séparément dans resultats_personne.exclu pour ne jamais réécrire un
-- mois déjà validé si le statut change ensuite.
CREATE TABLE IF NOT EXISTS personnes (
    nom TEXT PRIMARY KEY,
    exclu INTEGER NOT NULL DEFAULT 0 CHECK (exclu IN (0, 1))
);

-- §8.3 : un calcul mensuel validé par (année, mois). Un ré-import du même
-- mois remplace l'enregistrement précédent (ON DELETE CASCADE ci-dessous).
CREATE TABLE IF NOT EXISTS calculs_mensuels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    annee INTEGER NOT NULL,
    mois INTEGER NOT NULL CHECK (mois BETWEEN 1 AND 12),
    date_calcul TEXT NOT NULL,
    UNIQUE (annee, mois)
);

CREATE TABLE IF NOT EXISTS resultats_personne (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calcul_id INTEGER NOT NULL REFERENCES calculs_mensuels (id) ON DELETE CASCADE,
    nom TEXT NOT NULL,
    exclu INTEGER NOT NULL CHECK (exclu IN (0, 1)),
    heures_payees_minutes INTEGER NOT NULL,
    montant_brut INTEGER NOT NULL,
    versement_15 REAL NOT NULL DEFAULT 0,
    net_a_payer REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resultats_personne_calcul ON resultats_personne (calcul_id);

-- §8.2 : détail par séance, pour audit ("tracé ligne par ligne en cas de doute").
CREATE TABLE IF NOT EXISTS details_seances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resultat_personne_id INTEGER NOT NULL REFERENCES resultats_personne (id) ON DELETE CASCADE,
    eleve_nom TEXT NOT NULL,
    eleve_prenom TEXT NOT NULL,
    date TEXT NOT NULL,
    classe TEXT NOT NULL,
    niveau_resolu TEXT,
    matiere TEXT NOT NULL,
    duree_minutes INTEGER NOT NULL,
    categorie_tarif TEXT NOT NULL,
    source_tarif TEXT NOT NULL,
    tarif_horaire REAL NOT NULL,
    montant REAL NOT NULL,
    tarif_exceptionnel INTEGER NOT NULL DEFAULT 0 CHECK (tarif_exceptionnel IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_details_seances_resultat ON details_seances (resultat_personne_id);

-- §8.2 : zone "à vérifier" — séances à niveau non résolu (§5).
CREATE TABLE IF NOT EXISTS seances_non_resolues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calcul_id INTEGER NOT NULL REFERENCES calculs_mensuels (id) ON DELETE CASCADE,
    enseignant TEXT NOT NULL,
    eleve_nom TEXT NOT NULL,
    eleve_prenom TEXT NOT NULL,
    date TEXT NOT NULL,
    classe TEXT NOT NULL,
    niveau_de_classe TEXT NOT NULL,
    matiere TEXT NOT NULL,
    duree_minutes INTEGER NOT NULL,
    raison TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_non_resolues_calcul ON seances_non_resolues (calcul_id);

-- §8.2 : zone "à vérifier" — intervenants absents de l'annuaire (§7-B).
CREATE TABLE IF NOT EXISTS intervenants_inconnus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calcul_id INTEGER NOT NULL REFERENCES calculs_mensuels (id) ON DELETE CASCADE,
    nom TEXT NOT NULL,
    heures_minutes INTEGER NOT NULL,
    nb_seances INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inconnus_calcul ON intervenants_inconnus (calcul_id);

-- Calcul en cours, pas encore "Enregistré" dans l'historique (§ correctif
-- rafraîchissement navigateur) : une seule ligne (id=1), remplacée à chaque
-- calcul/édition, effacée après un "Enregistrer" réussi. N'est pas une
-- donnée d'audit — juste un filet de sécurité pour ne pas perdre une saisie
-- en cours si la page est rechargée (ce qui vide st.session_state).
CREATE TABLE IF NOT EXISTS brouillon_calcul (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    annee INTEGER NOT NULL,
    mois INTEGER NOT NULL,
    donnees BLOB NOT NULL,
    date_maj TEXT NOT NULL
);

-- V2 (PRD §7-C, §10) : tarif personnalisé par (enseignant, catégorie), remplace le tarif du
-- barème global pour cette catégorie uniquement quand cet enseignant l'enseigne.
CREATE TABLE IF NOT EXISTS exceptions_enseignant (
    enseignant TEXT NOT NULL,
    categorie TEXT NOT NULL,
    tarif_horaire REAL NOT NULL,
    PRIMARY KEY (enseignant, categorie)
);

-- V2 (PRD §10) : tarif forcé pour un élève nommé, indépendant de la matière et du niveau.
-- Priorité sur exceptions_enseignant (règle confirmée : le tarif élève l'emporte).
CREATE TABLE IF NOT EXISTS exceptions_eleve (
    eleve_nom TEXT NOT NULL,
    eleve_prenom TEXT NOT NULL,
    tarif_horaire REAL NOT NULL,
    PRIMARY KEY (eleve_nom, eleve_prenom)
);
