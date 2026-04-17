# dissyslab/office/utils.py
#
# Shared utilities for dissyslab.office.office_compiler and
# dissyslab.office.make_office (the implementations behind
# `dsl run` and `dsl build`). Contains all parsing, validation,
# display, and component generation logic. Neither tool should
# duplicate anything here.

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


SOURCE_GENERATION_PROMPT = """You are writing a DisSysLab source component in Python.

A DisSysLab source is a class with a run() generator method that yields
message dicts. Each message dict has these standard keys:
    {
        "source":    str,   # name of the source
        "title":     str,   # headline or subject
        "text":      str,   # main content
        "url":       str,   # link to original, or ""
        "timestamp": str,   # ISO datetime string, or ""
    }

The class must:
1. Accept configuration in __init__ (poll_interval, max_items, etc.)
2. Have a run() generator method that yields dicts forever (or until max_items)
3. Sleep poll_interval seconds between fetches
4. Print progress messages like: [SourceName] Fetching...
5. Handle exceptions gracefully — print error and continue, never crash

Also write a convenience factory function at the bottom:
    def source_name(arg1=default, arg2=default, ...) -> ClassName:
        return ClassName(arg1=arg1, arg2=arg2, ...)

Here is an example of a complete DisSysLab source (Hacker News RSS):

import time
import feedparser

class HackerNewsSource:
    def __init__(self, max_articles=20, poll_interval=None):
        self.max_articles = max_articles
        self.poll_interval = poll_interval

    def run(self):
        while True:
            print("[HackerNews] Fetching...")
            try:
                feed = feedparser.parse("https://hnrss.org/newest")
                entries = feed.entries[:self.max_articles]
                for entry in entries:
                    yield {
                        "source":    "hacker_news",
                        "title":     entry.get("title", ""),
                        "text":      entry.get("summary", ""),
                        "url":       entry.get("link", ""),
                        "timestamp": entry.get("published", ""),
                    }
            except Exception as e:
                print(f"[HackerNews] Error: {e}")
            if self.poll_interval:
                print(f"[HackerNews] Sleeping {self.poll_interval}s...")
                time.sleep(self.poll_interval)
            else:
                break

def hacker_news(max_articles=20, poll_interval=None):
    return HackerNewsSource(max_articles=max_articles, poll_interval=poll_interval)

Write the complete Python file for the requested source. Include all imports.
Return only the Python code — no explanation, no markdown fences.
"""


SINK_GENERATION_PROMPT = """You are writing a DisSysLab sink component in Python.

A DisSysLab sink is a class with a run(msg) method that receives a message dict
and does something with it (saves to database, sends notification, posts to API, etc.).

Each message dict has these standard keys:
    {
        "source":    str,
        "title":     str,
        "text":      str,
        "url":       str,
        "timestamp": str,
    }
Plus any additional fields added by agents upstream.

The class must:
1. Accept configuration in __init__ (endpoint, credentials via env vars, etc.)
2. Have a run(msg) method — NOT a generator, just a regular function
3. Handle exceptions gracefully — print error and continue
4. Never crash the network — always catch exceptions in run()

Also write a convenience factory function at the bottom.

Write the complete Python file. Include all imports.
Return only the Python code — no explanation, no markdown fences.
"""


# ── Source Registry ───────────────────────────────────────────────────────────

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
    "web": {
        "type":        "mcp_shortcut",
        "import":      "from components.sources.mcp_source import MCPSource",
        "class":       "MCPSource",
        "server":      "fetch",
        "tool":        "fetch",
        "arg_map":     {"url": "url"},
        "passthrough": ["poll_interval", "max_items"],
    },
    "search": {
        "type":        "mcp_shortcut",
        "import":      "from components.sources.mcp_source import MCPSource",
        "class":       "MCPSource",
        "server":      "brave_search",
        "tool":        "brave_web_search",
        "arg_map":     {"query": "query"},
        "passthrough": ["poll_interval", "max_items"],
    },

    # ── Gmail and Calendar ────────────────────────────────────────────────────
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


# ── Load previously generated components ─────────────────────────────────────

def _load_generated_components():
    """
    Scan components/sources/generated/ and components/sinks/generated/
    and auto-register any previously generated components.
    Runs once at import time so generated sources/sinks persist across sessions.
    """
    for kind, registry in [("source", SOURCE_REGISTRY), ("sink", SINK_REGISTRY)]:
        generated_dir = Path(f"components/{kind}s/generated")
        if not generated_dir.exists():
            continue
        for path in generated_dir.glob(f"*_{kind}.py"):
            name = path.stem.replace(f"_{kind}", "")
            if name in registry:
                continue
            code = path.read_text()
            match = re.search(r'^class\s+(\w+)', code, re.MULTILINE)
            if not match:
                continue
            class_name = match.group(1)
            import_stmt = (
                f"from components.{kind}s.generated.{name}_{kind} "
                f"import {class_name}"
            )
            if kind == "source":
                registry[name] = {
                    "type":   "generated",
                    "import": import_stmt,
                    "class":  class_name,
                }
            else:
                registry[name] = {
                    "import": import_stmt,
                    "class":  class_name,
                    "args":   "named",
                    "call":   "run",
                }


# Auto-load generated components at import time
_load_generated_components()


# ── Component Generation (Phase 3) ────────────────────────────────────────────

HINT_EXAMPLES = [
    '"Use Open-Meteo API: api.open-meteo.com/v1/forecast — free, no API key"',
    '"Use arXiv API: export.arxiv.org/api/query?search_query=cat:cs.AI"',
    '"Use yfinance library: yf.Ticker(ticker).fast_info gives current price"',
]


def _strip_markdown_fences(code):
    """Remove markdown code fences if Claude wrapped the code in them."""
    code = re.sub(r'^```python\s*\n', '', code.strip())
    code = re.sub(r'\n```\s*$', '', code)
    return code.strip()


def _call_claude_for_component(kind, name, args, hint):
    """Call Claude to generate a source or sink Python file."""
    system = SOURCE_GENERATION_PROMPT if kind == "source" else SINK_GENERATION_PROMPT

    args_desc = ", ".join(f"{k}={repr(v)}" for k,
                          v in args.items()) if args else "no args"
    hint_line = f"\nUser hint: {hint}" if hint else ""

    user_msg = (
        f"Write a DisSysLab {kind} called '{name}'.\n"
        f"The user specified these arguments: {args_desc}\n"
        f"{hint_line}\n"
        f"The factory function at the bottom must be named '{name}'."
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": user_msg}]
    )
    return _strip_markdown_fences(response.content[0].text)


def _summarize_component(kind, name, code):
    """Ask Claude to describe the generated component in plain English."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": (
            f"Describe what this DisSysLab {kind} called '{name}' does "
            f"in 2-3 plain English sentences. No technical terms, no code. "
            f"Just what data it fetches or sends, how often, and what "
            f"information it returns or delivers.\n\n{code}"
        )}]
    )
    return response.content[0].text.strip()


def _test_component(kind, name, code, args):
    """
    Run the generated source once and return a plain English sample,
    or an error message if it fails.
    Only applicable to sources — sinks are not tested.
    """
    if kind != "source":
        return None

    try:
        # Dynamically import and instantiate the generated class
        import importlib.util
        import sys

        # Write to a temp location and import
        generated_dir = Path(f"components/{kind}s/generated")
        file_path = generated_dir / f"{name}_{kind}.py"

        spec = importlib.util.spec_from_file_location(
            f"components.{kind}s.generated.{name}_{kind}",
            file_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        factory = getattr(module, name)
        # Override poll_interval and max_items for test
        test_args = {k: v for k, v in args.items()
                     if k not in ("poll_interval", "max_items")}
        obj = factory(**test_args)

        # Get just one item
        gen = obj.run()
        sample = next(gen)

        # Ask Claude to describe the sample in plain English
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=150,
            messages=[{"role": "user", "content": (
                f"Describe this data sample in 2-3 plain English sentences "
                f"as if explaining to a non-technical person what information "
                f"their office will receive. No code, no field names.\n\n"
                f"{json.dumps(sample, indent=2)}"
            )}]
        )
        return response.content[0].text.strip()

    except Exception as e:
        return f"Could not connect: {e}"


def _get_class_name(code):
    """Extract the first class name from generated Python code."""
    match = re.search(r'^class\s+(\w+)', code, re.MULTILINE)
    return match.group(1) if match else None


def generate_component(kind, name, args, _retry=False):
    """
    Interactively generate a source or sink component.

    Shows plain English description (not code) to the user.
    Tests the connection and shows a sample message.
    Saves to components/{kind}s/generated/{name}_{kind}.py.
    Updates SOURCE_REGISTRY or SINK_REGISTRY in place.
    Generated components persist across sessions via _load_generated_components().

    Returns True if component was generated and registered, False otherwise.
    """
    if not _retry:
        print()
        print(f"  ⚠️  I don't recognize '{name}' as a known {kind}.")
        answer = input(
            f"     Shall I build a connector to this {kind}? (yes / no): "
        ).strip().lower()

        if answer != "yes":
            print()
            print(f"  To add a custom {kind}:")
            print(f"  - Look at examples in components/{kind}s/")
            print(f"  - Copy an existing {kind} as a starting point")
            print(
                f"  - Add it to {'SOURCE' if kind == 'source' else 'SINK'}_REGISTRY in office_utils.py")
            print(f"  - Or describe what you want and ask Claude to build it for you")
            return False

    print()
    print("  A hint helps me find the right data. For example:")
    for ex in HINT_EXAMPLES:
        print(f"    {ex}")
    print()
    hint = input(
        "  Any hints? (single line, press Enter to skip): "
    ).strip()

    print()
    print(f"  Building connector...")

    code = _call_claude_for_component(kind, name, args, hint)
    summary = _summarize_component(kind, name, code)

    print()
    print("  Here's what I'll create:")
    print("  " + "─" * 60)
    for line in summary.splitlines():
        print(f"  {line}")
    print("  " + "─" * 60)
    print()

    confirm = input("  Does this sound right? (yes / no): ").strip().lower()
    if confirm != "yes":
        print()
        retry = input(
            "  Try again with a different hint? (yes / no): "
        ).strip().lower()
        if retry == "yes":
            return generate_component(kind, name, args, _retry=True)
        print(f"  '{name}' connector not built. Edit your office.md and try again.")
        return False

    # Save to generated directory
    generated_dir = Path(f"components/{kind}s/generated")
    generated_dir.mkdir(parents=True, exist_ok=True)
    init_file = generated_dir / "__init__.py"
    if not init_file.exists():
        init_file.write_text("")

    file_path = generated_dir / f"{name}_{kind}.py"
    file_path.write_text(code)
    print(f"  ✓ Connector saved to {file_path}")

    # Register the new component
    class_name = _get_class_name(code)
    if not class_name:
        print(f"  ⚠️  Could not detect class — please add manually to registry.")
        return False

    import_stmt = (
        f"from components.{kind}s.generated.{name}_{kind} import {class_name}"
    )

    if kind == "source":
        SOURCE_REGISTRY[name] = {
            "type":   "generated",
            "import": import_stmt,
            "class":  class_name,
        }
    else:
        SINK_REGISTRY[name] = {
            "import": import_stmt,
            "class":  class_name,
            "args":   "named",
            "call":   "run",
        }

    # Test the connection
    if kind == "source":
        print()
        print(f"  Testing connection to '{name}'...")
        sample_desc = _test_component(kind, name, code, args)
        if sample_desc and not sample_desc.startswith("Could not connect"):
            print(f"  ✓ Connected! Here's a sample of what your office will receive:")
            print()
            print("  " + "─" * 60)
            for line in sample_desc.splitlines():
                print(f"  {line}")
            print("  " + "─" * 60)
            print()
            useful = input(
                "  Does this look useful? (yes / no): "
            ).strip().lower()
            if useful != "yes":
                retry = input(
                    "  Try again with a different hint? (yes / no): "
                ).strip().lower()
                if retry == "yes":
                    file_path.unlink()  # remove saved file
                    return generate_component(kind, name, args, _retry=True)
                print(
                    f"  '{name}' connector removed. Edit your office.md and try again.")
                file_path.unlink()
                return False
        else:
            print(f"  ⚠️  {sample_desc}")
            print(f"  The connector was saved but may need a better hint.")
            print(f"  You can delete {file_path} and recompile to try again.")

    print(f"  ✓ '{name}' connector ready.")
    return True


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
    """
    Cross-check office against role library.
    For unknown sources/sinks, offers to generate them via Claude.
    Returns list of error strings (empty = all good).
    """
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
            generated = generate_component(
                "sink", sink["name"], sink.get("args", {})
            )
            if not generated:
                errors.append(
                    f"Unknown sink '{sink['name']}'. "
                    f"Available: {list(SINK_REGISTRY.keys())}"
                )

    for source in office["sources"]:
        if source["name"] not in SOURCE_REGISTRY:
            generated = generate_component(
                "source", source["name"], source.get("args", {})
            )
            if not generated:
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
            kwargs = expand_shortcut(sname, args)
            cls = reg["class"]
            arg_str = ", ".join(f"{k}={repr(v)}" for k, v in kwargs.items())
            lines.append(f"_{sname} = {cls}({arg_str})")

        else:
            # generated, mcp, bluesky, gmail, calendar, and any future types
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
