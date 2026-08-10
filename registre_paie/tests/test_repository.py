"""Tests de db/repository.py — schéma, barème par défaut, exclusions,
enregistrement/relecture d'un mois, remplacement en cas de réimport (§8.3)."""

import db.repository as repo
from core.agregation import agreger
from core.tarification import BAREME_PAR_DEFAUT
from tests.conftest import faire_seance


def _conn():
    return repo.connecter(":memory:")


def test_bareme_initialise_avec_les_valeurs_par_defaut():
    conn = _conn()
    assert repo.lire_bareme(conn) == BAREME_PAR_DEFAUT


def test_definir_tarif_modifie_le_bareme_sans_toucher_le_reste():
    conn = _conn()
    repo.definir_tarif(conn, "Primaire", 1600)
    bareme = repo.lire_bareme(conn)
    assert bareme["Primaire"] == 1600
    assert bareme["Collège"] == BAREME_PAR_DEFAUT["Collège"]


def test_exclusions_vides_par_defaut_puis_modifiables():
    conn = _conn()
    assert repo.lire_exclusions(conn) == set()

    repo.definir_exclusion(conn, "NDONGO NGA MAXIME", True)
    assert repo.lire_exclusions(conn) == {"NDONGO NGA MAXIME"}

    repo.definir_exclusion(conn, "NDONGO NGA MAXIME", False)
    assert repo.lire_exclusions(conn) == set()


def _resultat_exemple():
    seance = faire_seance(
        enseignant="X",
        eleve_nom="DUPONT",
        eleve_prenom="Jean",
        niveau_de_classe="6EME",
        classe="6EME",
        matiere="Mathématiques",
        duree_minutes=60,
    )
    seance_non_resolue = faire_seance(enseignant="X", niveau_de_classe="", classe="", duree_minutes=30)
    return agreger(
        seances=[seance, seance_non_resolue],
        personnes_connues={"X"},
        exclusions=set(),
        versements_15={"X": 500},
        bareme=BAREME_PAR_DEFAUT,
    )


def test_enregistrer_et_charger_un_mois():
    conn = _conn()
    resultat = _resultat_exemple()

    calcul_id = repo.enregistrer_calcul_mensuel(conn, 2026, 7, resultat)
    assert calcul_id is not None

    mois = repo.charger_mois(conn, 2026, 7)
    assert mois is not None
    assert mois.annee == 2026 and mois.mois == 7
    assert mois.nb_seances_non_resolues == 1
    assert mois.nb_intervenants_inconnus == 0
    assert len(mois.resultats) == 1

    r = mois.resultats[0]
    assert r.nom == "X"
    assert r.montant_brut == 2000
    assert r.versement_15 == 500
    assert r.net_a_payer == 1500

    details = repo.charger_details_seances(conn, r.id)
    assert len(details) == 1
    assert details[0]["eleve_nom"] == "DUPONT"
    assert details[0]["montant"] == 2000


def test_charger_mois_absent_renvoie_none():
    conn = _conn()
    assert repo.charger_mois(conn, 2026, 1) is None


def test_reimport_meme_mois_remplace_lancien_calcul():
    conn = _conn()
    repo.enregistrer_calcul_mensuel(conn, 2026, 7, _resultat_exemple())

    seance_differente = faire_seance(
        enseignant="Y", niveau_de_classe="BTS", classe="BTS", matiere="Mathématiques", duree_minutes=120
    )
    nouveau_resultat = agreger(
        seances=[seance_differente],
        personnes_connues={"Y"},
        exclusions=set(),
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
    )
    repo.enregistrer_calcul_mensuel(conn, 2026, 7, nouveau_resultat)

    assert repo.lister_mois(conn) == [(2026, 7, repo.lister_mois(conn)[0][2])]
    mois = repo.charger_mois(conn, 2026, 7)
    assert [r.nom for r in mois.resultats] == ["Y"]
    assert mois.nb_seances_non_resolues == 0


def test_lister_mois_ordre_du_plus_recent_au_plus_ancien():
    conn = _conn()
    resultat = _resultat_exemple()
    repo.enregistrer_calcul_mensuel(conn, 2026, 5, resultat)
    repo.enregistrer_calcul_mensuel(conn, 2026, 7, resultat)
    repo.enregistrer_calcul_mensuel(conn, 2026, 6, resultat)

    mois = [(a, m) for a, m, _ in repo.lister_mois(conn)]
    assert mois == [(2026, 7), (2026, 6), (2026, 5)]


def test_brouillon_absent_par_defaut():
    conn = _conn()
    assert repo.charger_brouillon(conn) is None


def test_brouillon_sauvegarde_puis_relu():
    conn = _conn()
    resultat = _resultat_exemple()

    repo.sauvegarder_brouillon(conn, 2026, 7, resultat)

    brouillon = repo.charger_brouillon(conn)
    assert brouillon is not None
    annee, mois, _date_maj, resultat_relu = brouillon
    assert (annee, mois) == (2026, 7)
    assert resultat_relu.resultats_par_personne["X"].montant_brut == 2000
    assert resultat_relu.seances_non_resolues[0].raison == resultat.seances_non_resolues[0].raison


def test_brouillon_resauvegarde_remplace_le_precedent():
    conn = _conn()
    repo.sauvegarder_brouillon(conn, 2026, 5, _resultat_exemple())
    repo.sauvegarder_brouillon(conn, 2026, 7, _resultat_exemple())

    annee, mois, _date_maj, _resultat = repo.charger_brouillon(conn)
    assert (annee, mois) == (2026, 7)


def test_brouillon_efface():
    conn = _conn()
    repo.sauvegarder_brouillon(conn, 2026, 7, _resultat_exemple())

    repo.effacer_brouillon(conn)

    assert repo.charger_brouillon(conn) is None


def test_mettre_a_jour_versement_15_recalcule_le_net():
    conn = _conn()
    calcul_id = repo.enregistrer_calcul_mensuel(conn, 2026, 7, _resultat_exemple())
    mois = repo.charger_mois(conn, 2026, 7)
    resultat_personne_id = mois.resultats[0].id

    repo.mettre_a_jour_versement_15(conn, resultat_personne_id, 800)

    mois_maj = repo.charger_mois(conn, 2026, 7)
    r = mois_maj.resultats[0]
    assert r.versement_15 == 800
    assert r.net_a_payer == 2000 - 800
