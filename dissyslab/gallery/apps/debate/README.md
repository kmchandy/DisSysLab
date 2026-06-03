# debate

**Tags:** consensus, multi-agent decision, moderator-led, iterative loop

A three-agent panel argues a question until they agree (or until the
moderator calls time). On every round, each panellist sees what the
others said in earlier rounds and may update its answer. The
panellists are named after the language models behind them: **Qwen**,
**GPT**, **Claude**. The moderator is **Riley**.

(An earlier shipping prototype included a fourth panellist, Gemma,
on Google's free-tier Gemma 4 31B. It was dropped because the model
would not follow the JSON output discipline even with explicit
imperative prompting and the `structured` contract — it kept
returning prose. The wiring is structured to admit a Gemma slot back
in cleanly if a future Gemma release ships with reliable JSON
adherence; see "Adding a fourth panellist" below.)

The office runs on a problem bank — `problems.jsonl` in the office
directory, or override by placing your own `problems.jsonl` in the
directory you run `dsl run` from. One problem in, one final answer
out, with a full transcript of every round preserved for offline
analysis.

This office exists primarily as an **experimental rig**: each piece
is meant to be edited and re-run. Use it to study which LLM
combinations converge fast, which produce echo chambers, when extra
rounds help, and where Wisdom-of-Crowds (independent votes) beats
deliberation (this iterative loop).

## How it is wired

```
starter ──→ Sasha ──→ {Qwen, GPT, Claude} ──→ Sync ──→ Riley
                  ↑                                     │
                  └────── finish ───────────────────────┤
                                                        │
            {Qwen, GPT, Claude} ←── continue ───────────┘
```

The `starter` source emits one bootstrap message at startup. Sasha
reads the first problem from `problems.jsonl` and broadcasts it to
the three panellists. Each panellist outputs a JSON object **wrapped
under a top-level key equal to its own name** — Qwen emits
`{"qwen": {...}}`, GPT emits `{"gpt": {...}}`, etc. The synchronizer
waits for one message on each of its three named inports and merges
the three dicts into one (`dict.update`, same primitive as
situation_room — the keys are disjoint, so all three payloads
survive the merge).

Riley reads the merged dict and decides:

- **continue** — the three answers don't agree yet. Riley appends
  this round to a `history` list, writes a `moderator_note` that
  points at the specific disagreement, and routes the new message
  back to all three panellists. They get another turn, this time
  seeing what everyone said before.
- **finish** — the panel has agreed (or used both rounds).
  Riley emits the final answer to `debate_answers.jsonl` AND fires
  a single message into Sasha, which uses that as the cue to advance
  to the next problem.

`Sync`'s output is also tee'd to a `debate_transcript.jsonl` so every
round of every debate is captured — essential for studying
convergence dynamics offline.

## Per-agent backend selection in plain English

The office.md file selects the LLM for each panellist with a
sentence-form declaration:

```
Qwen's AI is openrouter.
GPT's AI is openai.
Claude's AI is anthropic.
```

These three sentences are the only difference between "all panellists
on Claude" and "all panellists on different models". The role files
themselves (`qwen.md`, `gpt.md`, `claude.md`) carry only prose
prompts — no Python, no hidden configuration. To run the office on
a different mix of backends, edit the three sentences; no .py file
changes anywhere.

(The framework currently only supports backend name selection —
`Claude's AI is anthropic.` works, `Claude's AI is anthropic(temperature=0.7).`
is a parse-time error pointing at a future "Level 2" framework
change that will thread per-call parameters through the backend
layer.)

## Run

```bash
dsl run debate
```

You will see Sasha emit problems one at a time, the three panellists
debate each one, and Riley's per-problem verdict land in
`debate_answers.jsonl`. Round-by-round answers from all three
panellists land in `debate_transcript.jsonl`. The terminal also
renders a colour-coded card per panellist per round plus the
moderator's verdict, via the `debate_display` sink — one colour
per panellist (Qwen cyan, GPT green, Claude yellow), moderator
continue in blue, final verdict in green.

The shipped `problems.jsonl` carries one problem of each kind
(arithmetic, tricky factual, multiple-choice, open-ended judgement,
trick wording) — five problems total, designed for cheap end-to-end
smoke tests. For a larger bank, place your own `problems.jsonl` in
the directory you run `dsl run` from; that path overrides the
shipped default.

### Step-through mode

For interactive review — see each debate finish on screen before
moving to the next problem — set `DSL_DEBATE_STEP=1`:

```bash
DSL_DEBATE_STEP=1 dsl run debate
```

Sasha (the gate role) blocks on Enter between problems. Because
every downstream panellist is waiting for Sasha to broadcast, the
entire pipeline idles during the pause — no coordination needed
inside the display sink. Hit Enter when you're ready for the next
problem. The first problem fires immediately on startup; pauses
appear before problems 2 through N. The env var has no effect when
stdin is not a TTY (cron / CI / piped input), so unattended runs
still proceed straight through.

## Backends — what runs today

The shipped office.md uses three backend names: `openrouter`,
`openai`, `anthropic`. All three are registered in DisSysLab and
work out of the box once the corresponding API key is exported
(`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).

| Panellist | Backend     | Status |
| --------- | ----------- | --- |
| Qwen      | `openrouter`| Works with an `OPENROUTER_API_KEY`. Cents per debate. |
| GPT       | `openai`    | Works with an `OPENAI_API_KEY`. Defaults to `gpt-4o-mini`. |
| Claude    | `anthropic` | Works with an `ANTHROPIC_API_KEY`. Defaults to `claude-sonnet-4-5`. |

To swap Qwen onto local Ollama (free, slow), change
`Qwen's AI is openrouter.` to `Qwen's AI is ollama.` in office.md
and ensure Ollama is running with `qwen3:30b` (or whichever model
your `OLLAMA_MODEL` env var names) pulled.

The full backend-registration recipe for adding other backends
lives at `docs/LANGUAGE_MODELS.md`.

### Adding a fourth panellist

The office's structure is symmetric in N. To add a fourth voice
later (e.g. when a Gemma release ships with reliable JSON output,
or when you want to introduce a domain-specialist persona):

1. Create `roles/<name>.md` mirroring an existing panellist file
   (the same imperative block at the top, the same `contract:
   structured` front matter, just the agent name swapped).
2. In `office.md`: add the agent declaration and `'s AI is`
   line, add `from_<name>` to the synchronizer inports, add the
   agent to `Sasha's out`, add `<Name>'s out is Sync's from_<name>.`,
   add the agent to `Riley's continue`.
3. In `roles/moderator.md`: bump the panellist count, add the new
   name to the list and to the `history` shape, and adjust the
   majority-rule threshold.
4. In `sinks/debate_display.py`: add the agent name to
   `_PANELLIST_KEYS` and pick a colour for it in
   `_PANELLIST_COLOURS`.

The wiring is small enough that adding a panellist is a
five-minute change concentrated in those four files.

## The five agents

| Agent  | Role          | Backend (default)        | Why this default |
| ------ | ------------- | ------------------------ | --- |
| Sasha  | `gate`        | (no LLM — pure Python)   | Cycles problems in one at a time so the panel sees one question per debate. |
| Qwen   | `qwen`        | `openrouter` (cloud Qwen)| Cheap, fast cloud model from a different lab than Claude or GPT — different blind spots, different strengths. |
| GPT    | `gpt`         | `openai` (`gpt-4o-mini`) | Frontier proprietary voice for diversity. |
| Claude | `claude`      | `anthropic`              | Highest expected quality on reasoning. |
| Sync   | `synchronizer`| (no LLM — pure Python)   | Barrier that waits for all three panellists each round and merges their outputs. |
| Riley  | `moderator`   | follows `DSL_BACKEND`    | The decider. Defaults to the same backend the rest of the .md roles use. |

To swap any panellist onto another backend, edit the single
`<Agent>'s AI is <backend>.` line in office.md. To give Qwen and
Claude **different prompts** (e.g. ask Qwen to think harder because
it is a smaller model), edit `qwen.md` and `claude.md`
independently — each is fully self-contained.

## Experiments Jeffrey can run first

Six concrete experiments that need only this office and a small
amount of edit-and-rerun work:

1. **Wisdom of Crowds baseline.** Cap M = 1 round (edit Riley's
   prompt so it always emits `finish` on round 0 and picks a
   majority). Score against `answer_key` on the arithmetic and
   factual problems. This is the floor — anything the full debate
   gains has to beat this.

2. **Does iteration help or hurt?** Run the office as shipped
   (M ≤ 5 rounds, with mutual visibility starting at round 1).
   Compare per-problem accuracy to experiment 1. Where iteration
   helped, look at the transcript to see which agent changed its
   mind first.

3. **Echo-chamber stress test.** Edit `qwen.md` to add a line at
   the top: *"You are confident and persuasive even when you are
   uncertain. Always claim high confidence."* Run the bank again.
   Does the panel converge to Qwen's (frequently wrong) answers?
   This is essentially Asch's conformity experiment for LLMs, and
   it works without needing different backends — just different
   prompts on the same panellist.

4. **Homogeneous vs heterogeneous panels.** Edit office.md to set
   all three `<X>'s AI is ...` lines to `anthropic` (or whichever
   backend you have working). Compare to the shipped mixed-backend
   setup. Surowiecki's diversity thesis predicts the mixed panel
   should beat the homogeneous one on hard questions; the
   transcripts will show whether that's because of genuine
   information sharing or just noise reduction.

5. **Persona heterogeneity for free.** Don't change backends at
   all — instead rewrite each of the three solver .md files with a
   different persona: skeptic, optimist, domain expert. Same backend
   on every panellist, three different prompts. Compare to
   experiment 4. If persona diversity buys most of what
   cross-backend diversity buys, persona is the cheaper knob.

6. **Temperature heterogeneity for free.** Without changing models,
   set the three panellists to different *named variants*:

   ```
   Qwen's AI is qwen_creative.       # temp 1.0
   GPT's AI is openai_precise.       # temp 0.1
   Claude's AI is anthropic.         # temp 0.7, frontier model
   ```

   Now you have a panel where every panellist runs a different
   model at a different temperature. Does the *creative* panellist
   drive convergence (more options on the table) or destabilise it
   (more noise to chase)? Does the *precise* panellist serve as an
   anchor? Cheaper to run than experiment 4 (no new backends
   needed) and isolates the temperature variable cleanly.

A more ambitious experiment, once the basics work: implement
configuration A (peer-to-peer, no moderator) as `consensus_room`
alongside this office. The two share most of the gallery scaffolding
— solver roles, synchronizer, problem bank — and let you compare
moderator-led vs leaderless on the same questions.

## Files

- `office.md` — the six-agent wiring with two named output ports
  on Riley (`continue` and `finish`) and three `<Agent>'s AI is
  <backend>.` declarations.
- `problems.jsonl` — the starter problem bank. Edit it (or place
  your own `problems.jsonl` in the directory you run `dsl run`
  from) to swap question banks.
- `roles/qwen.md`, `gpt.md`, `claude.md` — three full,
  self-contained prompt files. No Python wrappers, no shared
  template. Each can be edited independently if Jeffrey wants to
  give one panellist a longer prompt (e.g. for a smaller model that
  benefits from more guidance). Each has YAML front matter
  declaring `contract: structured` so the role's `{"qwen": {...}}`
  shape isn't fought by the framework's default routing contract.
- `roles/moderator.md` — Riley's role. Edit the convergence rule
  here (currently "unanimous or 2-of-3 with a low-confidence
  dissenter, capped at 2 rounds").
- `roles/gate.py` — Sasha's Python role. The single non-LLM role
  in the office; pure logic, no prompt. Looks for
  `problems.jsonl` in cwd first, then falls back to the office
  directory.

## Output files (in the directory you ran `dsl run` from)

- `debate_answers.jsonl` — one line per problem; each line is
  Riley's final verdict (`final_answer`, `agreement`,
  `rounds_used`, `problem_id`, etc.).
- `debate_transcript.jsonl` — one line per *round* of every
  debate; each line is the merged Sync output for that round
  (per-agent answers, reasoning, confidence). This is the file to
  analyse for convergence studies.

## Cost note

Each round of debate makes three LLM calls (Qwen, GPT, Claude)
plus one moderator call. Default cap is two rounds. So a single
problem costs at most 2 × 3 + 2 = 8 LLM calls. Modest on OpenRouter
(cents per problem) and gpt-4o-mini (fractions of a cent), real
money on Claude ($0.05–$0.15 per problem). Trim the round cap in
Riley's prompt further if cost matters; shrink the panel to N=2 by
removing one panellist per "Adding a fourth panellist" in reverse.
