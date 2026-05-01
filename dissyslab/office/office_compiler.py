# dissyslab/office/office_compiler.py
#
# Compiles and runs a closed office from plain English role and office files.
# A closed office has no Inputs/Outputs — it is a complete, runnable network.
#
# Usage (preferred):
#   dsl run gallery/office_name/
#
# Equivalent invocations:
#   python -m dissyslab.office.office_compiler gallery/office_name/
#   python office_compiler.py gallery/office_name/   # deprecated root shim
#
# For open offices (composable black boxes), use `dsl build` instead
# (delegates to dissyslab.office.make_office).

import sys
import json
import time
import importlib
from collections import defaultdict
from pathlib import Path

from dissyslab import network
from dissyslab.blocks import Source, Sink
from dissyslab.blocks.role import Role
from dissyslab.components.transformers.ai_agent import ai_agent

from dissyslab.office.utils import (
    SOURCE_REGISTRY,
    SINK_REGISTRY,
    parse_roles,
    parse_office,
    validate,
    show_routing_table,
    expand_shortcut,
)


# ── Runtime helpers ───────────────────────────────────────────────────────────

def _import_class(import_stmt, class_name):
    """Import a class by its fully qualified module path."""
    module_path = import_stmt.split("import")[0].replace("from ", "").strip()
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class _RunStats:
    """
    Lightweight per-run counters. Read at shutdown to print a summary.

    Threading note: each Role and Sink runs on its own thread, so
    increments race. We don't take a lock — these are advisory counts
    for the end-of-run summary, not authoritative metrics. A missed
    increment here and there is fine.
    """

    def __init__(self):
        self.start_time = time.monotonic()
        self.agent_calls = defaultdict(int)        # name → int
        self.agent_errors = defaultdict(int)       # name → int
        self.agent_routes = defaultdict(            # name → port → int
            lambda: defaultdict(int)
        )
        self.sink_messages = defaultdict(int)      # name → int

    def elapsed_seconds(self) -> float:
        return time.monotonic() - self.start_time


def _make_role_fn(role_name, agent_fn, valid_dests, default_dest, stats):
    """
    Build a role function that calls the AI agent and returns
    a list of (message, destination) pairs.

    The closure captures role_name, agent_fn, default_dest, and stats
    so each role function is independent and contributes to the
    end-of-run summary.
    """
    def role_fn(msg):
        stats.agent_calls[role_name] += 1
        text = json.dumps(msg) if isinstance(msg, dict) else str(msg)
        try:
            raw = agent_fn(text)
            result = raw if isinstance(raw, dict) else json.loads(raw)
            out = {**msg, **result}
            destination = result.get("send_to", default_dest)
            if isinstance(destination, list):
                for dest in destination:
                    stats.agent_routes[role_name][dest] += 1
                return [(out, dest) for dest in destination]
            stats.agent_routes[role_name][destination] += 1
            return [(out, destination)]
        except Exception as e:
            stats.agent_errors[role_name] += 1
            print(f"[{role_name}] Error: {e}")
            return []
    return role_fn


def _wrap_sink_fn(sink_name, fn, stats):
    """Wrap a sink's call so each invocation bumps the per-sink counter."""
    def wrapped(msg):
        stats.sink_messages[sink_name] += 1
        return fn(msg)
    return wrapped


def _format_duration(seconds: float) -> str:
    """Pretty-print elapsed time as e.g. '1m 23s' or '14s'."""
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m {secs}s"


def _print_run_summary(stats: _RunStats, *, interrupted: bool) -> None:
    """
    Print a one-paragraph summary of what the office did. Called from
    the `finally` block in build_and_run() so it runs whether the office
    exits cleanly or via Ctrl-C.

    Goes to stderr so it doesn't pollute stdout if the user is piping
    briefings to a file.
    """
    elapsed = _format_duration(stats.elapsed_seconds())
    header = (
        "Office stopped (Ctrl-C)"
        if interrupted
        else "Office stopped"
    )
    lines = [
        "",
        f"── {header} after {elapsed} ──",
    ]

    if stats.agent_calls:
        lines.append("Agents:")
        for name in sorted(stats.agent_calls):
            calls = stats.agent_calls[name]
            errs = stats.agent_errors.get(name, 0)
            routes = stats.agent_routes.get(name, {})
            err_part = f", {errs} error{'s' if errs != 1 else ''}" if errs else ""
            route_part = ""
            if routes:
                pieces = ", ".join(
                    f"{port}={count}" for port, count in sorted(routes.items())
                )
                route_part = f"  ({pieces})"
            lines.append(
                f"  {name}: {calls} call{'s' if calls != 1 else ''}"
                f"{err_part}{route_part}"
            )

    if stats.sink_messages:
        lines.append("Sinks:")
        for name in sorted(stats.sink_messages):
            count = stats.sink_messages[name]
            lines.append(
                f"  {name}: {count} message{'s' if count != 1 else ''}"
            )

    if not stats.agent_calls and not stats.sink_messages:
        lines.append(
            "No agent calls or sink writes recorded. "
            "Check that the source produced messages and "
            "that the connections in office.md are correct."
        )

    lines.append(
        "Check your Anthropic usage at console.anthropic.com if you "
        "left the office running for a while."
    )
    print("\n".join(lines), file=sys.stderr)


# ── Build and run ─────────────────────────────────────────────────────────────

def build_and_run(roles, office, office_dir):
    """
    Directly construct Python objects from parsed roles and office,
    wire them into a network, and run it.

    No files are written. No text is generated.

    Records counters in a _RunStats object as the network runs, and
    prints a summary of agent calls and sink messages on shutdown
    (whether clean or via Ctrl-C).
    """
    office_path = Path(office_dir)
    stats = _RunStats()

    # Port index: role_name → {destination_name → out_N index}
    port_index = {
        role_name: {dest: i for i, dest in enumerate(role["sends_to"])}
        for role_name, role in roles.items()
    }

    # ── Role-level prompts (shared by all agents that play this role) ────────
    role_prompts = {}            # role_name → compiled system prompt
    role_dests = {}              # role_name → (valid_dests, default_dest)
    for role_name, role in roles.items():
        role_text = open(office_path / "roles" / f"{role_name}.md").read()
        valid_dests = role["sends_to"]
        default_dest = valid_dests[0]
        contract = (
            f'\nReturn JSON only, no explanation, no nested JSON:\n'
            f'{{"send_to": "<one of: {", ".join(valid_dests)}>", '
            f'"text": "<content>"}}'
        )
        role_prompts[role_name] = role_text.strip() + "\n" + contract
        role_dests[role_name] = (valid_dests, default_dest)

    # ── Role nodes ────────────────────────────────────────────────────────────
    # One wrapped role function per *agent* (not per role) so the run-stats
    # counters can distinguish two agents that share a role (e.g. two
    # `analyst`s named Alex and Sam).
    agent_nodes = {}
    for agent in office["agents"]:
        agent_name = agent["name"]
        role_name = agent["role"]
        valid_dests, default_dest = role_dests[role_name]
        agent_fn = ai_agent(role_prompts[role_name])
        wrapped_fn = _make_role_fn(
            agent_name, agent_fn, valid_dests, default_dest, stats
        )
        agent_nodes[agent_name] = Role(
            fn=wrapped_fn,
            statuses=roles[role_name]["sends_to"],
            name=agent_name,
        )

    # ── Sink nodes ────────────────────────────────────────────────────────────
    sink_nodes = {}
    for sink in office["sinks"]:
        name = sink["name"]
        args = sink["args"]
        reg = SINK_REGISTRY[name]
        cls = _import_class(reg["import"], reg["class"])
        obj = cls(**args) if args else cls()
        raw_fn = getattr(obj, reg["call"])
        sink_nodes[name] = Sink(
            fn=_wrap_sink_fn(name, raw_fn, stats), name=name
        )

    # ── Source nodes ──────────────────────────────────────────────────────────
    source_nodes = {}
    for source in office["sources"]:
        name = source["name"]
        args = source["args"]
        reg = SOURCE_REGISTRY[name]

        if reg["type"] == "rss":
            import dissyslab.components.sources.rss_normalizer as rss_normalizer
            factory = getattr(rss_normalizer, name)
            obj = factory(**args)

        elif reg["type"] == "mcp_shortcut":
            # Expand shortcut into full MCPSource kwargs
            kwargs = expand_shortcut(name, args)
            cls = _import_class(reg["import"], reg["class"])
            obj = cls(**kwargs)

        else:
            # handles bluesky, mcp, and any future source types
            cls = _import_class(reg["import"], reg["class"])
            obj = cls(**args) if args else cls()

        source_nodes[name] = Source(fn=obj.run, name=name)

    # ── Edges ─────────────────────────────────────────────────────────────────
    #
    # Connection grammar (per OFFICE_PARSER_PROMPT):
    #   "<source>'s destination is <agent>."
    #     → {"from": "<source>",  "from_port": "destination", "to": ["<agent>"]}
    #     The literal string "destination" is the marker for the (only)
    #     output port of every source. The recipient lives in `to[0]`.
    #
    #   "<agent>'s <port> is <agent-or-sink>."
    #   "<agent>'s <port> are <a> and <b>."
    #     → {"from": "<agent>", "from_port": "<port>", "to": [...]}
    #     `from_port` names a declared output port of the agent's role.
    #
    # The runtime relies on this contract being honored. If the parser
    # produces a different shape we raise a clear error rather than guess.
    edges = []
    for conn in office["connections"]:
        sender = conn["from"]
        from_port = conn["from_port"]
        to_list = conn["to"] or []

        if from_port == "destination":
            # Source → first agent. Sender MUST be a known source.
            if sender not in source_nodes:
                raise ValueError(
                    f"Connection {{'from': '{sender}', 'from_port': "
                    f"'destination', ...}} but '{sender}' is not a "
                    f"declared source. Either add it under Sources in "
                    f"office.md, or — if '{sender}' is an agent — give "
                    f"it an explicit output port name (the literal "
                    f"'destination' marker is reserved for sources)."
                )
            if not to_list:
                raise ValueError(
                    f"Source '{sender}' has no recipient in its "
                    f"connection. Expected: \"{sender}'s destination "
                    f"is <agent>.\""
                )
            recipient = to_list[0]
            if recipient not in agent_nodes:
                raise ValueError(
                    f"Source '{sender}' connects to '{recipient}', "
                    f"which is not a declared agent. Check the "
                    f"Agents section of office.md."
                )
            edges.append((source_nodes[sender], agent_nodes[recipient]))
            continue

        # Agent → agent or sink. Sender must be a known agent; the parser
        # is expected to put the literal port name in `from_port`.
        if sender in source_nodes:
            # Parser drift: a source edge but `from_port` isn't the
            # literal marker "destination". The parser prompt is meant
            # to prevent this; if it still happens, surface it loudly.
            raise ValueError(
                f"Parser produced an unexpected shape for source "
                f"'{sender}': from_port='{from_port}', to={to_list}. "
                f"Expected from_port='destination' (literal marker) "
                f"with the recipient in `to`. This usually means the "
                f"LLM-based parser misread "
                f"\"{sender}'s destination is <agent>.\" Try rerunning, "
                f"or simplify office.md."
            )
        if sender not in agent_nodes:
            raise ValueError(
                f"Connection from unknown sender '{sender}'. Sender "
                f"must be a Source or an Agent declared in office.md."
            )
        sender_node = agent_nodes[sender]
        role_name = next(
            a["role"] for a in office["agents"] if a["name"] == sender
        )
        if from_port not in port_index[role_name]:
            raise ValueError(
                f"Agent '{sender}' (role '{role_name}') has no output "
                f"port named '{from_port}'. Valid ports: "
                f"{list(port_index[role_name].keys())}."
            )
        idx = port_index[role_name][from_port]
        port = getattr(sender_node, f"out_{idx}")
        for to in to_list:
            if to == "discard":
                continue
            to_node = agent_nodes.get(to) or sink_nodes.get(to)
            if to_node is None:
                raise ValueError(
                    f"Agent '{sender}' connects to unknown destination "
                    f"'{to}'. Must be an agent or sink declared in "
                    f"office.md."
                )
            edges.append((port, to_node))

    # ── Run ───────────────────────────────────────────────────────────────────
    g = network(edges)
    interrupted = False
    try:
        g.run_network(timeout=None)
    except KeyboardInterrupt:
        # Clean Ctrl-C path. Re-raise after the summary so callers (the
        # CLI, runpy) still see SystemExit-equivalent behavior.
        interrupted = True
    finally:
        _print_run_summary(stats, interrupted=interrupted)
    if interrupted:
        # Surface as a normal exit code (130 = 128 + SIGINT) rather than
        # letting the traceback bubble up, so the CLI's _explain_failure
        # doesn't print a misleading "dsl run failed" banner over our
        # summary.
        sys.exit(130)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: dsl run <office_dir>")
        print("   or: python -m dissyslab.office.office_compiler <office_dir>")
        sys.exit(1)

    office_dir = sys.argv[1]

    roles = parse_roles(office_dir)
    office = parse_office(office_dir)

    if office["inputs"] or office["outputs"]:
        print()
        print("Error: this is an open office (has Inputs/Outputs).")
        print("Use `dsl build` instead:")
        print(f"  dsl build {office_dir}")
        sys.exit(1)

    errors = validate(roles, office)
    if errors:
        print()
        print("Errors found:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)

    show_routing_table(roles, office)

    answer = input("Does this look right? (yes / no): ").strip().lower()
    if answer != "yes":
        print()
        print("Edit your role or office files and run the compiler again.")
        sys.exit(0)

    print()
    print("🚀 Your office is starting up...")
    print()
    agent_names = ", ".join(
        f"{a['name']} ({a['role']})" for a in office["agents"]
    )
    source_names = ", ".join(s["name"] for s in office["sources"])
    print(f"   Agents:  {agent_names}")
    print(f"   Sources: {source_names}")
    # NOTE: We deliberately do NOT call generate_app() here. The office is
    # constructed and run in memory by build_and_run(); writing app.py to
    # disk is the job of `dsl build` (which uses make_office.py). Calling
    # generate_app() here would regenerate app.py inside every gallery
    # office on every `dsl run`, undoing the pure-English gallery layout.
    print()
    print("   Press Ctrl+C to stop.")
    print("━" * 60)
    print()
    build_and_run(roles, office, office_dir)
