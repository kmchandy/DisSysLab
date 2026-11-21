# Lab 2 plan: the cake room

Working plan for the rewrite of Lab 2 around `dissyslab/gallery/cake_room`.
The draft page is `course/lab2_cake.html`; it replaces `course/lab2.html`
(the incident room) when it is finished.

## The one goal

Show agents collaborating through a **shared whiteboard**, and that a
whiteboard's outcome is less predictable than a structured DSL network's.
Attacks are secondary: a realistic one that probably fails is fine.

## Why the cake room, not the incident room

- In the incident room one analyst can solve the case alone (the log shows
  the deploy and `retry_limit=0`), so the board adds little.
- In the cake room no detective can: each piece of evidence clears exactly
  one of four suspects. Only the board can leave Cal.
- The incident room's attack needed knowledge of the system's internals.
  A note pinned to a fridge needs none.

## The board is event-driven (decided 20 Nov)

No rounds: rounds are a synchronous all-to-all exchange in disguise. The
board changes only when a detective writes, and sends itself to every
detective who has not seen the change. A detective with nothing new answers
`post: no`. At most one copy is outstanding per detective, so nobody reads
a board without its own last note. When nobody is busy, the judge gets the
board. A cap of 12 notes bounds a run.

## Outline

1. **The case.** Four suspects, three detectives, one private piece of
   evidence each; who clears whom; how the board works; predictions.
   *Drafted.*
2. **Run it once.** `dsl check`, `dsl run`, `show.py`: read the board note
   by note; find the note where each detective first names Cal, and a stale
   read.
3. **Run it ten times.** Count verdicts, notes, and the order of first
   notes. The spread is the lesson.
4. **The same detectives as a structured network.** No board: each
   detective writes only to Judy. Ten runs; compare accuracy and spread.
   Students measure the claim, not take it on trust.
5. **A realistic attack.** A note on the fridge (`witness.jsonl`: a
   neighbour says Dee did it; the door log says otherwise). Predict, then
   measure. A failure is a result; explain why it failed (the board is how
   the lie is caught).
6. **Questions and a write-up table.**

## Open

- `covering.jsonl` (Sam says Mo is covering for Ann): with the camera it is
  one witness against a record. Attack or discussion question?
- `trials.py` needs a `grade.py` for the cake room.
- The incident room stays in the gallery; its Lab 2 tests and page go when
  the new page replaces the old.

## Evidence so far

`course/lab2/traces/2026-11-20/`: two single runs on Haiku. With Ann cleared
only by Mo's word the verdict was unknown; with the garden camera, Cal.
