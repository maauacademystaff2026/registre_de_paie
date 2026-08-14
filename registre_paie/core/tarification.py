"""Calcul du tarif d'une séance payable (§5, §7-C, §10).

Ordre de résolution d'une séance, du plus spécifique au plus générique :
1. Exception élève (V2 §10, tarif forcé, indépendant matière/niveau) — si le
   couple (nom, prénom) de l'élève a un tarif forcé, il l'emporte sur tout le
   reste, y compris sur une exception enseignant éventuelle sur la même
   séance (règle de priorité confirmée par le client).
2. Sinon, catégorie déterminée comme avant : matière = langue seule
   (exactement) -> tarif langue quel que soit le niveau ; sinon -> tarif du
   niveau résolu (core/resolution_niveau.py).
3. Exception enseignant (V2 §7-C) sur cette catégorie -> remplace le tarif du
   barème pour cette catégorie uniquement.
4. Sinon, tarif du barème global (jamais codé en dur ici : toujours reçu en
   argument, comme les exceptions).
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
    seance: Seance,
    bareme: dict[str, float],
    exceptions_enseignant: dict[tuple[str, str], float] | None = None,
    exceptions_eleve: dict[tuple[str, str], float] | None = None,
) -> ResultatSeance | SeanceNonResolue:
    """Calcule le montant d'une séance payable. L'appelant garantit
    `seance.payable()` (une séance non payable n'a pas de tarif à calculer).

    `exceptions_enseignant` : {(enseignant, categorie): tarif_horaire} (§7-C).
    `exceptions_eleve` : {(eleve_nom, eleve_prenom): tarif_horaire} (§10) —
    prioritaire sur `exceptions_enseignant` si les deux s'appliqueraient à la
    même séance.
    """
    exceptions_enseignant = exceptions_enseignant or {}
    exceptions_eleve = exceptions_eleve or {}
    matiere = seance.matiere

    tarif_force_eleve = exceptions_eleve.get((seance.eleve_nom, seance.eleve_prenom))

    if est_langue_seule(matiere):
        categorie = "Langue seule"
        niveau_resolu = None
        source_tarif = "langue"
    else:
        resolu = resoudre_niveau(seance.niveau_de_classe, seance.classe)
        if resolu is None:
            if tarif_force_eleve is not None:
                # §10 : un tarif forcé ne dépend pas du niveau — l'élève est payé
                # même quand le niveau n'aurait normalement pas pu être résolu.
                categorie, niveau_resolu, source_tarif = "Exception élève", None, "eleve"
            else:
                return SeanceNonResolue(
                    seance=seance,
                    raison=(
                        "Niveau non résolu : 'Niveau de classe' "
                        f"({seance.niveau_de_classe!r}) et 'Classe' ({seance.classe!r}) "
                        "ne permettent pas d'identifier un niveau connu."
                    ),
                )
        else:
            niveau_resolu, categorie = resolu
            source_tarif = "niveau"

    if tarif_force_eleve is not None:
        tarif_horaire = tarif_force_eleve
        source_tarif = "eleve"
        tarif_exceptionnel = True
    else:
        tarif_enseignant = exceptions_enseignant.get((seance.enseignant, categorie))
        if tarif_enseignant is not None:
            tarif_horaire = tarif_enseignant
            tarif_exceptionnel = True
        else:
            tarif_horaire = bareme[categorie]
            tarif_exceptionnel = False

    montant = minutes_to_heures_decimales(seance.duree_minutes) * tarif_horaire

    return ResultatSeance(
        seance=seance,
        duree_minutes=seance.duree_minutes,
        niveau_resolu=niveau_resolu,
        categorie_tarif=categorie,
        source_tarif=source_tarif,
        tarif_horaire=tarif_horaire,
        montant=montant,
        tarif_exceptionnel=tarif_exceptionnel,
    )
