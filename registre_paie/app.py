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


def main():
    st.set_page_config(page_title="Registre de paie — MA-AU Academy", page_icon="🎓", layout="wide")
    st.logo(str(LOGO_PATH), size="large")
    # Couleur des titres alignée sur --edubin-heading-color du site (vert foncé) ;
    # le reste du thème (fonds, boutons) est piloté par .streamlit/config.toml.
    st.markdown(
        "<style>h1, h2, h3 { color: #004f27; }</style>",
        unsafe_allow_html=True,
    )
    conn = _connexion()

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
