#!/usr/bin/env python3
"""
ann_to_graph.py
---------------
Convertit un fichier .ann (brat LPP/GORGIAS v4) en graphe PNG haute résolution.
Compatible avec la sortie du prompt Claude v4 (rule, prefer, meta_prefer).

Niveaux LPP représentés :
  Level 0 — rule       (règles objet)
  Level 1 — prefer     (priorités entre règles)
  Level 2 — meta_prefer (priorités entre priorités)

Usage :
  python ann_to_graph.py mon_annotation.ann
  python ann_to_graph.py mon_annotation.ann -o sortie.png
  python ann_to_graph.py mon_annotation.ann --output dot
  python ann_to_graph.py mon_annotation.ann --no-legend
  python ann_to_graph.py mon_annotation.ann --title "Mon titre"
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# 1. STRUCTURES DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TextBound:
    brat_id: str
    kind: str          # Context | Option | Marker
    text: str
    logical_id: str | None = None
    attrs: dict[str, str] = field(default_factory=dict)


@dataclass
class Event:
    brat_id: str
    kind: str          # rule | prefer | meta_prefer
    trigger: str       # T-id du trigger (Option pour rule, Marker pour prefer/meta_prefer)
    args: dict[str, list[str]] = field(default_factory=dict)
    logical_id: str | None = None


@dataclass
class RuleNode:
    """Level 0 — règle objet."""
    rule_id: str          # ex: r1
    effect: str           # logical_id de l'Option
    conditions: list[str] # logical_ids des Contexts/Options conditions
    modality: str | None = None
    negated_effect: bool = False
    implicit_conditions: list[str] = field(default_factory=list)


@dataclass
class PrefNode:
    """Level 1 — prefer entre deux rule events."""
    pref_id: str          # ex: pr1
    winner: str           # logical_id du rule gagnant
    loser: str            # logical_id du rule perdant
    when: list[str]       # logical_ids des Contexts conditionnels
    marker_label: str = ""


@dataclass
class MetaPrefNode:
    """Level 2 — meta_prefer entre deux prefer/meta_prefer events."""
    meta_id: str          # ex: pp1
    winner: str           # logical_id du prefer/meta_prefer gagnant
    loser: str            # logical_id du prefer/meta_prefer perdant
    when: list[str]       # logical_ids des Contexts conditionnels
    marker_label: str = ""


@dataclass
class LPPGraph:
    labels: dict[str, str] = field(default_factory=dict)   # logical_id -> texte
    attrs_map: dict[str, dict[str, str]] = field(default_factory=dict)  # logical_id -> attrs
    rules: list[RuleNode] = field(default_factory=list)
    prefs: list[PrefNode] = field(default_factory=list)
    meta_prefs: list[MetaPrefNode] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# 2. PARSEUR .ann
# ═══════════════════════════════════════════════════════════════════════════

def natural_key(brat_id: str) -> tuple[str, int]:
    m = re.fullmatch(r"([A-Z]+)([0-9]+)", brat_id)
    return (m.group(1), int(m.group(2))) if m else (brat_id, 0)


def parse_ann(path: Path) -> tuple[dict[str, TextBound], dict[str, Event]]:
    textbounds: dict[str, TextBound] = {}
    events: dict[str, Event] = {}
    pending_attrs: list[tuple[str, str, str]] = []

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = raw.split("\t")
        ann_id = parts[0].strip()

        # ── TextBound ──────────────────────────────────────────────────────
        if ann_id.startswith("T"):
            if len(parts) < 3:
                raise ValueError(f"Ligne {lineno}: text-bound malformé : {raw!r}")
            meta = parts[1].split()
            kind = meta[0]
            text = parts[2].strip()
            textbounds[ann_id] = TextBound(ann_id, kind, text)

        # ── Event ──────────────────────────────────────────────────────────
        elif ann_id.startswith("E"):
            if len(parts) < 2:
                raise ValueError(f"Ligne {lineno}: event malformé : {raw!r}")
            chunks = parts[1].split()
            ev_kind_trigger = chunks[0]
            if ":" not in ev_kind_trigger:
                continue
            ev_kind, trigger = ev_kind_trigger.split(":", 1)
            args: dict[str, list[str]] = {}
            for chunk in chunks[1:]:
                if ":" not in chunk:
                    continue
                role, target = chunk.split(":", 1)
                args.setdefault(role, []).append(target)
            events[ann_id] = Event(ann_id, ev_kind, trigger, args)

        # ── Attribute ──────────────────────────────────────────────────────
        elif ann_id.startswith("A"):
            if len(parts) < 2:
                continue
            chunks = parts[1].split()
            if len(chunks) < 2:
                continue
            attr_name = chunks[0]
            target = chunks[1]
            value = chunks[2] if len(chunks) > 2 else "True"
            pending_attrs.append((target, attr_name, value))

    for target, attr_name, value in pending_attrs:
        if target in textbounds:
            textbounds[target].attrs[attr_name] = value

    return textbounds, events


# ═══════════════════════════════════════════════════════════════════════════
# 3. IDENTIFIANTS LOGIQUES
# ═══════════════════════════════════════════════════════════════════════════

def assign_logical_ids(
    textbounds: dict[str, TextBound],
    events: dict[str, Event],
) -> None:
    tb_counters: dict[str, int] = {"Context": 0, "Option": 0}
    tb_prefixes: dict[str, str] = {"Context": "c", "Option": "o"}

    for tb in sorted(textbounds.values(), key=lambda x: natural_key(x.brat_id)):
        if tb.kind not in tb_prefixes:
            continue
        tb_counters[tb.kind] += 1
        tb.logical_id = f"{tb_prefixes[tb.kind]}{tb_counters[tb.kind]}"

    ev_counters: dict[str, int] = {"rule": 0, "prefer": 0, "meta_prefer": 0}
    ev_prefixes: dict[str, str] = {"rule": "r", "prefer": "pr", "meta_prefer": "pp"}

    for ev in sorted(events.values(), key=lambda x: natural_key(x.brat_id)):
        if ev.kind not in ev_prefixes:
            continue
        ev_counters[ev.kind] += 1
        ev.logical_id = f"{ev_prefixes[ev.kind]}{ev_counters[ev.kind]}"


# ═══════════════════════════════════════════════════════════════════════════
# 4. CONSTRUCTION DU GRAPHE LPP
# ═══════════════════════════════════════════════════════════════════════════

def build_lpp_graph(
    textbounds: dict[str, TextBound],
    events: dict[str, Event],
) -> LPPGraph:
    assign_logical_ids(textbounds, events)
    graph = LPPGraph()

    # Labels et attributs pour Context et Option
    for tb in textbounds.values():
        if tb.logical_id:
            graph.labels[tb.logical_id] = tb.text
            if tb.attrs:
                graph.attrs_map[tb.logical_id] = dict(tb.attrs)

    ev_sorted = sorted(events.values(), key=lambda x: natural_key(x.brat_id))

    for ev in ev_sorted:

        # ── LEVEL 0 : rule ─────────────────────────────────────────────────
        if ev.kind == "rule":
            effects = ev.args.get("Effect", [])
            conditions = ev.args.get("Condition", [])
            if not effects:
                continue
            effect_tb = textbounds.get(effects[0])
            if not effect_tb or not effect_tb.logical_id:
                continue

            cond_lids = []
            implicit_lids = []
            for cid in conditions:
                ctb = textbounds.get(cid)
                if ctb and ctb.logical_id:
                    cond_lids.append(ctb.logical_id)
                    if ctb.attrs.get("Implicit") == "True":
                        implicit_lids.append(ctb.logical_id)

            modality = effect_tb.attrs.get("Modality")
            negated = effect_tb.attrs.get("Negated") == "True"

            graph.rules.append(RuleNode(
                rule_id=ev.logical_id,
                effect=effect_tb.logical_id,
                conditions=cond_lids,
                modality=modality,
                negated_effect=negated,
                implicit_conditions=implicit_lids,
            ))

        # ── LEVEL 1 : prefer ───────────────────────────────────────────────
        elif ev.kind == "prefer":
            winners = ev.args.get("Winner", [])
            losers = ev.args.get("Loser", [])
            whens = ev.args.get("When", [])
            if not winners or not losers:
                continue
            winner_ev = events.get(winners[0])
            loser_ev = events.get(losers[0])
            if not winner_ev or not loser_ev:
                continue

            when_lids = []
            for wid in whens:
                wtb = textbounds.get(wid)
                if wtb and wtb.logical_id:
                    when_lids.append(wtb.logical_id)

            # Texte du Marker (trigger)
            marker_tb = textbounds.get(ev.trigger)
            marker_label = marker_tb.text if marker_tb else ""

            graph.prefs.append(PrefNode(
                pref_id=ev.logical_id,
                winner=winner_ev.logical_id,
                loser=loser_ev.logical_id,
                when=when_lids,
                marker_label=marker_label,
            ))

        # ── LEVEL 2 : meta_prefer ──────────────────────────────────────────
        elif ev.kind == "meta_prefer":
            winners = ev.args.get("Winner", [])
            losers = ev.args.get("Loser", [])
            whens = ev.args.get("When", [])
            if not winners or not losers:
                continue
            winner_ev = events.get(winners[0])
            loser_ev = events.get(losers[0])
            if not winner_ev or not loser_ev:
                continue

            when_lids = []
            for wid in whens:
                wtb = textbounds.get(wid)
                if wtb and wtb.logical_id:
                    when_lids.append(wtb.logical_id)

            marker_tb = textbounds.get(ev.trigger)
            marker_label = marker_tb.text if marker_tb else ""

            graph.meta_prefs.append(MetaPrefNode(
                meta_id=ev.logical_id,
                winner=winner_ev.logical_id,
                loser=loser_ev.logical_id,
                when=when_lids,
                marker_label=marker_label,
            ))

    return graph


# ═══════════════════════════════════════════════════════════════════════════
# 5. STYLES DOT
# ═══════════════════════════════════════════════════════════════════════════

# Couleurs de fond par type de nœud
FILL_COLORS = {
    "context":      "#ddeeff",   # bleu clair  — Level 0 conditions
    "option":       "#d5f5e3",   # vert clair  — Level 0 conclusions
    "rule":         "#fff9c4",   # jaune       — Level 0 règle
    "prefer":       "#ead1f5",   # violet clair — Level 1
    "meta_prefer":  "#d2b4de",   # violet foncé — Level 2
    "literal":      "#eeeeee",
}

# Couleurs des arêtes
EDGE_COLORS = {
    "condition": "#2e86c1",   # bleu
    "effect":    "#1a7a40",   # vert foncé
    "winner":    "#7d3c98",   # violet
    "loser":     "#c0392b",   # rouge
    "when":      "#e67e22",   # orange
}

EDGE_STYLES = {
    "condition": "solid",
    "effect":    "solid",
    "winner":    "dashed",
    "loser":     "dashed",
    "when":      "dotted",
}

EDGE_ARROW = {
    "condition": "normal",
    "effect":    "normal",
    "winner":    "open",
    "loser":     "open",
    "when":      "normal",
}


def node_kind_from_lid(lid: str) -> str:
    if re.fullmatch(r"c\d+", lid):   return "context"
    if re.fullmatch(r"o\d+", lid):   return "option"
    if re.fullmatch(r"r\d+", lid):   return "rule"
    if re.fullmatch(r"pr\d+", lid):  return "prefer"
    if re.fullmatch(r"pp\d+", lid):  return "meta_prefer"
    return "literal"


def safe_id(lid: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", lid)
    return f"n_{cleaned}" if cleaned and cleaned[0].isdigit() else (cleaned or "empty")


def dot_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def wrap_label(lid: str, text: str, attrs: dict[str, str] | None = None,
               width: int = 38) -> str:
    """Construit le label affiché dans le nœud."""
    wrapped = "\\n".join(textwrap.wrap(text, width))
    # Badges d'attributs
    badges = []
    if attrs:
        if attrs.get("Implicit") == "True":
            badges.append("[implicit]")
        if attrs.get("Negated") == "True":
            badges.append("[negated]")
        mod = attrs.get("Modality")
        if mod:
            badges.append(f"[{mod}]")
    badge_str = "  " + "  ".join(badges) if badges else ""
    return f"{lid}\\n{wrapped}{badge_str}"


def rule_label(rid: str, modality: str | None, negated: bool) -> str:
    parts = [rid]
    if modality:
        parts.append(f"[{modality}]")
    if negated:
        parts.append("[negated]")
    return "\\n".join(parts)


def pref_label(pid: str, marker: str, level: str) -> str:
    short = marker[:30] + "…" if len(marker) > 30 else marker
    if short:
        return f"{pid}\\n{level}\\n« {short} »"
    return f"{pid}\\n{level}"


# ═══════════════════════════════════════════════════════════════════════════
# 6. LÉGENDE
# ═══════════════════════════════════════════════════════════════════════════

LEGEND_DOT = r"""
  subgraph cluster_legend {
    label="Légende LPP/GORGIAS";
    fontsize=13;
    fontname="Helvetica-Bold";
    style="rounded,filled";
    fillcolor="#fafafa";
    color="#999999";
    margin=18;

    subgraph cluster_leg_levels {
      label="Niveaux LPP";
      fontsize=11;
      fontname=Helvetica;
      style=rounded;
      color="#cccccc";
      margin=12;

      leg_ctx  [label="c1\nContext\n(condition)",
                shape=box, style="rounded,filled",
                fillcolor="#ddeeff", fontsize=9, fontname=Helvetica, width=1.5];
      leg_opt  [label="o1\nOption\n(conclusion)",
                shape=box, style="filled",
                fillcolor="#d5f5e3", fontsize=9, fontname=Helvetica, width=1.5];
      leg_rule [label="r1\nrule\n(Level 0)",
                shape=ellipse, style="filled",
                fillcolor="#fff9c4", fontsize=9, fontname=Helvetica, width=1.5];
      leg_pref [label="pr1\nprefer\n(Level 1)",
                shape=diamond, style="filled",
                fillcolor="#ead1f5", fontsize=9, fontname=Helvetica, width=1.5];
      leg_meta [label="pp1\nmeta_prefer\n(Level 2)",
                shape=diamond, style="filled",
                fillcolor="#d2b4de", fontsize=9, fontname=Helvetica, width=1.5];
      leg_ctx -> leg_opt -> leg_rule -> leg_pref -> leg_meta [style=invis];
    }

    subgraph cluster_leg_edges {
      label="Types d'arêtes";
      fontsize=11;
      fontname=Helvetica;
      style=rounded;
      color="#cccccc";
      margin=12;

      le_s1 [label="", shape=none, width=0.01, height=0.01];
      le_d1 [label="", shape=none, width=0.01, height=0.01];
      le_s2 [label="", shape=none, width=0.01, height=0.01];
      le_d2 [label="", shape=none, width=0.01, height=0.01];
      le_s3 [label="", shape=none, width=0.01, height=0.01];
      le_d3 [label="", shape=none, width=0.01, height=0.01];
      le_s4 [label="", shape=none, width=0.01, height=0.01];
      le_d4 [label="", shape=none, width=0.01, height=0.01];
      le_s5 [label="", shape=none, width=0.01, height=0.01];
      le_d5 [label="", shape=none, width=0.01, height=0.01];

      le_s1 -> le_d1 [label="condition", style=solid,  color="#2e86c1",
                       fontsize=9, fontname=Helvetica, arrowhead=normal];
      le_s2 -> le_d2 [label="effect",    style=solid,  color="#1a7a40",
                       fontsize=9, fontname=Helvetica, arrowhead=normal];
      le_s3 -> le_d3 [label="winner",    style=dashed, color="#7d3c98",
                       fontsize=9, fontname=Helvetica, arrowhead=open];
      le_s4 -> le_d4 [label="loser",     style=dashed, color="#c0392b",
                       fontsize=9, fontname=Helvetica, arrowhead=open];
      le_s5 -> le_d5 [label="when",      style=dotted, color="#e67e22",
                       fontsize=9, fontname=Helvetica, arrowhead=normal];

      le_s1 -> le_s2 -> le_s3 -> le_s4 -> le_s5 [style=invis];
      le_d1 -> le_d2 -> le_d3 -> le_d4 -> le_d5 [style=invis];
    }

    subgraph cluster_leg_attrs {
      label="Attributs";
      fontsize=11;
      fontname=Helvetica;
      style=rounded;
      color="#cccccc";
      margin=12;

      la1 [label="[implicit]\nCondition inventée\n(non présente dans\nle texte source)",
           shape=note, style=filled, fillcolor="#fff3cd",
           fontsize=8, fontname=Helvetica, width=1.8];
      la2 [label="[negated]\nProposition\nsémantiquement\nniée",
           shape=note, style=filled, fillcolor="#fde8e8",
           fontsize=8, fontname=Helvetica, width=1.8];
      la3 [label="[obligatory]\n[permitted]\n[recommended]\n[default]\nModalité déontique\nde l'Option",
           shape=note, style=filled, fillcolor="#e8f8e8",
           fontsize=8, fontname=Helvetica, width=1.8];
      la1 -> la2 -> la3 [style=invis];
    }
  }
"""


# ═══════════════════════════════════════════════════════════════════════════
# 7. GÉNÉRATION DOT
# ═══════════════════════════════════════════════════════════════════════════

def emit_dot(graph: LPPGraph, title: str, add_legend: bool) -> str:
    nodes: dict[str, tuple[str, str]] = {}   # safe_id -> (label_str, kind)
    edges: list[tuple[str, str, str]] = []   # (src_safe, dst_safe, role)

    def ensure_node(lid: str, label: str | None = None) -> None:
        sid = safe_id(lid)
        if sid not in nodes:
            kind = node_kind_from_lid(lid)
            lbl = label or lid
            nodes[sid] = (lbl, kind)

    def add_edge(src: str, dst: str, role: str) -> None:
        edges.append((safe_id(src), safe_id(dst), role))

    # ── Level 0 : rules ───────────────────────────────────────────────────
    for rule in graph.rules:
        # Nœud règle
        ensure_node(rule.rule_id,
                    rule_label(rule.rule_id, rule.modality, rule.negated_effect))

        # Nœud effet (Option)
        opt_text = graph.labels.get(rule.effect, rule.effect)
        opt_attrs = graph.attrs_map.get(rule.effect, {})
        ensure_node(rule.effect,
                    wrap_label(rule.effect, opt_text, opt_attrs))

        eff_role = f"effect ({rule.modality})" if rule.modality else "effect"
        add_edge(rule.rule_id, rule.effect, "effect")

        # Nœuds conditions
        for cid in rule.conditions:
            ctx_text = graph.labels.get(cid, cid)
            ctx_attrs = graph.attrs_map.get(cid, {})
            ensure_node(cid, wrap_label(cid, ctx_text, ctx_attrs))
            add_edge(cid, rule.rule_id, "condition")

    # ── Level 1 : prefer ──────────────────────────────────────────────────
    for pref in graph.prefs:
        ensure_node(pref.pref_id,
                    pref_label(pref.pref_id, pref.marker_label, "prefer"))
        ensure_node(pref.winner)
        ensure_node(pref.loser)
        add_edge(pref.pref_id, pref.winner, "winner")
        add_edge(pref.pref_id, pref.loser,  "loser")
        for wid in pref.when:
            ctx_text = graph.labels.get(wid, wid)
            ctx_attrs = graph.attrs_map.get(wid, {})
            ensure_node(wid, wrap_label(wid, ctx_text, ctx_attrs))
            add_edge(wid, pref.pref_id, "when")

    # ── Level 2 : meta_prefer ─────────────────────────────────────────────
    for mp in graph.meta_prefs:
        ensure_node(mp.meta_id,
                    pref_label(mp.meta_id, mp.marker_label, "meta_prefer"))
        ensure_node(mp.winner)
        ensure_node(mp.loser)
        add_edge(mp.meta_id, mp.winner, "winner")
        add_edge(mp.meta_id, mp.loser,  "loser")
        for wid in mp.when:
            ctx_text = graph.labels.get(wid, wid)
            ctx_attrs = graph.attrs_map.get(wid, {})
            ensure_node(wid, wrap_label(wid, ctx_text, ctx_attrs))
            add_edge(wid, mp.meta_id, "when")

    # ── DOT source ────────────────────────────────────────────────────────
    lines = [
        "digraph LPP {",
        f"  label={dot_quote(title)};",
        "  labelloc=t;",
        "  labeljust=l;",
        "  fontname=\"Helvetica-Bold\";",
        "  fontsize=16;",
        "  graph [rankdir=LR, bgcolor=white, pad=0.8,",
        "         nodesep=0.55, ranksep=1.2, splines=ortho];",
        "  node  [fontname=Helvetica, fontsize=10, margin=\"0.12,0.08\"];",
        "  edge  [fontname=Helvetica, fontsize=9];",
        "",
        "  // ── Level clusters ───────────────────────────────────────────",
        "  subgraph cluster_l0 {",
        "    label=\"Level 0 — Object rules\";",
        "    fontsize=11; fontname=Helvetica;",
        "    style=dashed; color=\"#aaaaaa\"; fillcolor=\"#fdfdf0\";",
    ]

    # Noeuds Level 0 (c*, o*, r*)
    for sid, (lbl, kind) in sorted(nodes.items()):
        if kind not in ("context", "option", "rule"):
            continue
        fill = FILL_COLORS.get(kind, "#eeeeee")
        shape = "ellipse" if kind == "rule" else "box"
        rounded = ",rounded" if kind == "context" else ""
        lines.append(
            f"    {sid} [label={dot_quote(lbl)}, shape={shape},"
            f" style=\"filled{rounded}\", fillcolor=\"{fill}\","
            f" penwidth=1.2];"
        )
    lines.append("  }")

    lines += [
        "",
        "  subgraph cluster_l1 {",
        "    label=\"Level 1 — Preferences\";",
        "    fontsize=11; fontname=Helvetica;",
        "    style=dashed; color=\"#9b59b6\"; fillcolor=\"#fdf5ff\";",
    ]
    for sid, (lbl, kind) in sorted(nodes.items()):
        if kind != "prefer":
            continue
        fill = FILL_COLORS["prefer"]
        lines.append(
            f"    {sid} [label={dot_quote(lbl)}, shape=diamond,"
            f" style=\"filled\", fillcolor=\"{fill}\","
            f" penwidth=1.4];"
        )
    lines.append("  }")

    lines += [
        "",
        "  subgraph cluster_l2 {",
        "    label=\"Level 2 — Meta-preferences\";",
        "    fontsize=11; fontname=Helvetica;",
        "    style=dashed; color=\"#6c3483\"; fillcolor=\"#f5eeff\";",
    ]
    for sid, (lbl, kind) in sorted(nodes.items()):
        if kind != "meta_prefer":
            continue
        fill = FILL_COLORS["meta_prefer"]
        lines.append(
            f"    {sid} [label={dot_quote(lbl)}, shape=diamond,"
            f" style=\"filled\", fillcolor=\"{fill}\","
            f" penwidth=1.6];"
        )
    lines.append("  }")

    # Noeuds non classifiés (literal)
    lines.append("")
    for sid, (lbl, kind) in sorted(nodes.items()):
        if kind != "literal":
            continue
        lines.append(
            f"  {sid} [label={dot_quote(lbl)}, shape=box,"
            f" style=\"filled\", fillcolor=\"{FILL_COLORS['literal']}\"];"
        )

    # Arêtes
    lines.append("")
    lines.append("  // ── Arêtes ──────────────────────────────────────────────")
    for src, dst, role in edges:
        role_key = role.split()[0]
        color = EDGE_COLORS.get(role_key, "#555555")
        style = EDGE_STYLES.get(role_key, "solid")
        arrow = EDGE_ARROW.get(role_key, "normal")
        pw = "2.0" if role_key in ("winner", "loser") else "1.3"
        lines.append(
            f"  {src} -> {dst} [label={dot_quote(role)},"
            f" color=\"{color}\", style={style},"
            f" arrowhead={arrow}, penwidth={pw}];"
        )

    if add_legend:
        lines.append(LEGEND_DOT)

    lines.append("}")
    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# 8. CLI
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("ann_file", type=Path,
                        help="Fichier .ann en entrée")
    parser.add_argument("--output", "-f",
                        choices=["png", "dot"], default="png",
                        help="Format de sortie : png (défaut) ou dot")
    parser.add_argument("-o", "--out-file", type=Path, default=None,
                        help="Fichier de sortie")
    parser.add_argument("--no-legend", action="store_true",
                        help="Supprimer la légende")
    parser.add_argument("--title", type=str, default=None,
                        help="Titre du graphe")
    parser.add_argument("--dpi", type=int, default=250,
                        help="Résolution PNG (défaut : 250)")
    args = parser.parse_args()

    ann_path: Path = args.ann_file
    if not ann_path.exists():
        print(f"Erreur : fichier introuvable : {ann_path}", file=sys.stderr)
        return 1

    title = args.title or ann_path.stem.replace("_", " ").replace("-", " ")

    print("[1/3] Lecture du fichier .ann …")
    textbounds, events = parse_ann(ann_path)
    print(f"      {len(textbounds)} text-bounds, {len(events)} events")

    print("[2/3] Construction du graphe LPP …")
    graph = build_lpp_graph(textbounds, events)
    print(f"      {len(graph.rules)} règle(s)  |  "
          f"{len(graph.prefs)} prefer  |  "
          f"{len(graph.meta_prefs)} meta_prefer")

    dot_content = emit_dot(graph, title, add_legend=not args.no_legend)

    if args.output == "dot":
        out_path = args.out_file or ann_path.with_suffix(".dot")
        out_path.write_text(dot_content, encoding="utf-8")
        print(f"[3/3] DOT généré → {out_path}")
        return 0

    # PNG
    dot_path = ann_path.with_suffix(".dot")
    dot_path.write_text(dot_content, encoding="utf-8")
    out_path = args.out_file or ann_path.with_suffix(".png")

    print(f"[3/3] Rendu PNG via Graphviz (dpi={args.dpi}) …")
    result = subprocess.run(
        ["dot", "-Tpng", f"-Gdpi={args.dpi}", str(dot_path), "-o", str(out_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"\nErreur Graphviz :\n{result.stderr}", file=sys.stderr)
        print("Installe Graphviz : https://graphviz.org/download/", file=sys.stderr)
        return 1

    size_kb = out_path.stat().st_size // 1024
    print(f"      PNG généré → {out_path}  ({size_kb} Ko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
