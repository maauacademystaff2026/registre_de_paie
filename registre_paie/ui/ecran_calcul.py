"""Écran principal (§8.1, §8.2) : import des 2 fichiers, calcul, résultats,
zone « à vérifier », détail par séance, enregistrement et export du mois."""

import io

import pandas as pd
import streamlit as st

import db.repository as repo
from core.agregation import agreger
from core.excel_import import ErreurImport, importer_annuaire, importer_seances
from core.utils import NOMS_MOIS, detecter_periode
from export.xlsx_export import exporter_resultats
from ui import style


def _importer_fichiers():
    st.subheader("1. Import des fichiers du mois")
    col1, col2 = st.columns(2)
    with col1:
        fichier_feuille = st.file_uploader("Feuille de temps (.xlsx)", type="xlsx", key="feuille_de_temps")
    with col2:
        fichier_appels = st.file_uploader("Gestion des appels (.xlsx)", type="xlsx", key="gestion_appels")

    if not (fichier_feuille and fichier_appels):
        st.info("Déposez les deux fichiers pour lancer le calcul.")
        return None, None

    try:
        annuaire = importer_annuaire(fichier_feuille)
        seances = importer_seances(fichier_appels)
    except ErreurImport as exc:
        st.error(str(exc))
        return None, None

    st.session_state["dernier_annuaire"] = annuaire
    st.success(f"{len(annuaire)} personne(s) à l'annuaire, {len(seances)} séance(s) importée(s).")
    return annuaire, seances


def _confirmer_periode(seances):
    periode = detecter_periode([s.date for s in seances])
    annee_defaut, mois_defaut = periode if periode else (2026, 1)

    st.subheader("2. Période détectée")
    col1, col2 = st.columns(2)
    with col1:
        annee = st.number_input("Année", min_value=2020, max_value=2100, value=annee_defaut, step=1)
    with col2:
        mois = st.number_input("Mois", min_value=1, max_value=12, value=mois_defaut, step=1)
    st.caption("Vérifiez que la période détectée est correcte avant de calculer.")
    return int(annee), int(mois)


def _calculer(conn, annuaire, seances, annee, mois):
    personnes_connues = {p.nom for p in annuaire}
    exclusions = repo.lire_exclusions(conn)
    bareme = repo.lire_bareme(conn)
    resultat = agreger(
        seances=seances,
        personnes_connues=personnes_connues,
        exclusions=exclusions,
        annee=annee,
        mois=mois,
        bareme=bareme,
        exceptions_enseignant=repo.lire_exceptions_enseignant(conn),
        exceptions_eleve=repo.lire_exceptions_eleve(conn),
    )
    # Un réimport de ce mois ne doit jamais réinitialiser silencieusement le
    # statut « Versé » déjà confirmé — ce fait n'est dérivable ni des
    # fichiers ni d'aucun réglage global, voir repo.reporter_versement_15_verse.
    report_effectue = repo.reporter_versement_15_verse(conn, annee, mois, resultat)
    return resultat, report_effectue


def _lignes_resultats(resultat):
    return [
        {
            "Nom": nom,
            "Exclu": r.exclu,
            "Heures payées": round(r.heures_payees_minutes / 60, 2),
            "Montant brut (F CFA)": r.montant_brut,
            "Versement du 15 (F CFA)": r.versement_15,
            "Versé": r.versement_15_verse,
            "Net à payer (F CFA)": r.net_a_payer,
        }
        for nom, r in sorted(resultat.resultats_par_personne.items())
    ]


def _afficher_resultats(resultat, versement_15_reporte=False):
    st.subheader("3. Résultats")

    if not resultat.resultats_par_personne:
        st.warning("Aucune personne payable ce mois-ci.")
        return

    if versement_15_reporte:
        st.info(
            "Ce mois avait déjà été enregistré — le statut « Versé » de chaque personne a été "
            "repris de ce précédent enregistrement. Vérifiez-le si les données réimportées ont "
            "changé pour une personne concernée."
        )

    st.caption(
        "« Versement du 15 » est calculé automatiquement (heures travaillées du 1er au 15 "
        "du mois, mêmes règles de tarification) — non modifiable. Cochez « Versé » "
        "uniquement pour les personnes ayant réellement reçu cette avance : "
        "« Net à payer » n'en déduit alors le montant."
    )
    df_edite = st.data_editor(
        pd.DataFrame(_lignes_resultats(resultat)),
        disabled=["Nom", "Exclu", "Heures payées", "Montant brut (F CFA)", "Versement du 15 (F CFA)", "Net à payer (F CFA)"],
        hide_index=True,
        key="editeur_resultats",
    )

    # st.data_editor ne recalcule pas les colonnes désactivées (ex. Net à
    # payer) dans le même rerun qu'une édition d'une autre colonne (ex.
    # Versé) : sans le rerun explicite ci-dessous, la case se coche à l'écran
    # mais le montant affiché reste celui d'avant le clic jusqu'à la
    # prochaine interaction.
    a_change = False
    for _, ligne in df_edite.iterrows():
        r = resultat.resultats_par_personne[ligne["Nom"]]
        nouveau_verse = bool(ligne["Versé"])
        if r.versement_15_verse != nouveau_verse:
            r.versement_15_verse = nouveau_verse
            a_change = True
    if a_change:
        st.rerun()

    total_brut = sum(r.montant_brut for r in resultat.resultats_par_personne.values())
    total_net = sum(r.net_a_payer for r in resultat.resultats_par_personne.values())
    col1, col2 = st.columns(2)
    col1.metric("Total brut", f"{total_brut:,.0f} F CFA".replace(",", " "))
    col2.metric("Total net à payer", f"{total_net:,.0f} F CFA".replace(",", " "))


def _afficher_a_verifier(resultat):
    st.subheader("4. À vérifier")

    if resultat.seances_non_resolues:
        st.markdown(f"**Séances à niveau non résolu ({len(resultat.seances_non_resolues)})**")
        st.dataframe(
            style.zebre(
                pd.DataFrame(
                    [
                        {
                            "Enseignant": sr.seance.enseignant,
                            "Date": sr.seance.date,
                            "Classe": sr.seance.classe,
                            "Niveau de classe": sr.seance.niveau_de_classe,
                            "Matière": sr.seance.matiere,
                            "Raison": sr.raison,
                        }
                        for sr in resultat.seances_non_resolues
                    ]
                )
            ),
            hide_index=True,
        )
    else:
        st.success("Aucune séance à niveau non résolu.")

    if resultat.intervenants_inconnus:
        st.markdown(f"**Intervenants absents de l'annuaire ({len(resultat.intervenants_inconnus)})**")
        st.dataframe(
            style.zebre(
                pd.DataFrame(
                    [
                        {
                            "Nom": ii.nom,
                            "Heures (non payées)": round(sum(s.duree_minutes for s in ii.seances) / 60, 2),
                            "Nb séances": len(ii.seances),
                        }
                        for ii in resultat.intervenants_inconnus
                    ]
                )
            ),
            hide_index=True,
        )
    else:
        st.success("Tous les intervenants sont reconnus dans l'annuaire.")


_LABEL_SOURCE_TARIF = {"langue": "Langue", "niveau": "Niveau", "eleve": "Élève (forcé)"}


def _afficher_detail_par_personne(resultat):
    st.subheader("5. Détail par séance")
    noms = sorted(resultat.resultats_par_personne)
    if not noms:
        return

    nom = st.selectbox("Personne", noms)
    details = resultat.resultats_par_personne[nom].details
    if not details:
        st.info("Aucune séance payée pour cette personne.")
        return

    st.dataframe(
        style.avec_total(
            pd.DataFrame(
                [
                    {
                        "Élève": f"{d.seance.eleve_nom} {d.seance.eleve_prenom}".strip(),
                        "Date": d.seance.date,
                        "Niveau": d.niveau_resolu or "—",
                        "Matière": d.seance.matiere,
                        "Durée (H)": f"{d.duree_minutes // 60:02d}:{d.duree_minutes % 60:02d}",
                        "Tarif (F CFA/h)": d.tarif_horaire,
                        "Source": _LABEL_SOURCE_TARIF.get(d.source_tarif, d.source_tarif),
                        "Personnalisé": "Oui" if d.tarif_exceptionnel else "",
                        "Montant (F CFA)": d.montant,
                    }
                    for d in details
                ]
            ),
            ["Montant (F CFA)"],
            "Élève",
        ),
        hide_index=True,
    )


def _enregistrer_et_exporter(conn, resultat, annee, mois):
    st.subheader("6. Enregistrer et exporter")
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Enregistrer ce mois dans l'historique"):
            repo.enregistrer_calcul_mensuel(conn, annee, mois, resultat)
            repo.effacer_brouillon(conn)
            st.success(f"Mois {mois:02d}/{annee} enregistré dans l'historique.")

    with col2:
        tampon = io.BytesIO()
        exporter_resultats(resultat, tampon)
        st.download_button(
            "Télécharger l'export .xlsx",
            data=tampon.getvalue(),
            file_name=f"paie_{annee}_{mois:02d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


def afficher(conn):
    st.header("Calcul du mois")

    # Le file_uploader perd son contenu si l'utilisateur change d'écran puis
    # revient ici (comportement standard de Streamlit) : on ne doit pas pour
    # autant faire disparaître un résultat déjà calculé, qui reste en session.
    annuaire, seances = _importer_fichiers()

    if annuaire is not None:
        annee, mois = _confirmer_periode(seances)
        if st.button("Calculer", type="primary"):
            resultat_calcule, report_effectue = _calculer(conn, annuaire, seances, annee, mois)
            st.session_state["resultat_calcul"] = resultat_calcule
            st.session_state["periode_calcul"] = (annee, mois)
            st.session_state["versement_15_reporte"] = report_effectue
            repo.sauvegarder_brouillon(conn, annee, mois, resultat_calcule)

    # Un rafraîchissement du navigateur (F5) ouvre une toute nouvelle session
    # Streamlit et vide st.session_state : on retrouve le dernier calcul non
    # enregistré en le relisant depuis la DB plutôt que de le perdre.
    if "resultat_calcul" not in st.session_state:
        brouillon = repo.charger_brouillon(conn)
        if brouillon is not None:
            annee_b, mois_b, date_maj, resultat_b = brouillon
            st.session_state["resultat_calcul"] = resultat_b
            st.session_state["periode_calcul"] = (annee_b, mois_b)
            st.info(
                f"Reprise du dernier calcul non enregistré : "
                f"{NOMS_MOIS[mois_b]} {annee_b} (calculé le {date_maj}). "
                f"Cliquez sur « Enregistrer » ci-dessous pour le conserver "
                f"dans l'historique, ou réimportez des fichiers pour le remplacer."
            )

    resultat = st.session_state.get("resultat_calcul")
    if resultat is None:
        return

    annee, mois = st.session_state["periode_calcul"]
    _afficher_resultats(resultat, st.session_state.get("versement_15_reporte", False))
    _afficher_a_verifier(resultat)
    _afficher_detail_par_personne(resultat)
    _enregistrer_et_exporter(conn, resultat, annee, mois)

    # Toute édition faite plus haut (case « Versé ») doit elle aussi rester
    # récupérable après un rafraîchissement, d'où la resauvegarde ici.
    repo.sauvegarder_brouillon(conn, annee, mois, resultat)
