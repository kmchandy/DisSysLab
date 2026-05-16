# New Grad Jobs

> Hacker News' "Who's Hiring" thread runs every month with a few
> hundred postings. This office reads it, filters down to
> entry-level / new-grad / intern openings in SWE, AI/ML, and Data
> Science, and reformats each match as a structured brief.
> Two agents. One office.md. Pick your engine.

## What this office does

```
hacker_news → Jordan (screener) ──── kept ──── Casey (formatter) ──→ intelligence_display
                                                                  └─→ jobs.jsonl
                                ─── dropped ──→ jobs.jsonl
```

Every ten minutes, the office polls the Hacker News firehose (or
any other tech-news feed you point at it), runs each posting past
a one-job screener agent that decides whether it fits the
new-grad / entry-level / intern profile, and then runs the keepers
through a one-job formatter agent that emits a clean structured
brief. Rejected postings are recorded too so you can audit later
what the screener dropped.

A sample brief looks like:

```json
{
  "role": "Software Engineer, New Grad",
  "company": "Anthropic",
  "location": "San Francisco, CA or Remote (US)",
  "type": "New Grad",
  "tech": ["Python", "TypeScript", "ML systems"],
  "text": "Anthropic is hiring new-grad software engineers
           across infrastructure, research engineering, and
           product. The role is open to candidates graduating
           within the past year and includes work on Claude's
           training and serving systems.",
  "flags": ["Visa Sponsorship", "Remote-Friendly"],
  "url": "https://news.ycombinator.com/item?id=...",
  "source": "hacker_news",
  "timestamp": "2026-05-13T14:22:18Z"
}
```

A dozen of these every cycle, into your terminal and onto disk.
No tab-switching, no rereading the same posting five times, no
"wait, did this one say new-grad or senior?" anxiety.

## Why this fits on a free local model

Both roles — `screener` and `formatter` — are one-job prompts of
under 30 lines each. Neither needs the model to "be smart" — they
need it to follow a structured instruction reliably. That's
exactly what small open-weight models do well. The office runs
fine on local Qwen3-30B-A3B (see `dev/PROMPTING_FOR_SLMS.md` for
why role-decomposition makes this work); you do not need a
frontier model.

## Run it

```bash
dsl run new_grad_jobs
```

Each kept posting prints to your terminal and appends to
`jobs.jsonl` in your working directory. Rejected postings are
recorded in the same JSONL with their reason for rejection. Press
Ctrl-C to stop polling. With `poll_interval=600`, the office
re-checks every ten minutes; new postings appear as the office
sees them.

## Make it yours

The office description is in
[`office.md`](office.md), annotated with `# SLOT N:` markers
showing the four edit slots. Pat-friendly remixes:

- **SLOT 1 — sources.** Swap `hacker_news` for `techcrunch`,
  `mit_tech_review`, `python_jobs`, or a custom RSS feed; combine
  sources to watch multiple boards at once.
- **SLOT 2 — screener.** Edit `roles/screener.md` to change the
  fit criteria — different industries (data engineering, product
  management, robotics), different seniority (senior roles only,
  internships only), different geographies (Europe-only, India-only),
  different tech stacks.
- **SLOT 3 — formatter.** Edit `roles/formatter.md` to change the
  output shape — add salary parsing, drop the "flags" field, write
  one-line summaries instead of two-sentence ones, emit Markdown
  instead of JSON.
- **SLOT 4 — sinks.** Replace `intelligence_display` with
  `markdown_digest(path="~/jobs.md")` for a single daily file in
  any markdown viewer, or `slack_sink` to push hits to a Slack
  channel, or `gmail_sink` to email yourself a roundup.

See [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
for the pattern this office instantiates and what other gallery
offices follow the same shape.

## What you should expect

- **Quality**: the screener is calibrated on Hacker News' Who's
  Hiring postings; quality on other sources may vary. The
  formatter's structured output is reliable on small open-weight
  models because it's a one-shot rewrite, not a reasoning task.
- **Speed**: depends on backend. On OpenRouter (`Qwen-2.5-7B`),
  ~1–3 minutes per polling cycle and well under a cent. On local
  Ollama, 10–30 minutes per cycle depending on hardware. The office is
  designed to run in the background on a cron, not at the speed
  of a chatbot.
- **Cost**: $0 on Ollama after the one-time model download;
  pennies per day on OpenRouter; tens of cents per day on Claude
  if you set every agent to use it. See
  [`docs/LANGUAGE_MODELS.md`](../../../../docs/LANGUAGE_MODELS.md)
  for per-role overrides.

## Credit

Originally contributed by Nyasha as a custom gallery app, adapted
to the v1.3+ gallery structure and the sense → think → respond
pattern.

## See also

- [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
  — the pattern this office instantiates.
- [`situation_room`](../situation_room/) — the bigger cousin: same
  shape with four parallel thinkers, a writer, and an editor.
- [`docs/BUILD_APPS.md`](../../../../docs/BUILD_APPS.md) — design
  and wire your own office from scratch.
