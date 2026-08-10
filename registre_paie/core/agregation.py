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


def agreger(
    seances: Iterable[Seance],
    personnes_connues: set[str],
    exclusions: set[str],
    versements_15: dict[str, float],
    bareme: dict[str, float],
) -> ResultatCalculMensuel:
    """Calcule le résultat mensuel complet.

    - `personnes_connues` : noms présents dans l'annuaire (Feuille de temps).
    - `exclusions` : noms cochés "Exclu" (§7-A) — toujours dans personnes_connues.
    - `versements_15` : avance déjà versée par nom (§6), défaut 0 si absent.
    - `bareme` : tarifs F CFA/heure par catégorie, ex. tarification.BAREME_PAR_DEFAUT.
    """
    seances_par_enseignant: dict[str, list[Seance]] = {}
    for seance in seances:
        if not seance.payable():
            continue
        nom = seance.enseignant.strip()
        seances_par_enseignant.setdefault(nom, []).append(seance)

    resultat = ResultatCalculMensuel()

    for nom, seances_personne in seances_par_enseignant.items():
        if nom not in personnes_connues:
            resultat.intervenants_inconnus.append(
                IntervenantInconnu(nom=nom, seances=tuple(seances_personne))
            )
            continue

        details = []
        for seance in seances_personne:
            calcul = calculer_resultat_seance(seance, bareme)
            if isinstance(calcul, SeanceNonResolue):
                resultat.seances_non_resolues.append(calcul)
            else:
                details.append(calcul)

        resultat.resultats_par_personne[nom] = ResultatPersonne(
            nom=nom,
            exclu=nom in exclusions,
            details=details,
            versement_15=versements_15.get(nom, 0.0),
        )

    return resultat
