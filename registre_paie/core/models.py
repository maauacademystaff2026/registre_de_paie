"""Structures de données du domaine (§2, §4, §8.2 du PRD).

Ces dataclasses sont le seul langage que parle `core/` : l'import Excel et la DB
convertissent leurs formats natifs vers ces structures avant tout calcul, et
n'en ressortent jamais (§11, principe directeur n°1).
"""

from dataclasses import dataclass, field

# §4 (corrigé) : le professeur est payé s'il s'est présenté, quel que soit
# l'état de l'élève (Présentiel/Dispensé/Retard/Absent — l'absence de l'élève
# n'est pas la faute du professeur). La seule séance non payable est celle où
# le PROFESSEUR lui-même était absent ("Absence du prof").
_MARQUEUR_ABSENCE_PROF = "absence du prof"


def est_absence_prof(etat_eleve: str) -> bool:
    return _MARQUEUR_ABSENCE_PROF in etat_eleve.strip().lower()


def est_payable(etat_eleve: str) -> bool:
    """§4 : payable sauf si le professeur lui-même était absent."""
    return not est_absence_prof(etat_eleve)


@dataclass(frozen=True)
class Personne:
    """Une entrée de l'annuaire (Feuille de temps, §2.1). Sert à identifier qui
    est qui — jamais de filtre de paiement (§3)."""

    nom: str
    roles: tuple[str, ...] = ()


@dataclass(frozen=True)
class Seance:
    """Une ligne du journal des appels (§2.2)."""

    enseignant: str
    eleve_nom: str
    eleve_prenom: str
    date: str  # ISO YYYY-MM-DD, converti à l'import depuis DD-MM-YYYY
    classe: str
    section: str
    niveau_de_classe: str
    matiere: str
    duree_minutes: int
    etat_eleve: str

    def payable(self) -> bool:
        return est_payable(self.etat_eleve)


@dataclass(frozen=True)
class ResultatSeance:
    """Détail calculé pour une séance payable (§8.2 : détail par séance)."""

    seance: Seance
    duree_minutes: int
    niveau_resolu: str | None
    categorie_tarif: str
    source_tarif: str  # "langue" ou "niveau"
    tarif_horaire: float
    montant: float  # exact, non arrondi (§7-E : l'arrondi n'intervient qu'au total personne)


@dataclass(frozen=True)
class SeanceNonResolue:
    """Séance payable dont le niveau n'a pu être résolu (§5) — exclue du calcul
    automatique, à traiter manuellement."""

    seance: Seance
    raison: str


@dataclass
class ResultatPersonne:
    """Agrégat par personne (§6, §8.2)."""

    nom: str
    exclu: bool = False
    details: list[ResultatSeance] = field(default_factory=list)
    versement_15: float = 0.0

    @property
    def heures_payees_minutes(self) -> int:
        return sum(d.duree_minutes for d in self.details)

    @property
    def montant_brut_exact(self) -> float:
        return sum(d.montant for d in self.details)

    @property
    def montant_brut(self) -> int:
        """Arrondi appliqué une seule fois, sur le total (§6, §7-E).

        Si la personne est exclue (§7-A), le brut payé est 0 même si des
        séances ont été enregistrées : `details`/`heures_payees_minutes`
        restent renseignés pour la traçabilité (zone "à vérifier"), seul le
        montant payé est neutralisé.
        """
        if self.exclu:
            return 0
        return round(self.montant_brut_exact)

    @property
    def net_a_payer(self) -> float:
        return self.montant_brut - self.versement_15


@dataclass(frozen=True)
class IntervenantInconnu:
    """Personne apparue comme enseignant dans le journal des appels mais absente
    de l'annuaire (§7-B) — jamais payée automatiquement."""

    nom: str
    seances: tuple[Seance, ...]


@dataclass
class ResultatCalculMensuel:
    """Sortie complète du calcul d'un mois (§8.2) : résultats par personne,
    séances non résolues, intervenants inconnus — les trois zones d'affichage."""

    resultats_par_personne: dict[str, ResultatPersonne] = field(default_factory=dict)
    seances_non_resolues: list[SeanceNonResolue] = field(default_factory=list)
    intervenants_inconnus: list[IntervenantInconnu] = field(default_factory=list)
