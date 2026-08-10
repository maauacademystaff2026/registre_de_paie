# Registre de paie — Cahier des charges (PRD)

Version 0.2 — stack technique retenue (§11), reste à trancher les questions du §7.

## 1. Contexte et objectif

Une école calcule chaque mois la paie des personnes qui donnent des cours, à partir de deux
exports Excel produits par le système de gestion de l'établissement. Aujourd'hui ce calcul est
fait manuellement / via un tableur fragile. L'objectif est une application locale et fiable qui :

1. importe les deux fichiers Excel du mois,
2. calcule automatiquement les heures payables et le montant dû par personne,
3. permet de saisir les avances versées le 15 du mois et les déduit,
4. conserve un historique consultable de tous les mois calculés (base de données annuelle),
5. exporte un état de paie final.

**Contrainte n°1 : fiabilité.** C'est un outil de paie — une erreur de calcul a un impact réel sur
des personnes. Toute règle ambiguë doit être tranchée explicitement (voir §7) avant codage, et
toute règle implémentée doit être couverte par un test automatisé avec des chiffres attendus
connus (voir §9), pas seulement vérifiée visuellement.

## 2. Fichiers d'entrée

### 2.1 Feuille de temps (`Feuille_de_temps.xlsx`)

Une ligne par personne et par rôle (une même personne peut apparaître plusieurs fois si elle a
plusieurs rôles, ex. Directeur d'études **et** Enseignant).

| Colonne | Type | Exemple |
|---|---|---|
| `#` | entier | 9 |
| `Nom` | texte | MBOCK GUY PAULIN |
| `Type d'utilisateur` | texte, une valeur parmi : `Direction`, `Directeur étude`, `Enseignant`, `Admin` | Enseignant |
| `1` … `31` | heures au format `HH:MM` texte, ou `-` si vide | `02:00` |
| `Totale d'heures effectuées` | `HH:MM` texte | `35:00` |
| `Taux horaire (EUR)` | nombre (⚠ libellé historique erroné : ce sont en réalité des F CFA) | 2000 |
| `Total (EUR)` | nombre | 70000 |

**Ce que l'app doit en extraire :** la liste des personnes et, pour chacune, son/ses rôle(s)
déclarés. **Ne pas utiliser** les colonnes d'heures ni de taux de ce fichier pour le calcul —
elles ne reflètent pas les nouvelles règles de tarification par niveau (voir §4). Ce fichier sert
uniquement d'annuaire du personnel.

### 2.2 Gestion des appels (`Gestion_des_appels.xlsx`)

Une ligne par séance de cours.

| Colonne | Type | Exemple |
|---|---|---|
| `État élève` | texte, une valeur parmi : `Présentiel`, `Dispensé`, `Absent`, `Retard - HH:MM` | Présentiel |
| `Noms` | texte (nom de l'élève) | KOP |
| `Prénoms` | texte (prénom de l'élève) | KIMYA |
| `Date` | texte `DD-MM-YYYY` | 01-07-2026 |
| `Classe` | texte, code de niveau | 6EME |
| `Section` | texte, souvent (mais pas toujours) « Nom Prénom » de l'élève | KOP KIMYA |
| `Niveau de classe` | texte, code de niveau ou `Tous les niveaux` | 6EME |
| `Enseignant/ Utilisateur` | texte, nom de l'intervenant | MBOCK GUY PAULIN |
| `Matière` | texte | Français |
| `Durée (H)` | texte `HH:MM` | 02:00 |

Valeurs réelles observées pour `Niveau de classe` : `CP, CE1, CE2, CM1, CM2` (primaire),
`6EME, 5EME, 4EME, 3EME` (collège), `2NDE, 1ERE, TLE` (lycée), `BTS`, et parfois
`Tous les niveaux` (non exploitable directement — voir §7, question ouverte).

Valeurs réelles observées pour `Matière` : `ANGLAIS, Français, Espagnole, Maths/Français,
Mathématiques, Physiques / Chimie, Science, Toutes les matières`.

## 3. Qui est payé (règle de base)

**Toute personne qui apparaît comme `Enseignant/ Utilisateur` sur une séance payable est payée
pour cette séance**, quel que soit son `Type d'utilisateur` déclaré dans la Feuille de temps
(Enseignant, Direction, ou Directeur d'études). Un membre de la Direction qui donne un cours est
payé comme un enseignant pour ce cours.

Autrement dit : le `Type d'utilisateur` de la Feuille de temps **n'est pas un filtre de
paiement**. Il sert d'annuaire (savoir qui est qui) mais toute séance loggée est potentiellement
payable, peu importe le rôle administratif de la personne.

**⚠️ Point à trancher avec le client avant développement — voir §7, question A.**
Une liste d'exclusions nominatives a été mentionnée à un stade antérieur du projet (personnes à
ne jamais payer à l'heure même si elles apparaissent comme intervenant). Cette liste doit être
revalidée : elle contredit potentiellement la règle ci-dessus si les personnes citées ont des
heures de cours réelles.

## 4. Quelle séance est payable

| État élève | Payable ? |
|---|---|
| Présentiel | Oui |
| Dispensé | Oui |
| Retard - HH:MM | Oui — **la durée totale de la séance (colonne `Durée (H)`) est payée en entier**, le retard de l'élève ne réduit pas la rémunération de l'enseignant |
| Absent | Non |

## 5. Tarification (V1 — barème simple, sans exception)

Pour la V1, **aucune exception** n'est appliquée (ni tarif personnalisé par enseignant, ni tarif
forcé par élève). Tout le monde suit strictement le barème ci-dessous. Les exceptions
(enseignant avec tarif personnalisé, élève avec tarif forcé) sont reportées en V2 — voir §10.

**Ordre d'application pour une séance donnée :**

1. Si la matière est **exactement** une langue seule (`ANGLAIS`, `Français`, ou `Espagnole` —
   pas en combinaison comme `Maths/Français`) → tarif langue, **quel que soit le niveau**.
2. Sinon → tarif du niveau de l'élève (voir tableau).

| Catégorie | Niveaux inclus | Tarif (F CFA / heure) |
|---|---|---|
| Langue seule | tous | 2 000 |
| Primaire | CP, CE1, CE2, CM1, CM2 | 1 500 |
| Collège | 6EME, 5EME, 4EME, 3EME | 2 000 |
| Lycée | 2NDE, 1ERE, TLE | 2 500 |
| BTS | BTS | 3 000 |

Ces cinq valeurs doivent être **modifiables dans l'application** (pas codées en dur), car elles
peuvent évoluer d'une année à l'autre.

**Résolution du niveau :** utiliser `Niveau de classe` en priorité. Si sa valeur est
`Tous les niveaux` (ou vide, ou non reconnue), essayer de déduire le niveau à partir du champ
`Classe` (recherche du code de niveau dans la chaîne, ex. `1ERE STL` → `1ERE` → Lycée).
Si aucun niveau n'est identifiable par ces deux moyens, **la séance doit être signalée comme
« non résolue » et exclue du calcul automatique**, avec une liste claire de ces séances non
résolues affichée à l'utilisateur pour traitement manuel — jamais de tarif à 0 silencieux.

## 6. Versement du 15

Pour chaque personne payée ce mois, un champ éditable **« Versement du 15 (F CFA) »**, saisi
manuellement par l'utilisateur (valeur par défaut 0). Ce montant est déduit du salaire brut
calculé pour obtenir le **net à payer** :

```
net_a_payer = round(salaire_brut) − versement_du_15
```

## 7. Questions ouvertes — à trancher avant tout développement

**A. Exclusions nominatives.** La liste suivante a été mentionnée dans une version antérieure du
projet comme « jamais payés à l'heure » : NDONGO NGA MAXIME, ELISE EYOUM, MBAALE DJENE LUMIERE,
KAMDEM RICH BILL. Or NDONGO NGA MAXIME, ELISE EYOUM et MBAALE DJENE LUMIERE ont des heures de
cours réelles (Dispensé) dans le journal des appels de juillet 2026 — donc sous la règle du §3
("un membre de la Direction qui donne cours est payé"), ils devraient être payés. **Cette liste
d'exclusion doit-elle être supprimée entièrement, conservée telle quelle, ou remplacée par un
mécanisme où l'utilisateur peut cocher/décocher au cas par cas dans l'application ?**
→ Recommandation : remplacer par une case à cocher « Exclu » modifiable par personne dans
l'application, plutôt qu'une liste figée dans le code — plus sûr et plus flexible.

**B. KAMDEM RICH BILL** n'a aucune ligne dans la Feuille de temps (aucun rôle déclaré) mais
apparaît comme intervenant dans le journal des appels (8h Dispensé). Doit-il être payé
automatiquement à la première apparition (créé automatiquement comme « Enseignant » dans
l'annuaire), ou l'application doit-elle bloquer/signaler et attendre une validation manuelle
avant de le payer ? → Recommandation : signaler, ne jamais créer ni payer automatiquement une
personne absente de l'annuaire.

**C. Molo Aline (1 600 F/h en primaire au lieu de 1 500 F/h)** — confirmé comme exception V2, pas
V1. À confirmer que c'est bien la seule exception connue à ce jour.

**D. Séances "Retard".** Confirmé : payées en entier (voir §4). À reconfirmer une fois le premier
calcul de test produit, car c'est un point qui a été corrigé une fois déjà.

**E. Arrondi.** Actuellement prévu à l'échelle du total par personne (`Math.round` du brut avant
déduction du versement du 15), pas séance par séance. À valider : c'est la méthode qui minimise
les écarts d'arrondi cumulés, mais si le client attend un arrondi séance par séance, le total
peut légèrement différer.

## 8. Fonctionnalités de l'application

### 8.1 Import
- Zone de dépôt dédiée n°1 : Feuille de temps (.xlsx).
- Zone de dépôt dédiée n°2 : Gestion des appels (.xlsx).
- Le calcul ne se déclenche qu'une fois les deux fichiers chargés et validés (schéma de colonnes
  reconnu — sinon message d'erreur explicite nommant la colonne manquante, jamais un plantage
  silencieux).
- Détection automatique du mois/période couverte (à partir des dates du journal des appels),
  affichée à l'utilisateur pour confirmation avant calcul.

### 8.2 Calcul et affichage
- Tableau des résultats : Nom, Heures payées, Montant brut, Versement du 15 (éditable),
  Net à payer.
- Ligne de total général.
- Zone « à vérifier » séparée listant : intervenants non reconnus dans l'annuaire, séances à
  niveau non résolu.
- **Détail par séance consultable** (par personne, dépliable ou exportable) : élève, date,
  niveau, matière, durée, tarif appliqué, source du tarif (langue / niveau) — indispensable pour
  qu'un montant puisse être vérifié et retracé ligne par ligne en cas de doute.

### 8.3 Historique / base de données annuelle
- Chaque calcul mensuel validé est enregistré de façon persistante (mois, année, détail par
  personne, détail par séance, versements du 15).
- Consultation possible des mois précédents (lecture seule, ou avec recalcul si les fichiers
  source sont réimportés).
- Export de l'historique complet (ex. tous les mois de l'année en un fichier).
- **Le stockage doit survivre à un changement de machine ou de navigateur** — voir §11
  (recommandation technique).

### 8.4 Export
- Export du mois calculé en `.xlsx` : une feuille "Résultats" (le tableau §8.2) + une feuille
  "Détail des séances" (le détail §8.2, pour audit).

## 9. Cas de test de référence (non-régression)

Ces chiffres ont été calculés et vérifiés manuellement à partir des données réelles de juillet
2026 sous la règle « tarif par niveau, sans exception, Enseignant uniquement, Retard payé » —
**mais restent à revalider une fois les questions du §7 tranchées**, notamment le point A qui
change qui est payé. Ils doivent néanmoins servir de fixture de test dès que la logique finale
est arrêtée : recalculer ces mêmes personnes et vérifier que le programme retombe sur des valeurs
cohérentes avec les règles validées.

| Enseignant | Heures (règle Présentiel+Dispensé, sans Retard) | Montant brut (F CFA) |
|---|---|---|
| MBOCK GUY PAULIN | 35,00 | 74 000 |
| Mbog NDJE Gaston Emmanuel | 38,50 | 86 500 |
| MOLO ALINE (sans exception 1 600) | 51,58 | 82 533 |
| FOZONG JOSEPH | 8,25 | 16 500 |
| LIZA ENONE LOICE | 10,50 | 21 000 |
| ANGOULA CLAUDE LEVI | 7,00 | 14 000 |
| Djene prof Lumière | 7,00 | 14 000 |
| FAMBOVE TSUGUINI ULRICH RONALD | 24,50 | 49 000 |
| KOOH JEAN | 4,00 | 6 000 |
| ENGOTO MBELEG prof Emmanuel | 20,00 | 43 000 |
| TIEUMENI DENIS | 20,00 | 50 000 |
| BELL LAURENT YVAN | 6,00 | 12 000 |
| NDJIBA DJONE MOISE | 15,00 | 40 500 |
| FOKAM LEONEL | 2,00 | 5 000 |

Total brut (ce sous-ensemble, sans Retard, sans les cas du §7) : 514 033 F CFA.

**Important :** ce tableau n'inclut pas les séances "Retard" (récemment déclarées payables) ni le
traitement des personnes du §7-A. Une fois ces règles tranchées, ces chiffres doivent être
recalculés et documentés à nouveau avant d'être figés comme référence de non-régression.

## 10. Hors périmètre V1 (reporté en V2)

- Tarif personnalisé par enseignant (ex. Molo Aline en primaire).
- Tarif forcé par élève nommé (ex. anciennes exceptions Hugo / Ingrid / Marc Yohann).
- Gestion multi-utilisateurs / accès simultané.
- Génération de bulletins de paie individuels formatés.

## 11. Stack technique retenue

| Couche | Choix | Rôle |
|---|---|---|
| Logique de calcul | Python, fonctions pures | Lecture fichiers → liste de séances → règles de tarification → agrégation par personne. Isolée de l'interface, testable indépendamment. |
| Lecture des fichiers Excel | `openpyxl` | Import des deux `.xlsx` (Feuille de temps, Gestion des appels). Déjà validé sur les fichiers réels du projet. |
| Tests | `pytest` | Suite de non-régression basée sur les cas de référence du §9 — doit échouer bruyamment si un changement de règle casse un résultat déjà validé. |
| Historique / base annuelle | SQLite (module `sqlite3`, inclus dans Python) | Un seul fichier local (`registre_paie.db`), sauvegardable comme un document normal — répond au besoin du §8.3 sans dépendre du cache d'un navigateur. |
| Interface | Streamlit | Une seule base de code Python, lancée en local (`streamlit run app.py`) et affichée dans le navigateur, mais 100% exécutée sur la machine de l'utilisateur — pas de serveur distant. |
| Distribution V1 | Script Python lancé localement | Nécessite Python installé une fois sur la machine. Empaquetage en exécutable (PyInstaller, icône double-clic) envisageable en V2, non nécessaire pour démarrer. |

**Principes directeurs :**
- La logique de règles ne doit jamais s'exécuter directement sur des cellules Excel : les deux
  fichiers sont convertis dès l'import en structures de données Python simples et documentées
  (listes de séances, annuaire du personnel), et toute la suite du calcul travaille sur ces
  structures.
- Aucune règle de tarification ne doit être codée en dur dans l'interface : les valeurs
  modifiables (barème par niveau, versements du 15, exclusions) vivent dans la base SQLite ou un
  fichier de configuration, pas dans le code.
- Chaque évolution de règle (V2 : exceptions par enseignant/élève) doit s'accompagner d'un
  nouveau cas de test avant d'être considérée comme fiable.

## 12. Prochaine étape

Trancher les questions du §7 (A à E), puis figer le tableau de référence du §9 sur cette base
avant de lancer le développement.
