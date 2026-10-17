# inbox_sorter

Messages that students send to the course staff, sorted by how soon they
need an answer. An English role, Tri, adds `urgency: urgent | routine`; a
router, Rex, sends urgent messages to the screen and to `urgent.jsonl`,
and the rest to `later.jsonl`.

    inbox -> Tri -> Rex
    Rex.urgent -> urgent, console_printer
    Rex.routine -> later

This is the office `docs/GETTING_STARTED.md` builds step by step, part 6.
If yours does not work, copy this one and compare:

    dsl init inbox_sorter finished_sorter

- The data is a file (`messages.jsonl`), so the office runs without a
  network; only Tri calls a model.
- `out: urgency (urgent | routine)` in `roles/triage.md` is the guardrail:
  a reply with any other value is reported and costs only that message,
  and `dsl check` compares the router's outboxes with those two values.
