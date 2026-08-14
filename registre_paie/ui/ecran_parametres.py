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


def _afficher_exceptions_enseignant(conn):
    st.subheader("Tarif personnalisé par enseignant (§7-C)")
    st.caption(
        "Remplace le tarif du barème pour cette catégorie, uniquement pour cet "
        "enseignant. S'il enseigne aussi d'autres catégories, elles restent au "
        "tarif standard sauf exception ajoutée séparément pour chacune."
    )

    exceptions = repo.lire_exceptions_enseignant(conn)
    bareme = repo.lire_bareme(conn)

    for (enseignant, categorie), tarif in sorted(exceptions.items()):
        col1, col2, col3 = st.columns([3, 2, 1])
        col1.markdown(f"**{enseignant}** — {categorie}")
        nouveau_tarif = col2.number_input(
            "Tarif (F CFA/h)",
            min_value=0,
            value=int(tarif),
            step=100,
            key=f"exc_ens_{enseignant}_{categorie}",
            label_visibility="collapsed",
        )
        if nouveau_tarif != tarif:
            repo.definir_exception_enseignant(conn, enseignant, categorie, nouveau_tarif)
        if col3.button("Retirer", key=f"del_ens_{enseignant}_{categorie}"):
            repo.supprimer_exception_enseignant(conn, enseignant, categorie)
            st.rerun()

    st.markdown("**Ajouter une exception**")
    noms_annuaire = sorted({p.nom for p in st.session_state.get("dernier_annuaire", [])})
    if not noms_annuaire:
        st.info("Importez d'abord une Feuille de temps (écran « Calcul du mois ») pour choisir un enseignant.")
        return

    col1, col2, col3 = st.columns([3, 2, 1])
    enseignant_choisi = col1.selectbox("Enseignant", noms_annuaire, key="nouvel_exc_ens_nom")
    categorie_choisie = col2.selectbox("Catégorie", sorted(bareme), key="nouvel_exc_ens_categorie")
    tarif_saisi = col3.number_input(
        "Tarif (F CFA/h)", min_value=0, value=int(bareme[categorie_choisie]), step=100, key="nouvel_exc_ens_tarif"
    )
    if st.button("Ajouter l'exception enseignant"):
        repo.definir_exception_enseignant(conn, enseignant_choisi, categorie_choisie, tarif_saisi)
        st.rerun()


def _afficher_exceptions_eleve(conn):
    st.subheader("Tarif forcé par élève (§10)")
    st.caption(
        "S'applique à toutes les séances de cet élève, quel que soit la matière "
        "ou le niveau — l'emporte sur un tarif enseignant si les deux s'appliquent."
    )

    exceptions = repo.lire_exceptions_eleve(conn)

    for (nom, prenom), tarif in sorted(exceptions.items()):
        col1, col2, col3 = st.columns([3, 2, 1])
        col1.markdown(f"**{nom} {prenom}**")
        nouveau_tarif = col2.number_input(
            "Tarif (F CFA/h)",
            min_value=0,
            value=int(tarif),
            step=100,
            key=f"exc_eleve_{nom}_{prenom}",
            label_visibility="collapsed",
        )
        if nouveau_tarif != tarif:
            repo.definir_exception_eleve(conn, nom, prenom, nouveau_tarif)
        if col3.button("Retirer", key=f"del_eleve_{nom}_{prenom}"):
            repo.supprimer_exception_eleve(conn, nom, prenom)
            st.rerun()

    st.markdown("**Ajouter une exception**")
    col1, col2, col3 = st.columns([2, 2, 2])
    nom_saisi = col1.text_input("Nom", key="nouvel_exc_eleve_nom")
    prenom_saisi = col2.text_input("Prénom", key="nouvel_exc_eleve_prenom")
    tarif_saisi = col3.number_input("Tarif (F CFA/h)", min_value=0, value=2000, step=100, key="nouvel_exc_eleve_tarif")
    if st.button("Ajouter l'exception élève"):
        if not nom_saisi.strip() or not prenom_saisi.strip():
            st.warning("Nom et prénom sont requis.")
        else:
            repo.definir_exception_eleve(conn, nom_saisi.strip(), prenom_saisi.strip(), tarif_saisi)
            st.rerun()


def afficher(conn):
    st.header("Paramètres")
    _afficher_bareme(conn)
    _afficher_exclusions(conn)
    st.subheader("Exceptions de tarification (V2)")
    _afficher_exceptions_enseignant(conn)
    _afficher_exceptions_eleve(conn)
