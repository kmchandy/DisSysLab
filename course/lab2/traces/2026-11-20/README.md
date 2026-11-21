# Cake room, 20 November 2026: two runs on claude-haiku-5-5

The first two runs of the event-driven cake room (`dissyslab/gallery/cake_room`)
on a real model. One run each, so they show what can happen, not how often.
`DSL_BACKEND=anthropic`, default model `claude-haiku-5-5`.

| Run | Evidence | Notes | Verdict |
|---|---|---|---|
| 1 | Ann cleared only by Mo's note (`run1_mo_note_evidence.jsonl`) | 7 | **unknown** |
| 2 | Ann cleared by the garden camera too (`run2_camera_evidence.jsonl`, now the gallery's `clean.jsonl`) | 7 | **cal** |

**Run 1.** Rae reached Cal by elimination (note 5), but Pip called Mo's note
"unconfirmed" (note 6), and Quinn said Cal was the only one left yet would not
name him (note 7). Judy cited Pip's doubt and said unknown. One detective's
doubt reached the judge through the board. Ann's alibi was the one clear that
rested on a person's word, not a record, so the evidence was changed.

**Run 2.** Every detective starts at unknown and ends at Cal, and can get
there only by reading the others' notes. Note 4 is a stale read: Pip wrote
"Ben or Cal" before Quinn's note reached it.

Each `*_report.jsonl` is the line Judy's report wrote: the whole board
(`n`, `by`, `note`, `suspect`), `culprit` and `reason`.
