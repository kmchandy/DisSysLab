# arXiv Research Tracker

Monitors three arXiv subject feeds for new research papers matching your
chosen topics. Classifies each paper by type and impact, and delivers a
daily research digest.

Unlike the other gallery apps, this one uses a web scraper instead of RSS —
arXiv doesn't offer RSS feeds for recent submissions. The scraper polls
hourly; arXiv updates once daily around 8pm Eastern, so most polls find
nothing new, which is fine.

## What it does

- Scrapes arxiv.org/list/cs.AI, cs.LG, and cs.CL (hourly)
- Filters papers to only those matching your chosen topics
- Classifies each paper by type (empirical / theoretical / survey / benchmark / system)
- Rates likely impact (high / medium / low)
- Streams one card per paper to your terminal
- Delivers a daily research digest at midnight

## How to run

```bash
export ANTHROPIC_API_KEY='your-key-here'
python3 -m gallery.arxiv_tracker.app
```

## What you'll see

```
🔴🔬 [   CS_AI] large language models
     Constitutional AI: Harmlessness from AI Feedback
     👤 Yuntao Bai, Andy Jones, Kamal Ndousse...
     💬 Introduces a method for training AI systems to be helpful and harmless.
     🔗 https://arxiv.org/abs/2212.08073

🟡📐 [   CS_LG] reinforcement learning
     Reward Model Ensembles Help Mitigate Overoptimization
     👤 Thomas Coste, Usman Anwar, Robert Kirk...
     💬 Shows that ensembling reward models reduces reward hacking in RLHF.
     🔗 https://arxiv.org/abs/2310.02743
```

A daily research digest is printed at midnight.

## How to customize

Open `app.py` and edit the `TOPICS` list at the top:

```python
TOPICS = [
    "large language models",
    "agents and multi-agent systems",
    "reinforcement learning",
    "distributed systems",
    "AI safety and alignment",
]
```

Change these to whatever you want to track. The filter agent uses this list
to decide which papers are relevant — no other code changes needed.

To track different arXiv subject feeds, change the imports:

```python
from dissyslab.components.sources.web_scraper import arxiv_cs_ai, arxiv_cs_cv, arxiv_cs_ro
```

Available feeds: `arxiv_cs_ai`, `arxiv_cs_lg`, `arxiv_cs_cl`, `arxiv_cs_cv`, `arxiv_cs_ro`.

## How it works

See [gallery/README.md](../README.md) for an explanation of the
gather-scatter pattern used by all gallery apps.

The key difference from RSS-based apps: `ArxivScraper` fetches the raw HTML
listing page and parses it directly using BeautifulSoup. The parsed paper
data — title, authors, subjects — is assembled into the standard five-key
article dict, so the rest of the pipeline is identical to any other gallery app.
