from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import difflib

KNOWN_BLOCKS = {
    "GenerateFromList": "dsl.block_lib.stream_generators.GenerateFromList",
    "TransformerFunction": "dsl.block_lib.stream_transformers.TransformerFunction",
    "RecordToList": "dsl.block_lib.stream_recorders.RecordToList",
    "BatchOutput": "dsl.connector_lib.outputs.batch_output.BatchOutput",
    "InputConnectorRSS": "dsl.connector_lib.inputs.rss.InputConnectorRSS",
    "InputConnectorFile": "dsl.connector_lib.inputs.file.InputConnectorFile",
    "OutputConnectorFileMarkdown": "dsl.connector_lib.outputs.file_md.OutputConnectorFileMarkdown",
    "ConsolePrettyPrinter": "dsl.connector_lib.outputs.console_pretty.ConsolePrettyPrinter",
}

# Fuzzy aliases students might type:
ALIASES = {
    "Batcher": "BatchOutput",
    "FunctionToBlock": "TransformerFunction",
    "ConsolePrinter": "ConsolePrettyPrinter",
    "InputRSS": "InputConnectorRSS",
    "InputFile": "InputConnectorFile",
    "OutputMarkdown": "OutputConnectorFileMarkdown",
}

DEFAULT_PORTS = {
    "GenerateFromList": ([], ["out"]),
    "TransformerFunction": (["in"], ["out"]),
    "RecordToList": (["in"], []),
    "BatchOutput": (["in"], ["out"]),
    "InputConnectorRSS": (["in"], ["out"]),
    "InputConnectorFile": (["in"], ["out"]),
    "OutputConnectorFileMarkdown": (["in"], []),
    "ConsolePrettyPrinter": (["in"], []),
}


@dataclass
class Correction:
    kind: str
    before: str
    after: str
    note: str


def _closest(name: str) -> str | None:
    pool = list(KNOWN_BLOCKS) + list(ALIASES)
    matches = difflib.get_close_matches(name, pool, n=1, cutoff=0.65)
    return matches[0] if matches else None


def correct_spec(draft: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Correction]]:
    """
    Accepts a dict with keys 'blocks' and 'connections'.
    Returns (corrected_spec, corrections).
    """
    corrections: List[Correction] = []
    blocks = dict(draft.get("blocks", {}))
    connections = list(draft.get("connections", []))

    corrected_blocks: Dict[str, Any] = {}
    for name, b in blocks.items():
        cls = b.get("class") or b.get("__class__") or b.get("type")
        params = dict(b.get("params", {}))

        # Normalize class name: alias → canonical; fuzzy match → canonical
        if cls in ALIASES:
            corrections.append(Correction(
                "alias", cls, ALIASES[cls], f"Aliased block class '{cls}' → '{ALIASES[cls]}'"))
            cls = ALIASES[cls]
        if cls not in KNOWN_BLOCKS:
            guess = _closest(cls) if cls else None
            if guess:
                corrections.append(Correction("fuzzy", str(
                    cls), guess, f"Guessed block class '{cls}' → '{guess}'"))
                cls = guess
            else:
                raise ValueError(
                    f"Unknown block class: {cls} for block '{name}'")

        # Default parameters (minimal examples)
        if cls == "BatchOutput" and "N" not in params:
            params["N"] = 50
            corrections.append(Correction(
                "default-param", f"{name}.N", "50", "Defaulted BatchOutput.N to 50"))

        corrected_blocks[name] = {"class": cls, "params": params}

    # Ports: fill missing port names if block has single in/out
    norm_conns = []
    for (fb, fp, tb, tp) in connections:
        if fb not in corrected_blocks or tb not in corrected_blocks:
            raise ValueError(
                f"Connection refers to unknown blocks: {(fb, tb)}")
        f_cls = corrected_blocks[fb]["class"]
        t_cls = corrected_blocks[tb]["class"]
        inports, outports = DEFAULT_PORTS[t_cls][0], DEFAULT_PORTS[f_cls][1]
        # Fill missing
        fp2 = fp or (DEFAULT_PORTS[f_cls][1][0]
                     if DEFAULT_PORTS[f_cls][1] else "out")
        tp2 = tp or (DEFAULT_PORTS[t_cls][0][0]
                     if DEFAULT_PORTS[t_cls][0] else "in")
        if fp != fp2:
            corrections.append(Correction(
                "default-port", f"{fb}.{fp}", f"{fb}.{fp2}", "Filled missing/unknown from-port"))
        if tp != tp2:
            corrections.append(Correction(
                "default-port", f"{tb}.{tp}", f"{tb}.{tp2}", "Filled missing/unknown to-port"))
        norm_conns.append((fb, fp2, tb, tp2))

    corrected = {"blocks": corrected_blocks, "connections": norm_conns}
    return corrected, corrections
