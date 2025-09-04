# dsl/user_interaction/draft_runner.py
"""
Run a "draft" network (blocks + connections) with friendly corrections.

Students write a loose draft:
    draft = {
        "blocks": {
            "gen": {"class": "GenerateFromList",
                    "params": {"items": [{"text": "hi"}, {"text": "there"}], "delay": 0.05}},
            "console": {"class": "ConsolePrettyPrinter",
                        "params": {"sample_size": 5, "title_fallback": "Hello Console"}}
        },
        "connections": [
            ("gen", "", "console", "")
        ]
    }

Then run it:
    from dsl.user_interaction.draft_runner import run_draft
    net, notes = run_draft(draft)

What this does:
- Uses the spec corrector to fix common mistakes (aliases, missing ports/params).
- Prints a tiny "plan" (blocks and connections) so learners see what will run.
- Executes the network.
- Prints any corrections that were applied (so learners learn by seeing).
"""

from __future__ import annotations
from typing import Any, Dict, Tuple, List
from importlib import import_module

from dsl.utils.spec_corrector import correct_spec, KNOWN_BLOCKS
from dsl.core import Network


# -------------------------- helpers ---------------------------------
def _build_block(class_name: str, params: Dict[str, Any]):
    """Import and construct a block by canonical class name (after correction)."""
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
            f"Could not import module '{module}'. "
            "If this block lives behind an optional extra (e.g. [gpt], [ml], [sheets]), "
            "install with:  pip install -e '.[EXTRA]'"
        ) from e
    except AttributeError as e:
        raise AttributeError(
            f"Module '{module}' does not define class '{cls}'."
        ) from e
    return cls_obj(**(params or {}))


def _print_plan(spec: Dict[str, Any]) -> None:
    """Show a tiny plan so students see what's about to run."""
    print("📦 Blocks:")
    for name, b in spec.get("blocks", {}).items():
        cls = b.get("class", "?")
        params = b.get("params", {})
        print(f"  - {name}: {cls}({params})")
    print("🔗 Connections:")
    for c in spec.get("connections", []):
        # Draft may use short forms; by now spec_corrector should have normalized,
        # but we keep it tolerant.
        try:
            a, ap, b, bp = c
        except Exception:
            print(f"  - {c}")
        else:
            ap = ap or "out"
            bp = bp or "in"
            print(f"  - ({a}:{ap}) → ({b}:{bp})")


def _print_notes(notes: List[Any]) -> None:
    """Pretty-print correction notes (dataclass or tuple tolerant)."""
    if not notes:
        print("✅ No corrections needed. Nice!")
        return
    print("\nℹ️  Corrections applied:")
    for n in notes:
        # Support either dataclass with fields or simple dict/tuple
        kind = getattr(n, "kind", None) or (
            n.get("kind") if isinstance(n, dict) else "note")
        before = getattr(n, "before", None) or (
            n.get("before") if isinstance(n, dict) else "")
        after = getattr(n, "after", None) or (
            n.get("after") if isinstance(n, dict) else "")
        note = getattr(n, "note", None) or (
            n.get("note") if isinstance(n, dict) else "")
        print(f"  - [{kind}] {before} → {after}  ({note})")


# -------------------------- main API --------------------------------
def run_draft(
    draft: Dict[str, Any],
    *,
    show_plan: bool = True,
    show_notes: bool = True,
) -> Tuple[Network, List[Any]]:
    """
    Correct, build, and run a draft network.

    Args:
        draft: {
            "blocks": { name: {"class": <str>, "params": <dict>} , ... },
            "connections": [ (from, from_port?, to, to_port?), ... ]
        }
        show_plan:   print blocks & connections before running (default: True)
        show_notes:  print correction notes after running (default: True)

    Returns:
        (net, notes)
          net   : the built Network object (already run)
          notes : list of correction notes produced by the spec corrector

    Raises:
        ValueError / ImportError with friendly hints when something is off.
    """
    if not isinstance(draft, dict) or "blocks" not in draft or "connections" not in draft:
        raise ValueError(
            "Draft must be a dict with keys 'blocks' and 'connections'. "
            "See Chapter 0 examples for a template."
        )

    # 1) Correct/normalize the draft
    spec, notes = correct_spec(draft)

    # 2) Optional: show a tiny plan
    if show_plan:
        print("▶️  Running draft network...\n")
        _print_plan(spec)
        print()

    # 3) Build blocks
    blocks = {}
    for name, b in spec["blocks"].items():
        blocks[name] = _build_block(b["class"], b.get("params", {}))

    # 4) Build & run the network
    net = Network(blocks=blocks, connections=spec["connections"])
    net.compile_and_run()

    # 5) Show correction notes (if any)
    if show_notes:
        _print_notes(notes)

    print("\n✨ Done.\n")
    return net, notes
