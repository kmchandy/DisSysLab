# DisSysLab Gallery

Five streaming apps you can run right now. Each monitors live data sources
continuously, filters for what matters to you, and delivers a daily digest.

All the intelligence is driven by plain-English prompts at the top of each
`app.py`. Change the prompt, change the behavior — no other code needed.

---

## The Apps

### 🤖 AI/ML Research Tracker
Monitors Hacker News, MIT Tech Review, TechCrunch, and VentureBeat AI for
AI and machine learning developments. Rates each article by sentiment and
impact level. Delivers a daily digest grouped by impact.
```
✅🔴 [    hacker_news] Mistral releases new open-weight model beating GPT-4
         https://news.ycombinator.com/item?id=...

❌🟡 [ mit_tech_review] AI hiring tools shown to amplify bias in new study
         https://www.technologyreview.com/...
```
```bash
python -m gallery.ai_ml_research.app
```

---

### 📰 Topic Tracker
Monitors Al Jazeera, NPR, and BBC World for topics you specify. Compares
how different international outlets frame the same story.

**Customize:** Edit `TOPICS` at the top of `app.py`:
```python
TOPICS = ["climate change", "artificial intelligence", "US elections"]
```
```
✅ [  aljazeera] [climate change] UN climate summit reaches landmark agreement
        https://www.aljazeera.com/...

❌ [   bbc_world] [US elections] Polling shows record low trust in institutions
        https://www.bbc.co.uk/...
```
```bash
python -m gallery.topic_tracker.app
```

---

### 💼 Job Postings Monitor
Monitors Python.org, RemoteOK, and We Work Remotely for jobs that match
your profile. Highlights the top 3 most promising postings each day.

**Customize:** Edit `JOB_CRITERIA` at the top of `app.py`:
```python
JOB_CRITERIA = """
I am a Python developer with 2 years of experience looking for a
remote backend or data engineering role at an AI or climate tech company.
"""
```
```
💼 [     python_jobs] Senior Backend Engineer - Python/FastAPI
   Strong match: remote backend role at an AI-focused company
   https://www.python.org/jobs/...
```
```bash
python -m gallery.job_postings.app
```

---

### 🛠️ Developer News Tracker
Monitors Hacker News, TechCrunch, and BBC Tech for news relevant to
software developers. Groups stories by category and flags cross-source coverage.

**Customize:** Edit `DEV_INTERESTS` at the top of `app.py`:
```python
DEV_INTERESTS = ["Python", "open source", "developer tools", "APIs", "AI coding assistants"]
```
```
✅ [  hacker_news] [open source] PostgreSQL 17 released with major performance gains
        https://news.ycombinator.com/...

➖ [   techcrunch] [APIs] Stripe overhauls developer documentation
        https://techcrunch.com/...
```
```bash
python -m gallery.developer_news.app
```

---

### 🌍 Climate Monitor
Monitors NASA, BBC Tech, and NPR for climate and environment news.
Tracks sentiment across sources and notes whether today's news is
encouraging or concerning.

**Customize:** Edit `CLIMATE_TOPICS` at the top of `app.py`:
```python
CLIMATE_TOPICS = ["climate change", "renewable energy", "carbon emissions", "extreme weather", "biodiversity"]
```
```
🌱 [      nasa] [renewable energy] Solar capacity hits record high in Q3 2025
        https://www.nasa.gov/...

🌊 [   npr_news] [extreme weather] Hurricane season most active on record
        https://feeds.npr.org/...
```
```bash
python -m gallery.climate_monitor.app
```

---

## Quick Start

**1. Set your API key:**
```bash
export ANTHROPIC_API_KEY='your-key'
```

**2. Pick an app and run it:**
```bash
python -m gallery.topic_tracker.app
```

**3. Personalize it** by editing the config variables at the top of `app.py`.

That's it. The app runs continuously, streaming matches to the console
and printing a digest once a day. Press `Ctrl+C` to stop.

---

## How It Works

Every app follows the same pattern: multiple RSS sources feed into an AI
filter that keeps only relevant articles, which flow to a display sink for
immediate output and accumulate in a stateful agent until a daily clock tick
triggers a digest report. This gather-scatter pattern is one of the core
topologies in distributed systems — and here it runs in a dozen lines of
network definition code.

To understand the pattern in depth, see [How It Works](../docs/HOW_IT_WORKS.md).
To build your own app using this pattern, see [Module 08](../examples/module_08/).