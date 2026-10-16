# The gallery

Each folder is one office. Each teaches one idea, roughly in this order:

| Office | Idea |
|---|---|
| [org_news_filter](org_news_filter/) | a router: an English role decides, a router routes |
| [returns_desk](returns_desk/) | one item at a time: a gate, and escalation |
| [room_climate_monitor](room_climate_monitor/) | a keyed synchronizer joining two sensors |
| [situation_room_pro](situation_room_pro/) | the built-in roles in a pipeline; a deduplicator |
| [arxiv_radar](arxiv_radar/) | two English roles you write; a display with chosen fields |
| [debate](debate/) | three models answer, a moderator judges, a loop for another round |
| [org_two_office_news](org_two_office_news/) | nested offices: one office used as an agent in another |
| [backyard_birds](backyard_birds/) | an agent that is a classifier, not a language model (`needs:`) |
| [mac_speed_suite](mac_speed_suite/) | Python roles that keep state; a collected synchronizer; a loop |

Copy one into a folder of your own and run it there:

    dsl list                              # what is here
    dsl init returns_desk my_desk         # copy it
    cd my_desk
    dsl check .                           # every problem, nothing run
    dsl run .

Running an office writes its output next to `office.md`, so run a copy
rather than the one inside the installed package.

The office language is described in
`docs/internals/design/officespeak_revised.md`. The version 1 gallery
(42 offices, in the sentence form) is on the `v1` branch and the
`v1.10.2` tag.
