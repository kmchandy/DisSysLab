# office_compiler.py

import sys
import json
import re
from pathlib import Path
from anthropic import Anthropic

client = Anthropic()

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
- "Sources: source(arg=val), ..." — data sources with optional arguments
- "Sinks: sink, sink(arg=val)" — data sinks with optional arguments
- "Agents:" section — one line per agent: "[name] is a [role]."
- "Connections:" section — one line per connection:
    "[source]'s destination is [agent]."
    "[agent]'s [port] is [agent_or_sink]."
    "[agent]'s [port] are [agent_or_sink] and [agent_or_sink]."

For connections, normalize plural port names to singular (copywriters → copywriter).

Return JSON only, no explanation, no nested JSON:
{
  "office_name": "name",
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


# ── Source Registry ────────────────────────────────────────────────────────────
# Add new sources here.
# type "rss"     — factory function from components/sources/rss_normalizer.py
# type "bluesky" — BlueSkyJetstreamSource, true streaming generator

SOURCE_REGISTRY = {
    # RSS normalizer sources
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
    # BlueSky Jetstream — true streaming, no auth needed
    "bluesky": {
        "type":   "bluesky",
        "import": "from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource",
        "class":  "BlueSkyJetstreamSource",
    },
}


# ── Sink Registry ──────────────────────────────────────────────────────────────
# Add new sinks here. Each entry specifies:
#   import  — the import statement to add to app.py
#   class   — the class name to instantiate
#   args    — how to format constructor args ("named" or "none")
#   call    — the method to call for each message

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
    return json.loads(match.group())


def validate(roles, office):
    """Cross-check office against role library. Returns list of error strings."""
    errors = []
    known_agents = {a["name"] for a in office["agents"]}
    known_sinks = {s["name"] for s in office["sinks"]}
    known_destinations = known_agents | known_sinks

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
                    f"Connection destination '{dest}' is not a known agent or sink."
                )

    for sink in office["sinks"]:
        if sink["name"] not in SINK_REGISTRY:
            errors.append(
                f"Unknown sink '{sink['name']}'. "
                f"Available sinks: {list(SINK_REGISTRY.keys())}"
            )

    for source in office["sources"]:
        if source["name"] not in SOURCE_REGISTRY:
            errors.append(
                f"Unknown source '{source['name']}'. "
                f"Available sources: {list(SOURCE_REGISTRY.keys())}"
            )

    return errors


def show_routing_table(roles, office):
    """Print the human-readable routing table."""
    print()
    print("Agents:")
    for agent in office["agents"]:
        role = roles[agent["role"]]
        sends = ", ".join(role["sends_to"])
        print(f"  {agent['name']}  —  {agent['role']}  (sends to: {sends})")

    print()
    print("Routing:")
    for conn in office["connections"]:
        sender = conn["from"]
        dest = conn["destination"]
        to = ", ".join(conn["to"])
        if dest == "destination":
            print(f"  {sender:12}  →  {to}")
        else:
            print(f"  {sender:12}  [{dest}]  →  {to}")


def generate_app(roles, office, office_dir):
    """Generate app.py from confirmed roles and office JSON."""

    office_path = Path(office_dir)
    app_path = office_path / "app.py"

    # Build port index map for each role: destination -> out_N
    port_index = {}
    for role_name, role in roles.items():
        port_index[role_name] = {
            dest: i for i, dest in enumerate(role["sends_to"])
        }

    lines = []

    # ── Header ────────────────────────────────────────────────────────────────
    lines += [
        f"# app.py — AUTO-GENERATED by office_compiler.py",
        f"# Office: {office['office_name']}",
        f"# Roles: {', '.join(roles.keys())}",
        f"#",
        f"# Routing:",
    ]
    for conn in office["connections"]:
        sender = conn["from"]
        dest = conn["destination"]
        to = ", ".join(conn["to"])
        if dest == "destination":
            lines.append(f"#   {sender}  →  {to}")
        else:
            lines.append(f"#   {sender} [{dest}]  →  {to}")
    lines += ["", ""]

    # ── Imports ───────────────────────────────────────────────────────────────
    # Collect RSS and BlueSky sources separately
    rss_sources = [
        s["name"] for s in office["sources"]
        if SOURCE_REGISTRY[s["name"]]["type"] == "rss"
    ]
    bluesky_sources = [
        s for s in office["sources"]
        if SOURCE_REGISTRY[s["name"]]["type"] == "bluesky"
    ]

    sink_imports = sorted({
        SINK_REGISTRY[s["name"]]["import"]
        for s in office["sinks"]
    })

    bluesky_imports = [
        SOURCE_REGISTRY[s["name"]]["import"]
        for s in bluesky_sources
    ]

    base_imports = [
        "import json",
        "import re",
        "",
        "from dsl import network",
        "from dsl.blocks import Source, Sink",
        "from dsl.blocks.role import Role",
        "from components.transformers.ai_agent import ai_agent",
    ]

    if rss_sources:
        base_imports.append(
            "from components.sources.rss_normalizer import " +
            ", ".join(rss_sources)
        )

    lines += base_imports + bluesky_imports + sink_imports + ["", ""]

    # ── Logging ───────────────────────────────────────────────────────────────
    lines += [
        "# ── Logging " + "─" * 58,
        "",
        "_log_file = open('flow.log', 'w')",
        "",
        "def _log(agent, destination, msg):",
        "    line = '─' * 62",
        "    _log_file.write(line + '\\n')",
        "    _log_file.write(f' {agent}  →  {destination}\\n')",
        "    _log_file.write(line + '\\n')",
        "    skip = {'send_to'}",
        "    for k, v in msg.items():",
        "        if k in skip:",
        "            continue",
        "        v_str = str(v)",
        "        if len(v_str) > 80:",
        "            v_str = v_str[:77] + '...'",
        "        _log_file.write(f' {k:<12} {v_str}\\n')",
        "    _log_file.write('\\n')",
        "    _log_file.flush()",
        "",
        "",
    ]

    # ── Role functions ─────────────────────────────────────────────────────────
    for role_name, role in roles.items():
        role_text = open(office_path / "roles" / f"{role_name}.md").read()
        valid_destinations = role["sends_to"]
        default_dest = valid_destinations[0]

        contract = (
            f'\nReturn JSON only, no explanation, no nested JSON:\n'
            f'{{"send_to": "<one of: {", ".join(valid_destinations)}>", '
            f'"text": "<content>"}}'
        )
        prompt = role_text.strip() + "\n" + contract

        lines += [
            f"# ── Role: {role_name} " + "─" * (60 - len(role_name)),
            f"",
            f"_{role_name}_prompt = {json.dumps(prompt)}",
            f"_{role_name}_ai = ai_agent(_{role_name}_prompt)",
            f"",
            f"def {role_name}_fn(msg):",
            f"    text = json.dumps(msg) if isinstance(msg, dict) else str(msg)",
            f"    try:",
            f"        raw    = _{role_name}_ai(text)",
            f"        result = raw if isinstance(raw, dict) else json.loads(raw)",
            f"        out    = {{**msg, **result}}",
            f'        destinations = result.get("send_to", ["{default_dest}"])',
            f"        if isinstance(destinations, str):",
            f"            destinations = [destinations]",
            f"        for dest in destinations:",
            f"            _log('{role_name}', dest, out)",
            f"        return [(out, dest) for dest in destinations]",
            f"    except Exception as e:",
            f'        print(f"[{role_name}] Error: {{e}}")',
            f"        return []",
            f"",
            f"",
        ]

    # ── Sinks ─────────────────────────────────────────────────────────────────
    lines += ["# ── Sinks " + "─" * 60, ""]
    for sink in office["sinks"]:
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

    # ── Sources ───────────────────────────────────────────────────────────────
    lines += ["# ── Sources " + "─" * 58, ""]
    for source in office["sources"]:
        name = source["name"]
        args = source["args"]
        reg = SOURCE_REGISTRY[name]

        if reg["type"] == "rss":
            # RSS: factory function, args passed directly
            arg_str = ", ".join(f"{k}={v}" for k, v in args.items())
            lines += [
                f'_{name} = {name}({arg_str})',
                f'src_{name} = Source(fn=_{name}.run, name="{name}")',
                "",
            ]
        elif reg["type"] == "bluesky":
            # BlueSky: class instantiation, interval for rate limiting
            arg_str = ", ".join(f"{k}={v}" for k, v in args.items())
            lines += [
                f'_{name} = {reg["class"]}({arg_str})',
                f'src_{name} = Source(fn=_{name}.run, name="{name}", interval=10)',
                "",
            ]
    lines += [""]

    # ── Agents ────────────────────────────────────────────────────────────────
    lines += ["# ── Agents " + "─" * 59, ""]
    for agent in office["agents"]:
        agent_name = agent["name"]
        role_name = agent["role"]
        sends_to = roles[role_name]["sends_to"]
        statuses_str = json.dumps(sends_to)
        lines += [
            f'{agent_name} = Role(fn={role_name}_fn, '
            f'statuses={statuses_str}, name="{agent_name}")',
        ]
    lines += ["", ""]

    # ── Network ───────────────────────────────────────────────────────────────
    lines += ["# ── Network " + "─" * 58, ""]
    lines += ["g = network(["]

    for conn in office["connections"]:
        if conn["destination"] == "destination":
            src = f"src_{conn['from']}"
            to = conn["to"][0]
            lines.append(f"    ({src}, {to}),")

    known_agents = {a["name"] for a in office["agents"]}
    for conn in office["connections"]:
        if conn["destination"] == "destination":
            continue
        sender = conn["from"]
        dest_name = conn["destination"]
        if sender in known_agents:
            agent = next(a for a in office["agents"] if a["name"] == sender)
            role_name = agent["role"]
            idx = port_index[role_name][dest_name]
            for to in conn["to"]:
                lines.append(
                    f"    ({sender}.out_{idx}, {to}),  "
                    f"# {dest_name}"
                )

    lines += ["])", "", ""]

    # ── Run ───────────────────────────────────────────────────────────────────
    lines += [
        'if __name__ == "__main__":',
        f'    print()',
        f'    print("{office["office_name"].replace("_", " ").title()}")',
        f'    print("=" * 60)',
        f'    print()',
        f'    g.run_network()',
        f'    _log_file.close()',
        f'    print()',
        f'    print("Done! Flow log written to flow.log")',
        f'    print()',
    ]

    app_code = "\n".join(lines)
    app_path.write_text(app_code)
    print(f"  ✓ Written to {app_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 office_compiler.py gallery/org_name/")
        sys.exit(1)

    office_dir = sys.argv[1]

    print()
    print("Parsing roles...")
    roles = parse_roles(office_dir)

    print()
    print("Parsing office...")
    office = parse_office(office_dir)

    print()
    print("Validating...")
    errors = validate(roles, office)
    if errors:
        print("Errors found:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    print("  ✓ All checks passed.")

    show_routing_table(roles, office)

    print()
    answer = input("Does this look right? (yes / no): ").strip().lower()
    if answer != "yes":
        print()
        print("Edit your role or office files and run the compiler again.")
        sys.exit(0)

    print()
    print("Generating app.py...")
    generate_app(roles, office, office_dir)
    print()
    print("Done! Run your app with:")
    print(
        f"  python3 -m {Path(office_dir).parts[-2]}.{Path(office_dir).parts[-1]}.app")
