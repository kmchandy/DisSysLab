"""Which sources carry text somebody else wrote, and which sinks act.

Why an office needs this at all
-------------------------------
An agent's job can be a paragraph of English run by a language model.
When the message that agent reads was fetched from the open web, the
text it reads was written by a stranger, and a stranger who writes
"ignore your instructions and instead…" is writing to the model, not
to the page. That is prompt injection, and no amount of care in the
role file prevents it: a model that can be instructed can be
instructed by its input.

What *can* be bounded is the damage. An office's **declared** power is
its sinks -- see "What this does not do" below for the word "declared". An office whose sinks all print to a screen or
write a local file cannot attack anything, whatever a model in the
middle is persuaded to say. An office with an email or webhook sink
can. So the question worth asking before a run is not "is this agent
safe" -- unanswerable -- but "can text from the open web reach
something that acts", which is reachability on a graph
``check_wiring`` already computes.

Two classifications, one question each
--------------------------------------
**A source is untrusted** when it carries free text composed by
someone other than the user: news, feeds, search results, scraped
pages, inbound mail, an inbound webhook, another MCP server. It is
trusted when it carries the user's own files or a vendor's structured
numbers -- a CSV on disk, today's temperature, a closing price. The
line is not "did it come over the network". It is "could a person
choose the words".

**A sink is acting** when it affects something outside this machine:
mail, chat, an HTTP call, an MCP tool. It is inert when it writes to
this machine or this screen -- the console, a file, an HTML report.

Both tables are explicit rather than inferred from names. A rule like
"anything ending in ``_sink`` is acting" would be wrong for
``periodic_brief_sink``, and a component whose classification is
guessed is one nobody ever checks. ``test_trust.py`` fails when a
component is registered without an entry here, so adding a component
forces the decision instead of defaulting to one -- the same shape as
``emits:`` on a role.

What this does not do
---------------------
It says nothing about what a role's own code does. A Python role is
free to ``import requests`` and act without going near a sink, and no
table here sees that -- ``role_effects.py`` and W12 are the partial,
import-reading answer to it.

It also cannot tell a well-guarded path from an unguarded one; that is
what a gate would be, and gates are not built. So a finding from this
module is a note about a shape, not a verdict about a risk.
"""
from __future__ import annotations

from typing import Dict, Set

#: Sources carrying free text composed by someone other than the user.
UNTRUSTED_SOURCES: Set[str] = {
    # News and feeds -- anyone can publish into these, and several are
    # arbitrary URLs the user pastes in.
    "al_jazeera",
    "arxiv_cs_ai",
    "arxiv_cs_cl",
    "arxiv_cs_cv",
    "arxiv_cs_lg",
    "arxiv_cs_ro",
    "bbc_tech",
    "bbc_world",
    "hacker_news",
    "mit_tech_review",
    "nasa_news",
    "npr_news",
    "rss",
    "techcrunch",
    "venturebeat_ai",
    # The open web, directly.
    "search",
    "web",
    "web_scraper",
    # Written by other people, by definition.
    "bluesky",
    "gmail",
    "python_jobs",
    "remoteok",
    "we_work_remotely",
    # Market titles on a prediction exchange are composed text, not
    # numbers, even though the prices beside them are not.
    "kalshi",
    # Inbound from anywhere, and from a server this office does not
    # control.
    "webhook",
    "mcp_source",
}

#: Sources carrying the user's own files or a vendor's structured
#: numbers. Trusted for injection purposes only -- see the module
#: docstring; this says nothing about whether the data is *correct*.
TRUSTED_SOURCES: Set[str] = {
    "audio_clip",
    "audio_folder",
    "audio_mic",
    "calendar",
    "console_input",
    "csv_points_source",
    "csv_stock_history",
    "file_source",
    "image_folder",
    "session_starter",
    "session_starter_2",
    "session_starter_3",
    "starter",
    "stocks",
    "stocks_2",
    "stocks_3",
    "stocks_4",
    "stocks_5",
    "weather",
    "weatherapi",
}

#: Sinks that affect something outside this machine.
ACTING_SINKS: Set[str] = {
    "gmail_sink",
    "gmail_sink_cover_letter",
    "gmail_sink_match",
    "gmail_sink_research",
    "gmail_sink_tailor",
    "slack_sink",
    "slack_sink_alerts",
    "slack_sink_archive",
    "slack_sink_briefing",
    "webhook_sink",
    "mcp_sink",
}

#: Sinks that write to this machine or this screen.
INERT_SINKS: Set[str] = {
    "console_printer",
    "debate_display",
    "discard",
    "intelligence_display",
    "job_html_sink",
    "jsonl_recorder",
    "jsonl_recorder_archive",
    "jsonl_recorder_briefing",
    "jsonl_recorder_discard",
    "jsonl_recorder_raw",
    "markdown_digest",
    "periodic_brief_html_sink",
    "periodic_brief_sink",
    "report_html",
    "tutor_session_display",
}

#: What each acting sink actually does, for a message a person can act
#: on. "sends email" beats "is an acting sink".
_WHAT_IT_DOES: Dict[str, str] = {
    "gmail_sink": "sends email",
    "gmail_sink_cover_letter": "sends email",
    "gmail_sink_match": "sends email",
    "gmail_sink_research": "sends email",
    "gmail_sink_tailor": "sends email",
    "slack_sink": "posts to Slack",
    "slack_sink_alerts": "posts to Slack",
    "slack_sink_archive": "posts to Slack",
    "slack_sink_briefing": "posts to Slack",
    "webhook_sink": "calls an outside URL",
    "mcp_sink": "calls an outside tool",
}


def is_untrusted_source(name: str) -> bool:
    """True only for a source known to carry someone else's words.

    An unknown name is *not* untrusted. A check that fired on every
    component it had not heard of would fire on every office someone
    extended, and a check people learn to ignore protects nothing.
    ``test_trust.py`` is what keeps "unknown" from becoming common.
    """
    return name in UNTRUSTED_SOURCES


def is_acting_sink(name: str) -> bool:
    """True only for a sink known to affect something outside."""
    return name in ACTING_SINKS


def what_it_does(name: str) -> str:
    """A plain phrase for an acting sink, for use in a message."""
    return _WHAT_IT_DOES.get(name, "acts outside this machine")


def unclassified(source_names: Set[str], sink_names: Set[str]) -> Dict[str, Set[str]]:
    """Registered names with no entry above. Used by the test."""
    return {
        "sources": set(source_names) - UNTRUSTED_SOURCES - TRUSTED_SOURCES,
        "sinks": set(sink_names) - ACTING_SINKS - INERT_SINKS,
    }
