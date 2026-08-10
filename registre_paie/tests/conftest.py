"""Fixtures et fabriques partagées par les tests."""

from core.models import Seance


def faire_seance(
    *,
    enseignant: str = "TEST ENSEIGNANT",
    eleve_nom: str = "NOM",
    eleve_prenom: str = "PRENOM",
    date: str = "2026-07-01",
    classe: str = "6EME",
    section: str = "",
    niveau_de_classe: str = "6EME",
    matiere: str = "Mathématiques",
    duree_minutes: int = 60,
    etat_eleve: str = "Présentiel",
) -> Seance:
    """Fabrique une Seance de test avec des valeurs par défaut raisonnables ;
    ne préciser que les champs pertinents pour le cas testé."""
    return Seance(
        enseignant=enseignant,
        eleve_nom=eleve_nom,
        eleve_prenom=eleve_prenom,
        date=date,
        classe=classe,
        section=section,
        niveau_de_classe=niveau_de_classe,
        matiere=matiere,
        duree_minutes=duree_minutes,
        etat_eleve=etat_eleve,
    )
