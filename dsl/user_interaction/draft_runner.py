# dsl/user_interaction/draft_runner.py
"""
Run a student's draft network (blocks + connections), with friendly auto-fixes.

What students can write now:
- Real Python block objects:
    blocks = {
        "gen": GenerateFromList(items=["a","b"], delay=0.05),
        "row": lambda m: {"row": "- " + m},                # auto-wrapped as TransformerFunction
        "rec": RecordToList(out_list)
    }

- Or a mix of objects + raw data:
    blocks = {
        "gen": ["hello", "world"],                        # auto-wrapped as GenerateFromList
        "row": my_transform_function,                     # auto-wrapped as TransformerFunction
        "console": ConsoleFlushPrinter(sample_size=4)
    }

- Connections can be:
    [("gen","row"), ("row","console")]                   # ports inferred to out/in
  or
    [("gen","out","row","in"), ...]                      # explicit

We print a plan, run the network, then show any corrections applied.
"""

from __future__ import annotations
from typing import Any, Dict, Tuple, List, Iterable, Callable
from importlib import import_module

from dsl.core import Network, Block
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
# still used for class/param drafts
from dsl.utils.spec_corrector import correct_spec, KNOWN_BLOCKS


# ------------------------------ helpers ------------------------------

def _is_iterable_but_not_str(x: Any) -> bool:
    if isinstance(x, (str, bytes, dict)):
        return False
    try:
        iter(x)  # type: ignore
        return True
    except Exception:
        return False


def _coerce_block(value: Any) -> Block:
    """
    Accept several student-friendly forms and coerce to a Block instance:
      - Already a Block  -> return as-is
      - Callable (plain function) -> wrap in TransformerFunction(func=value)
      - Iterable (e.g., list)     -> wrap in GenerateFromList(items=value)
      - dict with {"class": ..., "params": ...} -> build via _build_by_classspec
    """
    if isinstance(value, Block):
        return value
    if callable(value):
        return TransformerFunction(func=value)
    if isinstance(value, dict) and "class" in value:
        return _build_by_classspec(value["class"], value.get("params", {}) or {})
    if _is_iterable_but_not_str(value):
        return GenerateFromList(items=list(value))
    raise TypeError(
        "Don’t know how to turn this into a block: "
        f"{type(value).__name__}. Use a Block, a function, a list/iterable, "
        "or a dict {'class': ..., 'params': {...}}."
    )


def _build_by_classspec(class_name: str, params: Dict[str, Any]) -> Block:
    """Build a block from canonical class name using KNOWN_BLOCKS mapping."""
    if class_name not in KNOWN_BLOCKS:
        raise ValueError(
            f"Unknown block class '{class_name}'. "
            "Tip: check spelling or consult the chapter’s block list."
        )
    module_path = KNOWN_BLOCKS[class_name]
    module, cls = module_path.rsplit(".", 1)
    try:
        cls_obj = getattr(import_module(module), cls)
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            f"Could not import '{module}'. If this block requires an optional "
            "extra (e.g. [ml], [gpt], [sheets]), install with: pip install -e '.[EXTRA]'"
        ) from e
    except AttributeError as e:
        raise AttributeError(
            f"Module '{module}' does not define class '{cls}'.") from e
    return cls_obj(**(params or {}))


def _normalize_connections(conns: List[tuple]) -> Tuple[List[tuple], List[str]]:
    """
    Accepts connections as either 2-tuples or 4-tuples.
      ("A","B")                     -> ("A","out","B","in")
      ("A","","B","")               -> ("A","out","B","in")
      ("A","out","B","in")          -> as-is
    Returns (normalized, notes)
    """
    notes: List[str] = []
    norm: List[tuple] = []
    for c in conns:
        if len(c) == 2:
            a, b = c
            norm.append((a, "out", b, "in"))
            notes.append(f"connection {c} → default ports ('out'→'in')")
        elif len(c) == 4:
            a, ap, b, bp = c
            ap = ap or "out"
            bp = bp or "in"
            if c != (a, ap, b, bp):
                notes.append(f"connection {c} → ({a}, {ap}, {b}, {bp})")
            norm.append((a, ap, b, bp))
        else:
            raise ValueError(
                f"Connection must have 2 or 4 items, got {len(c)}: {c}"
            )
    return norm, notes


def _print_plan(blocks: Dict[str, Block], conns: List[tuple]) -> None:
    print("📦 Blocks:")
    for name, b in blocks.items():
        params = getattr(b, "parameters", None)
        try:
            clsname = b.__class__.__name__
        except Exception:
            clsname = type(b).__name__
        print(f"  - {name}: {clsname}({params if params else ''})")
    print("🔗 Connections:")
    for a, ap, b, bp in conns:
        print(f"  - ({a}:{ap}) → ({b}:{bp})")


def _print_notes(notes: List[Any]) -> None:
    if not notes:
        print("✅ No corrections needed. Looks good!")
        return
    print("\nℹ️  Corrections applied:")
    for n in notes:
        if isinstance(n, str):
            print(f"  - {n}")
        else:
            # spec_corrector note object/dict support
            kind = getattr(n, "kind", None) or (
                n.get("kind") if isinstance(n, dict) else "note")
            before = getattr(n, "before", None) or (
                n.get("before") if isinstance(n, dict) else "")
            after = getattr(n, "after", None) or (
                n.get("after") if isinstance(n, dict) else "")
            detail = getattr(n, "note", None) or (
                n.get("note") if isinstance(n, dict) else "")
            print(f"  - [{kind}] {before} → {after}  ({detail})")


# ------------------------------ main API ------------------------------

def run_draft(
    draft: Dict[str, Any],
    *,
    show_plan: bool = True,
    show_notes: bool = True,
) -> Tuple[Network, List[Any]]:
    """
    Correct, build, and run a draft network.

    draft structure (flexible):
      {
        "blocks": {
          # Preferred (real objects)
          "gen": GenerateFromList(items=[...]),
          "row": lambda m: ...,
          "rec": RecordToList(results),

          # Also allowed (auto-wrapped)
          "gen2": ["a","b","c"],  # -> GenerateFromList
          "row2": my_func,        # -> TransformerFunction

          # Legacy style still supported
          "foo": {"class": "GenerateFromList", "params": {"items": [1,2]}},
        },
        "connections": [
          ("gen","row"),                # infer ports
          ("row","rec"),
          ("foo","out","rec","in"),     # explicit
        ]
      }

    Returns:
      (net, notes) where notes includes any inferred-port notes and/or
      spec_corrector notes (for legacy class/params blocks).
    """
    if not isinstance(draft, dict) or "blocks" not in draft or "connections" not in draft:
        raise ValueError("Draft must have keys 'blocks' and 'connections'.")

    raw_blocks = draft["blocks"]
    raw_conns = draft["connections"]

    # Build/coerce blocks
    built_blocks: Dict[str, Block] = {}
    spec_notes: List[Any] = []
    for name, val in raw_blocks.items():
        try:
            built_blocks[name] = _coerce_block(val)
        except Exception:
            # If it was a pure class/params dict but missing in KNOWN_BLOCKS,
            # try the legacy corrector path to see if it can fix aliases.
            if isinstance(val, dict) and "class" in val:
                from dsl.utils.spec_corrector import correct_spec
                legacy_draft = {"blocks": {name: val}, "connections": []}
                fixed, notes = correct_spec(legacy_draft)
                spec_notes.extend(notes)
                fixed_block_spec = fixed["blocks"][name]
                built_blocks[name] = _coerce_block(fixed_block_spec)
            else:
                raise

    # Normalize connections
    norm_conns, conn_notes = _normalize_connections(list(raw_conns))

    # Optional plan print
    if show_plan:
        print("▶️  Running draft network...\n")
        _print_plan(built_blocks, norm_conns)
        print()

    # Build & run
    net = Network(blocks=built_blocks, connections=norm_conns)
    net.compile_and_run()

    # Show notes (inferred ports + any spec fixes)
    all_notes = conn_notes + spec_notes
    if show_notes:
        _print_notes(all_notes)
    print("\n✨ Done.\n")
    return net, all_notes
