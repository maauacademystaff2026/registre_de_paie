"""Script ponctuel : génère la documentation PDF du calcul de paie.
Pas un module de l'application — à exécuter une fois, pas testé/maintenu."""

from fpdf import FPDF

FONT_DIR = "C:/Windows/Fonts"
BLEU = (31, 73, 125)
GRIS = (90, 90, 90)
FOND_ENTETE = (31, 73, 125)
FOND_LIGNE_ALT = (240, 243, 248)


class DocPaie(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Arial", "I", 8)
        self.set_text_color(*GRIS)
        self.cell(0, 8, "Registre de paie — Documentation du calcul des salaires", align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*GRIS)
        self.line(10, 18, 200, 18)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 7)
        self.set_text_color(*GRIS)
        self.cell(0, 10, "MA-AU Academy — document généré automatiquement, à revalider avec chaque évolution du barème.", align="C")


def titre_section(pdf, numero, texte):
    pdf.ln(4)
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(*BLEU)
    pdf.cell(0, 10, f"{numero}. {texte}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*BLEU)
    pdf.set_line_width(0.6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)


def sous_titre(pdf, texte):
    pdf.ln(2)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(*BLEU)
    pdf.cell(0, 8, texte, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def paragraphe(pdf, texte, taille=10.5):
    pdf.set_font("Arial", "", taille)
    pdf.multi_cell(0, 6, texte, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def puce(pdf, texte, gras_prefixe=None):
    pdf.set_font("Arial", "", 10.5)
    x0 = pdf.get_x()
    pdf.cell(6, 6, "-")
    if gras_prefixe:
        pdf.set_font("Arial", "B", 10.5)
        largeur_prefixe = pdf.get_string_width(gras_prefixe + " ")
        pdf.cell(largeur_prefixe, 6, gras_prefixe + " ")
        pdf.set_font("Arial", "", 10.5)
        pdf.multi_cell(0, 6, texte, new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.multi_cell(0, 6, texte, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(x0)


def encadre_exemple(pdf, titre, lignes):
    pdf.ln(2)
    pdf.set_fill_color(*FOND_LIGNE_ALT)
    pdf.set_font("Arial", "B", 10.5)
    pdf.set_text_color(*BLEU)
    pdf.cell(0, 8, titre, new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    for ligne in lignes:
        pdf.set_fill_color(*FOND_LIGNE_ALT)
        pdf.multi_cell(0, 6, ligne, fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def tableau(pdf, entetes, lignes, largeurs):
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(*FOND_ENTETE)
    pdf.set_text_color(255, 255, 255)
    for entete, largeur in zip(entetes, largeurs):
        pdf.cell(largeur, 8, entete, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(0, 0, 0)
    for i, ligne in enumerate(lignes):
        pdf.set_fill_color(*(FOND_LIGNE_ALT if i % 2 else (255, 255, 255)))
        for valeur, largeur in zip(ligne, largeurs):
            pdf.cell(largeur, 8, str(valeur), border=1, align="C", fill=True)
        pdf.ln()
    pdf.ln(3)


pdf = DocPaie()
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_font("Arial", "", f"{FONT_DIR}/arial.ttf")
pdf.add_font("Arial", "B", f"{FONT_DIR}/arialbd.ttf")
pdf.add_font("Arial", "I", f"{FONT_DIR}/ariali.ttf")

# --- Page de titre ---------------------------------------------------------
pdf.add_page()
pdf.ln(30)
pdf.set_font("Arial", "B", 24)
pdf.set_text_color(*BLEU)
pdf.multi_cell(0, 12, "Registre de paie", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Arial", "", 16)
pdf.set_text_color(*GRIS)
pdf.multi_cell(0, 10, "Documentation du calcul des salaires", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(10)
pdf.set_font("Arial", "", 11)
pdf.set_text_color(0, 0, 0)
texte_intro = (
    "Ce document explique, en langage simple, où vivent les calculs dans "
    "l'application, comment le salaire de chaque séance est déterminé, et "
    "comment le total et le net à payer de chaque personne sont obtenus.\n\n"
    "Version des règles : 4 août 2026 (règles A à E du cahier des charges "
    "confirmées, y compris la correction sur les séances où l'élève est "
    "absent — voir section 3)."
)
pdf.multi_cell(0, 7, texte_intro, align="C", new_x="LMARGIN", new_y="NEXT")

# --- 1. Où vivent les calculs ----------------------------------------------
pdf.add_page()
titre_section(pdf, 1, "Où vivent les calculs dans l'application")

paragraphe(
    pdf,
    "L'application est organisée en dossiers, chacun avec un rôle précis. "
    "Aucun montant n'est jamais calculé « à la main » dans l'écran que vous "
    "voyez : l'écran ne fait qu'afficher ce que ces fichiers ont calculé."
)

tableau(
    pdf,
    ["Fichier", "Rôle"],
    [
        ["core/excel_import.py", "Lit les 2 fichiers Excel et les nettoie"],
        ["core/models.py", "Définit une séance « payable » (§3)"],
        ["core/tarification.py", "Calcule le tarif d'UNE séance"],
        ["core/agregation.py", "Additionne les séances par personne"],
        ["db/ (registre_paie.db)", "Barème, exclusions, historique"],
        ["export/xlsx_export.py", "Génère le fichier Excel de résultats"],
        ["ui/ + app.py", "L'écran affiché dans le navigateur"],
    ],
    [65, 120],
)

paragraphe(
    pdf,
    "Le barème (les 5 tarifs horaires) n'est écrit nulle part « en dur » "
    "dans le code : il est stocké dans le fichier registre_paie.db et "
    "modifiable depuis l'écran « Paramètres » de l'application. Un "
    "changement de tarif ne s'applique qu'aux calculs faits après la "
    "modification — les mois déjà enregistrés dans l'historique ne bougent pas."
)

# --- 2. Comment le tarif d'une séance est calculé ---------------------------
pdf.add_page()
titre_section(pdf, 2, "Comment le tarif d'une séance est calculé")

sous_titre(pdf, "Étape 1 — La séance est-elle payable ?")
puce(pdf, "Toutes les séances sont payables, y compris quand l'élève est absent — le professeur s'est présenté, ce n'est pas de sa faute.", "Règle générale :")
puce(pdf, "les 30 dernières minutes ne réduisent pas le salaire de l'enseignant.", "Retard de l'élève :")
puce(pdf, "aucun salaire pour cette séance.", "Absence du professeur lui-même :")

sous_titre(pdf, "Étape 2 — Quel tarif horaire s'applique ?")
paragraphe(
    pdf,
    "Deux cas, toujours dans cet ordre :\n"
    "1. Si la matière est UNIQUEMENT une langue (Anglais, Français ou "
    "Espagnol tout seul — pas « Maths/Français ») : tarif langue, quel que "
    "soit le niveau de l'élève.\n"
    "2. Sinon : le tarif dépend du niveau de l'élève, selon le barème ci-dessous."
)

tableau(
    pdf,
    ["Catégorie", "Niveaux inclus", "Tarif (F CFA / heure)"],
    [
        ["Langue seule", "tous niveaux", "2 000"],
        ["Primaire", "CP, CE1, CE2, CM1, CM2", "1 500"],
        ["Collège", "6EME, 5EME, 4EME, 3EME", "2 000"],
        ["Lycée", "2NDE, 1ERE, TLE", "2 500"],
        ["BTS", "BTS", "3 000"],
    ],
    [50, 90, 50],
)

paragraphe(
    pdf,
    "Ces 5 tarifs sont modifiables dans l'écran « Paramètres » — les valeurs "
    "ci-dessus sont celles utilisées par défaut.\n\n"
    "Si le niveau de l'élève n'est identifiable ni par la colonne « Niveau "
    "de classe » ni par la colonne « Classe », la séance n'est jamais "
    "payée à 0 F silencieusement : elle apparaît dans la zone « à vérifier » "
    "de l'application pour un traitement manuel."
)

sous_titre(pdf, "Étape 3 — Montant de la séance")
paragraphe(pdf, "Montant de la séance = durée de la séance (en heures) × tarif horaire déterminé à l'étape 2.")

encadre_exemple(
    pdf,
    "Exemple réel — ANGOULA CLAUDE LEVI, juillet 2026",
    [
        "15 séances d'Anglais avec le même élève (KOKAP Joakim-Nicolas), 30 minutes chacune.",
        "14 séances « Présentiel » + 1 séance « Absent » (élève absent, professeur présent) = 15 séances payables.",
        "Matière = Anglais seul -> tarif langue = 2 000 F CFA / heure, quel que soit le niveau (ici CP).",
        "Durée totale = 15 x 30 min = 450 min = 7,50 heures.",
        "Montant = 7,50 x 2 000 = 15 000 F CFA.",
    ],
)

# --- 3. Comment le total et le net à payer sont calculés --------------------
pdf.add_page()
titre_section(pdf, 3, "Comment le total et le net à payer sont calculés")

sous_titre(pdf, "Montant brut d'une personne")
paragraphe(
    pdf,
    "Le montant brut d'une personne est la somme des montants exacts de "
    "TOUTES ses séances payables du mois (calculés comme à la section 2), "
    "puis arrondi UNE SEULE FOIS à la fin — jamais séance par séance."
)

encadre_exemple(
    pdf,
    "Pourquoi arrondir seulement à la fin ?",
    [
        "Deux séances de 5 minutes à 2 000 F/heure (Collège) : chacune vaut exactement 166,666... F.",
        "Arrondi séance par séance : 167 + 167 = 334 F.",
        "Arrondi une seule fois sur le total (méthode retenue) : 166,67 + 166,67 = 333,33... -> 333 F.",
        "Les deux méthodes donnent un résultat différent sur de gros volumes de séances : arrondir une seule "
        "fois à la fin minimise les écarts cumulés sur l'ensemble du mois.",
    ],
)

sous_titre(pdf, "Net à payer")
paragraphe(
    pdf,
    "Net à payer = Montant brut (déjà arrondi) − Versement du 15.\n\n"
    "Le « Versement du 15 » est saisi manuellement par vous dans l'écran de "
    "calcul, personne par personne (0 F CFA par défaut si rien n'a été versé)."
)

sous_titre(pdf, "Total général du mois")
paragraphe(
    pdf,
    "Le total général affiché en bas du tableau est simplement la somme des "
    "montants bruts (ou nets) de toutes les personnes payables listées, "
    "exclusions comprises (une personne exclue contribue 0 F au total)."
)

# --- 4. Cas particuliers -----------------------------------------------------
pdf.add_page()
titre_section(pdf, 4, "Cas particuliers gérés automatiquement")

puce(pdf, "la personne apparaît dans le tableau avec ses heures réelles pour information, mais son montant est forcé à 0 F — jamais payée.", "Personne cochée « Exclue » :")
puce(pdf, "jamais payé automatiquement ; il apparaît dans la zone « à vérifier » avec ses heures, en attente d'une décision manuelle.", "Intervenant absent de la Feuille de temps :")
puce(pdf, "la séance est exclue du calcul automatique et listée dans la zone « à vérifier », jamais payée à 0 F silencieusement.", "Niveau de la séance impossible à identifier :")

# --- 5. Où modifier le barème -------------------------------------------------
pdf.add_page()
titre_section(pdf, 5, "Où et comment modifier le barème")

paragraphe(
    pdf,
    "Dans l'application : écran « Paramètres » (menu de gauche).\n\n"
    "Chaque tarif (Langue seule, Primaire, Collège, Lycée, BTS) est un champ "
    "modifiable directement. Le changement est enregistré dans le fichier "
    "registre_paie.db dès la saisie et s'applique au prochain calcul — "
    "jamais aux mois déjà enregistrés dans l'historique.\n\n"
    "Le fichier complémentaire « Barème et règles de paie.xlsx » fourni à "
    "côté de ce PDF liste ces mêmes valeurs sous forme de tableau, à titre "
    "de référence imprimable."
)

pdf.output("../Documentation_calcul_paie.pdf")
print("PDF genere")
