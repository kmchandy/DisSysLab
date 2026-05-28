# debate

**Tags:** consensus, multi-agent decision, moderator-led, iterative loop

A four-agent panel argues a question until they agree (or until the
moderator calls time). On every round, each panellist sees what the
others said in earlier rounds and may update its answer. The
panellists are named after the language models behind them: **Qwen**,
**Gemma**, **GPT**, **Claude**. The moderator is **Riley**.

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
starter ──→ Sasha ──→ {Qwen, Gemma, GPT, Claude} ──→ Sync ──→ Riley
                  ↑                                            │
                  └────── finish ──────────────────────────────┤
                                                               │
            {Qwen, Gemma, GPT, Claude} ←── continue ───────────┘
```

The `starter` source emits one bootstrap message at startup. Sasha
reads the first problem from `problems.jsonl` and broadcasts it to
the four panellists. Each panellist outputs a JSON object **wrapped
under a top-level key equal to its own name** — Qwen emits
`{"qwen": {...}}`, Gemma emits `{"gemma": {...}}`, etc. The
synchronizer waits for one message on each of its four named inports
and merges the four dicts into one (`dict.update`, same primitive as
situation_room — the keys are disjoint, so all four payloads survive
the merge).

Riley reads the merged dict and decides:

- **continue** — the four answers don't agree yet. Riley appends
  this round to a `history` list, writes a `moderator_note` that
  points at the specific disagreement, and routes the new message
  back to all four panellists. They get another turn, this time
  seeing what everyone said before.
- **finish** — the panel has agreed (or used all five rounds).
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
Qwen's AI is ollama.
Gemma's AI is gemma.
GPT's AI is openai.
Claude's AI is anthropic.
```

These four sentences are the only difference between "all panellists
on Claude" and "all panellists on different models". The role files
themselves (`qwen.md`, `gemma.md`, `gpt.md`, `claude.md`) carry only
prose prompts — no Python, no hidden configuration. To run the
office on a different mix of backends, edit the four sentences; no
.py file changes anywhere.

(The framework currently only supports backend name selection —
`Claude's AI is anthropic.` works, `Claude's AI is anthropic(temperature=0.7).`
is a parse-time error pointing at a future "Level 2" framework
change that will thread per-call parameters through the backend
layer.)

## Run

```bash
dsl run debate
```

You will see Sasha emit problems one at a time, the four panellists
debate each one, and Riley's per-problem verdict land in
`debate_answers.jsonl`. Round-by-round answers from all four
panellists land in `debate_transcript.jsonl`.

The shipped `problems.jsonl` has ten starter problems mixing clean
arithmetic, tricky facts, multiple-choice, open-ended judgement, and
deliberately-tricky wording. Replace it with your own bank to study
a different question class.

## Backends — what runs today

The shipped office.md uses four backend names: `ollama`, `gemma`,
`openai`, `anthropic`. Two of these are already registered in
DisSysLab; **two need a small amount of one-time setup before they
work**.

| Panellist | Backend  | Status |
| --------- | -------- | --- |
| Qwen      | `ollama` | Works out of the box if Ollama is installed and serving Qwen locally. |
| Gemma     | `gemma`  | **Not yet registered.** Register it by adapting `dissyslab/backends/ollama_backend.py` to point at a local Gemma model, then `register_backend("gemma", ...)`. Until you do, the office will fail at run time when Gemma's first round fires. |
| GPT       | `openai` | **Not yet registered.** Register an OpenAI backend mirroring the existing `AnthropicBackend` (~50 lines). |
| Claude    | `anthropic` | Works out of the box with an `ANTHROPIC_API_KEY`. |

While Gemma and GPT are missing, the simplest fix is to redirect
those panellists to backends you do have. For example, change to
`Gemma's AI is openrouter.` and `GPT's AI is openrouter.` if you
have an OpenRouter key — the office will then run end-to-end with
two of the four panellists effectively running the same model. Not
ideal for the diversity experiments but works for the convergence
ones.

The full backend-registration recipe lives at
`docs/LANGUAGE_MODELS.md` and is a 5-minute job once you have an
API key for the missing model.

## The five agents

| Agent  | Role          | Backend (default)        | Why this default |
| ------ | ------------- | ------------------------ | --- |
| Sasha  | `gate`        | (no LLM — pure Python)   | Cycles problems in one at a time so the panel sees one question per debate. |
| Qwen   | `qwen`        | `ollama` (local Qwen)    | Free, private, slow. Anchors the panel with a small open model. |
| Gemma  | `gemma`       | `gemma` (needs register) | Second open-model voice; expected to disagree with Qwen on subtle reasoning. |
| GPT    | `gpt`         | `openai` (needs register)| Frontier proprietary voice for diversity. |
| Claude | `claude`      | `anthropic`              | Highest expected quality on reasoning. |
| Sync   | `synchronizer`| (no LLM — pure Python)   | Barrier that waits for all four panellists each round and merges their outputs. |
| Riley  | `moderator`   | follows `DSL_BACKEND`    | The decider. Defaults to the same backend the rest of the .md roles use. |

To swap any panellist onto another backend, edit the single
`<Agent>'s AI is <backend>.` line in office.md. To give Qwen and
Claude **different prompts** (e.g. ask Qwen to think harder because
it is a smaller model), edit `qwen.md` and `claude.md`
independently — each is fully self-contained.

## Experiments Jeffrey can run first

Five concrete experiments that need only this office and a small
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
   all four `<X>'s AI is ...` lines to `anthropic` (or whichever
   backend you have working). Compare to the shipped mixed-backend
   setup. Surowiecki's diversity thesis predicts the mixed panel
   should beat the homogeneous one on hard questions; the
   transcripts will show whether that's because of genuine
   information sharing or just noise reduction.

5. **Persona heterogeneity for free.** Don't change backends at
   all — instead rewrite each of the four solver .md files with a
   different persona: skeptic, optimist, domain expert, synthesiser.
   Same backend on every panellist, four different prompts.
   Compare to experiment 4. If persona diversity buys most of what
   cross-backend diversity buys, persona is the cheaper knob.

A more ambitious experiment, once the basics work: implement
configuration A (peer-to-peer, no moderator) as `consensus_room`
alongside this office. The two share most of the gallery scaffolding
— solver roles, synchronizer, problem bank — and let you compare
moderator-led vs leaderless on the same questions.

## Files

- `office.md` — the seven-agent wiring with two named output ports
  on Riley (`continue` and `finish`) and four `<Agent>'s AI is
  <backend>.` declarations.
- `problems.jsonl` — the starter problem bank. Edit it (or place
  your own `problems.jsonl` in the directory you run `dsl run`
  from) to swap question banks.
- `roles/qwen.md`, `gemma.md`, `gpt.md`, `claude.md` — four full,
  self-contained prompt files. No Python wrappers, no shared
  template. Each can be edited independently if Jeffrey wants to
  give one panellist a longer prompt (e.g. for a smaller model that
  benefits from more guidance).
- `roles/moderator.md` — Riley's role. Edit the convergence rule
  here (currently "unanimous or 3-of-4 with a low-confidence
  dissenter, capped at 5 rounds").
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

Each round of debate makes four LLM calls (Qwen, Gemma, GPT, Claude)
plus one moderator call. Default cap is five rounds. So a single
problem costs at most 5 × 4 + 5 = 25 LLM calls. Cheap on Ollama
(free), modest on OpenRouter (cents per problem), real money on
Claude ($0.10–$0.30 per problem). Trim the round cap in Riley's
prompt or shrink the panel to N=2 if cost matters.
