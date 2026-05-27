# dissyslab/office/utils.py
"""
Source and sink registries — the catalogue of built-in components.

Used by ``dissyslab.office.compiler`` and
``dissyslab.office.codegen`` to materialise sources and sinks
declared in ``office.md`` (``Sources: hacker_news``,
``Sinks: discard``, …). The registries also auto-load any
user-generated component files dropped into
``components/sources/generated/`` or ``components/sinks/generated/``,
so a previously-generated source persists across sessions.

Why this module persists in v2
==============================

The v2 cutover replaced the LLM-driven parser, validator, and
codegen — those all moved into ``dissyslab.office``. What
remained worth keeping is the *catalogue itself*: the table that
maps a name like ``hacker_news`` to "an RSS source called
``HackerNewsSource`` whose factory takes ``max_articles`` and
``poll_interval``". Migrating every entry into the role library
would be a larger project; until then, ``office`` reaches into
this module to instantiate registry-backed sources and sinks.

Long-run direction
==================

The contents of these registries should eventually become regular
``AgentRoleEntry`` entries in a built-in role library. When that
happens, ``office.compiler._build_source`` /
``_build_sink`` go away and this module shrinks to just
``expand_shortcut`` for MCP plus the
``_load_generated_components`` hook.
"""
from __future__ import annotations

import re
from pathlib import Path


# ── Source Registry ───────────────────────────────────────────────────


SOURCE_REGISTRY = {
    # ── Generic parametric RSS ────────────────────────────────────────
    # The Pat-friendly form. Pat writes:
    #     Sources: rss(url="https://...", name="my_feed", max_articles=5)
    # in office.md. No framework edit, no shortcut name to invent.
    # See ``rss_normalizer.RSSNormalizer`` for the parameter list.
    "rss": {
        "type":   "rss_generic",
        "import": "from dissyslab.components.sources.rss_normalizer import RSSNormalizer",
        "class":  "RSSNormalizer",
    },

    # ── Named RSS shortcuts (use factory functions in rss_normalizer) ─
    # Convenience entries for common feeds. The framework's ``type``
    # field for these is ``"rss"`` (not ``"rss_generic"``), which tells
    # the compiler to call the matching factory function rather than
    # constructing RSSNormalizer directly.
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

    # ── arXiv subject feeds (web-scraped, not RSS) ────────────────────
    # arXiv doesn't expose RSS for "recent submissions" pages, so
    # these wrap an HTML scraper. Each entry resolves to a factory
    # function in ``web_scraper`` (parallel to the RSS pattern above).
    "arxiv_cs_ai":     {"type": "web_scraper_factory"},
    "arxiv_cs_lg":     {"type": "web_scraper_factory"},
    "arxiv_cs_cl":     {"type": "web_scraper_factory"},
    "arxiv_cs_cv":     {"type": "web_scraper_factory"},
    "arxiv_cs_ro":     {"type": "web_scraper_factory"},

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
    # Use aliases when an office watches more than one ticker. Each
    # alias is a distinct source instance backed by the same
    # StocksSource class. Pair each alias with its own ticker:
    #     stocks(ticker="AAPL"), stocks_2(ticker="NVDA"),
    #     stocks_3(ticker="MSFT"), ...
    "stocks": {
        "type":   "stocks",
        "import": "from dissyslab.components.sources.stocks_source import StocksSource",
        "class":  "StocksSource",
    },
    "stocks_2": {
        "type":   "stocks",
        "import": "from dissyslab.components.sources.stocks_source import StocksSource",
        "class":  "StocksSource",
    },
    "stocks_3": {
        "type":   "stocks",
        "import": "from dissyslab.components.sources.stocks_source import StocksSource",
        "class":  "StocksSource",
    },
    "stocks_4": {
        "type":   "stocks",
        "import": "from dissyslab.components.sources.stocks_source import StocksSource",
        "class":  "StocksSource",
    },
    "stocks_5": {
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

    # ── Generic HTTP fetch + BeautifulSoup scrape ─────────────────────
    # Different from `web` (which goes through an MCP server): runs
    # in-process via requests + bs4. Use this when you want to watch
    # an arbitrary URL whose page structure you know enough to give
    # CSS selectors for. Several Pat-facing offices use this —
    # competitor_watch, reading_list_processor.
    "web_scraper": {
        "type":   "web_scraper",
        "import": "from dissyslab.components.sources.web_scraper import WebScraper",
        "class":  "WebScraper",
    },

    # ── File / directory reader ───────────────────────────────────────
    # Reads from a file or a directory of files and yields one message
    # per item (line, record, or file, depending on format). Useful for
    # any "watch a folder of saved URLs / papers / notes / receipts"
    # workflow, and for replaying captured corpus data in tests.
    "file_source": {
        "type":   "file_source",
        "import": "from dissyslab.components.sources.file_source import FileSource",
        "class":  "FileSource",
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
    # ── App-specific sinks (live with their gallery app) ──
    # periodic_brief_sink and periodic_brief_html_sink hardcode the
    # bucket taxonomy (weather, stocks, calendar, gmail, news), the
    # field schema (temp_f, ticker, price, change_pct, ...), and the
    # visual layout of the periodic_brief office. That knowledge
    # belongs to the app, not to the framework — moving the files
    # into gallery/apps/periodic_brief/sinks/ lets components/sinks/
    # stay genuinely generic, and gives Pat a clear model: when she
    # writes her own app-specific renderer, it lives next to the
    # office.md that uses it. The registry still owns name resolution
    # so office.md doesn't need to change.
    # Shared by periodic_brief and periodic_brief_pro (the pro variant
    # uses the same renderer with extra sources).
    "periodic_brief_sink": {
        "import": "from dissyslab.gallery.apps.periodic_brief.sinks.periodic_brief_sink import PeriodicBriefSink",
        "class":  "PeriodicBriefSink",
        "args":   "named",
        "call":   "run",
    },
    "periodic_brief_html_sink": {
        "import": "from dissyslab.gallery.apps.periodic_brief.sinks.periodic_brief_html_sink import PeriodicBriefHtmlSink",
        "class":  "PeriodicBriefHtmlSink",
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


# ── Unified COMPONENT_REGISTRY ────────────────────────────────────────
#
# COMPONENT_REGISTRY is the single name-resolution surface for every
# named Python implementation Pat can reference from office.md.
# Sources, sinks, and Python-implemented agents (transformers) all
# live here. Each entry has a ``kind`` field — exactly one of
# ``"source"``, ``"sink"``, or ``"agent"`` — that tells the compiler
# what runtime wrapper to use.
#
# Position in office.md (Sources:, Sinks:, Agents:) is what actually
# drives code generation. ``kind`` is metadata: the compiler reads
# it to detect Pat mistakes like using a sink in a Sources: section,
# and to produce errors that name the right correction.
#
# For polymorphic components (e.g. a class that can serve as both a
# source and a sink), register two separate entries with different
# names. Same Python class can back both.
#
# **What is NOT here:** LLM-prompt roles (``deduplicator``, ``writer``,
# ``entity_extractor``, ...). Those live in ``dissyslab/roles/`` and
# are loaded by ``load_roles_dir()`` in
# ``dissyslab.office.library``. Pat's local ``roles/`` folder
# also goes through that path. The two surfaces are intentionally
# separate: this registry is for Python implementations, the role
# library is for English LLM prompts.
#
# **Compatibility:** ``SOURCE_REGISTRY`` and ``SINK_REGISTRY`` above
# are still the source of truth during the v1.6 transition;
# ``COMPONENT_REGISTRY`` is derived from them at import time. New
# Python-agent classes can be added directly to either surface —
# any future ``"agent"`` entries belong here (since there is no
# AGENT_REGISTRY).


COMPONENT_REGISTRY: dict = {}


def _build_component_registry() -> None:
    """Derive COMPONENT_REGISTRY from SOURCE_REGISTRY + SINK_REGISTRY.

    Called once at module import. Tags each entry with its ``kind``
    so the compiler can detect Pat misuse (sink-in-Sources, etc.).
    Idempotent if called more than once.
    """
    import warnings

    COMPONENT_REGISTRY.clear()
    for _name, _entry in SOURCE_REGISTRY.items():
        COMPONENT_REGISTRY[_name] = {**_entry, "kind": "source"}
    for _name, _entry in SINK_REGISTRY.items():
        if _name in COMPONENT_REGISTRY:
            # If a name appears in both registries, the framework has
            # an internal inconsistency. Warn at import; pick the sink
            # interpretation (last wins) since SINK_REGISTRY is loaded
            # second here, matching historical compiler behaviour.
            warnings.warn(
                f"COMPONENT_REGISTRY: name {_name!r} appears in both "
                f"SOURCE_REGISTRY and SINK_REGISTRY. Using the sink "
                f"interpretation.",
                stacklevel=2,
            )
        COMPONENT_REGISTRY[_name] = {**_entry, "kind": "sink"}


_build_component_registry()


def lookup_component(name: str):
    """Resolve a component name from the unified COMPONENT_REGISTRY.

    Returns the registry entry as a dict (with at least a ``kind``
    field) or ``None`` if the name is not registered. LLM-prompt
    roles are not in this registry — they are resolved separately
    by the role library
    (``dissyslab.office.library.load_roles_dir``).

    Callers should typically validate ``kind`` after lookup:

        entry = lookup_component(name)
        if entry is None:
            ...   # unknown name
        if entry["kind"] != expected_kind:
            ...   # misused — Pat put a sink in Sources, etc.
    """
    return COMPONENT_REGISTRY.get(name)


__all__ = [
    "COMPONENT_REGISTRY",
    "SINK_REGISTRY",
    "SOURCE_REGISTRY",
    "expand_shortcut",
    "lookup_component",
]
