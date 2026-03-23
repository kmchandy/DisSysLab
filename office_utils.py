# office_utils.py
#
# Shared utilities for office_compiler.py and make_office.py.
# Contains all parsing, validation, and display logic.
# Neither tool should duplicate anything here.

import json
import re
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()


# ── Prompts ───────────────────────────────────────────────────────────────────

ROLE_PARSER_PROMPT = """You are a compiler that extracts structured information from a role description.

A role description describes a job. The role receives one message and responds
by sending zero or more messages, each addressed to a destination role.

Extract:
1. role_name — from the # Role: heading or the opening sentence
2. sends_to — inferred from anywhere in the description where a message is
   explicitly sent to a named destination. Only include a destination if it
   is explicitly stated in the description.

Return JSON only, no explanation, no nested JSON:
{
  "role_name": "name",
  "sends_to": ["destination1", "destination2"]
}"""


OFFICE_PARSER_PROMPT = """You are a compiler that extracts structured information from an office spec.

An office spec follows this format:
- "# Office: name" — the office name
- "Inputs: port, ..." — optional external input port names (for open offices)
- "Outputs: port, ..." — optional external output port names (for open offices)
- "Sources: source(arg=val), ..." — optional data sources with optional arguments
- "Sinks: sink, sink(arg=val)" — optional data sinks with optional arguments
- "Agents:" section — one line per agent: "[name] is a [role]."
- "Connections:" section — one line per connection:
    "[source_or_input]'s destination is [agent]."
    "[agent]'s [port] is [agent_or_sink_or_output]."
    "[agent]'s [port] are [agent_or_sink_or_output] and [agent_or_sink_or_output]."

For connections, normalize plural port names to singular (copywriters → copywriter).

Return JSON only, no explanation, no nested JSON:
{
  "office_name": "name",
  "inputs": ["port_name"],
  "outputs": ["port_name"],
  "sources": [
    {"name": "source_name", "args": {"arg": value}}
  ],
  "sinks": [
    {"name": "sink_name", "args": {"arg": value}}
  ],
  "agents": [
    {"name": "agent_name", "role": "role_name"}
  ],
  "connections": [
    {"from": "name", "destination": "port_name", "to": ["name"]}
  ]
}"""


# ── Source Registry ───────────────────────────────────────────────────────────

SOURCE_REGISTRY = {
    "al_jazeera":      {"type": "rss"},
    "bbc_world":       {"type": "rss"},
    "bbc_tech":        {"type": "rss"},
    "npr_news":        {"type": "rss"},
    "hacker_news":     {"type": "rss"},
    "techcrunch":      {"type": "rss"},
    "mit_tech_review": {"type": "rss"},
    "venturebeat_ai":  {"type": "rss"},
    "nasa_news":       {"type": "rss"},
    "python_jobs":     {"type": "rss"},
    "bluesky": {
        "type":    "bluesky",
        "import":  "from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource",
        "class":   "BlueSkyJetstreamSource",
    },
}


# ── Sink Registry ─────────────────────────────────────────────────────────────

SINK_REGISTRY = {
    "jsonl_recorder": {
        "import": "from components.sinks.sink_jsonl_recorder import JSONLRecorder",
        "class":  "JSONLRecorder",
        "args":   "named",
        "call":   "run",
    },
    "console_printer": {
        "import": "from components.sinks.console_display import ConsoleDisplay",
        "class":  "ConsoleDisplay",
        "args":   "none",
        "call":   "run",
    },
    "intelligence_display": {
        "import": "from components.sinks.intelligence_display import IntelligenceDisplay",
        "class":  "IntelligenceDisplay",
        "args":   "named",
        "call":   "run",
    },
}


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_role(role_path):
    """Call Claude to extract role_name and sends_to from one role file."""
    text = open(role_path).read()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=ROLE_PARSER_PROMPT,
        messages=[{"role": "user", "content": text}]
    )
    raw = response.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    return json.loads(match.group())


def parse_roles(office_dir):
    """Parse all role files in roles/ subdirectory. Returns dict keyed by role_name."""
    roles_dir = Path(office_dir) / "roles"
    role_files = sorted(roles_dir.glob("*.md"))
    roles = {}
    for path in role_files:
        print(f"  Parsing role: {path.name}")
        role = parse_role(path)
        roles[role["role_name"]] = role
        print(f"    role_name: {role['role_name']}")
        print(f"    sends_to:  {role['sends_to']}")
    return roles


def parse_office(office_dir):
    """Call Claude to extract structured JSON from office.md."""
    office_path = Path(office_dir) / "office.md"
    text = open(office_path).read()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=OFFICE_PARSER_PROMPT,
        messages=[{"role": "user", "content": text}]
    )
    raw = response.content[0].text
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    parsed = json.loads(match.group())
    parsed.setdefault("inputs", [])
    parsed.setdefault("outputs", [])
    return parsed


# ── Validation ────────────────────────────────────────────────────────────────

def validate(roles, office):
    """Cross-check office against role library. Returns list of error strings."""
    errors = []
    known_agents = {a["name"] for a in office["agents"]}
    known_sinks = {s["name"] for s in office["sinks"]}
    known_outputs = set(office.get("outputs", []))
    known_destinations = known_agents | known_sinks | known_outputs | {
        "discard"}

    for agent in office["agents"]:
        if agent["role"] not in roles:
            errors.append(
                f"Agent '{agent['name']}' has role '{agent['role']}' "
                f"which is not in the role library."
            )

    for conn in office["connections"]:
        sender = conn["from"]
        port = conn["destination"]
        if sender in known_agents:
            agent = next(a for a in office["agents"] if a["name"] == sender)
            role_name = agent["role"]
            if role_name in roles:
                valid_ports = roles[role_name]["sends_to"]
                if port != "destination" and port not in valid_ports:
                    errors.append(
                        f"Connection from '{sender}' uses port '{port}' "
                        f"but role '{role_name}' declares: {valid_ports}"
                    )
        for dest in conn["to"]:
            if dest not in known_destinations:
                errors.append(
                    f"Connection destination '{dest}' is not a known "
                    f"agent, sink, output port, or 'discard'."
                )

    for sink in office["sinks"]:
        if sink["name"] not in SINK_REGISTRY:
            errors.append(
                f"Unknown sink '{sink['name']}'. "
                f"Available: {list(SINK_REGISTRY.keys())}"
            )

    for source in office["sources"]:
        if source["name"] not in SOURCE_REGISTRY:
            errors.append(
                f"Unknown source '{source['name']}'. "
                f"Available: {list(SOURCE_REGISTRY.keys())}"
            )

    return errors


# ── Display ───────────────────────────────────────────────────────────────────

def show_routing_table(roles, office):
    """Print the human-readable routing table."""
    print()
    print(f"Office: {office['office_name']}")

    if office["inputs"]:
        print(f"Inputs:  {', '.join(office['inputs'])}")
    if office["outputs"]:
        print(f"Outputs: {', '.join(office['outputs'])}")

    print()
    print("Agents:")
    for agent in office["agents"]:
        role = roles[agent["role"]]
        sends = ", ".join(role["sends_to"])
        print(f"  {agent['name']:<12}  {agent['role']:<16}  sends to: {sends}")

    print()
    print("Routing:")
    for conn in office["connections"]:
        sender = conn["from"]
        dest = conn["destination"]
        to = ", ".join(conn["to"])
        if dest == "destination":
            print(f"  {sender:<16}  →  {to}")
        else:
            print(f"  {sender:<16}  [{dest}]  →  {to}")
    print()
