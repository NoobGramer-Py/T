"""
Entity relationship graph for T's intelligence system.
Builds a JSON graph connecting people, organisations, domains, IPs, emails, usernames.
Sent to frontend for D3.js interactive visualisation.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Literal
from core.logger import get_logger

log = get_logger("intel.graph")

NodeType = Literal["person", "org", "domain", "ip", "email", "username",
                   "phone", "breach", "password", "location", "social"]

COLORS: dict[str, str] = {
    "person":   "#00ff88",
    "org":      "#00d4ff",
    "domain":   "#a0f4ff",
    "ip":       "#ffb300",
    "email":    "#ff88cc",
    "username": "#cc88ff",
    "phone":    "#ff6600",
    "breach":   "#ff3300",
    "password": "#ff6600",
    "location": "#88ff88",
    "social":   "#0088ff",
}


@dataclass
class Node:
    id:       str
    type:     NodeType
    label:    str
    detail:   str = ""
    ts:       float = field(default_factory=time.time)
    risk:     str = "info"   # info | medium | high | critical


@dataclass
class Edge:
    source: str
    target: str
    label:  str
    weight: int = 1


class IntelGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        self._edges: list[Edge]      = []

    def add_node(self, node_id: str, node_type: NodeType,
                 label: str, detail: str = "", risk: str = "info") -> str:
        """Add or update a node. Returns node_id."""
        nid = _normalise_id(node_id)
        if nid not in self._nodes:
            self._nodes[nid] = Node(id=nid, type=node_type,
                                     label=label, detail=detail, risk=risk)
        else:
            # Update detail if new info
            if detail:
                self._nodes[nid].detail = detail
        return nid

    def add_edge(self, source: str, target: str, label: str, weight: int = 1) -> None:
        src = _normalise_id(source)
        tgt = _normalise_id(target)
        if src not in self._nodes or tgt not in self._nodes:
            return
        # Deduplicate
        if not any(e.source == src and e.target == tgt and e.label == label
                   for e in self._edges):
            self._edges.append(Edge(src, tgt, label, weight))

    def to_dict(self) -> dict:
        return {
            "nodes": [
                {
                    "id":     n.id,
                    "type":   n.type,
                    "label":  n.label,
                    "detail": n.detail,
                    "color":  COLORS.get(n.type, "#888"),
                    "risk":   n.risk,
                    "ts":     n.ts,
                }
                for n in self._nodes.values()
            ],
            "edges": [
                {"source": e.source, "target": e.target,
                 "label": e.label, "weight": e.weight}
                for e in self._edges
            ],
        }

    def clear(self) -> None:
        self._nodes.clear()
        self._edges.clear()

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return len(self._edges)


# ── Output parser — builds graph from Intel stream lines ──────────────────────

def parse_intel_output(lines: list[str], root_id: str, graph: IntelGraph) -> None:
    """
    Parse intelligence output lines and extract entities into the graph.
    Looks for emails, domains, IPs, phone numbers, URLs, usernames.
    """
    email_re    = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    ip_re       = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    domain_re   = re.compile(r"\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}\b")
    phone_re    = re.compile(r"\+?\d[\d\s\-().]{7,}\d")
    breach_re   = re.compile(r"Breach:\s+(\S+)")
    found_re    = re.compile(r"\[(\+|!)\]\s+(\S+)")   # sherlock/maigret hits
    onion_re    = re.compile(r"http://[a-z2-7]{16,56}\.onion[^\s]*")
    paste_re    = re.compile(r"https?://pastebin\.com/\S+")

    text = "\n".join(lines)

    for email in set(email_re.findall(text)):
        nid = graph.add_node(email, "email", email, risk="medium")
        graph.add_edge(root_id, nid, "email")

    for ip in set(ip_re.findall(text)):
        if not ip.startswith("127.") and not ip.startswith("0."):
            nid = graph.add_node(ip, "ip", ip)
            graph.add_edge(root_id, nid, "resolved_to")

    for breach in set(breach_re.findall(text)):
        nid = graph.add_node(f"breach_{breach}", "breach", breach, risk="high")
        graph.add_edge(root_id, nid, "found_in_breach")

    for match in found_re.finditer(text):
        symbol, platform = match.group(1), match.group(2)
        if symbol in ("+", "!"):
            nid = graph.add_node(f"social_{platform}", "social", platform)
            graph.add_edge(root_id, nid, "account_found")

    for onion in set(onion_re.findall(text)):
        nid = graph.add_node(onion, "domain", onion[:40] + "…", risk="info")
        graph.add_edge(root_id, nid, "dark_web_mention")

    for paste in set(paste_re.findall(text)):
        nid = graph.add_node(paste, "breach", "Paste: " + paste[-20:], risk="high")
        graph.add_edge(root_id, nid, "found_in_paste")


# ── Module-level graph ─────────────────────────────────────────────────────────

_graph = IntelGraph()


def get_graph() -> IntelGraph:
    return _graph


def reset_graph() -> None:
    _graph.clear()


def _normalise_id(val: str) -> str:
    return re.sub(r"[^a-zA-Z0-9@._:\-/+]", "_", val)[:80]
