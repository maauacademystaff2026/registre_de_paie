"""Conversions HH:MM <-> minutes, utilisées par l'import, le calcul et l'export."""

import re
from collections import Counter

_HHMM_RE = re.compile(r"^(\d{1,3}):([0-5]\d)$")

NOMS_MOIS = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]


def hhmm_to_minutes(valeur: str) -> int:
    """Convertit 'HH:MM' en minutes entières. Lève ValueError si le format est invalide."""
    match = _HHMM_RE.match(valeur.strip())
    if not match:
        raise ValueError(f"Format HH:MM invalide : {valeur!r}")
    heures, minutes = match.groups()
    return int(heures) * 60 + int(minutes)


def minutes_to_hhmm(total_minutes: int) -> str:
    """Convertit des minutes entières en 'HH:MM'."""
    heures, minutes = divmod(total_minutes, 60)
    return f"{heures:02d}:{minutes:02d}"


def minutes_to_heures_decimales(total_minutes: int) -> float:
    """Convertit des minutes entières en heures décimales (ex. 90 -> 1.5)."""
    return total_minutes / 60


def detecter_periode(dates_iso: list[str]) -> tuple[int, int] | None:
    """§8.1 : détecte le mois/année le plus représenté parmi des dates ISO
    (YYYY-MM-DD), à confirmer par l'utilisateur avant calcul. None si vide."""
    if not dates_iso:
        return None
    compte = Counter((date[:4], date[5:7]) for date in dates_iso)
    (annee, mois), _ = compte.most_common(1)[0]
    return int(annee), int(mois)
