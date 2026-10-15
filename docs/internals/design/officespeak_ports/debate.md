# Paper port 3 of 5: `debate`

Ported by hand against `officespeak_revised.md` (with port 2's additions).
Nothing here runs yet.

Three models answer the same question; a moderator reads the three answers
and either accepts one or sends the panel another round with a note. One
question is debated at a time.

## Before

```
Sources: starter
Sinks: jsonl_recorder(path="debate_answers.jsonl"),
       jsonl_recorder_briefing(path="debate_transcript.jsonl"),
       debate_display

Agents:
Sasha is a gate.                      # local roles/gate.py, not the built-in gate
Qwen is a qwen.
Qwen's AI is openrouter.
GPT is a gpt.
GPT's AI is openai.
Claude is a claude.
Claude's AI is anthropic.
Sync is a synchronizer(inboxes=["from_qwen", "from_gpt", "from_claude"]).
Riley is a moderator.

Connections:
starter's destination is Sasha.
Sasha's out is Qwen, GPT, Claude.
Qwen's out is Sync's from_qwen.
GPT's out is Sync's from_gpt.
Claude's out is Sync's from_claude.
Sync's out is Riley, jsonl_recorder_briefing, debate_display.
Riley's continue is Qwen, GPT, Claude, debate_display.
Riley's finish is jsonl_recorder, Sasha, debate_display.
```

- `roles/gate.py` (150 lines) subclasses the framework's `Agent`, reads
  `problems.jsonl` itself, adds `round: 0` and `history: []`, emits one
  problem each time it is signalled, and pauses for Enter when the
  environment variable `DSL_DEBATE_STEP` is set.
- `qwen.md`, `gpt.md`, `claude.md` are the same 80 lines with one name
  changed. Each wraps its answer under its own name so that "the office's
  synchronizer" can merge them.
- `moderator.md` decides finish/continue **and** builds the next message:
  copies `problem` and `problem_id`, increments `round`, and rebuilds the
  whole `history` list by copying three answer objects. It also enforces the
  two-round cap. Its front matter says `adds: text` (the port 1 bug again).
- `debate_display` (a sink in `apps/debate/sinks/`, registered in the
  framework's own registry) tells three message shapes apart by which fields
  are present.

## After

```
# Office: debate

Sources: problems is a file_source(filepath="problems.jsonl")
Sinks: answers is a jsonl_recorder(path="debate_answers.jsonl"),
       transcript is a jsonl_recorder(path="debate_transcript.jsonl"),
       debate_display

Agents:
Gate is a gate.
Qwen is a qwen.
Qwen's AI is openrouter.
GPT is a gpt.
GPT's AI is openai.
Claude is a claude.
Claude's AI is anthropic.
Sync is a synchronizer(inboxes=["qwen", "gpt", "claude"], on="problem_id").
Riley is a moderator.
Ref is a referee(max_rounds=2).
Rex is a router(on="next").

Connections:
problems's out is Gate.
Gate's out is Qwen, GPT, Claude.
Qwen's out is Sync's qwen.
GPT's out is Sync's gpt.
Claude's out is Sync's claude.
Sync's out is Riley, transcript.
Riley's out is Ref.
Ref's out is Rex, debate_display.
Rex's continue is Qwen, GPT, Claude.
Rex's finish is answers, Gate's done.
```

```
problems → Gate → Qwen ┐
            ↑     GPT  ┼→ Sync → Riley → Ref → Rex ─ continue → Qwen, GPT, Claude
            │     Claude┘   └→ transcript   └→ debate_display
            └────────────────────────────────────── finish → Gate's done, answers
```

**Who does what.** The models judge; Python keeps the rules.

| Agent | Kind | Does |
|---|---|---|
| Gate | built-in gate | admits one problem; waits for `done` before the next |
| Qwen, GPT, Claude | English annotators | each adds its answer under its own name |
| Sync | synchronizer | merges the three answers to the same problem |
| Riley | English annotator | judges agreement; names the answer; writes the note |
| Ref | Python author | applies the round cap; builds the final record or the next round |
| Rex | router | `finish` or `continue` |

`problems.jsonl`, one line per problem, now carries the starting fields
itself, so nothing is added out of sight:

```
{"problem_id": "math-01", "problem": "What is 13 * 19?", "round": 0, "history": []}
```

The answer keys move to `answer_keys.jsonl`
(`{"problem_id": "math-01", "answer_key": "247"}`), read only by the grading
script after the run.

### `roles/qwen.md` (`gpt.md`, `claude.md`: the same with the name changed)

```
---
emits: Qwen's answer, with its reasoning and confidence
in: problem, round, history
out: qwen
---
You are Qwen, one of three panellists (qwen, gpt, claude) who answer a
question together. A moderator reads the three answers after each round.

You receive a JSON object. "problem" is the question. "round" is the round
number, starting at 0. "history" lists the earlier rounds; each entry holds
every panellist's answer and the moderator's note for that round.

[the paragraphs on weighing the others' reasoning, unchanged]

Return only a JSON object with one field, "qwen", whose value is an object
with the fields "answer" (a few words; for multiple choice, just the label),
"reasoning" (one or two sentences) and "confidence" (a number from 0 to 1).
```

Removed: "Always send to out", the sentence about the synchronizer, and four
sentences on JSON formatting ("first character must be `{`", no fences, …).
One fence is unwrapped (4.5), and the closing sentence says the rest.

### `roles/moderator.md`

```
---
emits: how far the panel agrees, the answer it supports, and a note
in: problem, qwen, gpt, claude
out: agreement (unanimous | majority | none), final_answer, note
---
You moderate a panel of three, qwen, gpt and claude, who answer the same
question. You receive a JSON object with the question in "problem" and each
panellist's answer in the fields "qwen", "gpt" and "claude". Each of these
is an object with "answer", "reasoning" and "confidence".

Decide how far the panel agrees:
- "unanimous": all three gave essentially the same answer;
- "majority": two agree and the third is noticeably less confident;
- "none": otherwise.

"final_answer" is the answer best supported by the panel's reasoning.
"note" is one or two sentences naming the specific point of disagreement
and the panellist who should address it; it is "" when the panel agrees.

Return only a JSON object with the fields "agreement", "final_answer" and
"note".
```

The moderator no longer copies anything, counts rounds, or builds `history`.

### `roles/referee.py`

```python
"""
---
emits: the debate's final record, or the message for the next round
kind: author
in: problem_id, problem, round, history, qwen, gpt, claude, agreement, final_answer, note
out: next (finish | continue), problem_id, problem, history
out if next is finish: final_answer, agreement, rounds_used
out if next is continue: round
---
Arguments: max_rounds -- the most rounds a debate may use (default 2).
"""

PANEL = ["qwen", "gpt", "claude"]


def step(item, settings):
    this_round = {"round": item["round"], "note": item["note"]}
    for name in PANEL:
        this_round[name] = item[name]
    history = item["history"] + [this_round]
    rounds_used = item["round"] + 1

    if item["agreement"] != "none" or rounds_used >= settings["max_rounds"]:
        return [{
            "next": "finish",
            "problem_id": item["problem_id"],
            "problem": item["problem"],
            "history": history,
            "final_answer": item["final_answer"],
            "agreement": item["agreement"] if item["agreement"] != "none" else "timeout",
            "rounds_used": rounds_used,
        }]
    return [{
        "next": "continue",
        "problem_id": item["problem_id"],
        "problem": item["problem"],
        "history": history,
        "round": rounds_used,
    }]


class Referee:
    def __init__(self, max_rounds=2):
        self.settings = {"max_rounds": max_rounds}

    def __call__(self, item):
        return step(item, self.settings)
```

Stateless, so no `checkpoint`/`restore`. A student can test `step` with
three dictionaries and no model.

`debate_display` now receives only Ref's messages and reads `next` to tell
the two kinds apart; `history` holds every round it shows. Its `in:` is
`next, problem_id, problem, history`.

## Findings for the spec

1. **The local `gate.py` reuses the name of the built-in `gate`.** Under 4.2
   that is an error. It is also unnecessary: `file_source` plus the built-in
   gate do the same job, and 150 lines of framework-subclassing code
   disappear. The spec should name the gate's inboxes: **`in` and `done`**
   (the code already uses `done`; section 6 says "control inbox").

2. **An author that returns two shapes of message.** Ref's `finish` message
   has `final_answer, agreement, rounds_used`; its `continue` message has
   `round`. 4.5 requires every object to have every field in `out:`, so
   neither shape passes. **Proposal:** an `out:` line may be conditioned on a
   listed value:
   ```
   out: next (finish | continue), problem_id, problem, history
   out if next is finish: final_answer, agreement, rounds_used
   out if next is continue: round
   ```
   This also lets `dsl check` know exactly which fields travel down each
   router branch: here, that the `continue` branch carries no `agreement`
   back to Riley (finding 5).

3. **No optional fields.** `answer_key` used to ride along "untouched" so the
   moderator could be told not to look at it. Under 4.5 an undeclared field
   is dropped, and declaring it would make it required. **Recommendation:**
   keep `answer_key` out of the office. It stays in a separate key file, and
   grading joins `debate_answers.jsonl` with the key on `problem_id`. The
   moderator then cannot peek, and the spec needs no optional-field syntax.
   (Port 2's `writer` was resolved the same way, by being strict.)

4. **The synchronizer's key need not be unique for ever.** Here `problem_id`
   repeats in every round of one problem. The rule should say: **no two items
   in progress at the same time share a key.** The gate guarantees that here.
   Section 6 (port 2) says "unique per item"; reword.

5. **Loops need an author to start the next round.** Because an annotator
   only adds (4.1), the panellists cannot be sent a message that already
   holds `qwen`, and Riley cannot be sent one that already holds `agreement`.
   Ref, an author, builds a fresh message that carries forward only what the
   next round needs. This is a consequence, not a change: a teaching point for
   the gate-loop example. The static check must follow router branches and
   know that a gate's `done` inbox forwards nothing; finding 2 supplies the
   field sets.

6. **Judgement versus rules.** The two-round cap moved from the moderator's
   prompt to Python (Principle 0). The moderator's job shrank to three
   judgements. No spec change; a good worked example of the principle.

7. **Three copies of one panellist role.** No parameters (4.2), plus disjoint
   field names for the synchronizer, means three near-identical files.
   **Recommendation:** keep them. It costs no new concept, and the README can
   say why. (The alternative, a synchronizer option that nests each input
   under its inbox name, is one more thing to learn.)

8. **Office-local sinks and sources.** `debate_display` lives in the app's
   `sinks/` folder but is registered in the framework's own registry, so a
   student cannot add a sink without editing DisSysLab. **Proposal:** an
   office's `sinks/` and `sources/` folders are searched by name like
   `roles/`, with the same rules (one class per file, no DisSysLab import,
   reusing a built-in name is an error). Add to section 8, step 1.

9. **Stateless Python roles.** 4.3 says examples are written as
   `step(item, state, settings) -> (out, new_state)`. For a stateless role
   that means passing `{}` around. **Proposal:** a stateless role's example
   form is `step(item, settings) -> out`.

10. **Hidden switch dropped.** The `DSL_DEBATE_STEP` pause was behaviour set
    by an environment variable, visible nowhere in the office. It is not
    ported. If a step-through is wanted, it belongs in the display sink as an
    argument, `debate_display(pause=true)`.

Old: 6 agents, 5 role files (one 150-line Python class). New: 8 agents,
5 role files (one 50-line function), and the moderator no longer copies JSON.
