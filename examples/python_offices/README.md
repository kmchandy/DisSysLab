# Python Offices (Legacy Examples)

These six offices pre-date DisSysLab's English office grammar. They are
written entirely in raw Python — every wire, agent, and source is built
by hand in `app.py` rather than declared in `office.md`.

They live here, outside the shipped gallery, because the Path A user
experience is built around offices a first-year student can read and
modify *as plain English*. These offices use patterns that are
considerably more advanced (custom `Transform` blocks, `StatefulAgent`,
`ClockSource`, deep `dissyslab.components` imports) and so they would
get in the way if surfaced by `dsl list`.

We keep them around as *examples* of what the Python framework can do,
for students who outgrow the Path A surface and want to peek under the
hood.

## What's here

| Folder | What it does |
| --- | --- |
| `ai_ml_research/` | Polls multiple AI/ML RSS feeds, classifies and summarizes articles. Uses prepackaged demo data so it runs without API keys. |
| `arxiv_tracker/` | Watches arXiv for new papers in a chosen subject area. |
| `climate_news/` | Aggregates and analyzes climate-related news from several sources. |
| `developer_news/` | Pulls developer-focused feeds (Hacker News, etc.) and summarizes. |
| `job_postings/` | Watches a job-board feed and surfaces postings matching a profile. |
| `topic_tracker/` | Generic topic-watcher: subscribe to feeds, filter by topic, summarize. |

## How to run

These are Python scripts, not Path A offices. There is no `dsl run` for
them. From the repository root:

```bash
python3 examples/python_offices/ai_ml_research/app.py
```

(Same shape for the other five.)

## Status

These offices are **not** maintained against the current Path A
toolchain. Some imports may have drifted; some may need an API key set
in the environment. The intent is illustrative — read the code to see
how to build a non-trivial office in raw Python — not to be a smooth
user experience.

If you want a smooth experience, see `dissyslab/gallery/` and the
"Path A in 60 seconds" walkthrough in the project README.
