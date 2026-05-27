<div align="center">

<h1>Analysis of Annotated Text Corpora for the Construction of LPP Argumentation Graphs</h1>

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Graphviz](https://img.shields.io/badge/Graphviz-required-E67E22)
![Format](https://img.shields.io/badge/Format-brat%20.ann-6C3483)
[![ANR GRAIL](https://img.shields.io/badge/ANR-GRAIL%20ANR--25--CE23--5597-2E86C1)](https://grail.mi.parisdescartes.fr)

![Argument Mining](https://img.shields.io/badge/Argument%20Mining-555555)
![LPP%2FGORGIAS](https://img.shields.io/badge/LPP%2FGORGIAS-555555)
![Prompt Engineering](https://img.shields.io/badge/Prompt%20Engineering-555555)
![NLP](https://img.shields.io/badge/NLP-555555)
![Symbolic AI](https://img.shields.io/badge/Symbolic%20AI-555555)

[Master 1 Distributed Artificial Intelligence](https://math-info.u-paris.fr/international-masters-distributed-artificial-intelligence-dai-agent-based-computing/) · Université Paris Cité · 2025-2026

**Authors:** [Thomas Gourmelen](https://github.com/thmsgo18), [Noureddine Mohammedi](https://github.com/Mr-Noredine)  
**Supervisors:** Élise Bonzon, Jérôme Delobelle

[Version française](README.fr.md)

</div>

---

<h2>Table of Contents</h2>

- [1. Project Overview](#1-project-overview)
- [2. Repository Structure](#2-repository-structure)
- [3. Related Work](#3-related-work)
  - [3.1 Formal Argumentation and Computational Frameworks](#31-formal-argumentation-and-computational-frameworks)
  - [3.2 LPP/GORGIAS](#32-lppgorgias)
  - [3.3 The brat Format](#33-the-brat-format)
- [4. Research Question and Objectives](#4-research-question-and-objectives)
- [5. Components](#5-components)
  - [5.1 Annotation Prompt](#51-annotation-prompt)
  - [5.2 Visualization Script](#52-visualization-script)
- [6. Results](#6-results)
- [7. Associated Documents](#7-associated-documents)
- [8. Main References](#8-main-references)

---

## 1. Project Overview

This repository is part of the ANR **[GRAIL](https://grail.mi.parisdescartes.fr)** project (*Generative aRgumentative ArtificiAl InteLligence*, ANR-25-CE23-5597). GRAIL aims to develop neuro-symbolic AI agents capable of explicitly justifying their reasoning through the **LPP/GORGIAS** formalism.

The objective of this Research Study and Work (TER) is to build a bridge between existing argument mining corpora and this formalism, automating the transition using a large language model (Claude).

**Partner laboratories:**

| Laboratory | Institution | Team |
|------------|-------------|------|
| LIPADE | Université Paris Cité | É. Bonzon, J. Delobelle, P. Moraitis, J. Rossit |
| LLF | CNRS / Université Paris Cité | T. Bernard, B. Crabbé |
| IRIT | Université Toulouse III | C. Braud, J.-G. Mailly, P. Muller |
| Bar-Ilan University | Israel | O. Shehory |

---

## 2. Repository Structure

```
lpp-argument-mining/
├── src/
│   ├── prompt-claude.txt                        # LPP/GORGIAS annotation prompt
│   ├── ann_to_graph.py                          # Visualization script (.ann -> .png)
│   └── results/
│       ├── CASE_OF__ALKASI_v._TURKEY/
│       │   ├── CASE_OF__ALKASI_v._TURKEY.txt    # Source text
│       │   ├── CASE_OF__ALKASI_v._TURKEY.ann    # Generated LPP annotation
│       │   ├── CASE_OF__ALKASI_v._TURKEY.dot    # Intermediate Graphviz source
│       │   └── CASE_OF__ALKASI_v._TURKEY.png    # Visualized LPP graph
│       └── Twelve_angry_men/
│           ├── Twelve_Angry_Men.txt             # Source text
│           ├── Twelve_angry_men.ann             # Generated LPP annotation
│           ├── Twelve_angry_men.dot             # Intermediate Graphviz source
│           └── Twelve_angry_men.png             # Visualized LPP graph
├── research_paper/
│   ├── GORGIAS: Applying argumentation.pdf                            # Kakas et al., 2019
│   └── Argumentation Based Decision Making for Autonomous Agents.pdf  # Kakas & Moraitis, 2003
├── TER_Rapport.pdf                              # Full research report
├── Presentation_TER.html                        # Interactive presentation (with effects)
└── Presentation_TER.pdf                         # Static presentation (no effects)
```

---

## 3. Related Work

### 3.1 Formal Argumentation and Computational Frameworks

Computational argumentation models reasoning in which arguments, built from premises and conclusions, can support or attack one another. **Dung's framework (1995)** is the foundation of the field, representing a system as a pair *(Args, Att)*, but remains abstract on the internal structure of arguments. **ASPIC+** introduces strict and defeasible rules, bringing this framework closer to an exploitable logical representation without constituting a textual annotation scheme.

**Argument mining** deals with the extraction of these structures from natural texts: identifying components (**Claim**, **Premise**) and relations (**Support**, **Attack**). These corpora remain heterogeneous and insufficient to produce decision-making reasoning with explicit priorities — this is the contribution of LPP/GORGIAS.

### 3.2 LPP/GORGIAS

**LPP** (*Logic Programming with Priorities*) is a structured argumentation formalism developed by Kakas, Moraitis and Spanoudakis. **GORGIAS** is its open-source implementation (available since 2003). The formalism rests on the following formal definition:

> **Definition 4** *(Kakas, Moraitis & Spanoudakis)* — *An agent's argumentative policy theory T is a triple* **T** = (*T*, *P*<sub>R</sub>, *P*<sub>C</sub>) *where the rules in T do not refer to h<sub>p</sub>, all the rules in P*<sub>R</sub> *are priority rules with head h<sub>p</sub>(r*<sub>1</sub>*, r*<sub>2</sub>*) s.t. r*<sub>1</sub>*, r*<sub>2</sub> *∈ T and all rules in P*<sub>C</sub> *are priority rules with head h<sub>p</sub>(R*<sub>1</sub>*, R*<sub>2</sub>*) s.t. R*<sub>1</sub>*, R*<sub>2</sub> *∈ P*<sub>R</sub> *∪ P*<sub>C</sub>*.*

In this TER, we adapted this structure to argumentative text: *T* maps to `rule` (Level 0), *P*<sub>R</sub> to `prefer` (Level 1), and *P*<sub>C</sub> to `meta_prefer` (Level 2). The textual entities Context, Option and Marker constitute their annotatable translation in brat format.

LPP organizes all reasoning into **three strict hierarchical levels**:

```
┌─────────────────────────────────────┐
│  Level 2 : meta_prefer              │
│  Priorities between preferences     │
└─────────────────────────────────────┘
                   ▲
┌─────────────────────────────────────┐
│  Level 1 : prefer                   │
│  Priorities between rules           │
└─────────────────────────────────────┘
                   ▲
┌─────────────────────────────────────┐
│  Level 0 : rule                     │
│  Context(s)  ──►  Option            │
└─────────────────────────────────────┘
```

| Level | Primitive | Role |
|:-----:|-----------|------|
| 0 | `rule` | Derive an Option (conclusion) from one or more Context (conditions) |
| 1 | `prefer` | Express that one `rule` overrides another in a given context |
| 2 | `meta_prefer` | Express that one `prefer` overrides another in a more specific context |

**Textual entities:**

| Entity | Definition |
|--------|------------|
| **Context** | Fact, condition, circumstance or procedural posture feeding a conclusion |
| **Option** | Conclusion, decision, judgment or available alternative |
| **Marker** | Explicit textual priority cue (*"takes precedence over"*, *"notwithstanding"*, *"overrides"*...) |

The hierarchy is strict: a `prefer` always ranks two `rule` events, a `meta_prefer` always ranks two `prefer` or `meta_prefer` events. Level-skipping is not allowed.

### 3.3 The brat Format

> **brat** (*brat rapid annotation tool*) is a web-based text annotation tool developed at the University of Tokyo. Its `.ann` file format is a de facto standard in NLP for corpus annotation.

A `.ann` file contains three types of lines:

```
# T-lines: text-bound entities  (id  type  start  end  text)
T1    Context   0   34    a person has been finally acquitted
T2    Option   51  144    a civil court may still rule on property consequences

# E-lines: events               (id  type:trigger  roles)
E1    rule:T2   Condition:T1   Effect:T2
E21   prefer:T71   Winner:E2   Loser:E9   When:T69

# A-lines: attributes           (id  name  target  value)
A1    Modality   T2   permitted
A2    Negated    T5   True
```

Character offsets are zero-based, with an exclusive end boundary. The format is compatible with several existing argument mining corpora, notably ArgumentMiningECHR.

---

## 4. Research Question and Objectives

**Central question:** how can we guide the transition from a raw argumentative text to an LPP representation compatible with GORGIAS, and to what extent can this transition be automated?

Five objectives structured the work:

1. Analyze 17 argument mining corpora to evaluate their relevance for LPP.
2. Define annotation principles enabling the transition from classical argument mining labels to LPP levels.
3. Build an operational prompt producing a brat (`.ann`) annotation at all three LPP levels.
4. Evaluate this prompt on two texts: an ECHR ruling (legal reasoning) and an excerpt from *Twelve Angry Men* (deliberative reasoning).
5. Identify the limits of automation and the points requiring human validation.

---

## 5. Components

### 5.1 Annotation Prompt

**File:** `src/prompt-claude.txt`

Prompt written in English to maximize Claude's performance, applicable to any sufficiently explicit argumentative text. To use it, replace the `<<<INPUT_TEXT>>>` tag at the end of the file with the text to annotate.

The prompt is organized into eight blocks: LPP reminder, annotation schema, preference-ranking texts, step-by-step methodology, errors to avoid, four annotated examples, strict output format, pre-emission self-verification.

**Output format:**

```
T<id>   Context | Option | Marker   <start> <end>   <exact span>
E<id>   rule:T<id>          Condition:T<id> ...   Effect:T<id>
E<id>   prefer:T<id>        Winner:E<id>          Loser:E<id>    [When:T<id>]
E<id>   meta_prefer:T<id>   Winner:E<id>          Loser:E<id>    [When:T<id>]
A<id>   Modality | Negated | Implicit   T<id>   <value>
```

---

### 5.2 Visualization Script

**File:** `src/ann_to_graph.py`

Converts a `.ann` file into a high-resolution PNG graph via Graphviz. Parses entities, reconstructs the LPP hierarchy, generates the intermediate DOT source, then produces the image.

**Requirements:** Python 3.8+ and [Graphviz](https://graphviz.org/download/) in the `PATH`.

```bash
python src/ann_to_graph.py <file.ann>              # PNG output (default)
python src/ann_to_graph.py <file.ann> -o out.png   # custom output file
python src/ann_to_graph.py <file.ann> --output dot # export DOT source
python src/ann_to_graph.py <file.ann> --no-legend  # without legend
python src/ann_to_graph.py <file.ann> --dpi 300    # custom resolution
```

**Visual conventions:**

| Element | Shape | Color | Level |
|---------|:-----:|-------|:-----:|
| Context | Rounded rectangle | Light blue | 0 |
| Option | Rectangle | Light green | 0 |
| `rule` | Ellipse | Yellow | 0 |
| `prefer` | Diamond | Light purple | 1 |
| `meta_prefer` | Diamond | Dark purple | 2 |

| Edge | Style | Color |
|------|:-----:|-------|
| condition | Solid | Blue |
| effect | Solid | Green |
| winner | Dashed | Purple |
| loser | Dashed | Red |
| when | Dotted | Orange |

---

## 6. Results

The prompt was evaluated on two complementary texts.

<table>
<thead>
<tr>
<th>Criterion</th>
<th>Alkasi v. Turkey (ECHR)</th>
<th>Twelve Angry Men</th>
</tr>
</thead>
<tbody>
<tr><td>Text type</td><td>Formal legal</td><td>Multi-speaker deliberative</td></tr>
<tr><td>Source corpus</td><td>ArgumentMiningECHR</td><td>NoDE_datasets</td></tr>
<tr><td>Annotated entities</td><td>28 (13 Context, 14 Option, 1 Marker)</td><td>74 (40 Context, 33 Option, 1 Marker)</td></tr>
<tr><td><code>rule</code></td><td>14</td><td>20</td></tr>
<tr><td><code>prefer</code></td><td>0</td><td>1 (E21)</td></tr>
<tr><td><code>meta_prefer</code></td><td>0</td><td>0</td></tr>
<tr><td>Attributes</td><td>7 Modality</td><td>8 Modality, 4 Negated</td></tr>
<tr><td>Graph structure</td><td>Linear, deductive</td><td>Parallel branches</td></tr>
<tr><td>Human validation</td><td>Low</td><td>High</td></tr>
</tbody>
</table>

**Alkasi v. Turkey:** the graph illustrates a deductive chain E1 -> E2 -> E3 -> E4 leading to the admissibility of the application. No `prefer` is produced, which is consistent: the text contains no explicit priority marker between competing rules.

**Twelve Angry Men:** the single `prefer` produced (E21) opposes the presumption of innocence (E2, Winner) against a credibility attack (E9, Loser) via the marker *"you can't trust them"*. This result illustrates the limits of automation: this marker is more of a rhetorical generalization than a canonical priority marker, and requires human review.

For a detailed analysis of the methodology, annotation principles and results, see the [research report](TER_Rapport.pdf).

---

## 7. Associated Documents

| Document | Format | Description |
|----------|:------:|-------------|
| [`TER_Rapport.pdf`](TER_Rapport.pdf) | PDF | Full research report: context, related work, contributions, results |
| [`Presentation_TER.html`](Presentation_TER.html) | HTML | Defense presentation with animations and transition effects |
| [`Presentation_TER.pdf`](Presentation_TER.pdf) | PDF | Static version of the presentation, without effects |

---

## 8. Main References

Both foundational papers on the LPP/GORGIAS formalism used in this TER are available in the [`research_paper/`](research_paper/) folder.

**[1]** Antonis C. Kakas, Pavlos Moraitis and Nikolaos I. Spanoudakis.
*GORGIAS: Applying argumentation.*
Argument & Computation, vol. 10, pp. 55-81, IOS Press, 2019.
DOI: [10.3233/AAC-181006](https://doi.org/10.3233/AAC-181006)
— Primary reference for the LPP formalism and GORGIAS implementation. Source of Definition 4 cited in the related work section.

**[2]** Antonis Kakas and Pavlos Moraitis.
*Argumentation Based Decision Making for Autonomous Agents.*
AAMAS'03, Melbourne, Australia, 2003.
— Presents the argumentation-based decision-making framework for autonomous agents, theoretical foundation of the LPP approach.
