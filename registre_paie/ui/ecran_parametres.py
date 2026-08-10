"""Écran de configuration (§5, §7-A) : barème par catégorie, personnes exclues.

Aucune valeur n'est codée en dur ici (§11) : tout vient de/repart vers
db/repository.py, qui fait autorité sur l'état courant.
"""

import streamlit as st

import db.repository as repo


def _afficher_bareme(conn):
    st.subheader("Barème (F CFA / heure)")
    st.caption("Modifiable ici, jamais codé en dur — s'applique au prochain calcul (§5).")

    bareme = repo.lire_bareme(conn)
    for categorie in sorted(bareme):
        nouvelle_valeur = st.number_input(
            categorie, min_value=0, value=int(bareme[categorie]), step=100, key=f"tarif_{categorie}"
        )
        if nouvelle_valeur != bareme[categorie]:
            repo.definir_tarif(conn, categorie, nouvelle_valeur)


def _afficher_exclusions(conn):
    st.subheader("Personnes exclues du paiement à l'heure (§7-A)")
    st.caption(
        "Une personne cochée ici n'est jamais payée, même si elle apparaît "
        "comme intervenant sur des séances réelles ce mois-ci."
    )

    noms_annuaire = {p.nom for p in st.session_state.get("dernier_annuaire", [])}
    noms_deja_configures = repo.lire_exclusions(conn)
    tous_les_noms = sorted(noms_annuaire | noms_deja_configures)

    if not tous_les_noms:
        st.info("Importez d'abord une Feuille de temps (écran « Calcul du mois ») pour voir la liste des personnes.")
        return

    for nom in tous_les_noms:
        exclu_actuel = nom in noms_deja_configures
        nouvel_etat = st.checkbox(nom, value=exclu_actuel, key=f"exclu_{nom}")
        if nouvel_etat != exclu_actuel:
            repo.definir_exclusion(conn, nom, nouvel_etat)


def afficher(conn):
    st.header("Paramètres")
    _afficher_bareme(conn)
    _afficher_exclusions(conn)
