"""What each check code means, in one place.

Why this file exists
--------------------
``dsl check`` prints a code beside every finding -- ``W4``, ``G1``,
``W12``. Codes are worth having: they are stable across rewordings, they
make a test say which check it is pinning, and they give two people a
way to refer to the same finding without quoting a sentence at each
other.

They are also opaque. A reader who sees ``W11`` and does not already
know what it is has, until now, had nowhere to go. The meanings lived in
the code that emits them, scattered over nine hundred lines, and in
CHANGELOG entries filed by release. The author of this project could not
remember them either, which is the observation that produced this file.

So: one table, and ``dsl checks`` prints it. ``dsl checks W11`` prints
one entry.

Why the table is not the source of the messages
-----------------------------------------------
Each finding's *message* is written where it is raised, because it is
built from the office in front of it -- names, ports, spelling
suggestions. This file holds what does not vary: what the check is
called, what it means in general, and whether it is a fault or a note.

``test_check_catalogue.py`` reads ``check_wiring.py`` and fails if a code
is raised without an entry here, or has an entry and is raised nowhere,
or disagrees about severity. A catalogue that can drift from the code is
worse than none, because it is believed.

The numbers are identifiers, not a sequence
-------------------------------------------
W2 sat unimplemented for a long time while the codes around it shipped.
It kept its number rather than being reused for something else, and
that is the rule: a code means one thing for ever, so an old report
still says what it said.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Check:
    """One check, as a person would explain it."""

    code: str
    severity: str  # "error" -- the office is wrong | "note" -- read it
    title: str  # a few words, the name of the fault
    meaning: str  # what it means, and what to do

    @property
    def is_error(self) -> bool:
        return self.severity == "error"


#: Every code ``dsl check`` can print. Order is the order they are
#: reported in, which is roughly the order they matter.
CHECKS: Dict[str, Check] = {
    "W1": Check(
        "W1",
        "error",
        "an inbox nothing writes to",
        "An agent declares an inbox, and no connection sends anything to "
        "it. The agent will wait on that inbox forever and never do its "
        "work -- so this is the usual reason an office starts and then "
        "appears to hang. Either wire something to the inbox or remove it "
        "from the agent's list.",
    ),
    "W2": Check(
        "W2",
        "error",
        "an outbox wired to nothing",
        "A role says `send to <name>` and nothing is connected to that "
        "outbox. Worse than the inbox case: an unwired inbox blocks, but "
        "an unwired outbox raises the first time the agent uses it -- so "
        "a filter wired only on `keep` passes every check and then stops "
        "on the first item it wants to discard. Either wire it, or take "
        "that sentence out of the role.",
    ),
    "W3": Check(
        "W3",
        "error",
        "an unreachable agent",
        "There is no path from any source to this agent, so nothing will "
        "ever arrive and it will never run. Usually a missing connection, "
        "sometimes a misspelled name earlier in the chain.",
    ),
    "W4": Check(
        "W4",
        "error",
        "a dead end",
        "This agent's output reaches no sink, so whatever it produces is "
        "computed and thrown away. Reported at the frontier: if a chain of "
        "four agents all lead nowhere, you are told about the first, "
        "because fixing that one fixes the rest.",
    ),
    "W5": Check(
        "W5",
        "error",
        "no such source or sink",
        "A name in the Sources or Sinks line is in no registry. The nearest "
        "real name is suggested, because the cause is nearly always "
        "spelling. `dsl list` shows every shipped source and sink.",
    ),
    "W6": Check(
        "W6",
        "error",
        "no file behind a role",
        "An agent is given a role, and there is no roles/<name>.md or "
        "roles/<name>.py and no built-in role by that name. Create the file "
        "or correct the spelling.",
    ),
    "W7": Check(
        "W7",
        "note",
        "a feedback loop",
        "Some agents send messages round in a circle. This is legal and "
        "often exactly what you meant, so it is a note rather than a fault. "
        "What the note tells you is whether anything in the loop decides "
        "when to stop: a loop with a gate can terminate, a loop without one "
        "runs until you stop it.",
    ),
    "W8": Check(
        "W8",
        "error",
        "a source with no destination, or a sink nothing feeds",
        "Either a source is fetching things nobody reads, or a sink is "
        "connected to nothing and will produce no output. The second is the "
        "usual explanation for an empty output file.",
    ),
    "W9": Check(
        "W9",
        "error",
        "a name that is nothing at all",
        "A connection mentions a name that is not a declared source, sink or "
        "agent. Almost always a typo in the Connections section -- check it "
        "against the Agents section.",
    ),
    "W10": Check(
        "W10",
        "error",
        "a sub-office that is not there",
        "An agent is declared as `office at <path>`, and there is no office "
        "at that path. The path is relative to this office's folder.",
    ),
    "W11": Check(
        "W11",
        "note",
        "text from the open web reaching something that acts",
        "A source that carries words a stranger wrote -- news, a feed, "
        "scraped pages, inbound mail -- has a path to a sink that affects "
        "the world outside this machine: email, chat, a webhook. An agent "
        "whose job is English is run by a model, and a model that can be "
        "instructed can be instructed by its input. Nothing about this is "
        "necessarily wrong; the note exists so you decide rather than "
        "discover. An office whose sinks all print or write a local file "
        "never sees it.",
    ),
    "W12": Check(
        "W12",
        "note",
        "a role's own Python reaching outside",
        "A role's code imports something that reaches the network or starts "
        "another program, or calls eval / os.system. Often that is the whole "
        "point of the role. This check reads imports only: it cannot see "
        "what the code does, cannot follow a renamed import, and can be "
        "evaded. Its silence is not a clean bill of health -- read code you "
        "did not write.",
    ),
    "W13": Check(
        "W13",
        "error",
        "a message sent to an inbox that does not exist",
        "A connection names an inbox the receiving agent does not have — "
        "almost always a misspelling. Nothing arrives, the agent waits on "
        "the inbox it does have, and the office hangs. Until roles declared "
        "their inboxes this could not be seen at all: the office checked "
        "clean, ran, and failed naming a port you never typed.",
    ),
    "G1": Check(
        "G1",
        "error",
        "an agent with no role yet",
        "You have written down a name -- `Jay is unassigned.` -- and not yet "
        "said what it does. In a draft office this is reported as something "
        "still to do and the check passes; `dsl run` refuses until you say.",
    ),
    "G2": Check(
        "G2",
        "error",
        "nothing leaves this office",
        "The office has no sink, so it will run, finish, and show you "
        "nothing. Add console_printer to watch it, or jsonl_recorder to keep "
        "what it produced.",
    ),
}


def get(code: str) -> Check | None:
    """One check by code, case-insensitively. None if there is no such code."""
    return CHECKS.get(code.strip().upper())


def _wrap(text: str, width: int, indent: str) -> List[str]:
    import textwrap

    return textwrap.wrap(text, width=width, initial_indent=indent,
                         subsequent_indent=indent) or [indent.rstrip()]


def catalogue_lines(code: str | None = None, width: int = 76) -> List[str]:
    """The table, or one entry, as lines ready to print."""
    if code is not None:
        check = get(code)
        if check is None:
            known = ", ".join(CHECKS)
            return [
                f"There is no check called {code!r}.",
                "",
                f"  Known codes: {known}",
            ]
        word = "problem" if check.is_error else "note"
        return [
            f"{check.code}  {check.title}",
            f"      reported as a {word}",
            "",
            *_wrap(check.meaning, width, "      "),
        ]

    lines = [
        "The checks `dsl check` can report.",
        "",
        "A problem means the office is wrong and will not run correctly.",
        "A note means read it and decide -- the office is not wrong.",
        "",
    ]
    for check in CHECKS.values():
        mark = " " if check.is_error else "*"
        lines.append(f"  {check.code:<5}{mark} {check.title}")
    lines += [
        "",
        "  * a note, not a problem",
        "",
        "Run `dsl checks W11` for what one of them means.",
    ]
    return lines
