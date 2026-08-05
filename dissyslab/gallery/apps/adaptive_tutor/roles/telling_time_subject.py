# dissyslab/gallery/apps/adaptive_tutor/roles/telling_time_subject.py

"""
TELLING_TIME subject -- third instance of adaptive_tutor's subject
contract (see ``_subject_common.py``). Added to check the contract
against a genuinely different problem *shape* than fractions or
multiplication_facts: instead of "compute a number", the problem
describes a clock face in words and asks the child to say what time
it is.

Deliberate point of interest, matching fractions_subject.py's role in
the pair of existing examples: telling time has real, RICH answer
equivalence, richer than fractions' -- the same instant can correctly
be written as a digital string ("3:15"), a named quarter/half form
("quarter past 3"), or a minutes-past/minutes-to phrase ("15 minutes
past 3", "45 minutes past 2"). ``correct_answer`` is always the
canonical digital form; every other accepted spelling is *derived*
from the same (hour, minute) pair that generated the problem's own
text, never hand-typed into a separate list -- that's what
``check_problem_ground_truth.py``'s self-consistency check is for.

Deliberately out of scope (matches this contract's boundary, not a
bug): AM/PM. A clock face alone doesn't distinguish 3:15 AM from
3:15 PM, so grading_notes tells CHECKER to ignore AM/PM entirely
rather than inventing an ungroundable rule for it.
"""

import os
import random
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _subject_common import register_subject_bank_role  # noqa: E402

VARIANTS: Dict[str, Dict[str, Any]] = {
    # Only the four "named" quarter-hour marks -- every accepted form
    # (o'clock / quarter past / half past / quarter to) is exercised.
    "easy": {"session_length": 4, "minute_choices": [0, 15, 30, 45]},
    # Every 5-minute clock-face mark, including ones with no special
    # name (10, 20, 35, 50, ...), which fall back to "N minutes past/
    # to the hour" phrasing.
    "hard": {
        "session_length": 5,
        "minute_choices": [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55],
    },
}

_NUM_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}


def _next_hour(h: int) -> int:
    return 1 if h == 12 else h + 1


def _time_forms(h: int, m: int) -> Tuple[str, List[str]]:
    """Compute the canonical digital answer and every equivalent
    spelling for the (hour, minute) pair a problem was generated
    from. Pure function of (h, m) -- no randomness here, so it can't
    be the source of a determinism bug (see check_problem_ground_truth
    .py's check #3); only the caller's rng choices feed in."""
    digital = f"{h}:{m:02d}"
    nh = _next_hour(h)
    forms = {digital, f"{h:02d}:{m:02d}"}

    if m == 0:
        forms.add(f"{h} o'clock")
        forms.add(f"{_NUM_WORDS[h]} o'clock")
    elif m == 15:
        forms.add(f"quarter past {h}")
        forms.add(f"quarter past {_NUM_WORDS[h]}")
        forms.add(f"15 minutes past {h}")
    elif m == 30:
        forms.add(f"half past {h}")
        forms.add(f"half past {_NUM_WORDS[h]}")
        forms.add(f"30 minutes past {h}")
    elif m == 45:
        forms.add(f"quarter to {nh}")
        forms.add(f"quarter to {_NUM_WORDS[nh]}")
        forms.add(f"45 minutes past {h}")
        forms.add(f"15 minutes to {nh}")
    else:
        forms.add(f"{m} minutes past {h}")
        if m > 30:
            forms.add(f"{60 - m} minutes to {nh}")

    return digital, sorted(forms)


def _telling_time_generate_problem(rng: random.Random, params: Dict[str, Any]) -> Dict[str, Any]:
    minute_choices = params.get("minute_choices", [0, 15, 30, 45])
    h = rng.randint(1, 12)
    m = rng.choice(minute_choices)
    nh = _next_hour(h)

    if m == 0:
        text = (
            f"The hour hand points exactly at the {h} and the minute hand "
            f"points at the 12. What time is it?"
        )
    else:
        minute_mark = m // 5  # clock-face number (1-11) the minute hand sits on
        text = (
            f"The hour hand is between the {h} and the {nh}, and the minute "
            f"hand points at the {minute_mark}. What time is it?"
        )

    digital, accepted_forms = _time_forms(h, m)

    # Plausible wrong answer for STUDENT to type when scripted to miss:
    # the time 5 minutes off on the same clock face (a real minute-hand
    # misread, not an unrelated placeholder string), formatted the same
    # digital way as `digital`.
    dm = m + 5
    dh = h
    if dm >= 60:
        dm -= 60
        dh = _next_hour(h)
    distractor = f"{dh}:{dm:02d}"

    return {
        "text": text,
        "correct_answer": digital,
        "accepted_forms": accepted_forms,
        "distractor": distractor,
        "grading_notes": (
            "Accept any common way of naming this time: the digital form "
            "('H:MM'), 'o'clock', 'quarter past/to', 'half past', a spelled-"
            "out hour word ('quarter past three'), or an explicit 'N minutes "
            "past/to the hour' phrase. Ignore AM/PM entirely -- a clock face "
            "alone never distinguishes them, so neither should grading."
        ),
    }


role = register_subject_bank_role(
    "telling_time", VARIANTS, _telling_time_generate_problem,
)
