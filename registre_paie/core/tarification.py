"""Calcul du tarif d'une séance payable (§5).

Ordre : matière = langue seule (exactement) -> tarif langue quel que soit le
niveau ; sinon -> tarif du niveau résolu (core/resolution_niveau.py). Aucune
exception enseignant/élève en V1 (§7-C) — le barème est le seul paramètre
variable, jamais codé en dur ici : il est toujours reçu en argument.
"""

from core.models import ResultatSeance, Seance, SeanceNonResolue
from core.resolution_niveau import resoudre_niveau
from core.utils import minutes_to_heures_decimales

# §5 : barème par défaut (F CFA / heure) — sert de valeur initiale pour la DB
# et de fixture de test. En production, le barème effectif vient de la DB
# (modifiable dans l'application), jamais de cette constante.
BAREME_PAR_DEFAUT: dict[str, float] = {
    "Langue seule": 2000,
    "Primaire": 1500,
    "Collège": 2000,
    "Lycée": 2500,
    "BTS": 3000,
}

_MATIERES_LANGUE_SEULE = {"ANGLAIS", "Français", "Espagnole"}
_MATIERES_LANGUE_SEULE_CASEFOLD = {m.casefold() for m in _MATIERES_LANGUE_SEULE}


def est_langue_seule(matiere: str) -> bool:
    """§5.1 : correspondance exacte à une langue seule, pas en combinaison
    (ex. 'Maths/Français' ne matche pas)."""
    return matiere.strip().casefold() in _MATIERES_LANGUE_SEULE_CASEFOLD


def calculer_resultat_seance(
    seance: Seance, bareme: dict[str, float]
) -> ResultatSeance | SeanceNonResolue:
    """Calcule le montant d'une séance payable. L'appelant garantit
    `seance.payable()` (une séance non payable n'a pas de tarif à calculer)."""
    matiere = seance.matiere

    if est_langue_seule(matiere):
        categorie = "Langue seule"
        niveau_resolu = None
        source_tarif = "langue"
    else:
        resolu = resoudre_niveau(seance.niveau_de_classe, seance.classe)
        if resolu is None:
            return SeanceNonResolue(
                seance=seance,
                raison=(
                    "Niveau non résolu : 'Niveau de classe' "
                    f"({seance.niveau_de_classe!r}) et 'Classe' ({seance.classe!r}) "
                    "ne permettent pas d'identifier un niveau connu."
                ),
            )
        niveau_resolu, categorie = resolu
        source_tarif = "niveau"

    tarif_horaire = bareme[categorie]
    montant = minutes_to_heures_decimales(seance.duree_minutes) * tarif_horaire

    return ResultatSeance(
        seance=seance,
        duree_minutes=seance.duree_minutes,
        niveau_resolu=niveau_resolu,
        categorie_tarif=categorie,
        source_tarif=source_tarif,
        tarif_horaire=tarif_horaire,
        montant=montant,
    )
