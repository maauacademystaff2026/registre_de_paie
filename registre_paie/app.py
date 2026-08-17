"""Point d'entrée Streamlit (§11) : `streamlit run app.py`, tout s'exécute en
local sur la machine de l'utilisateur — aucun serveur distant."""

from pathlib import Path

import streamlit as st

import db.repository as repo
from ui import ecran_calcul, ecran_historique, ecran_parametres, ecran_tableau_bord

DB_PATH = Path(__file__).parent / "registre_paie.db"
LOGO_PATH = Path(__file__).parent / "assets" / "logo.png"


@st.cache_resource
def _connexion():
    return repo.connecter(str(DB_PATH))


def _verifier_mot_de_passe() -> bool:
    """Page de connexion (mot de passe partagé) : la vraie valeur vit dans
    st.secrets (registre_paie/.streamlit/secrets.toml en local, Secrets de
    l'app sur Streamlit Cloud) — jamais codée en dur ni committée."""
    if st.session_state.get("authentifie"):
        return True

    if "mot_de_passe" not in st.secrets:
        st.error(
            "Aucun mot de passe configuré (`mot_de_passe` absent des secrets). "
            "Voir registre_paie/.streamlit/secrets.toml en local, ou Paramètres "
            "de l'application → Secrets sur Streamlit Cloud."
        )
        return False

    _, col_centre, _ = st.columns([1, 1.1, 1])
    with col_centre:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.image(str(LOGO_PATH), width=140)
            st.markdown(
                "<h2 style='text-align:center; color:#004f27; margin:0.5rem 0 0 0;'>Registre de paie</h2>"
                "<p style='text-align:center; color:#666; margin:0 0 1rem 0;'>MA-AU Academy</p>",
                unsafe_allow_html=True,
            )
            with st.form("connexion"):
                mot_de_passe_saisi = st.text_input("Mot de passe", type="password")
                connecte = st.form_submit_button(
                    "Se connecter", type="primary", use_container_width=True
                )
            if connecte:
                if mot_de_passe_saisi == st.secrets["mot_de_passe"]:
                    st.session_state["authentifie"] = True
                    st.rerun()
                else:
                    st.error("Mot de passe incorrect.")
    return False


def main():
    st.set_page_config(page_title="Registre de paie — MA-AU Academy", page_icon="🎓", layout="wide")
    st.logo(str(LOGO_PATH), size="large")
    # Couleur des titres alignée sur --edubin-heading-color du site (vert foncé) ;
    # le reste du thème (fonds, boutons) est piloté par .streamlit/config.toml.
    st.markdown(
        "<style>h1, h2, h3 { color: #004f27; }</style>",
        unsafe_allow_html=True,
    )

    if not _verifier_mot_de_passe():
        return

    conn = _connexion()

    if st.sidebar.button("Se déconnecter"):
        st.session_state.pop("authentifie", None)
        st.rerun()

    ecran = st.sidebar.radio(
        "Navigation", ["Tableau de bord", "Calcul du mois", "Historique", "Paramètres"]
    )

    if ecran == "Tableau de bord":
        ecran_tableau_bord.afficher(conn)
    elif ecran == "Calcul du mois":
        ecran_calcul.afficher(conn)
    elif ecran == "Historique":
        ecran_historique.afficher(conn)
    else:
        ecran_parametres.afficher(conn)


if __name__ == "__main__":
    main()
