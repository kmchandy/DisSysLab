# Research Agenda for DisSysLab

This is a year-plus research direction list, not a v1.4 punch list. The
tactical backlog (the launch checklist, individual bugs, doc gaps) is
tracked separately in the TaskList. This document is the longer arc:
what DisSysLab is becoming as students, contributors, and users grow
the framework alongside us.

Four threads, each independent enough to be worked on alone but
related enough that progress in one creates appetite in the others.

---

## 1. Community-built libraries — sources, sinks, AI transformers, Python transformers

### Why this matters

DisSysLab's power isn't the framework, it's the libraries. An office.md
is just a description of how a few items from a few libraries fit
together. If the libraries stay small, the framework solves toy
problems. If the libraries get rich, a typical Pat can build a working
office by picking items from menus — without writing any custom roles,
sources, or sinks.

Right now every library entry is something we wrote: the 13 roles in
`dissyslab/roles/`, the one `fn_lib` entry (`dedup`), the sources in
`dissyslab/components/sources/`, the sinks. Users can override locally,
but there's no path for them to *contribute* an entry that becomes
available to other users.

### Current state

- The framework has three library directories: `dissyslab/roles/`,
  `dissyslab/fn_lib/`, `dissyslab/components/{sources,sinks}/`.
- Per-office override works: a local `roles/X.py` shadows the framework's
  `dissyslab/roles/X.md`.
- Nothing in between — no third tier for "Kamala's entity_extractor that
  uses GLiNER instead of an LLM" being available to other users.

### Open questions

- **Where do user-contributed components live?** Three plausible models:
  *bundled in the wheel* (curated, slow-moving); *separate pip packages*
  (discoverable via PyPI; standard pattern for "plugins"); *centralized
  marketplace* (a `dissyslab-community` repo of role.md files anyone
  can PR into).
- **Discovery.** If user-published, how does Pat find them? `dsl
  library search "entity extractor"` returning results from a registry?
- **Quality bar.** What's the minimum standard to accept a contribution?
  Tests? A working example office? Review by whom?
- **Naming collisions.** Two users contribute `entity_extractor`. How
  does an office.md disambiguate? Namespaces (`kamala/entity_extractor`)?
- **Versioning.** Pat's office references `entity_extractor` — which
  version? Pinned per office, or always latest?

### Near-term threads

Mostly design work, no code yet:

1. Decide on the contribution model (bundled vs. plugin vs. marketplace).
   Probably plugin packages via Python entry-points — standard pattern
   for projects this shape (`pytest`, `flake8`).
2. Write a single contributor walkthrough: "how to publish a role to
   `dissyslab-community`." One end-to-end example, even if the registry
   is just a folder.
3. Decide naming-collision policy now, before the convention gels around
   whatever the first three contributors do.

---

## 2. DSL as a meta-framework — abstractions Kamala can extract

### Why this matters

`build_office()` (the programmatic path) takes the place that office.md
takes for plain text: it generates an office structure from a few
parameters. There's exactly one such generator today
(`build_office()` in `dissyslab/patterns/sense_think_respond.py`),
producing instances of the sense → think → respond pattern.

That's one pattern. There are obviously others. Each one is a function
that takes a small set of inputs and produces an office. If we extract
the next handful of patterns into similar generators, then Pats can
build new offices by *picking a pattern + filling its slots from
libraries* — no office.md authoring, no Python.

This is also the natural surface for a React (or any web) UX. The UX
calls `build_office("sense_think_respond", sources=..., thinkers=...)`,
the framework returns the office, the UX renders it as a graph or
copies the generated office.md into the user's folder.

### Current state

- One pattern generator: `build_office()` for sense → think → respond.
- The office.md grammar covers fan-out, fan-in, synchronization, named
  ports, conditional routing — wide enough to describe many patterns.
- No UX. Today everything is `dsl run`, `dsl list`, `dsl init` on the
  command line.

### Open questions

- **Which patterns deserve generators?** Strong candidates: *router*
  (input → classifier → branch to one of N specialists); *RAG*
  (retriever → grounder → composer); *revise loop* (write → critique →
  rewrite, with the critique as a feedback edge); *map-reduce* (split
  → N workers → merge → reduce).
- **Parameterization granularity.** Each pattern has hyperparameters. The
  sense → think → respond one has `sources=`, `thinkers=`, `writer=`,
  `sinks=`. What's the right number — too few and the pattern doesn't
  cover real variants; too many and it stops feeling like a pattern.
- **UX shape.** Should the UX produce office.md (preserving the
  English-text artifact as the source of truth) or directly construct a
  network graph? The first is easier to debug, the second is more
  visual. Both?
- **Pattern composition.** Can patterns nest? An office-of-offices where
  the outer office is RAG and one of its components is a sense → think
  → respond sub-office?

### Near-term threads

1. Inventory existing gallery offices. Which can be expressed as
   instances of a generator function? `competitor_watch`, `inbox_triage`,
   `lead_qualifier`, `ticket_router` are all sense → think → respond
   variants — one generator already covers them. Are there genuinely
   different patterns hiding in the gallery?
2. Sketch the *router* pattern as the next generator. Probably the most
   useful for chatbots (see thread 4).
3. Decide whether the UX is React, Streamlit, or something else. The
   choice has knock-on effects on contributor experience.

---

## 3. Polyglot AI — specialized models per role

### Why this matters

DSL currently assumes every role is an LLM call. That's correct for
generation-shaped roles (the writer composing a briefing). For
classification-shaped roles (entity extraction, sentiment, severity
tagging) and computation-shaped roles (arithmetic, deduplication,
sorting), an LLM is overkill — slower, more expensive, and often
*worse* than a purpose-built model.

**What the contribution actually is.** The pitch is NOT "specialists
match Claude on bare zero-shot." That would be a quality-comparison
paper. The pitch is: *builders can compose offices where specialists
do their bit, so Pat gets the benefits (cost, speed, privacy) without
knowing anything about specialists.* Pat sees `dsl run my_office`. The
office.md she runs references roles like `entity_extractor` and
`severity_classifier` — exactly the names she'd use with all-LLM
backends. What changes underneath is invisible to her: maybe Eve is
spaCy NER, maybe Sam is BART-MNLI with a tailored hypothesis prompt
and a keyword floor, maybe Riley is still Claude. Builders tune the
specialist prompts as hard as they would tune an LLM prompt. Pat just
runs the office.

A typical situation_room run today is six LLM calls per article (four
extractors + writer + the deduplicator, which is already a Python
function). Replace the four extractors with specialized models:

- entity_extractor → spaCy or GLiNER (~10 ms per article, offline, free)
- sentiment_classifier → Cardiff Twitter-roBERTa (~50 ms, offline, free)
- topic_tagger → BART-MNLI zero-shot classification (~100 ms, offline)
- severity_classifier → rules + a small classifier

That leaves Riley (the writer) as the only LLM call. ~1 call per
article instead of ~5. Pat's office runs faster, costs less, uses less
energy. And the framework demonstrates a real point: "AI" is a toolbox,
not a single dial.

### Current state

- The `Backend` protocol takes `(system, user)` and returns text. It's
  LLM-shaped.
- `fn_lib` exists for Python-function roles (dedup is the one entry),
  but isn't yet unified with the AI-backend choice in office.md syntax.
- No first-class support for "this role's backend is a spaCy pipeline"
  or "this role's backend is a HuggingFace classifier."

### Open questions

- **The right abstraction.** Is the answer (i) a per-role adapter
  pattern where each role chooses its own backend, (ii) a richer
  Backend interface beyond `(str, str) → str`, or (iii) a separate
  abstraction layer ("Component") that's neither LLM-call nor pure-
  Python?
- **Quality measurement.** How do we benchmark spaCy NER vs Claude's
  entity_extractor on the same corpus? Do we have a corpus?
- **Energy and latency.** Can we measure watts and milliseconds per
  role and surface those numbers in the office's run summary, so Pat
  sees the cost of each backend choice?
- **Catalog.** What's the right shortlist for each role-shaped task?
  See "near-term" below.

### Near-term threads (Mani has asked for help here this week)

#### 3a. Survey: specialized models per role-library entry

For each role currently in `dissyslab/roles/`, identify the top 1–2
non-LLM (or much smaller LLM) candidates. My initial recommendations:

- **entity_extractor**: GLiNER (zero-shot, generalist, ~150 MB) is the
  strongest single recommendation; spaCy's `en_core_web_trf` for
  English-only is the safe production default.
- **sentiment_classifier**: cardiffnlp/twitter-roberta-base-sentiment-latest
  for short-form text; SamLowe/roberta-base-go_emotions if you want
  richer labels (27 emotions vs 3 sentiments).
- **topic_tagger**: facebook/bart-large-mnli (zero-shot, ~1.5 GB) or
  MoritzLaurer/deberta-v3-base-zeroshot-v2.0 (smaller, often as good).
- **severity_classifier**: probably a fine-tuned small classifier
  trained on a labeled severity corpus. No good off-the-shelf option I
  know of; might be the place where the role-decomposition pattern with
  a small LLM (Phi-3-mini, Qwen-2.5-1.5B) still wins.
- **geolocator**: spaCy's NER + a gazetteer (GeoNames) — pure rule-based
  pipeline, no model needed.
- **summarizer**: facebook/bart-large-cnn (~1.6 GB) for extractive-
  flavored summaries; google/pegasus for abstractive. Both faster and
  cheaper than even a small LLM on long inputs.
- **arithmetic / math** (if/when added): `sympy` for symbolic,
  `numpy`/`scipy` for numeric — skip the LLM entirely. Use a small LLM
  only for "translate this word problem into a sympy expression."

I can produce a more detailed shortlist with HuggingFace links, model
sizes, license notes, and known failure modes — say within a week.

#### 3b. Backend-adapter sketch

Two paths to evaluate side by side:

- **Path A**: keep the `Backend` interface as `(str, str) → str` and
  wrap each specialized model in a thin adapter that turns a structured
  call into a prompt+response shape. Compatible with the current
  framework but feels forced.
- **Path B**: introduce a `Role` interface that's richer than the
  current `nl_role` ←→ `Backend` pair. Roles can choose any callable
  shape, including non-LLM. The current `nl_role` becomes one concrete
  Role; a `spacy_role` becomes another.

My instinct is Path B, but it's not a small refactor. Worth a design
doc before any code.

#### 3c. End-to-end POC

One office reimplemented with polyglot backends: `situation_room` with
spaCy for entities, roberta for sentiment, BART-MNLI for topic, Qwen
for the writer. Measure on the same corpus:

- Quality (vs. all-Qwen and all-Claude baselines)
- Latency per article
- Watt-hours per article (rough)
- Dollars per article

This is also publishable. See thread for Paper 2 (`task #110` in the
TaskList) which is the empirical SLM-vs-LLM paper.

---

## 4. Office grammar for chatbots and conversational systems

### Why this matters

Every example in DSL today is sense-and-respond: the office wakes up,
pulls from sources, processes, writes to sinks, terminates (or polls).
Pat does this work, but Pat uses chatbots more. ChatGPT, Claude.ai,
Perplexity — turn-based conversational interfaces are where most of
Pat's AI minutes go.

A chatbot, structurally, is still a network of agents. A
sophisticated one is:

```
user input → router → [specialist A | specialist B | specialist C] →
             composer → user output → [next turn]
```

Or a RAG chatbot:

```
user query → retriever → grounder → composer → user output → [next turn]
```

These are real agent networks. DSL's vocabulary (sources, agents,
sinks, connections, named ports, state) covers most of what they need
— but DSL has no first-class concept of a *conversation*, a *turn*, or
the cycle that links user output back to user input.

If we extend the grammar to cover chat without losing the simplicity of
the sense-and-respond case, then DSL covers most of what Pat actually
asks AI to do. That's a much bigger Pat audience.

### Current state

- Office.md is acyclic. The `Connections` block describes a DAG.
- The framework supports `state=` on blocks (so an agent can carry
  memory across messages) but there's no notion of conversation-scoped
  state.
- Sources and Sinks are not interactive — they pull/push on a schedule
  or to a destination, but they don't sit on a user's stdin.
- No multi-tenant model. One office instance per process.

### Open questions

- **The grammar.** Does office.md need a new construct (a `Conversation:`
  block?) or does it already cover this with the right Source/Sink?
- **Cycles.** Should office.md allow cyclic connections? A "reply →
  user → query" loop is a cycle in the formal graph. Could be hidden
  inside an interactive Source/Sink wrapper.
- **Memory.** Where does per-turn context live? Per-conversation
  context? Across-conversation user memory (preferences, history)?
- **Retrieval.** RAG is the dominant chatbot pattern. Does it deserve a
  first-class abstraction or is it just "Source: vector_retriever +
  Agent: grounder + Agent: composer"?
- **Multi-tenancy.** Can one office instance serve many concurrent
  conversations? Most production chatbots do this; DSL would need to
  acquire the concept.

### Near-term threads

1. Write a single chatbot office.md sketch by hand — the canonical
   "answer questions about my company's docs" RAG bot. Just try to
   write it in current DSL grammar. The places it breaks (or where the
   English feels strained) will tell us what new constructs are needed.
2. Build an interactive `Source` and `Sink` pair: a REPL-style source
   (reads from stdin / a websocket) and a matching sink. Verify the
   existing framework can run a one-turn chatbot office without any
   grammar changes.
3. From those two experiments, decide whether chat needs new grammar
   or just new components.

---

## How this list is maintained

This is a north star, not a backlog. The tactical work — bug fixes,
launch checklist items, individual feature requests — lives in the
TaskList and gets refreshed weekly. This document gets refreshed every
quarter:

- Add a thread if a new research direction shows up that's worth a year
  of effort.
- Promote an item from a thread's "near-term" section into the TaskList
  when it becomes tactical (a real task with a deadline).
- Don't delete completed work — note it as "shipped in vX.Y" so the
  thread retains its history.

The point of having both this file and the TaskList is to keep the
year-horizon strategy from being smothered by the week-horizon
deadlines, while keeping the week-horizon deadlines from being
smothered by the year-horizon strategy.
