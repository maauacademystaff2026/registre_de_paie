"""Accès SQLite (§8.3, §11) : seule couche à connaître le schéma de la DB.

Ne contient aucune règle de tarification — elle reçoit des structures déjà
calculées par `core/` (ResultatCalculMensuel) et se contente de les persister
ou de les relire. Les valeurs modifiables par l'utilisateur (barème, exclusions,
versements du 15) vivent ici, jamais codées en dur dans `core/` ou `ui/`.
"""

import datetime as _dt
import pickle
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from core.models import ResultatCalculMensuel
from core.tarification import BAREME_PAR_DEFAUT

_SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")


def connecter(chemin: str) -> sqlite3.Connection:
    """Ouvre (ou crée) la base et s'assure que le schéma existe. Le barème est
    initialisé avec les valeurs par défaut de core/tarification.py uniquement
    si la table est vide (premier lancement) — ensuite la DB fait autorité.

    `check_same_thread=False` : Streamlit ré-exécute le script sur des threads
    du pool à chaque interaction, et `@st.cache_resource` garde une seule
    connexion partagée entre ces reruns — sqlite3 refuse ça par défaut
    (`SQLite objects created in a thread can only be used in that same
    thread`). Sans concurrence réelle (application locale mono-utilisateur,
    §11), c'est le contournement standard, pas un risque de corruption."""
    conn = sqlite3.connect(chemin, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA_SQL)
    _migrer_schema(conn)
    _initialiser_bareme_si_vide(conn)
    conn.commit()
    return conn


def _migrer_schema(conn: sqlite3.Connection) -> None:
    """`CREATE TABLE IF NOT EXISTS` (schema.sql) ne retrofit pas de colonne sur une
    table déjà existante d'une DB déployée avant l'ajout des exceptions V2 : on
    l'ajoute ici si absente, sans jamais toucher aux lignes déjà enregistrées."""
    colonnes_details = {ligne["name"] for ligne in conn.execute("PRAGMA table_info(details_seances)")}
    if "tarif_exceptionnel" not in colonnes_details:
        conn.execute(
            "ALTER TABLE details_seances ADD COLUMN tarif_exceptionnel INTEGER NOT NULL DEFAULT 0"
        )

    colonnes_resultats = {ligne["name"] for ligne in conn.execute("PRAGMA table_info(resultats_personne)")}
    if "versement_15_verse" not in colonnes_resultats:
        conn.execute(
            "ALTER TABLE resultats_personne ADD COLUMN versement_15_verse INTEGER NOT NULL DEFAULT 0"
        )


def _initialiser_bareme_si_vide(conn: sqlite3.Connection) -> None:
    (nb,) = conn.execute("SELECT COUNT(*) FROM parametres_bareme").fetchone()
    if nb == 0:
        conn.executemany(
            "INSERT INTO parametres_bareme (categorie, tarif_horaire) VALUES (?, ?)",
            BAREME_PAR_DEFAUT.items(),
        )


# --- Barème (§5) ------------------------------------------------------------


def lire_bareme(conn: sqlite3.Connection) -> dict[str, float]:
    lignes = conn.execute("SELECT categorie, tarif_horaire FROM parametres_bareme").fetchall()
    return {ligne["categorie"]: ligne["tarif_horaire"] for ligne in lignes}


def definir_tarif(conn: sqlite3.Connection, categorie: str, tarif_horaire: float) -> None:
    conn.execute(
        "UPDATE parametres_bareme SET tarif_horaire = ? WHERE categorie = ?",
        (tarif_horaire, categorie),
    )
    conn.commit()


# --- Exclusions par personne (§7-A) -----------------------------------------


def lire_exclusions(conn: sqlite3.Connection) -> set[str]:
    lignes = conn.execute("SELECT nom FROM personnes WHERE exclu = 1").fetchall()
    return {ligne["nom"] for ligne in lignes}


def definir_exclusion(conn: sqlite3.Connection, nom: str, exclu: bool) -> None:
    conn.execute(
        "INSERT INTO personnes (nom, exclu) VALUES (?, ?) "
        "ON CONFLICT(nom) DO UPDATE SET exclu = excluded.exclu",
        (nom, int(exclu)),
    )
    conn.commit()


# --- Exceptions de tarification V2 (§7-C, §10) ------------------------------


def lire_exceptions_enseignant(conn: sqlite3.Connection) -> dict[tuple[str, str], float]:
    lignes = conn.execute(
        "SELECT enseignant, categorie, tarif_horaire FROM exceptions_enseignant"
    ).fetchall()
    return {(l["enseignant"], l["categorie"]): l["tarif_horaire"] for l in lignes}


def definir_exception_enseignant(
    conn: sqlite3.Connection, enseignant: str, categorie: str, tarif_horaire: float
) -> None:
    conn.execute(
        "INSERT INTO exceptions_enseignant (enseignant, categorie, tarif_horaire) "
        "VALUES (?, ?, ?) ON CONFLICT(enseignant, categorie) "
        "DO UPDATE SET tarif_horaire = excluded.tarif_horaire",
        (enseignant, categorie, tarif_horaire),
    )
    conn.commit()


def supprimer_exception_enseignant(conn: sqlite3.Connection, enseignant: str, categorie: str) -> None:
    conn.execute(
        "DELETE FROM exceptions_enseignant WHERE enseignant = ? AND categorie = ?",
        (enseignant, categorie),
    )
    conn.commit()


def lire_exceptions_eleve(conn: sqlite3.Connection) -> dict[tuple[str, str], float]:
    lignes = conn.execute(
        "SELECT eleve_nom, eleve_prenom, tarif_horaire FROM exceptions_eleve"
    ).fetchall()
    return {(l["eleve_nom"], l["eleve_prenom"]): l["tarif_horaire"] for l in lignes}


def definir_exception_eleve(
    conn: sqlite3.Connection, eleve_nom: str, eleve_prenom: str, tarif_horaire: float
) -> None:
    conn.execute(
        "INSERT INTO exceptions_eleve (eleve_nom, eleve_prenom, tarif_horaire) "
        "VALUES (?, ?, ?) ON CONFLICT(eleve_nom, eleve_prenom) "
        "DO UPDATE SET tarif_horaire = excluded.tarif_horaire",
        (eleve_nom, eleve_prenom, tarif_horaire),
    )
    conn.commit()


def supprimer_exception_eleve(conn: sqlite3.Connection, eleve_nom: str, eleve_prenom: str) -> None:
    conn.execute(
        "DELETE FROM exceptions_eleve WHERE eleve_nom = ? AND eleve_prenom = ?",
        (eleve_nom, eleve_prenom),
    )
    conn.commit()


# --- Calculs mensuels (§8.3) -------------------------------------------------


@dataclass
class ResultatPersonneHistorique:
    id: int
    nom: str
    exclu: bool
    heures_payees_minutes: int
    montant_brut: int
    versement_15: float
    versement_15_verse: bool
    net_a_payer: float


@dataclass
class CalculMensuelHistorique:
    id: int
    annee: int
    mois: int
    date_calcul: str
    resultats: list[ResultatPersonneHistorique] = field(default_factory=list)
    nb_seances_non_resolues: int = 0
    nb_intervenants_inconnus: int = 0


def enregistrer_calcul_mensuel(
    conn: sqlite3.Connection, annee: int, mois: int, resultat: ResultatCalculMensuel
) -> int:
    """Enregistre un mois calculé. Si (année, mois) existe déjà, l'ancien
    enregistrement est remplacé en entier (§8.3 : recalcul si fichiers
    réimportés) — jamais de fusion partielle."""
    with conn:
        conn.execute(
            "DELETE FROM calculs_mensuels WHERE annee = ? AND mois = ?", (annee, mois)
        )
        curseur = conn.execute(
            "INSERT INTO calculs_mensuels (annee, mois, date_calcul) VALUES (?, ?, ?)",
            (annee, mois, _dt.datetime.now().isoformat(timespec="seconds")),
        )
        calcul_id = curseur.lastrowid

        for nom, resultat_personne in resultat.resultats_par_personne.items():
            curseur = conn.execute(
                "INSERT INTO resultats_personne "
                "(calcul_id, nom, exclu, heures_payees_minutes, montant_brut, versement_15, "
                "versement_15_verse, net_a_payer) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    calcul_id,
                    nom,
                    int(resultat_personne.exclu),
                    resultat_personne.heures_payees_minutes,
                    resultat_personne.montant_brut,
                    resultat_personne.versement_15,
                    int(resultat_personne.versement_15_verse),
                    resultat_personne.net_a_payer,
                ),
            )
            resultat_personne_id = curseur.lastrowid

            conn.executemany(
                "INSERT INTO details_seances "
                "(resultat_personne_id, eleve_nom, eleve_prenom, date, classe, niveau_resolu, "
                "matiere, duree_minutes, categorie_tarif, source_tarif, tarif_horaire, montant, "
                "tarif_exceptionnel) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    (
                        resultat_personne_id,
                        d.seance.eleve_nom,
                        d.seance.eleve_prenom,
                        d.seance.date,
                        d.seance.classe,
                        d.niveau_resolu,
                        d.seance.matiere,
                        d.duree_minutes,
                        d.categorie_tarif,
                        d.source_tarif,
                        d.tarif_horaire,
                        d.montant,
                        int(d.tarif_exceptionnel),
                    )
                    for d in resultat_personne.details
                ),
            )

        conn.executemany(
            "INSERT INTO seances_non_resolues "
            "(calcul_id, enseignant, eleve_nom, eleve_prenom, date, classe, niveau_de_classe, "
            "matiere, duree_minutes, raison) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    calcul_id,
                    sr.seance.enseignant,
                    sr.seance.eleve_nom,
                    sr.seance.eleve_prenom,
                    sr.seance.date,
                    sr.seance.classe,
                    sr.seance.niveau_de_classe,
                    sr.seance.matiere,
                    sr.seance.duree_minutes,
                    sr.raison,
                )
                for sr in resultat.seances_non_resolues
            ),
        )

        conn.executemany(
            "INSERT INTO intervenants_inconnus (calcul_id, nom, heures_minutes, nb_seances) "
            "VALUES (?, ?, ?, ?)",
            (
                (
                    calcul_id,
                    ii.nom,
                    sum(s.duree_minutes for s in ii.seances),
                    len(ii.seances),
                )
                for ii in resultat.intervenants_inconnus
            ),
        )

    return calcul_id


def lister_mois(conn: sqlite3.Connection) -> list[tuple[int, int, str]]:
    """(année, mois, date_calcul), du plus récent au plus ancien."""
    lignes = conn.execute(
        "SELECT annee, mois, date_calcul FROM calculs_mensuels ORDER BY annee DESC, mois DESC"
    ).fetchall()
    return [(l["annee"], l["mois"], l["date_calcul"]) for l in lignes]


def charger_mois(conn: sqlite3.Connection, annee: int, mois: int) -> CalculMensuelHistorique | None:
    """Lecture seule d'un mois déjà calculé (§8.3). Le détail par séance
    (§8.2) se charge à part via `charger_details_seances`, sur demande
    (dépliable), pour ne pas tout recharger en mémoire d'un coup."""
    ligne_calcul = conn.execute(
        "SELECT id, annee, mois, date_calcul FROM calculs_mensuels WHERE annee = ? AND mois = ?",
        (annee, mois),
    ).fetchone()
    if ligne_calcul is None:
        return None

    lignes_resultats = conn.execute(
        "SELECT id, nom, exclu, heures_payees_minutes, montant_brut, versement_15, "
        "versement_15_verse, net_a_payer "
        "FROM resultats_personne WHERE calcul_id = ? ORDER BY nom",
        (ligne_calcul["id"],),
    ).fetchall()

    (nb_non_resolues,) = conn.execute(
        "SELECT COUNT(*) FROM seances_non_resolues WHERE calcul_id = ?", (ligne_calcul["id"],)
    ).fetchone()
    (nb_inconnus,) = conn.execute(
        "SELECT COUNT(*) FROM intervenants_inconnus WHERE calcul_id = ?", (ligne_calcul["id"],)
    ).fetchone()

    return CalculMensuelHistorique(
        id=ligne_calcul["id"],
        annee=ligne_calcul["annee"],
        mois=ligne_calcul["mois"],
        date_calcul=ligne_calcul["date_calcul"],
        resultats=[
            ResultatPersonneHistorique(
                id=l["id"],
                nom=l["nom"],
                exclu=bool(l["exclu"]),
                heures_payees_minutes=l["heures_payees_minutes"],
                montant_brut=l["montant_brut"],
                versement_15=l["versement_15"],
                versement_15_verse=bool(l["versement_15_verse"]),
                net_a_payer=l["net_a_payer"],
            )
            for l in lignes_resultats
        ],
        nb_seances_non_resolues=nb_non_resolues,
        nb_intervenants_inconnus=nb_inconnus,
    )


def reporter_versement_15_verse(
    conn: sqlite3.Connection, annee: int, mois: int, resultat: ResultatCalculMensuel
) -> bool:
    """Si (année, mois) a déjà un enregistrement, reprend le statut Versé de
    chaque personne présente dans les deux calculs, en mutant `resultat` sur
    place. Ce fait n'est dérivable ni des fichiers importés ni d'aucun réglage
    global (barème, exclusions, exceptions) : un réimport recalcule tout le
    reste à raison, mais ne doit jamais réinitialiser silencieusement ce fait-
    là à "non versé", au risque de faire disparaître une avance déjà
    confirmée payée à quelqu'un. Renvoie True si un report a eu lieu (pour
    affichage à l'écran), False si (année, mois) n'existait pas encore."""
    mois_existant = charger_mois(conn, annee, mois)
    if mois_existant is None:
        return False
    verse_par_nom = {r.nom: r.versement_15_verse for r in mois_existant.resultats}
    for nom, resultat_personne in resultat.resultats_par_personne.items():
        if nom in verse_par_nom:
            resultat_personne.versement_15_verse = verse_par_nom[nom]
    return True


def charger_details_seances(conn: sqlite3.Connection, resultat_personne_id: int) -> list[sqlite3.Row]:
    """Détail par séance d'une personne pour un mois donné (§8.2, audit)."""
    return conn.execute(
        "SELECT eleve_nom, eleve_prenom, date, classe, niveau_resolu, matiere, "
        "duree_minutes, categorie_tarif, source_tarif, tarif_horaire, montant, "
        "tarif_exceptionnel "
        "FROM details_seances WHERE resultat_personne_id = ? ORDER BY date",
        (resultat_personne_id,),
    ).fetchall()


# --- Brouillon : calcul en cours, pas encore enregistré ---------------------


def sauvegarder_brouillon(
    conn: sqlite3.Connection, annee: int, mois: int, resultat: ResultatCalculMensuel
) -> None:
    """Filet de sécurité contre le rafraîchissement du navigateur (qui crée
    une nouvelle session Streamlit et vide `st.session_state`) : persiste le
    calcul affiché à l'écran, même s'il n'a pas encore été "Enregistré"."""
    conn.execute(
        "INSERT INTO brouillon_calcul (id, annee, mois, donnees, date_maj) VALUES (1, ?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET annee = excluded.annee, mois = excluded.mois, "
        "donnees = excluded.donnees, date_maj = excluded.date_maj",
        (annee, mois, pickle.dumps(resultat), _dt.datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()


def charger_brouillon(
    conn: sqlite3.Connection,
) -> tuple[int, int, str, ResultatCalculMensuel] | None:
    """(année, mois, date_maj, résultat) du calcul en cours, ou None s'il n'y en a pas."""
    ligne = conn.execute(
        "SELECT annee, mois, donnees, date_maj FROM brouillon_calcul WHERE id = 1"
    ).fetchone()
    if ligne is None:
        return None
    return ligne["annee"], ligne["mois"], ligne["date_maj"], pickle.loads(ligne["donnees"])


def effacer_brouillon(conn: sqlite3.Connection) -> None:
    """Appelé après un "Enregistrer" réussi : le calcul vit désormais dans
    l'historique, le brouillon n'a plus de raison d'être proposé au retour."""
    conn.execute("DELETE FROM brouillon_calcul WHERE id = 1")
    conn.commit()


def definir_versement_15_verse(conn: sqlite3.Connection, resultat_personne_id: int, verse: bool) -> None:
    """Confirme ou corrige, pour un mois déjà enregistré, si l'avance calculée
    (versement_15) a réellement été remise à la personne, et recalcule le net
    à payer en conséquence (§6, mis à jour). Contrairement à l'ancien
    `mettre_a_jour_versement_15` qu'elle remplace, le MONTANT lui-même n'est
    jamais retapé ici — seul ce fait (versé ou non) est corrigeable après coup,
    puisqu'il peut n'être confirmé qu'après l'enregistrement du mois."""
    conn.execute(
        "UPDATE resultats_personne SET versement_15_verse = ?, "
        "net_a_payer = CASE WHEN ? THEN montant_brut - versement_15 ELSE montant_brut END "
        "WHERE id = ?",
        (int(verse), int(verse), resultat_personne_id),
    )
    conn.commit()
