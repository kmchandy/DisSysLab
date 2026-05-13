# New Grad Jobs

> A continuously-running office that watches a tech-jobs feed for
> entry-level / new-grad / intern openings and reformats each
> match as a clean job brief. Pick your engine — free local Qwen,
> hosted OpenRouter, Claude, or your own.

## What this office does

Every few minutes, New Grad Jobs polls Hacker News' "Who's Hiring"
thread (and other tech-news sources you can swap in), screens each
posting for fit, and reformats the keepers into structured job
briefs you can scan over coffee.

```
hacker_news → Jordan (screener) ──── kept ──── Casey (formatter) ──→ intelligence_display
                                                                  └─→ jobs.jsonl
                                ─── dropped ──→ jobs.jsonl
```

Two agents. One source. One screening decision, one reformatting
pass.

**Screener (Jordan)** keeps a posting if it is:

- an entry-level / new-grad / junior / intern role,
- in Software Engineering, AI/ML, Data Science, or closely related,
- located in the US or Canada (or remote and open to US/Canada
  applicants),
- ideally mentioning Python.

**Formatter (Casey)** writes a clean brief with role, company,
location, type, tech, two-sentence summary, flags (visa
sponsorship, remote-friendly), url, source, timestamp.

## Run it

```bash
dsl run new_grad_jobs
```

Each kept posting is printed to your terminal and appended to
`jobs.jsonl` in your working directory. Rejected postings are
recorded in the same JSONL so you can audit what the screener
dropped. Press Ctrl-C to stop polling.

## What's actually in office.md

The office description is in
[`office.md`](office.md), annotated with `# SLOT N:` markers
showing the four edit slots. Pat-friendly remixes:

- **SLOT 1 — sources.** Swap `hacker_news` for `techcrunch`,
  `mit_tech_review`, or a custom RSS feed; combine sources to
  watch multiple boards.
- **SLOT 2 — screener.** Edit `roles/screener.md` to change the
  fit criteria — different industries, different seniority levels,
  different geographies, different tech stacks.
- **SLOT 3 — formatter.** Edit `roles/formatter.md` to change the
  fields, the summary length, the flag set.
- **SLOT 4 — sinks.** Replace `intelligence_display` with
  `markdown_digest(path="~/jobs.md")` for a daily file you can
  open in any markdown viewer, or `slack_sink` to push hits to a
  Slack channel.

See [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
for the pattern this office instantiates.

## What you should expect

- **Quality**: the screener is a one-job classifier with a short
  prompt — small open-weight models (Qwen3-A3B) handle it
  reliably. The formatter is also one-shot per posting.
- **Speed**: Hacker News' Who's Hiring thread has a few hundred
  postings; each screened posting is one LLM call, each kept
  posting is one more. On OpenRouter, a full pass is 1-3 minutes
  and a few cents; on local Ollama, 10-30 minutes.
- **Cost**: $0/month on Ollama (after the one-time model
  download), pennies per day on OpenRouter, dimes per day on
  Claude.

## Credit

Originally contributed by Nyasha as a custom gallery app, adapted
to the v1.3+ gallery structure and the `sense → think → respond`
pattern.

## See also

- [`docs/PATTERN_sense_think_respond.md`](../../../../docs/PATTERN_sense_think_respond.md)
  — the pattern this office instantiates.
- [`situation_room`](../situation_room/) — the bigger cousin: same
  shape with four parallel thinkers, a writer, and an editor.
- [`docs/BUILD_APPS.md`](../../../../docs/BUILD_APPS.md) — design
  and wire your own office from scratch.
