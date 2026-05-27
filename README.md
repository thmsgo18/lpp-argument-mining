<div align="center">

<h1>Analyse de Corpus Argumentatifs pour la Construction de Graphes LPP/GORGIAS</h1>

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Graphviz](https://img.shields.io/badge/Graphviz-requis-E67E22)
![Format](https://img.shields.io/badge/Format-brat%20.ann-6C3483)
![ANR GRAIL](https://img.shields.io/badge/ANR-GRAIL%20ANR--25--CE23--5597-2E86C1)

Master 1 Intelligence Artificielle Distribuée · Université Paris Cité · 2025-2026

**Auteurs :** Thomas Gourmelen, Noureddine Mohammedi  
**Encadrants :** Élise Bonzon, Jérôme Delobelle

</div>

---

<h2>Table des matières</h2>

- [1. Présentation du projet](#1-présentation-du-projet)
- [2. État de l'art](#2-état-de-lart)
  - [2.1 Argumentation computationnelle](#21-argumentation-computationnelle)
  - [2.2 LPP/GORGIAS](#22-lppgorgias)
  - [2.3 Le format brat](#23-le-format-brat)
  - [2.4 Argument mining et ses limites](#24-argument-mining-et-ses-limites)
- [3. Problématique et objectifs](#3-problématique-et-objectifs)
- [4. Structure du dépôt](#4-structure-du-dépôt)
- [5. Composants](#5-composants)
  - [5.1 Prompt d'annotation](#51-prompt-dannotation)
  - [5.2 Script de visualisation](#52-script-de-visualisation)
- [6. Résultats](#6-résultats)
- [7. Documents associés](#7-documents-associés)

---

## 1. Présentation du projet

Ce dépôt s'inscrit dans le projet ANR **GRAIL** (*Generative aRgumentative ArtificiAl InteLligence*), porté par le LIPADE, le LLF et l'IRIT. L'objectif de GRAIL est de développer des agents neuro-symboliques capables de justifier leur raisonnement de manière explicite via le formalisme **LPP/GORGIAS**.

L'enjeu de ce TER est de construire un pont entre les corpus d'argument mining existants et ce formalisme, en automatisant la transition grâce à un modèle de langue large (Claude).

---

## 2. État de l'art

### 2.1 Argumentation computationnelle

L'argumentation computationnelle modélise des systèmes où des arguments construits à partir de prémisses peuvent se soutenir ou s'attaquer. Le cadre de **Dung (1995)** est le fondement du domaine : il représente un système comme une paire *(Args, Att)* et définit des sémantiques d'acceptabilité (admissible, préférée, stable), mais reste abstrait sur la structure interne des arguments. **ASPIC+** introduit des règles strictes et défaisables et rapproche ce cadre d'une logique exploitable, sans pour autant constituer un schéma d'annotation textuelle.

### 2.2 LPP/GORGIAS

> **LPP** (*Logic Programming with Priorities*) est un formalisme d'argumentation structurée développé par Kakas, Moraitis et Spanoudakis. **GORGIAS** en est l'implémentation open source (disponible depuis 2003).

LPP organise tout raisonnement en **trois niveaux hiérarchiques stricts** :

```
┌─────────────────────────────────────┐
│  Level 2 : meta_prefer              │
│  Priorités entre préférences        │
└──────────────────┬──────────────────┘
                   │ arbitre
┌──────────────────▼──────────────────┐
│  Level 1 : prefer                   │
│  Priorités entre règles             │
└──────────────────┬──────────────────┘
                   │ arbitre
┌──────────────────▼──────────────────┐
│  Level 0 : rule                     │
│  Context(s)  ──►  Option            │
└─────────────────────────────────────┘
```

| Niveau | Primitive | Rôle |
|:------:|-----------|------|
| 0 | `rule` | Dériver une Option (conclusion) à partir d'un ou plusieurs Context (conditions) |
| 1 | `prefer` | Exprimer qu'une `rule` l'emporte sur une autre dans un contexte donné |
| 2 | `meta_prefer` | Exprimer qu'une `prefer` l'emporte sur une autre dans un contexte plus spécifique |

**Entités textuelles :**

| Entité | Définition |
|--------|------------|
| **Context** | Fait, condition, circonstance ou posture procédurale alimentant une conclusion |
| **Option** | Conclusion, décision, jugement ou alternative disponible |
| **Marker** | Marqueur textuel explicite de priorité (*"takes precedence over"*, *"notwithstanding"*, *"overrides"*...) |

La hiérarchie est stricte : un `prefer` porte toujours sur deux `rule`, un `meta_prefer` porte toujours sur deux `prefer` ou `meta_prefer`. Il n'y a pas de saut de niveau.

### 2.3 Le format brat

> **brat** (*brat rapid annotation tool*) est un outil d'annotation textuelle web développé à l'Université de Tokyo. Son format `.ann` est un standard de facto en TAL pour l'annotation de corpus.

Un fichier `.ann` contient trois types de lignes :

```
# T-lines : entités textuelles  (identifiant  type  début  fin  texte)
T1    Context   0   34    a person has been finally acquitted
T2    Option   51  144    a civil court may still rule on property consequences

# E-lines : événements          (identifiant  type:déclencheur  rôles)
E1    rule:T2   Condition:T1   Effect:T2
E21   prefer:T71   Winner:E2   Loser:E9   When:T69

# A-lines : attributs           (identifiant  nom  cible  valeur)
A1    Modality   T2   permitted
A2    Negated    T5   True
```

Les offsets sont basés sur zéro, borne de fin exclusive. Le format est compatible avec plusieurs corpus d'argument mining existants, notamment ArgumentMiningECHR.

### 2.4 Argument mining et ses limites

L'argument mining extrait automatiquement des structures argumentatives (**Claim**, **Premise**, **Support**, **Attack**) depuis des textes naturels. Ces corpus sont hétérogènes et insuffisants pour LPP/GORGIAS :

| Etiquette AM | Correspondance LPP | Limite |
|---|---|---|
| **Claim** | Option ? | Peut être une prémisse intermédiaire |
| **Premise** | Context ? | Peut être la conclusion d'un argument précédent |
| **Support** | `rule` ? | Ne spécifie pas Condition ni Effect |
| **Attack** | `prefer` ? | Ne suffit pas sans marqueur de priorité explicite |

La transition vers GORGIAS nécessite donc un schéma d'annotation dédié, travaillé directement sur le texte brut.

---

## 3. Problématique et objectifs

**Question centrale :** comment guider la transition d'un texte argumentatif brut vers une représentation LPP compatible avec GORGIAS, et dans quelle mesure peut-on l'automatiser ?

Cinq objectifs ont structuré les travaux :

1. Analyser 17 corpus d'argument mining pour évaluer leur pertinence pour LPP.
2. Définir des principes d'annotation permettant le passage des étiquettes classiques aux niveaux LPP.
3. Construire un prompt opérationnel produisant une annotation brat (`.ann`) aux trois niveaux LPP.
4. Evaluer ce prompt sur deux textes : un arrêt CEDH (juridique) et un extrait de *Douze Hommes en Colère* (délibératif).
5. Identifier les limites de l'automatisation et les points exigeant une validation humaine.

---

## 4. Structure du dépôt

```
lpp-argument-mining/
├── src/
│   ├── prompt-claude.txt                        # Prompt d'annotation LPP/GORGIAS
│   ├── ann_to_graph.py                          # Script de visualisation (.ann -> .png)
│   └── results/
│       ├── CASE_OF__ALKASI_v._TURKEY/
│       │   ├── CASE_OF__ALKASI_v._TURKEY.txt    # Texte source
│       │   ├── CASE_OF__ALKASI_v._TURKEY.ann    # Annotation LPP générée
│       │   ├── CASE_OF__ALKASI_v._TURKEY.dot    # Source Graphviz intermédiaire
│       │   └── CASE_OF__ALKASI_v._TURKEY.png    # Graphe LPP visualisé
│       └── Twelve_angry_men/
│           ├── Twelve_Angry_Men.txt             # Texte source
│           ├── Twelve_angry_men.ann             # Annotation LPP générée
│           ├── Twelve_angry_men.dot             # Source Graphviz intermédiaire
│           └── Twelve_angry_men.png             # Graphe LPP visualisé
├── rapport.pdf                                  # Rapport de TER (a venir)
└── presentation.pdf                             # Présentation de soutenance (a venir)
```

---

## 5. Composants

### 5.1 Prompt d'annotation

**Fichier :** `src/prompt-claude.txt`

Prompt rédigé en anglais pour maximiser les performances de Claude, applicable à tout texte argumentatif. Pour l'utiliser, remplacer la balise `<<<INPUT_TEXT>>>` en fin de fichier par le texte à annoter.

Le prompt est structuré en huit blocs : rappel LPP, schéma d'annotation, cas des textes à préférences, méthodologie pas-à-pas, erreurs à éviter, quatre exemples annotés, format de sortie strict, auto-vérification avant émission.

**Format de sortie :**

```
T<id>   Context | Option | Marker   <start> <end>   <texte exact>
E<id>   rule:T<id>          Condition:T<id> ...   Effect:T<id>
E<id>   prefer:T<id>        Winner:E<id>          Loser:E<id>    [When:T<id>]
E<id>   meta_prefer:T<id>   Winner:E<id>          Loser:E<id>    [When:T<id>]
A<id>   Modality | Negated | Implicit   T<id>   <valeur>
```

---

### 5.2 Script de visualisation

**Fichier :** `src/ann_to_graph.py`

Convertit un fichier `.ann` en graphe PNG haute résolution via Graphviz. Parse les entités, reconstruit la hiérarchie LPP, génère le DOT intermédiaire, puis produit l'image.

**Prérequis :** Python 3.8+ et [Graphviz](https://graphviz.org/download/) dans le `PATH`.

```bash
python src/ann_to_graph.py <fichier.ann>              # PNG par défaut
python src/ann_to_graph.py <fichier.ann> -o out.png   # fichier de sortie
python src/ann_to_graph.py <fichier.ann> --output dot # exporter le DOT
python src/ann_to_graph.py <fichier.ann> --no-legend  # sans légende
python src/ann_to_graph.py <fichier.ann> --dpi 300    # résolution personnalisée
```

**Conventions visuelles :**

| Element | Forme | Couleur | Niveau |
|---------|:-----:|---------|:------:|
| Context | Rectangle arrondi | Bleu clair | 0 |
| Option | Rectangle | Vert clair | 0 |
| `rule` | Ellipse | Jaune | 0 |
| `prefer` | Losange | Violet clair | 1 |
| `meta_prefer` | Losange | Violet foncé | 2 |

| Arête | Style | Couleur |
|-------|:-----:|---------|
| condition | Trait plein | Bleu |
| effect | Trait plein | Vert |
| winner | Tirets | Violet |
| loser | Tirets | Rouge |
| when | Pointillés | Orange |

---

## 6. Résultats

Le prompt a été évalué sur deux textes complémentaires.

<table>
<thead>
<tr>
<th>Critère</th>
<th>Alkasi c. Turquie (CEDH)</th>
<th>Douze Hommes en Colère</th>
</tr>
</thead>
<tbody>
<tr><td>Type de texte</td><td>Juridique formel</td><td>Délibératif multi-locuteurs</td></tr>
<tr><td>Corpus source</td><td>ArgumentMiningECHR</td><td>NoDE_datasets</td></tr>
<tr><td>Entités annotées</td><td>28 (13 Context, 14 Option, 1 Marker)</td><td>74 (40 Context, 33 Option, 1 Marker)</td></tr>
<tr><td><code>rule</code></td><td>14</td><td>20</td></tr>
<tr><td><code>prefer</code></td><td>0</td><td>1 (E21)</td></tr>
<tr><td><code>meta_prefer</code></td><td>0</td><td>0</td></tr>
<tr><td>Attributs</td><td>7 Modality</td><td>8 Modality, 4 Negated</td></tr>
<tr><td>Structure du graphe</td><td>Linéaire, déductive</td><td>Branches parallèles</td></tr>
<tr><td>Validation humaine</td><td>Faible</td><td>Elevée</td></tr>
</tbody>
</table>

**Alkasi c. Turquie :** le graphe illustre une chaîne déductive E1 -> E2 -> E3 -> E4 menant à l'admissibilité de la requête. Aucun `prefer` n'est produit, ce qui est cohérent : le texte ne contient aucun marqueur explicite de priorité entre règles concurrentes.

**Douze Hommes en Colère :** le seul `prefer` produit (E21) oppose la présomption d'innocence (E2, Winner) à une attaque sur la crédibilité (E9, Loser) via le marqueur *"you can't trust them"*. Ce résultat illustre la limite de l'automatisation : ce marqueur relève davantage d'une généralisation rhétorique que d'un marqueur de priorité canonique, et nécessite une relecture humaine.

---

## 7. Documents associés

| Document | Description | Statut |
|----------|-------------|:------:|
| `rapport.pdf` | Rapport de TER complet | A venir |
| `presentation.pdf` | Présentation de soutenance | A venir |
