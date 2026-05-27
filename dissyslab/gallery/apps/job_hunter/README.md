# job_hunter

**Tags:** filter, fan-out, multi-agent pipeline, file-include

A five-agent office that watches four tech-jobs RSS feeds and, for
every posting it likes, runs four separate language-model agents in
parallel: a screener, a matcher, a tailor (resume rewriter), a drafter
(cover letter writer), and a researcher (company background). The
result of each pass is a job-application packet: a match report, a
tailored resume, a cover letter, and a company brief — produced
automatically while the candidate sleeps.

The office is in the gallery as a showcase of DSL's flexibility: one
office.md, five LLM agents, eight sinks, the conditional-branch
pattern, and the new ``{{include: filename}}`` directive (used by
matcher, tailor, and drafter to embed the candidate's resume into
their prompts). Originally seeded by Nyasha Makaya as part of his
React app for DisSysLab.

## Run

```bash
dsl run job_hunter
```

While the office runs you will see:

- **Console:** one card per matched job in the situation-room display.
- **`matched_jobs.html`** in the current directory — a live-refreshing
  HTML report with one card per match (open it in a browser; reload
  to see new matches).
- **`matched_jobs.jsonl`** — the same matches as raw JSON lines.
- **`discarded_jobs.jsonl`** — postings Alex screened out, so you
  can review what the office is rejecting and adjust the screener
  prompt if needed.
- **`outbox.md`** — a Markdown feed of *all four* email types the
  office produces (Job Match notification, Tailored Resume, Cover
  Letter Draft, Company Brief), one block per email, ready to copy
  into a real email or job-application form.

By default all four `gmail_sink_*` instances are in **preview mode**
— they do not actually send anything; they append to `outbox.md`. To
send for real, set the `GMAIL_USER` and `GMAIL_APP_PASSWORD`
environment variables (see "Turn on email notifications" below) and
every sink switches automatically — no office.md change required.

## How it is wired

```
hacker_news    ─┐
python_jobs    ─┤
remoteok       ─┼→ Alex ─relevant→ Morgan ─matched_jobs→ ┬→ intelligence_display
we_work_remotely┘    │                                    ├→ matched_jobs.jsonl
                     │                                    ├→ matched_jobs.html
                     │                                    ├→ outbox.md (Match)
                     │                                    ├→ Riley   (tailored resume)  → outbox.md
                     │                                    ├→ Dakota  (cover letter)     → outbox.md
                     │                                    └→ Sage    (company brief)    → outbox.md
                     └─discard──→ discarded_jobs.jsonl
```

The office demonstrates:

- **Conditional branch.** Alex has two output ports (`relevant`,
  `discard`); each goes to a different downstream block.
- **Fan-out.** Morgan's single `matched_jobs` port fans out to seven
  destinations — three recorders, the console display, and three
  follow-on LLM agents — all evaluated in parallel.
- **File-included prompts.** matcher, tailor, and drafter each embed
  `resume.md` into their system prompt via the framework's
  `{{include: resume.md}}` directive. Edit `resume.md` and all three
  prompts pick up the new content the next time the office starts.
- **Preview-mode sinks.** Four distinct `gmail_sink` instances share
  the same outbox so the candidate has one place to read everything,
  but each carries its own subject so the entries are easy to
  scan.

## The five agents

| Agent  | Role         | What it does |
| ------ | ------------ | --- |
| Alex   | `screener`   | Keeps only postings relevant to a CS new-grad / intern; routes the rest to `discarded_jobs.jsonl`. |
| Morgan | `matcher`    | Compares the posting against `resume.md` and emits a structured match report (title, company, location, salary, match_rating, resume_matches, skills_match, gaps, application_link, reason). |
| Riley  | `tailor`     | Rewrites `resume.md` to foreground experience relevant to *this specific job* — reorders, rewords, drops. Never invents experience. |
| Dakota | `drafter`    | Writes a 220-320 word cover letter that ties three concrete resume bullets to three concrete elements of the role. |
| Sage   | `researcher` | Produces a short company-background brief (what they do, recent direction, why this role might appeal to the candidate, three interview questions). Honest about gaps in its training knowledge. |

## Customise

- **Edit `resume.md`** in this folder. The shipped version is a
  placeholder for "Pat Smith", a CS student graduating June 2027.
  Replace with your own resume — and because matcher, tailor and
  drafter all `{{include: resume.md}}`, every downstream agent picks
  up the new content automatically.
- **Edit `roles/screener.md`** to change what jobs count as
  relevant. The current screener targets early-career technical
  roles (intern / new grad / IC engineering).
- **Edit `roles/matcher.md`** to change the structured match
  schema or the match-rating thresholds.
- **Edit `roles/tailor.md` / `drafter.md` / `researcher.md`** to
  change tone, length, or output shape.
- **Change which feeds to watch** by editing the `Sources:` line.
  The framework ships shortcuts for `hacker_news`, `python_jobs`,
  `remoteok`, `we_work_remotely`; any new RSS feed works with
  `rss(url="...", name="my_feed")`.
- **Turn on email notifications.** Change the four
  `gmail_sink_*(to="you@example.com", ...)` lines to your address,
  then set the `GMAIL_USER` and `GMAIL_APP_PASSWORD` environment
  variables (one-time setup at
  myaccount.google.com → Security → App passwords). All four sinks
  detect credentials and switch from preview to sending. To drop a
  follow-on agent (e.g. you don't want cover letters), remove it
  from the `Agents:` section and its corresponding connection line.

## Cost note

The office runs **five LLM calls per relevant posting** (Alex,
Morgan, Riley, Dakota, Sage). With a small local model (e.g. Qwen
via Ollama or OpenRouter) this is essentially free. With a frontier
API model, expect a non-trivial bill if you point this at a high-
volume feed — consider lowering `max_articles` in the `Sources:`
line, or removing one or more of the follow-on agents.
