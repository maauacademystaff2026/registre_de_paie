"""Écran « Tableau de bord » : vue d'ensemble sur tous les mois déjà
enregistrés dans l'historique — évolution du coût total et classement des
intervenants. Lecture seule : aucun calcul n'est refait ici, tout vient des
montants déjà figés par `core/agregation.py` au moment de chaque "Enregistrer"
(cf. db/repository.py:enregistrer_calcul_mensuel)."""

import pandas as pd
import streamlit as st

import db.repository as repo
from core.utils import NOMS_MOIS
from ui import style


def _construire_donnees(conn, mois_disponibles):
    lignes_mensuelles = []
    lignes_par_personne = []

    for annee, mois, _date_calcul in mois_disponibles:
        calcul = repo.charger_mois(conn, annee, mois)
        total_brut = sum(r.montant_brut for r in calcul.resultats)
        total_net = sum(r.net_a_payer for r in calcul.resultats)
        lignes_mensuelles.append(
            {
                "annee": annee,
                "mois": mois,
                "Période": f"{NOMS_MOIS[mois]} {annee}",
                "Total brut (F CFA)": total_brut,
                "Total net (F CFA)": total_net,
                "Personnes payées": sum(1 for r in calcul.resultats if not r.exclu and r.montant_brut > 0),
            }
        )
        for r in calcul.resultats:
            lignes_par_personne.append(
                {
                    "Nom": r.nom,
                    "Montant brut (F CFA)": r.montant_brut,
                    "Heures payées": round(r.heures_payees_minutes / 60, 2),
                }
            )

    df_mensuel = pd.DataFrame(lignes_mensuelles).sort_values(["annee", "mois"]).reset_index(drop=True)
    df_personnes = pd.DataFrame(lignes_par_personne)
    return df_mensuel, df_personnes


def afficher(conn):
    st.header("Tableau de bord")

    mois_disponibles = repo.lister_mois(conn)
    if not mois_disponibles:
        st.info(
            "Aucun mois enregistré pour l'instant. Calculez un mois dans "
            "« Calcul du mois » puis cliquez sur « Enregistrer » pour qu'il "
            "apparaisse ici."
        )
        return

    df_mensuel, df_personnes = _construire_donnees(conn, mois_disponibles)

    col1, col2, col3 = st.columns(3)
    col1.metric("Mois enregistrés", len(df_mensuel))
    col2.metric(
        "Total brut cumulé",
        f"{df_mensuel['Total brut (F CFA)'].sum():,.0f} F CFA".replace(",", " "),
    )
    col3.metric(
        "Moyenne mensuelle (brut)",
        f"{df_mensuel['Total brut (F CFA)'].mean():,.0f} F CFA".replace(",", " "),
    )

    st.subheader("Évolution du coût total par mois")
    st.line_chart(df_mensuel.set_index("Période")[["Total brut (F CFA)", "Total net (F CFA)"]])

    st.subheader("Classement des intervenants (cumul de tous les mois enregistrés)")
    cumul = (
        df_personnes.groupby("Nom", as_index=False)
        .agg({"Montant brut (F CFA)": "sum", "Heures payées": "sum"})
        .sort_values("Montant brut (F CFA)", ascending=False)
        .reset_index(drop=True)
    )

    if len(cumul) > 5:
        top_n = st.slider("Nombre d'intervenants affichés", 5, len(cumul), min(10, len(cumul)))
        cumul_affiche = cumul.head(top_n)
    else:
        cumul_affiche = cumul

    st.bar_chart(cumul_affiche.set_index("Nom")["Montant brut (F CFA)"])

    st.subheader("Détail par mois")
    st.dataframe(
        style.avec_total(
            df_mensuel[["Période", "Total brut (F CFA)", "Total net (F CFA)", "Personnes payées"]],
            ["Total brut (F CFA)", "Total net (F CFA)", "Personnes payées"],
            "Période",
        ),
        hide_index=True,
    )

    st.subheader("Cumul par intervenant")
    st.dataframe(
        style.avec_total(cumul, ["Montant brut (F CFA)", "Heures payées"], "Nom"),
        hide_index=True,
    )
