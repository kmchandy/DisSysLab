# export_to_yaml.py — YAML export/load/validate utilities for AL
"""
Utilities to export the in-memory `network` dict to YAML, load it back,
and validate its structure. Intended to live at: dsl/user_interaction/export_to_yaml.py

Requires: PyYAML (install with `pip install pyyaml`).
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import yaml

# ---- Allowed functions per block type (guardrails) ----
ALLOWED_FUNCTIONS = {
    "generate": {"GenerateFromList", "GenerateFromFile"},
    "transform": {"GPT_Prompt"},
    "record": {"RecordToFile", "RecordToList"},
    "fan-in": {"MergeAsynch", "MergeSynch"},
    "fan-out": {"Broadcast"},
}

# ---- Default ports per block type (for validation & helpful errors) ----
DEFAULT_PORTS = {
    "generator": {"inports": [], "outports": ["out"]},
    "transform": {"inports": ["in"], "outports": ["out"]},
    "record": {"inports": ["in"], "outports": []},
    "fan-in": {"inports": ["in1", "in2"], "outports": ["out"]},
    "fan-out": {"inports": ["in"], "outports": ["out1", "out2"]},
}


def export_to_yaml(network: Dict) -> str:
    """Return a YAML string representing the network."""
    # Keep key order for readability
    return yaml.dump(network, sort_keys=False)


def load_from_yaml(yaml_text: Optional[str] = None, *, file_path: Optional[str] = None) -> Dict:
    """Load and return a network dict from YAML text or file.

    Exactly one of yaml_text or file_path must be provided.
    """
    if (yaml_text is None) == (file_path is None):
        raise ValueError("Provide exactly one of yaml_text or file_path")
    if file_path:
        with open(file_path, "r") as f:
            return yaml.safe_load(f)
    return yaml.safe_load(yaml_text)  # type: ignore[arg-type]


def validate_network(network: Dict) -> List[str]:
    """Return a list of human-friendly error strings. Empty list means valid."""
    errors: List[str] = []

    # 1) Basic structure checks
    if not isinstance(network, dict):
        return ["Network must be a dict"]
    if "blocks" not in network or "connections" not in network:
        return ["Network must have 'blocks' and 'connections'"]

    blocks = network.get("blocks", {})
    connections = network.get("connections", [])

    if not isinstance(blocks, dict):
        errors.append("'blocks' must be a dict")
    if not isinstance(connections, list):
        errors.append("'connections' must be a list")

    # 2) Block validation
    seen_names = set()
    for name, b in blocks.items():
        if name in seen_names:
            errors.append(f"Duplicate block name: {name}")
        seen_names.add(name)
        btype = b.get("type")
        if btype not in DEFAULT_PORTS:
            errors.append(f"Block '{name}': invalid type '{btype}'")
            continue
        # Ensure ports exist; if missing, suggest defaults
        inports = b.get("inports")
        outports = b.get("outports")
        if inports is None or outports is None:
            errors.append(
                f"Block '{name}': missing ports; expected inports/outports for type '{btype}' "
                f"(suggest {DEFAULT_PORTS[btype]})"
            )
        # Function guardrails
        func = b.get("function")
        if func is not None:
            allowed = ALLOWED_FUNCTIONS.get(btype, set())
            if func not in allowed:
                errors.append(
                    f"Block '{name}': function '{func}' not allowed for type '{btype}'. "
                    f"Allowed: {sorted(allowed)}"
                )

    # 3) Connection validation
    for idx, c in enumerate(connections):
        frm = c.get("from")
        to = c.get("to")
        fport = c.get("from_port")
        tport = c.get("to_port")

        if frm not in blocks:
            errors.append(f"Conn[{idx}]: from-block '{frm}' not found")
            continue
        if to not in blocks:
            errors.append(f"Conn[{idx}]: to-block '{to}' not found")
            continue

        frm_type = blocks[frm].get("type")
        to_type = blocks[to].get("type")
        frm_outs = blocks[frm].get("outports") or DEFAULT_PORTS.get(
            frm_type, {}).get("outports", [])
        to_ins = blocks[to].get("inports") or DEFAULT_PORTS.get(
            to_type, {}).get("inports", [])

        if fport not in frm_outs:
            errors.append(
                f"Conn[{idx}]: invalid from_port '{fport}' for '{frm}'. Available: {frm_outs}"
            )
        if tport not in to_ins:
            errors.append(
                f"Conn[{idx}]: invalid to_port '{tport}' for '{to}'. Available: {to_ins}"
            )

    return errors


# ---- Convenience: make missing ports explicit (optional helper) ----

def fill_missing_ports(network: Dict) -> Dict:
    """Return a copy with default inports/outports filled based on type if absent."""
    import copy
    n2 = copy.deepcopy(network)
    for name, b in n2.get("blocks", {}).items():
        btype = b.get("type")
        if btype in DEFAULT_PORTS:
            # no-op for []
            b.setdefault("inports", DEFAULT_PORTS[btype]["inports"])
            # no-op for []
            b.setdefault("outports", DEFAULT_PORTS[btype]["outports"])
    return n2
