# dissyslab/office/make_network.py
#
# Compiles a network.md spec into app.py — a runnable Python file
# that wires together multiple open offices into a larger network.
#
# Usage:
#   python -m dissyslab.office.make_network gallery/org_two_office_news/
#
# The directory must contain a network.md file.
# Each office referenced must already have an app.py generated
# by `dsl build` (or `python -m dissyslab.office.make_office`).

import sys
import json
import re
from pathlib import Path
from anthropic import Anthropic

from dissyslab.office.utils import (
    SOURCE_REGISTRY,
    SINK_REGISTRY,
)

client = Anthropic()


# ── Parser prompt ─────────────────────────────────────────────────────────────

NETWORK_PARSER_PROMPT = """You are a compiler that extracts structured information from a network spec.

A network spec describes how multiple offices are connected together.
It follows this general format:
- "# Network: name" — the network name
- "Sources: source(arg=val), ..." — data sources with optional arguments
- "Sinks: sink, sink(arg=val)" — data sinks with optional arguments
- "Offices:" section — one line per office: "[name] is [path]."
  where path is a folder path like gallery/org_two_office_news/news_monitor
- "Connections:" section — lines like:
    "[source]'s destination is [office]'s [port]."
    "[office]'s [port] is [office]'s [port]."
    "[office]'s [port] is [sink]."

Extract all information and return JSON only, no explanation:
{
  "network_name": "name",
  "sources": [
    {"name": "source_name", "args": {"arg": value}}
  ],
  "sinks": [
    {"name": "sink_name", "args": {"arg": value}}
  ],
  "offices": [
    {"name": "office_name", "path": "gallery/org/office"}
  ],
  "connections": [
    {"from": "name", "from_port": "port_or_destination", "to": "name", "to_port": "port_or_null"}
  ]
}

For connections:
- Sources always have from_port "destination"
- If the receiver is a sink with no port, set to_port to null
- Strip trailing periods from all values
"""


# ── Parse ─────────────────────────────────────────────────────────────────────

def parse_network(network_dir):
    """Call Claude to extract structured JSON from network.md."""
    network_path = Path(network_dir) / "network.md"
    text = open(network_path).read()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=NETWORK_PARSER_PROMPT,
        messages=[{"role": "user", "content": text}]
    )
    raw = response.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(match.group())


# ── Validate ──────────────────────────────────────────────────────────────────

def validate(network):
    """Basic validation of parsed network. Returns list of error strings."""
    errors = []
    known_offices = {o["name"] for o in network["offices"]}
    known_sources = {s["name"] for s in network["sources"]}
    known_sinks = {s["name"] for s in network["sinks"]}
    known_names = known_offices | known_sources | known_sinks

    for office in network["offices"]:
        path = Path(office["path"])
        if not (path / "app.py").exists():
            errors.append(
                f"Office '{office['name']}' has no app.py at {path}. "
                f"Run `dsl build {path}` first."
            )

    for conn in network["connections"]:
        if conn["from"] not in known_names:
            errors.append(
                f"Connection sender '{conn['from']}' is not a known source, office, or sink.")
        if conn["to"] not in known_names:
            errors.append(
                f"Connection receiver '{conn['to']}' is not a known source, office, or sink.")

    for sink in network["sinks"]:
        if sink["name"] not in SINK_REGISTRY:
            errors.append(
                f"Unknown sink '{sink['name']}'. "
                f"Available: {list(SINK_REGISTRY.keys())}"
            )

    for source in network["sources"]:
        if source["name"] not in SOURCE_REGISTRY:
            errors.append(
                f"Unknown source '{source['name']}'. "
                f"Available: {list(SOURCE_REGISTRY.keys())}"
            )

    return errors


# ── Display ───────────────────────────────────────────────────────────────────

def show_routing_table(network):
    """Print human-readable routing table."""
    print()
    print(f"Network: {network['network_name']}")
    print()

    if network["sources"]:
        print("Sources:")
        for s in network["sources"]:
            args = ", ".join(f"{k}={v}" for k, v in s["args"].items())
            print(f"  {s['name']}({args})")

    if network["offices"]:
        print()
        print("Offices:")
        for o in network["offices"]:
            print(f"  {o['name']:<20}  {o['path']}")

    if network["sinks"]:
        print()
        print("Sinks:")
        for s in network["sinks"]:
            print(f"  {s['name']}")

    print()
    print("Connections:")
    for conn in network["connections"]:
        from_port = conn["from_port"]
        to_port = conn["to_port"]
        sender = f"{conn['from']}.{from_port}" if from_port != "destination" else conn["from"]
        receiver = f"{conn['to']}.{to_port}" if to_port else conn["to"]
        print(f"  {sender:<35}  →  {receiver}")
    print()


# ── Generate app.py ───────────────────────────────────────────────────────────

def write_app(network, network_dir):
    """Generate a runnable app.py that wires offices together."""
    network_path = Path(network_dir).resolve()
    app_path = network_path / "app.py"
    network_name = network["network_name"]

    lines = []

    # ── Header ────────────────────────────────────────────────────────────────

    lines += [
        f"# app.py — AUTO-GENERATED by make_network.py",
        f"# Network: {network_name}",
        f"",
    ]

    # ── Topology comment ──────────────────────────────────────────────────────

    lines += ["# Topology:"]
    for conn in network["connections"]:
        from_part = f"{conn['from']}.{conn['from_port']}" if conn["from_port"] != "destination" else conn["from"]
        to_part = f"{conn['to']}.{conn['to_port']}" if conn["to_port"] else conn["to"]
        lines.append(f"#   {from_part}  →  {to_part}")
    lines += ["", ""]

    # ── Imports ───────────────────────────────────────────────────────────────

    rss_sources = [
        s["name"] for s in network["sources"]
        if SOURCE_REGISTRY.get(s["name"], {}).get("type") == "rss"
    ]
    bluesky_sources = [
        s for s in network["sources"]
        if SOURCE_REGISTRY.get(s["name"], {}).get("type") == "bluesky"
    ]
    sink_imports = sorted({
        SINK_REGISTRY[s["name"]]["import"]
        for s in network["sinks"]
    })
    bluesky_imports = [
        SOURCE_REGISTRY[s["name"]]["import"]
        for s in bluesky_sources
    ]

    lines += [
        "from dissyslab import network",
        "from dissyslab.blocks import Source, Sink",
    ]
    if rss_sources:
        lines += [
            "from dissyslab.components.sources.rss_normalizer import " +
            ", ".join(rss_sources)
        ]
    lines += bluesky_imports
    lines += sink_imports

    # Office imports — derived mechanically from folder paths
    lines += [""]
    for office in network["offices"]:
        dotted = office["path"].replace("/", ".")
        name = office["name"]
        lines.append(f"from {dotted}.app import {name}")
    lines += ["", ""]

    # ── Sources ───────────────────────────────────────────────────────────────

    lines += ["# ── Sources " + "─" * 58, ""]
    for source in network["sources"]:
        name = source["name"]
        args = source["args"]
        reg = SOURCE_REGISTRY[name]
        if reg["type"] == "rss":
            arg_str = ", ".join(f"{k}={v}" for k, v in args.items())
            lines += [
                f'_{name} = {name}({arg_str})',
                f'src_{name} = Source(fn=_{name}.run, name="{name}")',
                "",
            ]
        elif reg["type"] == "bluesky":
            arg_str = ", ".join(f"{k}={v}" for k, v in args.items())
            cls = SOURCE_REGISTRY[name]["class"]
            lines += [
                f'_{name} = {cls}({arg_str})',
                f'src_{name} = Source(fn=_{name}.run, name="{name}")',
                "",
            ]
    lines += [""]

    # ── Sinks ─────────────────────────────────────────────────────────────────

    lines += ["# ── Sinks " + "─" * 60, ""]
    for sink in network["sinks"]:
        name = sink["name"]
        args = sink["args"]
        reg = SINK_REGISTRY[name]
        if reg["args"] == "named" and args:
            arg_str = ", ".join(
                f'{k}="{v}"' if isinstance(v, str) else f"{k}={v}"
                for k, v in args.items()
            )
            init = f'{reg["class"]}({arg_str})'
        else:
            init = f'{reg["class"]}()'
        lines += [
            f'_{name} = {init}',
            f'{name} = Sink(fn=_{name}.{reg["call"]}, name="{name}")',
            "",
        ]
    lines += [""]

    # ── Network edges ─────────────────────────────────────────────────────────

    known_sources = {s["name"] for s in network["sources"]}
    known_sinks = {s["name"] for s in network["sinks"]}

    edge_lines = []
    for conn in network["connections"]:
        sender = conn["from"]
        from_port = conn["from_port"]
        receiver = conn["to"]
        to_port = conn["to_port"]

        # Left side of edge
        if sender in known_sources:
            left = f"src_{sender}"
        elif from_port and from_port != "destination":
            left = f"{sender}.{from_port}"
        else:
            left = sender

        # Right side of edge
        if receiver in known_sinks:
            right = receiver
        elif to_port:
            right = f"{receiver}.{to_port}"
        else:
            right = receiver

        edge_lines.append(f"    ({left}, {right}),")

    lines += ["# ── Network " + "─" * 58, ""]
    lines += ["g = network(["]
    lines += edge_lines
    lines += ["])", "", ""]

    # ── Run block ─────────────────────────────────────────────────────────────

    lines += [
        'if __name__ == "__main__":',
        f'    print()',
        f'    print("{network_name.replace("_", " ").title()}")',
        f'    print("=" * 60)',
        f'    print()',
        f'    g.run_network()',
        f'    print()',
        f'    print("Done!")',
        f'    print()',
    ]

    app_path.write_text("\n".join(lines))
    print(f"  ✓ Written to {app_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m dissyslab.office.make_network <network_dir>")
        sys.exit(1)

    network_dir = sys.argv[1]

    print()
    print("Parsing network...")
    net = parse_network(network_dir)

    print()
    print("Validating...")
    errors = validate(net)
    if errors:
        print("Errors found:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("  ✓ All checks passed.")

    show_routing_table(net)

    answer = input("Does this look right? (yes / no): ").strip().lower()
    if answer != "yes":
        print()
        print("Edit your network.md and run the compiler again.")
        sys.exit(0)

    print()
    print("Generating app.py...")
    write_app(net, network_dir)
    print()
    print("Done!")
    print()
    print("Run with:")
    rel = Path(network_dir).parts
    print(f"  python3 -m {'.'.join(rel)}.app")
