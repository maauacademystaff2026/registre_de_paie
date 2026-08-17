"""Agrégation des séances en résultats par personne (§6, §8.2).

Pipeline : séances -> filtrer payables (§4) -> grouper par enseignant ->
distinguer intervenant connu/inconnu (§7-B) -> tarifer chaque séance (§5) en
séparant les non résolues -> construire un ResultatPersonne par personne
connue, avec arrondi unique sur le total (§7-E).
"""

from collections.abc import Iterable

from core.models import (
    IntervenantInconnu,
    ResultatCalculMensuel,
    ResultatPersonne,
    Seance,
    SeanceNonResolue,
)
from core.tarification import calculer_resultat_seance

_DERNIER_JOUR_PREMIERE_QUINZAINE = 15


def _dans_premiere_quinzaine(date_iso: str, annee: int, mois: int) -> bool:
    """§6 (mis à jour) : une séance compte pour le Versement du 15 si elle est
    datée du 1er au 15 du mois calculé — jamais un autre mois. Une simple
    comparaison de chaînes (`date <= "...-15"`) inclurait à tort un mois
    antérieur dont les dates trient avant le 15 du mois cible."""
    return date_iso[:7] == f"{annee:04d}-{mois:02d}" and int(date_iso[8:10]) <= _DERNIER_JOUR_PREMIERE_QUINZAINE


def _construire_resultats_par_personne(
    seances: Iterable[Seance],
    personnes_connues: set[str],
    exclusions: set[str],
    bareme: dict[str, float],
    exceptions_enseignant: dict[tuple[str, str], float] | None,
    exceptions_eleve: dict[tuple[str, str], float] | None,
) -> tuple[dict[str, ResultatPersonne], list[SeanceNonResolue], list[IntervenantInconnu]]:
    """Coeur du calcul, factorisé pour être appelé une fois sur le mois
    entier et une fois sur la première quinzaine (Versement du 15) — mêmes
    règles de tarification et d'exclusion dans les deux cas."""
    seances_par_enseignant: dict[str, list[Seance]] = {}
    for seance in seances:
        if not seance.payable():
            continue
        nom = seance.enseignant.strip()
        seances_par_enseignant.setdefault(nom, []).append(seance)

    resultats_par_personne: dict[str, ResultatPersonne] = {}
    seances_non_resolues: list[SeanceNonResolue] = []
    intervenants_inconnus: list[IntervenantInconnu] = []

    for nom, seances_personne in seances_par_enseignant.items():
        if nom not in personnes_connues:
            intervenants_inconnus.append(IntervenantInconnu(nom=nom, seances=tuple(seances_personne)))
            continue

        details = []
        for seance in seances_personne:
            calcul = calculer_resultat_seance(seance, bareme, exceptions_enseignant, exceptions_eleve)
            if isinstance(calcul, SeanceNonResolue):
                seances_non_resolues.append(calcul)
            else:
                details.append(calcul)

        resultats_par_personne[nom] = ResultatPersonne(nom=nom, exclu=nom in exclusions, details=details)

    return resultats_par_personne, seances_non_resolues, intervenants_inconnus


def agreger(
    seances: Iterable[Seance],
    personnes_connues: set[str],
    exclusions: set[str],
    annee: int,
    mois: int,
    bareme: dict[str, float],
    exceptions_enseignant: dict[tuple[str, str], float] | None = None,
    exceptions_eleve: dict[tuple[str, str], float] | None = None,
) -> ResultatCalculMensuel:
    """Calcule le résultat mensuel complet.

    - `personnes_connues` : noms présents dans l'annuaire (Feuille de temps).
    - `exclusions` : noms cochés "Exclu" (§7-A) — toujours dans personnes_connues.
    - `annee`, `mois` : période calculée — sert à isoler les séances du 1er au
      15 pour le Versement du 15 (§6, mis à jour : calculé, plus saisi).
    - `bareme` : tarifs F CFA/heure par catégorie, ex. tarification.BAREME_PAR_DEFAUT.
    - `exceptions_enseignant`, `exceptions_eleve` : overrides V2 (§7-C, §10),
      voir core/tarification.py:calculer_resultat_seance. Optionnels — une
      année sans exception configurée se comporte exactement comme en V1.
    """
    seances = list(seances)
    resultats_par_personne, seances_non_resolues, intervenants_inconnus = (
        _construire_resultats_par_personne(
            seances, personnes_connues, exclusions, bareme, exceptions_enseignant, exceptions_eleve
        )
    )

    seances_premiere_quinzaine = [s for s in seances if _dans_premiere_quinzaine(s.date, annee, mois)]
    resultats_premiere_quinzaine, _, _ = _construire_resultats_par_personne(
        seances_premiere_quinzaine, personnes_connues, exclusions, bareme, exceptions_enseignant, exceptions_eleve
    )
    for nom, resultat_personne in resultats_par_personne.items():
        premiere_quinzaine = resultats_premiere_quinzaine.get(nom)
        resultat_personne.versement_15 = premiere_quinzaine.montant_brut if premiere_quinzaine else 0.0

    return ResultatCalculMensuel(
        resultats_par_personne=resultats_par_personne,
        seances_non_resolues=seances_non_resolues,
        intervenants_inconnus=intervenants_inconnus,
    )
