# Office examples (DisSysLab 2.0)

Each folder is one office, written in the line syntax of the spec
(`docs/internals/design/officespeak_revised.md`). Each teaches one idea:

| Example | Idea |
|---|---|
| `org_news_filter` | a router: an English role decides, a router routes |
| `returns_desk` | one item at a time: a gate, and escalation |
| `room_climate_monitor` | a keyed synchronizer joining two sensors |
| `situation_room_pro` | the built-in roles in a pipeline; a deduplicator |
| `arxiv_radar` | two English roles you write; a display with chosen fields |
| `debate` | three models answer, a moderator judges, a loop for another round |
| `org_two_office_news` | nested offices: one office used as an agent in another |
| `backyard_birds` | an agent that is a classifier, not a language model (`needs:`) |
| `mac_speed_suite` | Python roles that keep state; a collected synchronizer; a loop |

Until the 2.0 release, run them from Python:

    from pathlib import Path
    from dissyslab.office.build import run_office
    run_office(Path("dissyslab/office_examples/returns_desk"))

At the 2.0 release these become the gallery, and the old gallery is
archived (restructure_plan.md, Phase 6).
