"""Mise en forme des tableaux affichés (couleurs MA-AU Academy, §thème) :
lignes alternées pour distinguer chaque ligne, ligne de total mise en
évidence, et formatage des nombres (sans quoi un `pandas.Styler` affiche par
défaut les colonnes à virgule avec 6 décimales, ex. "15000.000000").

Ne s'applique qu'aux tableaux en lecture seule (`st.dataframe`) : un
`pandas.Styler` n'est pas accepté par `st.data_editor`, qui doit rester
affiché sans cette mise en forme."""

import pandas as pd
import pandas.api.types as ptypes

_VERT_ZEBRE = "#eef7e0"  # dérivé du vert boutons du site (#94c93d), très clair
_VERT_TOTAL = "#4a7a1e"  # même teinte, assombrie pour rester lisible en blanc
_BLANC = "#ffffff"


def _appliquer_couleurs(df: pd.DataFrame, ligne_total: bool):
    def _couleurs_ligne(ligne):
        if ligne_total and ligne.name == len(df) - 1:
            return [f"background-color: {_VERT_TOTAL}; color: #ffffff; font-weight: 600"] * len(ligne)
        couleur = _VERT_ZEBRE if ligne.name % 2 == 1 else _BLANC
        return [f"background-color: {couleur}"] * len(ligne)

    return df.style.apply(_couleurs_ligne, axis=1)


def _formateur_nombre(serie_originale: pd.Series):
    """Entier avec espace milliers si toutes les valeurs de la colonne sont
    des nombres entiers (montants F CFA) ; sinon 2 décimales maximum, sans
    zéro inutile (durées en heures, ex. 7.5 et non 7.50 ou 7.500000)."""
    valeurs = pd.to_numeric(serie_originale, errors="coerce").dropna()
    entiers = valeurs.empty or (valeurs % 1 == 0).all()

    def _formater(valeur):
        if pd.isna(valeur):
            return ""
        if entiers:
            return f"{valeur:,.0f}".replace(",", " ")
        return f"{valeur:.2f}".rstrip("0").rstrip(".")

    return _formater


def _appliquer_formats(styler, df_reference: pd.DataFrame):
    """Choisit le format de chaque colonne à partir de `df_reference` (avant
    ajout éventuel de la ligne de total, pour ne pas laisser l'imprécision
    d'une somme flottante influencer la décision entier/décimal)."""
    formats = {}
    for colonne in df_reference.columns:
        serie = df_reference[colonne]
        if ptypes.is_bool_dtype(serie):
            formats[colonne] = lambda v: "" if pd.isna(v) else str(v)
        elif ptypes.is_numeric_dtype(serie):
            formats[colonne] = _formateur_nombre(serie)
    return styler.format(formats) if formats else styler


def zebre(df: pd.DataFrame):
    """Tableau en lecture seule avec lignes alternées, sans ligne de total."""
    return _appliquer_formats(_appliquer_couleurs(df, ligne_total=False), df)


def avec_total(df: pd.DataFrame, colonnes_a_sommer: list[str], colonne_libelle: str):
    """Ajoute une ligne « Total » (somme de `colonnes_a_sommer`) puis applique
    lignes alternées + mise en évidence de cette ligne de total."""
    if df.empty:
        return _appliquer_formats(_appliquer_couleurs(df, ligne_total=False), df)

    # Les colonnes ni sommées ni libellées doivent rester "vides" avec un type
    # compatible avec leur colonne d'origine : une chaîne "" dans une colonne
    # int64/bool casse la sérialisation Arrow de st.dataframe (Streamlit s'en
    # remet, mais avec une trace d'erreur bruyante en coulisses) — pd.NA est
    # le "vide" sûr pour tout ce qui n'est pas déjà du texte (dtype object).
    ligne_total = {}
    for colonne in df.columns:
        if colonne == colonne_libelle:
            ligne_total[colonne] = "Total"
        elif colonne in colonnes_a_sommer:
            ligne_total[colonne] = df[colonne].sum()
        elif df[colonne].dtype == object:
            ligne_total[colonne] = ""
        else:
            ligne_total[colonne] = pd.NA

    df_avec_total = pd.concat([df, pd.DataFrame([ligne_total])], ignore_index=True)
    styler = _appliquer_couleurs(df_avec_total, ligne_total=True)
    return _appliquer_formats(styler, df)
