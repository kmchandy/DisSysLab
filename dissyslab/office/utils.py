# dissyslab/office/utils.py
"""
Source and sink registries — the catalogue of built-in components.

Used by ``dissyslab.office_v2.compiler`` and
``dissyslab.office_v2.codegen`` to materialise sources and sinks
declared in ``office.md`` (``Sources: hacker_news``,
``Sinks: discard``, …). The registries also auto-load any
user-generated component files dropped into
``components/sources/generated/`` or ``components/sinks/generated/``,
so a previously-generated source persists across sessions.

Why this module persists in v2
==============================

The v2 cutover replaced the LLM-driven parser, validator, and
codegen — those all moved into ``dissyslab.office_v2``. What
remained worth keeping is the *catalogue itself*: the table that
maps a name like ``hacker_news`` to "an RSS source called
``HackerNewsSource`` whose factory takes ``max_articles`` and
``poll_interval``". Migrating every entry into the role library
would be a larger project; until then, ``office_v2`` reaches into
this module to instantiate registry-backed sources and sinks.

Long-run direction
==================

The contents of these registries should eventually become regular
``AgentRoleEntry`` entries in a built-in role library. When that
happens, ``office_v2.compiler._build_source`` /
``_build_sink`` go away and this module shrinks to just
``expand_shortcut`` for MCP plus the
``_load_generated_components`` hook.
"""
from __future__ import annotations

import re
from pathlib import Path


# ── Source Registry ───────────────────────────────────────────────────


SOURCE_REGISTRY = {
    # ── RSS sources ───────────────────────────────────────────────────
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

    # ── BlueSky streaming ─────────────────────────────────────────────
    "bluesky": {
        "type":   "bluesky",
        "import": "from dissyslab.components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource",
        "class":  "BlueSkyJetstreamSource",
    },

    # ── Weather (first-class, no key) ─────────────────────────────────
    "weather": {
        "type":   "weather",
        "import": "from dissyslab.components.sources.weather_source import WeatherSource",
        "class":  "WeatherSource",
    },

    # ── WeatherAPI.com (multi-day forecast, requires API key) ─────────
    # Use this when an office needs a 1–14 day forecast (one message
    # per day) rather than current weather. Free tier available; set
    # WEATHERAPI_KEY in your environment. Contributed by Nyasha.
    "weatherapi": {
        "type":   "weatherapi",
        "import": "from dissyslab.components.sources.weatherapi_source import WeatherAPISource",
        "class":  "WeatherAPISource",
    },

    # ── Stocks (first-class, no key) ──────────────────────────────────
    "stocks": {
        "type":   "stocks",
        "import": "from dissyslab.components.sources.stocks_source import StocksSource",
        "class":  "StocksSource",
    },

    # ── Full MCP source (advanced users) ──────────────────────────────
    "mcp_source": {
        "type":   "mcp",
        "import": "from dissyslab.components.sources.mcp_source import MCPSource",
        "class":  "MCPSource",
    },

    # ── MCP shortcuts (Path A users) ──────────────────────────────────
    "web": {
        "type":        "mcp_shortcut",
        "import":      "from dissyslab.components.sources.mcp_source import MCPSource",
        "class":       "MCPSource",
        "server":      "fetch",
        "tool":        "fetch",
        "arg_map":     {"url": "url"},
        "passthrough": ["poll_interval", "max_items"],
    },
    "search": {
        "type":        "mcp_shortcut",
        "import":      "from dissyslab.components.sources.mcp_source import MCPSource",
        "class":       "MCPSource",
        "server":      "brave_search",
        "tool":        "brave_web_search",
        "arg_map":     {"query": "query"},
        "passthrough": ["poll_interval", "max_items"],
    },

    # ── Gmail and Calendar ────────────────────────────────────────────
    "gmail": {
        "type":   "gmail",
        "import": "from dissyslab.components.sources.gmail_source import GmailSource",
        "class":  "GmailSource",
    },
    "calendar": {
        "type":   "calendar",
        "import": "from dissyslab.components.sources.calendar_source import CalendarSource",
        "class":  "CalendarSource",
    },

    # ── HTTP webhook listener (push-style source) ─────────────────────
    "webhook": {
        "type":   "webhook",
        "import": "from dissyslab.components.sources.webhook_source import WebhookSource",
        "class":  "WebhookSource",
    },
}


# ── Shortcut expansion ────────────────────────────────────────────────


def expand_shortcut(name, user_args):
    """Expand an mcp_shortcut entry into MCPSource constructor kwargs.

    The shortcut's ``arg_map`` translates user-friendly keys to MCP
    argument names; ``passthrough`` keys go to the MCPSource
    constructor as-is (poll_interval, max_items, …).
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


# ── Sink Registry ─────────────────────────────────────────────────────


SINK_REGISTRY = {
    "discard": {
        "import": "from dissyslab.components.sinks.discard import Discard",
        "class":  "Discard",
        "args":   "none",
        "call":   "run",
    },
    "jsonl_recorder": {
        "import": "from dissyslab.components.sinks.sink_jsonl_recorder import JSONLRecorder",
        "class":  "JSONLRecorder",
        "args":   "named",
        "call":   "run",
    },
    # Aliases that allow multiple JSONLRecorder instances in one office.
    # Each alias creates a distinct sink instance sharing the same
    # underlying class. Matches the SOURCE_REGISTRY convention where
    # each RSS feed (bbc_world, al_jazeera, ...) is a distinct name
    # sharing the same RSS implementation. Add more aliases as needed.
    "jsonl_recorder_discard": {
        "import": "from dissyslab.components.sinks.sink_jsonl_recorder import JSONLRecorder",
        "class":  "JSONLRecorder",
        "args":   "named",
        "call":   "run",
    },
    "jsonl_recorder_briefing": {
        "import": "from dissyslab.components.sinks.sink_jsonl_recorder import JSONLRecorder",
        "class":  "JSONLRecorder",
        "args":   "named",
        "call":   "run",
    },
    "jsonl_recorder_archive": {
        "import": "from dissyslab.components.sinks.sink_jsonl_recorder import JSONLRecorder",
        "class":  "JSONLRecorder",
        "args":   "named",
        "call":   "run",
    },
    "jsonl_recorder_raw": {
        "import": "from dissyslab.components.sinks.sink_jsonl_recorder import JSONLRecorder",
        "class":  "JSONLRecorder",
        "args":   "named",
        "call":   "run",
    },
    "console_printer": {
        "import": "from dissyslab.components.sinks.console_display import ConsoleDisplay",
        "class":  "ConsoleDisplay",
        "args":   "none",
        "call":   "run",
    },
    "intelligence_display": {
        "import": "from dissyslab.components.sinks.intelligence_display import IntelligenceDisplay",
        "class":  "IntelligenceDisplay",
        "args":   "named",
        "call":   "run",
    },
    "markdown_digest": {
        "import": "from dissyslab.components.sinks.markdown_digest import MarkdownDigest",
        "class":  "MarkdownDigest",
        "args":   "named",
        "call":   "run",
    },
    "periodic_brief_sink": {
        "import": "from dissyslab.components.sinks.periodic_brief_sink import PeriodicBriefSink",
        "class":  "PeriodicBriefSink",
        "args":   "named",
        "call":   "run",
    },
    "mcp_sink": {
        "import": "from dissyslab.components.sinks.mcp_sink import MCPSink",
        "class":  "MCPSink",
        "args":   "named",
        "call":   "run",
    },
    "gmail_sink": {
        "import": "from dissyslab.components.sinks.gmail_sink import GmailSink",
        "class":  "GmailSink",
        "args":   "named",
        "call":   "run",
    },
    "slack_sink": {
        "import": "from dissyslab.components.sinks.slack_sink import SlackSink",
        "class":  "SlackSink",
        "args":   "named",
        "call":   "run",
    },
    # Aliases that allow multiple SlackSink instances in one office,
    # one per channel. Each alias creates a distinct sink instance
    # sharing the same underlying class. Pair each alias with its own
    # webhook_url_env argument (or the same env var if you want both
    # to point at one channel).
    "slack_sink_alerts": {
        "import": "from dissyslab.components.sinks.slack_sink import SlackSink",
        "class":  "SlackSink",
        "args":   "named",
        "call":   "run",
    },
    "slack_sink_briefing": {
        "import": "from dissyslab.components.sinks.slack_sink import SlackSink",
        "class":  "SlackSink",
        "args":   "named",
        "call":   "run",
    },
    "slack_sink_archive": {
        "import": "from dissyslab.components.sinks.slack_sink import SlackSink",
        "class":  "SlackSink",
        "args":   "named",
        "call":   "run",
    },
    "webhook_sink": {
        "import": "from dissyslab.components.sinks.webhook_sink import WebhookSink",
        "class":  "WebhookSink",
        "args":   "named",
        "call":   "run",
    },
}


# ── Load previously generated components ─────────────────────────────


def _load_generated_components():
    """Auto-register any previously-generated source/sink modules.

    Scans ``components/sources/generated/`` and
    ``components/sinks/generated/`` for ``*_source.py`` /
    ``*_sink.py`` files. For each, it extracts the first
    ``class <ClassName>`` and registers an entry pointing at it.
    Runs once at import time so generated components persist
    across sessions.

    The actual *generation* (asking Claude to write the source/sink
    file) is no longer part of the package; if you have generated
    files left over from a previous workflow they keep working.
    """
    for kind, registry in [
        ("source", SOURCE_REGISTRY),
        ("sink", SINK_REGISTRY),
    ]:
        generated_dir = Path(f"components/{kind}s/generated")
        if not generated_dir.exists():
            continue
        for path in generated_dir.glob(f"*_{kind}.py"):
            name = path.stem.replace(f"_{kind}", "")
            if name in registry:
                continue
            code = path.read_text()
            match = re.search(r"^class\s+(\w+)", code, re.MULTILINE)
            if not match:
                continue
            class_name = match.group(1)
            import_stmt = (
                f"from dissyslab.components.{kind}s.generated."
                f"{name}_{kind} import {class_name}"
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


# Auto-load generated components at import time.
_load_generated_components()


__all__ = [
    "SINK_REGISTRY",
    "SOURCE_REGISTRY",
    "expand_shortcut",
]
