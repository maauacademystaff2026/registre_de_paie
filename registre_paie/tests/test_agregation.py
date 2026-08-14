"""Tests unitaires d'agrégation (§4, §6, §7 A/B/D/E)."""

from core.agregation import agreger
from core.tarification import BAREME_PAR_DEFAUT
from tests.conftest import faire_seance


def test_absence_de_l_eleve_est_payee_en_entier():
    # §4 (corrigé) : le professeur s'est présenté, l'absence de l'élève ne lui
    # est pas imputable -> payé comme Présentiel/Dispensé/Retard.
    seance = faire_seance(
        enseignant="X",
        etat_eleve="Absent",
        niveau_de_classe="6EME",
        classe="6EME",
        matiere="Mathématiques",
        duree_minutes=120,
    )

    resultat = agreger(
        seances=[seance],
        personnes_connues={"X"},
        exclusions=set(),
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
    )

    r = resultat.resultats_par_personne["X"]
    assert r.heures_payees_minutes == 120
    assert r.montant_brut == 4000  # 2h x 2000 F/h (Collège)


def test_absence_du_professeur_nest_jamais_payable():
    # §4 (corrigé) : seule séance non payable -- le professeur lui-même absent.
    seance = faire_seance(enseignant="X", etat_eleve="Absence du prof", duree_minutes=120)

    resultat = agreger(
        seances=[seance],
        personnes_connues={"X"},
        exclusions=set(),
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
    )

    assert resultat.resultats_par_personne == {}
    assert resultat.seances_non_resolues == []
    assert resultat.intervenants_inconnus == []


def test_retard_paye_en_entier_sur_la_duree_totale():
    # §4/§7-D : 'Retard - 00:10' -> les 120 minutes de Durée (H) sont payées
    # en entier, le retard de l'élève n'est jamais déduit.
    seance = faire_seance(
        enseignant="X",
        etat_eleve="Retard - 00:10",
        niveau_de_classe="CE1",
        classe="CE1",
        matiere="Mathématiques",
        duree_minutes=120,
    )

    resultat = agreger(
        seances=[seance],
        personnes_connues={"X"},
        exclusions=set(),
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
    )

    r = resultat.resultats_par_personne["X"]
    assert r.heures_payees_minutes == 120
    assert r.montant_brut == 3000  # 2h x 1500 F/h (Primaire)


def test_intervenant_absent_de_lannuaire_est_signale_non_paye():
    seance = faire_seance(enseignant="KAMDEM RICH BILL", etat_eleve="Dispensé", duree_minutes=480)

    resultat = agreger(
        seances=[seance],
        personnes_connues=set(),  # absent de l'annuaire, §7-B
        exclusions=set(),
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
    )

    assert resultat.resultats_par_personne == {}
    assert len(resultat.intervenants_inconnus) == 1
    assert resultat.intervenants_inconnus[0].nom == "KAMDEM RICH BILL"


def test_personne_exclue_nest_pas_payee_mais_reste_tracee():
    # §7-A : case à cocher Exclu -> montant à 0, mais heures/détail conservés
    # pour la traçabilité (zone "à vérifier").
    seance = faire_seance(enseignant="NDONGO NGA MAXIME", etat_eleve="Dispensé", duree_minutes=60)

    resultat = agreger(
        seances=[seance],
        personnes_connues={"NDONGO NGA MAXIME"},
        exclusions={"NDONGO NGA MAXIME"},
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
    )

    r = resultat.resultats_par_personne["NDONGO NGA MAXIME"]
    assert r.exclu is True
    assert r.montant_brut == 0
    assert r.heures_payees_minutes == 60  # séance toujours visible dans le détail
    assert len(r.details) == 1


def test_arrondi_applique_sur_le_total_personne_pas_par_seance():
    # Deux séances de 5 min à 2000 F/h (Collège) : montant exact par séance
    # 166.666..., total exact 333.333... -> round(total) = 333.
    # Un arrondi séance par séance donnerait 167 + 167 = 334 (§7-E).
    seances = [
        faire_seance(enseignant="X", niveau_de_classe="6EME", classe="6EME", matiere="Mathématiques", duree_minutes=5),
        faire_seance(enseignant="X", niveau_de_classe="6EME", classe="6EME", matiere="Mathématiques", duree_minutes=5),
    ]

    resultat = agreger(
        seances=seances,
        personnes_connues={"X"},
        exclusions=set(),
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
    )

    assert resultat.resultats_par_personne["X"].montant_brut == 333


def test_versement_du_15_deduit_du_brut_arrondi():
    seance = faire_seance(enseignant="X", niveau_de_classe="6EME", classe="6EME", matiere="Mathématiques", duree_minutes=60)

    resultat = agreger(
        seances=[seance],
        personnes_connues={"X"},
        exclusions=set(),
        versements_15={"X": 500},
        bareme=BAREME_PAR_DEFAUT,
    )

    r = resultat.resultats_par_personne["X"]
    assert r.montant_brut == 2000
    assert r.net_a_payer == 1500


def test_agreger_applique_les_exceptions_enseignant_et_eleve():
    # §7-C, §10 : agreger() doit transmettre les deux dicts d'exceptions
    # jusqu'à core/tarification.py, séance par séance.
    seance_exception_enseignant = faire_seance(
        enseignant="MOLO ALINE", eleve_nom="A", matiere="Mathématiques",
        niveau_de_classe="CE1", classe="CE1", duree_minutes=60,
    )
    seance_exception_eleve = faire_seance(
        enseignant="MOLO ALINE", eleve_nom="HUGO", eleve_prenom="X", matiere="Mathématiques",
        niveau_de_classe="6EME", classe="6EME", duree_minutes=60,
    )

    resultat = agreger(
        seances=[seance_exception_enseignant, seance_exception_eleve],
        personnes_connues={"MOLO ALINE"},
        exclusions=set(),
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
        exceptions_enseignant={("MOLO ALINE", "Primaire"): 1600},
        exceptions_eleve={("HUGO", "X"): 5000},
    )

    r = resultat.resultats_par_personne["MOLO ALINE"]
    montants = {d.montant for d in r.details}
    assert montants == {1600, 5000}
    assert r.montant_brut == 1600 + 5000


def test_seance_non_resolue_exclue_du_calcul_automatique():
    seance_ok = faire_seance(enseignant="X", niveau_de_classe="6EME", classe="6EME", matiere="Mathématiques", duree_minutes=60)
    seance_non_resolue = faire_seance(enseignant="X", niveau_de_classe="", classe="", matiere="Mathématiques", duree_minutes=60)

    resultat = agreger(
        seances=[seance_ok, seance_non_resolue],
        personnes_connues={"X"},
        exclusions=set(),
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
    )

    assert len(resultat.seances_non_resolues) == 1
    r = resultat.resultats_par_personne["X"]
    assert len(r.details) == 1
    assert r.montant_brut == 2000  # seule la séance résolue est payée
