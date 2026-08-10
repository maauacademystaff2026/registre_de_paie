"""Non-régression bout en bout : import + tarification + agrégation sur les
vrais fichiers de juillet 2026, sous les règles A-E confirmées (§7) et la
règle §4 corrigée : le professeur est payé pour toute séance où il s'est
présenté, y compris "Absent" (élève absent, pas le professeur) — seule
"Absence du prof" n'est pas payable. Le tableau §4 du PRD tel qu'écrit
("Absent -> Non payable") était incorrect ; corrigé sur retour direct du client.

Ces chiffres remplacent le tableau §9 du PRD : celui-ci a été calculé
manuellement à partir d'un état antérieur des données / d'un barème différent
(9 des 14 montants concordaient exactement, les 5 écarts ont chacun une cause
identifiée — voir la conversation de validation). §9 anticipait explicitement
cette re-validation : "ces chiffres doivent être recalculés et documentés à
nouveau avant d'être figés comme référence de non-régression."

Si ce test casse après une modification du barème ou des règles, ce n'est pas
forcément une régression — vérifiez d'abord que le changement est voulu, puis
recalculez et mettez à jour les chiffres ci-dessous en connaissance de cause.
"""

from pathlib import Path

from core.agregation import agreger
from core.excel_import import importer_annuaire, importer_seances
from core.tarification import BAREME_PAR_DEFAUT

FIXTURES = Path(__file__).parent / "fixtures"
FEUILLE_DE_TEMPS = FIXTURES / "Feuille_de_temps_juillet2026.xlsx"
GESTION_APPELS = FIXTURES / "Gestion_des_appels_juillet2026.xlsx"

# §7-A : liste connue à ce jour, remplacée en pratique par la case "Exclu"
# par personne (recommandation retenue) — reproduite ici en dur uniquement
# pour figer ce cas de test précis.
EXCLUSIONS_JUILLET_2026 = {
    "NDONGO NGA MAXIME",
    "ELISE EYOUM",
    "MBAALE DJENE LUMIERE",
    "KAMDEM RICH BILL",
}

# nom -> (heures payées en minutes, montant brut F CFA, exclu)
REFERENCE_JUILLET_2026 = {
    "ANGOULA CLAUDE LEVI": (450, 15000, False),
    "BELL LAURENT YVAN": (360, 12000, False),
    "Djene prof Lumière": (540, 18000, False),
    "ELISE EYOUM": (360, 0, True),
    "ENGOTO MBELEG prof Emmanuel": (1200, 40000, False),
    "FAMBOVE TSUGUINI ULRICH RONALD": (1470, 49000, False),
    "FOKAM LEONEL": (120, 5000, False),
    "FOZONG JOSEPH": (540, 18000, False),
    "KOOH JEAN": (240, 6000, False),
    "LIZA ENONE LOICE": (630, 21000, False),
    "MBAALE DJENE LUMIERE": (1185, 0, True),
    "MBOCK GUY PAULIN": (2220, 74000, False),
    "MOLO ALINE": (3445, 86125, False),
    "Mbog NDJE Gaston Emmanuel": (2310, 86500, False),
    "NDJIBA DJONE MOISE": (1020, 45500, False),
    "NDONGO NGA MAXIME": (60, 0, True),
    "TIEUMENI DENIS": (1440, 49000, False),
}

TOTAL_BRUT_HORS_EXCLUS = 525125


def _calculer_juillet_2026():
    annuaire = importer_annuaire(str(FEUILLE_DE_TEMPS))
    seances = importer_seances(str(GESTION_APPELS))
    personnes_connues = {p.nom for p in annuaire}

    return agreger(
        seances=seances,
        personnes_connues=personnes_connues,
        exclusions=EXCLUSIONS_JUILLET_2026,
        versements_15={},
        bareme=BAREME_PAR_DEFAUT,
    )


def test_aucune_seance_non_resolue():
    resultat = _calculer_juillet_2026()
    assert resultat.seances_non_resolues == []


def test_seul_intervenant_inconnu_est_kamdem_rich_bill():
    # §7-B : orthographe minuscule dans le journal, absent de l'annuaire.
    resultat = _calculer_juillet_2026()
    assert len(resultat.intervenants_inconnus) == 1
    inconnu = resultat.intervenants_inconnus[0]
    assert inconnu.nom == "kamdem rich bill"
    assert sum(s.duree_minutes for s in inconnu.seances) == 480  # 8h, comme cité au §7-B


def test_montants_par_personne_juillet_2026():
    resultat = _calculer_juillet_2026()

    assert set(resultat.resultats_par_personne) == set(REFERENCE_JUILLET_2026)

    for nom, (minutes_ref, montant_ref, exclu_ref) in REFERENCE_JUILLET_2026.items():
        r = resultat.resultats_par_personne[nom]
        assert r.heures_payees_minutes == minutes_ref, nom
        assert r.montant_brut == montant_ref, nom
        assert r.exclu == exclu_ref, nom


def test_total_brut_hors_personnes_exclues():
    resultat = _calculer_juillet_2026()
    total = sum(r.montant_brut for r in resultat.resultats_par_personne.values())
    assert total == TOTAL_BRUT_HORS_EXCLUS
