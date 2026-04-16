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
#
# Three entry types:
#
#   type: "rss"            — handled by rss_normalizer; name is the factory fn
#   type: "mcp"            — full MCPSource; user passes server/tool/args directly
#   type: "mcp_shortcut"   — named shortcut that expands to MCPSource
#                            user writes: web(url="...", poll_interval=300)
#                            compiler expands to:
#                              MCPSource(server=<server>, tool=<tool>,
#                                        args={<arg_map key>: user_value, ...},
#                                        poll_interval=<poll_interval>)
#                            arg_map: maps user arg names → MCPSource args keys
#                            passthrough: args passed directly to MCPSource
#                                         (not wrapped in args={})

SOURCE_REGISTRY = {
    # ── RSS sources ───────────────────────────────────────────────────────────
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

    # ── BlueSky streaming ─────────────────────────────────────────────────────
    "bluesky": {
        "type":   "bluesky",
        "import": "from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource",
        "class":  "BlueSkyJetstreamSource",
    },

    # ── Full MCP source (advanced users) ──────────────────────────────────────
    "mcp_source": {
        "type":   "mcp",
        "import": "from components.sources.mcp_source import MCPSource",
        "class":  "MCPSource",
    },

    # ── MCP shortcuts (Path A users) ──────────────────────────────────────────
    # web(url="https://...", poll_interval=300)
    "web": {
        "type":       "mcp_shortcut",
        "import":     "from components.sources.mcp_source import MCPSource",
        "class":      "MCPSource",
        "server":     "fetch",
        "tool":       "fetch",
        "arg_map":    {"url": "url"},        # user arg → mcp args dict key
        "passthrough": ["poll_interval", "max_items"],
    },

    # search(query="AI news today", poll_interval=3600)
    "search": {
        "type":       "mcp_shortcut",
        "import":     "from components.sources.mcp_source import MCPSource",
        "class":      "MCPSource",
        "server":     "brave_search",
        "tool":       "brave_web_search",
        "arg_map":    {"query": "query"},
        "passthrough": ["poll_interval", "max_items"],
    },
    "gmail": {
        "type":   "gmail",
        "import": "from components.sources.gmail_source import GmailSource",
        "class":  "GmailSource",
    },
    "calendar": {
        "type":   "calendar",
        "import": "from components.sources.calendar_source import CalendarSource",
        "class":  "CalendarSource",
    },
}


# ── Shortcut expansion ────────────────────────────────────────────────────────

def expand_shortcut(name, user_args):
    """
    Expand an mcp_shortcut registry entry into MCPSource constructor kwargs.

    Returns a dict suitable for: MCPSource(**kwargs)

    For example, web(url="https://example.com", poll_interval=300) expands to:
        MCPSource(server="fetch", tool="fetch",
                  args={"url": "https://example.com"},
                  poll_interval=300)
    """
    reg = SOURCE_REGISTRY[name]
    mcp_args = {}
    passthrough_kwargs = {}

    for user_key, user_val in user_args.items():
        if user_key in reg.get("passthrough", []):
            passthrough_kwargs[user_key] = user_val
        elif user_key in reg.get("arg_map", {}):
            mapped_key = reg["arg_map"][user_key]
            if mapped_key is not None:
                mcp_args[mapped_key] = user_val

    return {
        "server": reg["server"],
        "tool":   reg["tool"],
        "args":   mcp_args,
        **passthrough_kwargs,
    }


# ── Sink Registry ─────────────────────────────────────────────────────────────

SINK_REGISTRY = {
    "discard": {
        "import": "from components.sinks.discard import Discard",
        "class":  "Discard",
        "args":   "none",
        "call":   "run",
    },
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
    "mcp_sink": {
        "import": "from components.sinks.mcp_sink import MCPSink",
        "class":  "MCPSink",
        "args":   "named",
        "call":   "run",
    },
    "gmail_sink": {
        "import": "from components.sinks.gmail_sink import GmailSink",
        "class":  "GmailSink",
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
        role = parse_role(path)
        roles[role["role_name"]] = role
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


# ── Code Generation ───────────────────────────────────────────────────────────

def generate_app(roles, office, office_dir):
    """
    Write a standalone app.py into the office directory.
    The user can run this directly without recompiling.
    """
    office_path = Path(office_dir)
    office_name = office["office_name"]

    lines = []

    # Header
    lines += [
        f"# app.py — {office_name}",
        f"# Generated by office_compiler.py",
        f"# Run: python3 {office_path}/app.py",
        f"#",
        f"# Edit your role or office files and recompile to regenerate.",
        f"",
        f"import json",
        f"from dsl import network",
        f"from dsl.blocks import Source, Sink",
        f"from dsl.blocks.role import Role",
        f"from components.transformers.ai_agent import ai_agent",
        f"",
    ]

    # Sink imports
    seen_imports = set()
    for sink in office["sinks"]:
        reg = SINK_REGISTRY[sink["name"]]
        imp = reg["import"]
        if imp not in seen_imports:
            lines.append(imp)
            seen_imports.add(imp)

    # Source imports
    for source in office["sources"]:
        reg = SOURCE_REGISTRY[source["name"]]
        if reg["type"] == "rss":
            imp = "import components.sources.rss_normalizer as rss_normalizer"
        else:
            imp = reg["import"]
        if imp not in seen_imports:
            lines.append(imp)
            seen_imports.add(imp)

    lines += ["", ""]

    # Role functions
    lines.append("# ── Role functions ───────────────────────────────────────")
    lines.append("")
    for role_name, role in roles.items():
        role_text = open(office_path / "roles" / f"{role_name}.md").read()
        valid_dests = role["sends_to"]
        default_dest = valid_dests[0]
        contract = (
            f'\\nReturn JSON only, no explanation, no nested JSON:\\n'
            f'{{"send_to": "<one of: {", ".join(valid_dests)}>", '
            f'"text": "<content>"}}'
        )
        prompt = role_text.strip() + "\\n" + contract
        prompt_repr = repr(prompt)

        lines += [
            f"_{role_name}_agent = ai_agent({prompt_repr})",
            f"",
            f"def _{role_name}_fn(msg):",
            f"    text = json.dumps(msg) if isinstance(msg, dict) else str(msg)",
            f"    try:",
            f"        raw = _{role_name}_agent(text)",
            f"        result = raw if isinstance(raw, dict) else json.loads(raw)",
            f"        out = {{**msg, **result}}",
            f"        destination = result.get('send_to', {repr(default_dest)})",
            f"        if isinstance(destination, list):",
            f"            return [(out, dest) for dest in destination]",
            f"        return [(out, destination)]",
            f"    except Exception as e:",
            f"        print(f'[{role_name}] Error: {{e}}')",
            f"        return []",
            f"",
        ]

    lines += ["", "# ── Nodes ────────────────────────────────────────────────", ""]

    # Port index
    port_index = {
        rn: {dest: i for i, dest in enumerate(r["sends_to"])}
        for rn, r in roles.items()
    }

    # Agent nodes
    for agent in office["agents"]:
        aname = agent["name"]
        rname = agent["role"]
        statuses = repr(roles[rname]["sends_to"])
        lines.append(
            f"{aname} = Role(fn=_{rname}_fn, statuses={statuses}, name={repr(aname)})"
        )
    lines.append("")

    # Sink nodes
    for sink in office["sinks"]:
        sname = sink["name"]
        args = sink["args"]
        reg = SINK_REGISTRY[sname]
        cls = reg["class"]
        if args:
            arg_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
            lines.append(f"_{sname} = {cls}({arg_str})")
        else:
            lines.append(f"_{sname} = {cls}()")
        lines.append(
            f"{sname} = Sink(fn=_{sname}.{reg['call']}, name={repr(sname)})"
        )
    lines.append("")

    # Source nodes
    for source in office["sources"]:
        sname = source["name"]
        args = source["args"]
        reg = SOURCE_REGISTRY[sname]

        if reg["type"] == "rss":
            if args:
                arg_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                lines.append(f"_{sname} = rss_normalizer.{sname}({arg_str})")
            else:
                lines.append(f"_{sname} = rss_normalizer.{sname}()")

        elif reg["type"] == "mcp_shortcut":
            # Expand shortcut into full MCPSource kwargs
            kwargs = expand_shortcut(sname, args)
            cls = reg["class"]
            arg_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
            lines.append(f"_{sname} = {cls}({arg_str})")

        else:
            # mcp, bluesky, and any future types
            cls = reg["class"]
            if args:
                arg_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                lines.append(f"_{sname} = {cls}({arg_str})")
            else:
                lines.append(f"_{sname} = {cls}()")

        lines.append(
            f"{sname} = Source(fn=_{sname}.run, name={repr(sname)})"
        )
    lines.append("")

    # Edges
    lines += ["# ── Network ──────────────────────────────────────────────", ""]
    lines.append("edges = [")
    for conn in office["connections"]:
        sender = conn["from"]
        dest_name = conn["destination"]
        to_list = conn["to"]
        if dest_name == "destination":
            lines.append(f"    ({sender}, {to_list[0]}),")
        else:
            rname = next(
                a["role"] for a in office["agents"] if a["name"] == sender
            )
            idx = port_index[rname][dest_name]
            for to in to_list:
                if to == "discard":
                    continue
                lines.append(f"    ({sender}.out_{idx}, {to}),")
    lines.append("]")
    lines.append("")

    # Run
    lines += [
        "if __name__ == '__main__':",
        f"    print('🚀 Starting {office_name}...')",
        f"    print('   Press Ctrl+C to stop.')",
        f"    print('━' * 60)",
        f"    print()",
        f"    g = network(edges)",
        f"    g.run_network()",
    ]

    # Write file
    app_path = office_path / "app.py"
    app_path.write_text("\n".join(lines) + "\n")
    print(f"   Saved: {app_path}")
