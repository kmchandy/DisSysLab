# Office examples (DisSysLab 2.0)

Each folder is one office, written in the line syntax of the spec
(`docs/internals/design/officespeak_revised.md`). Each teaches one idea:

| Example | Idea |
|---|---|
| `org_news_filter` | a router: an English role decides, a router routes |
| `returns_desk` | one item at a time: a gate, and escalation |
| `room_climate_monitor` | a keyed synchronizer joining two sensors |

More follow as they are rewritten (spec section 12): `arxiv_radar`,
`situation_room_pro`, `debate`, `org_two_office_news`, `backyard_birds`,
`mac_speed_suite`.

Until the 2.0 release, run them from Python:

    from pathlib import Path
    from dissyslab.office.build import run_office
    run_office(Path("dissyslab/office_examples/returns_desk"))

At the 2.0 release these become the gallery, and the old gallery is
archived (restructure_plan.md, Phase 6).
