# Job Postings Monitor

Monitors three job boards for software engineering and data science roles.
Filters postings by seniority level and remote work arrangement, and
delivers a daily digest of new openings.

## What it does

- Pulls from Python.org Jobs, RemoteOK, and We Work Remotely
- Filters out postings that aren't software engineering or data science roles
- Classifies each posting by seniority (junior / mid / senior / lead)
- Identifies remote work arrangement (remote / hybrid / on-site)
- Streams one line per posting to your terminal
- Delivers a daily digest grouped by seniority level

## How to run

```bash
export ANTHROPIC_API_KEY='your-key-here'
python3 -m gallery.job_postings.app
```

## What you'll see

```
🌐 [     python_jobs] [JUNIOR] Junior Python Developer — Remote, Berlin
🏠 [        remoteok] [   MID] Full Stack Engineer (Python/React) — Hybrid NYC
🏢 [we_work_remotely] [SENIOR] Senior Data Scientist — On-Site San Francisco
```

A daily digest grouped by seniority is printed at midnight.

## How to customize

Open `app.py` and edit the `relevance_agent` prompt to target a different
role type. For example, to focus on ML engineering roles:

```python
relevance_agent = ai_agent("""
    Is this a job posting for a machine learning engineer or ML researcher role?
    Return JSON only, no explanation: {"relevant": true or false}
""")
```

You can also add your own criteria — for example a `salary_agent` that
extracts salary range from the posting text.

## How it works

See [gallery/README.md](../README.md) for an explanation of the
gather-scatter pattern used by all gallery apps.