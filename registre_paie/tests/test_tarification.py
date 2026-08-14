"""Tests unitaires de tarification (§5) — décisions confirmées A-E.

Ces cas ne reproduisent pas encore les chiffres du §9 (qui nécessitent les
vrais fichiers Excel, non fournis à ce stade) : ils vérifient chaque règle du
barème isolément avec des séances synthétiques et des montants calculés à la main.
"""

import pytest

from core.models import ResultatSeance, SeanceNonResolue
from core.tarification import BAREME_PAR_DEFAUT, calculer_resultat_seance, est_langue_seule
from tests.conftest import faire_seance


def test_langue_seule_prioritaire_sur_le_niveau():
    # ANGLAIS en primaire (CE1, 1500 F/h) doit quand même être payé au tarif
    # langue (2000 F/h), pas au tarif primaire — §5, règle 1.
    seance = faire_seance(matiere="ANGLAIS", niveau_de_classe="CE1", classe="CE1", duree_minutes=60)

    resultat = calculer_resultat_seance(seance, BAREME_PAR_DEFAUT)

    assert isinstance(resultat, ResultatSeance)
    assert resultat.source_tarif == "langue"
    assert resultat.categorie_tarif == "Langue seule"
    assert resultat.tarif_horaire == 2000
    assert resultat.montant == 2000


def test_matiere_combinee_nest_pas_langue_seule():
    # 'Maths/Français' n'est pas une langue seule -> tarif du niveau.
    assert est_langue_seule("Maths/Français") is False
    seance = faire_seance(matiere="Maths/Français", niveau_de_classe="CE1", classe="CE1", duree_minutes=60)

    resultat = calculer_resultat_seance(seance, BAREME_PAR_DEFAUT)

    assert isinstance(resultat, ResultatSeance)
    assert resultat.source_tarif == "niveau"
    assert resultat.categorie_tarif == "Primaire"
    assert resultat.tarif_horaire == 1500


@pytest.mark.parametrize("matiere", ["ANGLAIS", "Français", "Espagnole", "anglais", "français"])
def test_langues_seules_reconnues_insensible_a_la_casse(matiere):
    assert est_langue_seule(matiere) is True


@pytest.mark.parametrize(
    "niveau_de_classe,categorie,tarif",
    [
        ("CP", "Primaire", 1500),
        ("CE1", "Primaire", 1500),
        ("CM2", "Primaire", 1500),
        ("6EME", "Collège", 2000),
        ("3EME", "Collège", 2000),
        ("2NDE", "Lycée", 2500),
        ("TLE", "Lycée", 2500),
        ("BTS", "BTS", 3000),
    ],
)
def test_bareme_par_niveau(niveau_de_classe, categorie, tarif):
    seance = faire_seance(
        matiere="Mathématiques",
        niveau_de_classe=niveau_de_classe,
        classe=niveau_de_classe,
        duree_minutes=60,
    )

    resultat = calculer_resultat_seance(seance, BAREME_PAR_DEFAUT)

    assert isinstance(resultat, ResultatSeance)
    assert resultat.categorie_tarif == categorie
    assert resultat.tarif_horaire == tarif


def test_resolution_niveau_via_classe_si_niveau_de_classe_non_exploitable():
    # 'Tous les niveaux' -> repli sur Classe ; '1ERE STL' contient le code '1ERE' -> Lycée.
    seance = faire_seance(
        matiere="Mathématiques",
        niveau_de_classe="Tous les niveaux",
        classe="1ERE STL",
        duree_minutes=60,
    )

    resultat = calculer_resultat_seance(seance, BAREME_PAR_DEFAUT)

    assert isinstance(resultat, ResultatSeance)
    assert resultat.niveau_resolu == "1ERE"
    assert resultat.categorie_tarif == "Lycée"
    assert resultat.tarif_horaire == 2500


def test_niveau_non_resolu_est_signale_pas_tarif_zero():
    # Ni Niveau de classe ni Classe n'indiquent un niveau connu -> jamais 0 silencieux (§5).
    seance = faire_seance(matiere="Mathématiques", niveau_de_classe="", classe="", duree_minutes=60)

    resultat = calculer_resultat_seance(seance, BAREME_PAR_DEFAUT)

    assert isinstance(resultat, SeanceNonResolue)
    assert resultat.seance is seance


def test_montant_proportionnel_a_la_duree():
    # 1h30 à 2000 F/h (Collège) = 3000 F.
    seance = faire_seance(matiere="Mathématiques", niveau_de_classe="6EME", classe="6EME", duree_minutes=90)

    resultat = calculer_resultat_seance(seance, BAREME_PAR_DEFAUT)

    assert isinstance(resultat, ResultatSeance)
    assert resultat.montant == 3000


def test_bareme_est_un_parametre_pas_code_en_dur():
    # Un barème custom passé en argument doit être respecté, preuve que rien
    # n'est codé en dur dans la fonction de calcul (§5, §11).
    bareme_custom = {**BAREME_PAR_DEFAUT, "Collège": 9999}
    seance = faire_seance(matiere="Mathématiques", niveau_de_classe="6EME", classe="6EME", duree_minutes=60)

    resultat = calculer_resultat_seance(seance, bareme_custom)

    assert isinstance(resultat, ResultatSeance)
    assert resultat.tarif_horaire == 9999


# --- Exceptions V2 (§7-C, §10) ------------------------------------------------


def test_exception_enseignant_remplace_le_tarif_de_sa_categorie():
    # Molo Aline : 1600 F/h en Primaire au lieu des 1500 F/h du barème (§7-C).
    seance = faire_seance(
        enseignant="MOLO ALINE", matiere="Mathématiques", niveau_de_classe="CE1", classe="CE1", duree_minutes=60
    )

    resultat = calculer_resultat_seance(
        seance, BAREME_PAR_DEFAUT, exceptions_enseignant={("MOLO ALINE", "Primaire"): 1600}
    )

    assert isinstance(resultat, ResultatSeance)
    assert resultat.tarif_horaire == 1600
    assert resultat.tarif_exceptionnel is True
    assert resultat.source_tarif == "niveau"  # la catégorie reste déterminée par le niveau


def test_exception_enseignant_ne_sapplique_qua_sa_propre_categorie():
    # L'exception de Molo Aline est scopée à Primaire : une séance Collège
    # pour la même enseignante reste au tarif standard.
    seance = faire_seance(
        enseignant="MOLO ALINE", matiere="Mathématiques", niveau_de_classe="6EME", classe="6EME", duree_minutes=60
    )

    resultat = calculer_resultat_seance(
        seance, BAREME_PAR_DEFAUT, exceptions_enseignant={("MOLO ALINE", "Primaire"): 1600}
    )

    assert isinstance(resultat, ResultatSeance)
    assert resultat.tarif_horaire == BAREME_PAR_DEFAUT["Collège"]
    assert resultat.tarif_exceptionnel is False


def test_exception_eleve_force_le_tarif_quel_que_soit_matiere_et_niveau():
    # §10 : un tarif forcé par élève l'emporte, y compris sur une matière
    # langue seule qui aurait normalement priorité (§5, règle 1).
    seance = faire_seance(
        eleve_nom="HUGO", eleve_prenom="X", matiere="ANGLAIS", niveau_de_classe="CE1", classe="CE1", duree_minutes=60
    )

    resultat = calculer_resultat_seance(
        seance, BAREME_PAR_DEFAUT, exceptions_eleve={("HUGO", "X"): 5000}
    )

    assert isinstance(resultat, ResultatSeance)
    assert resultat.tarif_horaire == 5000
    assert resultat.source_tarif == "eleve"
    assert resultat.tarif_exceptionnel is True


def test_exception_eleve_paye_meme_si_niveau_non_resolu():
    # Un tarif forcé ne dépend pas du niveau : la séance n'est plus signalée
    # "non résolue" pour cet élève, contrairement au cas général (§5).
    seance = faire_seance(
        eleve_nom="HUGO", eleve_prenom="X", matiere="Mathématiques", niveau_de_classe="", classe="", duree_minutes=60
    )

    resultat = calculer_resultat_seance(
        seance, BAREME_PAR_DEFAUT, exceptions_eleve={("HUGO", "X"): 5000}
    )

    assert isinstance(resultat, ResultatSeance)
    assert resultat.tarif_horaire == 5000
    assert resultat.niveau_resolu is None
    assert resultat.montant == 5000


def test_exception_eleve_prioritaire_sur_exception_enseignant():
    # Règle de priorité confirmée par le client : si les deux s'appliquent à
    # la même séance, le tarif élève l'emporte sur le tarif enseignant.
    seance = faire_seance(
        enseignant="MOLO ALINE",
        eleve_nom="HUGO",
        eleve_prenom="X",
        matiere="Mathématiques",
        niveau_de_classe="CE1",
        classe="CE1",
        duree_minutes=60,
    )

    resultat = calculer_resultat_seance(
        seance,
        BAREME_PAR_DEFAUT,
        exceptions_enseignant={("MOLO ALINE", "Primaire"): 1600},
        exceptions_eleve={("HUGO", "X"): 5000},
    )

    assert isinstance(resultat, ResultatSeance)
    assert resultat.tarif_horaire == 5000
    assert resultat.source_tarif == "eleve"


def test_sans_exception_configuree_comportement_identique_a_la_v1():
    # exceptions_enseignant/exceptions_eleve omis (défaut None) -> aucun
    # changement de comportement par rapport à V1.
    seance = faire_seance(matiere="Mathématiques", niveau_de_classe="6EME", classe="6EME", duree_minutes=60)

    resultat = calculer_resultat_seance(seance, BAREME_PAR_DEFAUT)

    assert isinstance(resultat, ResultatSeance)
    assert resultat.tarif_exceptionnel is False
