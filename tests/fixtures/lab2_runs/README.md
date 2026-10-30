# Real runs of Lab 2, for the Class 6 page

`2026-10-29.jsonl`: 40 runs of the gallery's `incident_room`, as
`trials.py` wrote them, on `anthropic: claude-sonnet-4-5` (Mani, 29 Oct).

- `A clean`: 10 runs on `evidence/clean.jsonl`.
- `A log`, `A log, changed`, `A log, bounded`: 30 runs on
  `evidence/log_injection.jsonl`, **all on the unchanged office**: the
  role file meant for the last two batches was never swapped in. The
  Class 6 page calls them batches 1 to 3 of the same office, which is
  what they are.

`course/IncidentRoom.html` quotes these runs and prints their rates;
`tests/integration/test_incident_room_page.py` checks every quote and
number against this file.
