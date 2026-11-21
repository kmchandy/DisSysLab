# cake_room

A cake vanished from the kitchen. It was Ann, Ben, Cal or Dee. Three
detectives and a judge find out who, on a shared **whiteboard**. It is
the office for **Lab 2**: how agents work together when everything any
of them writes goes to all of them.

    evidence -> Board -> Rex
    Rex.door -> Pip -> Board
    Rex.shop -> Quinn -> Board
    Rex.fridge -> Rae -> Board
    Rex.judge -> Judy -> report

Each detective (an LLM agent) holds one piece of evidence the others do
not see, and each piece clears exactly one suspect. Nobody can name the
culprit alone; the board can.

`Board` (`roles/board.py`, Python) is the whiteboard, and it is
event-driven: there are no rounds. It changes only when a detective
writes a note, and whenever it changes, every detective who has not seen
the change is sent the board as it is now. A detective who reads the
board and has nothing new to add says so (`post: no`). When no detective
is busy and none has unseen notes, nothing will ever be written again,
and the board goes to `Judy`, who gives the verdict.

The order in which notes arrive depends on which model call finishes
first, so the same office, run twice, can fill the board differently.

    dsl init cake_room lab2
    cd lab2
    dsl check .
    dsl run .
    python show.py          # the board note by note, and the verdict

The files:

- `evidence.jsonl`: what the office reads, one line per detective. To
  start with it is `evidence/clean.jsonl`.
- `evidence/`: `clean.jsonl`, and three variants that add a note to the
  fridge: `witness.jsonl` (a neighbour says Dee did it; the door log
  says otherwise), `covering.jsonl` (a neighbour says Mo is covering for
  Ann) and `note_to_ai.jsonl` (a note addressed to the detectives).
- `roles/`: the board, the three detectives and the judge.
- `show.py`: the board of the last run, note by note: who wrote, whom
  they suspected, where a detective changed its mind, and every **stale
  read** (a note written while other notes were landing, unread). Each
  note records `read`, how many notes its writer had read.

Lab 2 (`course/lab2.html`) is being rewritten around this office.
`trials.py` is not working yet: it still expects the incident room's
`grade.py`.
