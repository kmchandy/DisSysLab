"""Text from the open web reaching something that acts.

The office below parses today, runs today, and `dsl check` reported it
as fine:

    Sources: web_scraper(url="...")
    Agents:  Alice is a summarizer.
    Sinks:   gmail_sink

A scraped page is written by a stranger. `summarizer` is a paragraph of
English run by a language model. A model that can be instructed can be
instructed by its input, so no wording of that paragraph closes the
path -- what can be closed is the other end. An office affects the
world only through its sinks, and an office whose sinks all print or
write a local file cannot attack anything however persuaded the middle
is.

So W11 asks the only question that is decidable here: can an untrusted
source reach an acting sink. It is reachability on the graph W3 and W4
already build.
"""
from __future__ import annotations

from pathlib import Path

from dissyslab.office import trust
from dissyslab.office.utils import SINK_REGISTRY, SOURCE_REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[2]


# ── every component is classified ─────────────────────────────────────


def test_every_registered_component_is_classified():
    """The check that keeps the tables honest as components are added.

    A component nobody classified would be silently treated as trusted
    or inert, which is the safe-looking answer and the wrong one. Same
    shape as `emits:` on a role: the test is what turns "somebody
    should decide" into "somebody must".
    """
    missing = trust.unclassified(set(SOURCE_REGISTRY), set(SINK_REGISTRY))
    assert not missing["sources"] and not missing["sinks"], (
        f"unclassified: {missing}.\n"
        "Add each to dissyslab/office/trust.py. A source is untrusted "
        "when it carries free text someone else composed; a sink is "
        "acting when it affects something outside this machine."
    )


def test_the_two_classes_do_not_overlap():
    assert not (trust.UNTRUSTED_SOURCES & trust.TRUSTED_SOURCES)
    assert not (trust.ACTING_SINKS & trust.INERT_SINKS)


def test_every_acting_sink_can_say_what_it_does():
    """The message names the consequence -- "sends email" -- because
    "is an acting sink" is a category and not a thing a person can act
    on."""
    for name in trust.ACTING_SINKS:
        assert trust.what_it_does(name) != "acts outside this machine", (
            f"{name} has no phrase in _WHAT_IT_DOES"
        )


def test_an_unknown_name_is_not_treated_as_dangerous():
    """A check that fired on every component it had not heard of would
    fire on every office anyone extended, and a check people learn to
    skip protects nothing. The test above is what stops "unknown" from
    becoming the common case."""
    assert not trust.is_untrusted_source("something_nobody_registered")
    assert not trust.is_acting_sink("something_nobody_registered")


# ── the check itself ──────────────────────────────────────────────────


