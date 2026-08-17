"""Écran d'historique (§8.3) : consultation des mois déjà calculés, lecture
seule, et export de tous les mois d'une année en un fichier."""

import io

import pandas as pd
import streamlit as st

import db.repository as repo
from core.utils import NOMS_MOIS
from export.xlsx_export import exporter_historique_annee
from ui import style


def _afficher_tableau_resultats(calcul):
    df = pd.DataFrame(
        [
            {
                "Nom": r.nom,
                "Exclu": "Oui" if r.exclu else "",
                "Heures payées": round(r.heures_payees_minutes / 60, 2),
                "Montant brut (F CFA)": r.montant_brut,
                "Versement du 15 (F CFA)": r.versement_15,
                "Versé": "Oui" if r.versement_15_verse else "",
                "Net à payer (F CFA)": r.net_a_payer,
            }
            for r in calcul.resultats
        ]
    )
    st.dataframe(
        style.avec_total(
            df,
            ["Heures payées", "Montant brut (F CFA)", "Versement du 15 (F CFA)", "Net à payer (F CFA)"],
            "Nom",
        ),
        hide_index=True,
    )

    if calcul.nb_seances_non_resolues or calcul.nb_intervenants_inconnus:
        st.caption(
            f"Zone « à vérifier » au moment de ce calcul : "
            f"{calcul.nb_seances_non_resolues} séance(s) non résolue(s), "
            f"{calcul.nb_intervenants_inconnus} intervenant(s) inconnu(s)."
        )


def _afficher_confirmation_versement_15(conn, calcul):
    candidats = [r for r in calcul.resultats if r.versement_15 > 0]
    if not candidats:
        return

    st.markdown("**Confirmer le Versement du 15**")
    st.caption(
        "Cochez pour les personnes ayant réellement reçu leur avance calculée — "
        "« Net à payer » est recalculé et enregistré immédiatement."
    )
    for r in candidats:
        montant = f"{r.versement_15:,.0f} F CFA".replace(",", " ")
        nouveau_verse = st.checkbox(f"{r.nom} — {montant}", value=r.versement_15_verse, key=f"verse_{r.id}")
        if nouveau_verse != r.versement_15_verse:
            repo.definir_versement_15_verse(conn, r.id, nouveau_verse)
            st.rerun()


def _afficher_detail_par_personne(conn, calcul):
    if not calcul.resultats:
        return
    nom_choisi = st.selectbox("Détail par séance pour", [r.nom for r in calcul.resultats])
    resultat_id = next(r.id for r in calcul.resultats if r.nom == nom_choisi)
    details = repo.charger_details_seances(conn, resultat_id)
    if details:
        st.dataframe(
            style.avec_total(pd.DataFrame([dict(d) for d in details]), ["montant"], "eleve_nom"),
            hide_index=True,
        )
    else:
        st.info("Aucune séance payée pour cette personne.")


def afficher(conn):
    st.header("Historique")

    mois_disponibles = repo.lister_mois(conn)
    if not mois_disponibles:
        st.info("Aucun mois enregistré pour l'instant.")
        return

    options = {f"{NOMS_MOIS[m]} {a}": (a, m) for a, m, _ in mois_disponibles}
    choix = st.selectbox("Mois", list(options))
    annee, mois = options[choix]

    calcul = repo.charger_mois(conn, annee, mois)
    st.caption(f"Calculé le {calcul.date_calcul}")

    _afficher_tableau_resultats(calcul)
    _afficher_confirmation_versement_15(conn, calcul)
    _afficher_detail_par_personne(conn, calcul)

    st.subheader(f"Export de l'année {annee}")
    tampon = io.BytesIO()
    exporter_historique_annee(conn, annee, tampon)
    st.download_button(
        f"Télécharger l'historique {annee} (.xlsx)",
        data=tampon.getvalue(),
        file_name=f"historique_paie_{annee}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
