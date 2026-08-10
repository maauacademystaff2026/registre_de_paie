"""Résolution du niveau d'une séance et de sa catégorie tarifaire (§5).

Priorité : `Niveau de classe`. Si absent/vide/`Tous les niveaux`/non reconnu,
tentative d'extraction du code depuis `Classe` (ex. "1ERE STL" -> "1ERE").
Si toujours rien : la séance doit être traitée comme non résolue par l'appelant
(voir core/tarification.py) — cette fonction ne renvoie jamais de valeur par défaut.
"""

import re

CODE_A_CATEGORIE: dict[str, str] = {
    "CP": "Primaire",
    "CE1": "Primaire",
    "CE2": "Primaire",
    "CM1": "Primaire",
    "CM2": "Primaire",
    "6EME": "Collège",
    "5EME": "Collège",
    "4EME": "Collège",
    "3EME": "Collège",
    "2NDE": "Lycée",
    "1ERE": "Lycée",
    "TLE": "Lycée",
    "BTS": "BTS",
}

# Du plus long au plus court pour éviter qu'un code plus court ne masque un
# code plus long lors de la recherche par sous-chaîne.
_CODES_TRIES = sorted(CODE_A_CATEGORIE, key=len, reverse=True)

_VALEUR_NON_EXPLOITABLE = "tous les niveaux"


def extraire_code_niveau(texte: str) -> str | None:
    """Cherche un code de niveau connu dans `texte` (insensible à la casse,
    délimité par des bordures de mot). Retourne le code canonique ou None."""
    if not texte:
        return None
    texte_upper = texte.strip().upper()
    for code in _CODES_TRIES:
        if re.search(rf"\b{re.escape(code)}\b", texte_upper):
            return code
    return None


def resoudre_niveau(niveau_de_classe: str, classe: str) -> tuple[str, str] | None:
    """Retourne (code_niveau, categorie) ou None si non résolu (§5)."""
    niveau_de_classe = (niveau_de_classe or "").strip()
    if niveau_de_classe and niveau_de_classe.lower() != _VALEUR_NON_EXPLOITABLE:
        code = extraire_code_niveau(niveau_de_classe)
        if code:
            return code, CODE_A_CATEGORIE[code]

    code = extraire_code_niveau(classe or "")
    if code:
        return code, CODE_A_CATEGORIE[code]

    return None
