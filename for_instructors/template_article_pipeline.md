# DisSysLab Template: Article Processing Pipeline

**Pattern:** Source → Filter → Analyze → Route → Output  
**Use this when:** You want to monitor websites, news feeds, or social media, 
analyze each article, and act on the results.

**Copy this template, then tell Claude:**
> "Use this DisSysLab template to build an app that monitors [YOUR TOPIC]. 
> Filter out [WHAT TO IGNORE]. For each article, [WHAT TO ANALYZE]. 
> Send [CONDITION] articles to [WHERE]."

---

## TEMPLATE
```python
# ============================================================
# DisSysLab Article Processing Pipeline
# ============================================================
# TOPIC:    [e.g., "Python news from Hacker News"]
# FILTER:   [e.g., "drop spam and job postings"]  
# ANALYZE:  [e.g., "sentiment and urgency"]
# OUTPUT:   [e.g., "urgent positive articles to console and archive"]
# ============================================================

from dsl import network
from dsl.blocks import Source, Transform, Sink, Split

# ── Demo Sources (no API keys needed) ──────────────────────
from components.sources.demo_rss_source import DemoRSSSource
# SLOT: choose feed_name from: "hacker_news", "tech_news", "reddit_python"
rss = DemoRSSSource(feed_name="hacker_news")  # REPLACE FEED

# ── Live Source (uncomment to use real RSS) ─────────────────
# from components.sources.rss_source import RSSSource
# rss = RSSSource("https://YOUR_FEED_URL/rss")  # REPLACE URL

# ── AI Agents ───────────────────────────────────────────────
from components.transformers.prompts import (
    SPAM_DETECTOR,
    SENTIMENT_ANALYZER,
    # URGENCY_DETECTOR,     # uncomment if needed
    # TOPIC_CLASSIFIER,     # uncomment if needed
)
from components.transformers.demo_ai_agent import demo_ai_agent
# SLOT: swap demo_ai_agent → ai_agent for real Claude analysis
spam_detector    = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)


# ── Step 1: Filter ───────────────────────────────────────────
def filter_unwanted(article: dict) -> dict | None:
    """Drop articles you don't want. Return None to discard."""
    result = spam_detector(article)
    if result["is_spam"]:
        return None
    # SLOT: add more filter conditions here
    # e.g., if "job" in article["title"].lower(): return None
    return article


# ── Step 2: Analyze ──────────────────────────────────────────
def analyze(article: dict) -> dict:
    """Add analysis fields to the article dict."""
    result = sentiment_analyzer(article)
    article["sentiment"] = result["sentiment"]   # "POSITIVE" | "NEGATIVE" | "NEUTRAL"
    article["score"]     = result["score"]       # float -1.0 to 1.0
    # SLOT: add more analysis here, e.g.:
    # urgency = urgency_detector(article)
    # article["urgency"] = urgency["urgency"]
    return article


# ── Step 3: Route ────────────────────────────────────────────
def route(article: dict) -> list:
    """
    Return [out_0, out_1, out_2] — None means skip that output.
    SLOT: change routing conditions to match your use case.
    """
    is_interesting = article["score"] > 0.2   # REPLACE CONDITION
    return [
        article if is_interesting else None,   # out_0 → archive
        article,                               # out_1 → console (always)
        article if article["score"] < -0.5 else None,  # out_2 → alert (very negative)
    ]


# ── Sinks ────────────────────────────────────────────────────
from components.sinks.jsonl_recorder import JSONLRecorder
from components.sinks.demo_email_alerter import DemoEmailAlerter

archive = JSONLRecorder(path="articles.jsonl", mode="w", flush_every=1)
alerter = DemoEmailAlerter(to_address="you@example.com", subject_prefix="[ALERT]")


def display(article: dict) -> None:
    """SLOT: customize what you print."""
    icon = {"POSITIVE": "✅", "NEGATIVE": "❌", "NEUTRAL": "➖"}.get(article["sentiment"], "?")
    print(f"{icon} [{article['sentiment']:>8}] {article['title']}")


# ── Build Network ────────────────────────────────────────────
source      = Source(fn=rss.run,           name="feed")
spam_filter = Transform(fn=filter_unwanted, name="filter")
analyzer    = Transform(fn=analyze,         name="analyze")
router      = Split(fn=route, num_outputs=3, name="router")
archive_sink = Sink(fn=archive.run,         name="archive")
console_sink = Sink(fn=display,             name="console")
alert_sink   = Sink(fn=alerter.run,         name="alert")

g = network([
    (source,       spam_filter),
    (spam_filter,  analyzer),
    (analyzer,     router),
    (router.out_0, archive_sink),
    (router.out_1, console_sink),
    (router.out_2, alert_sink),
])

# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("📰 Article Pipeline — demo mode")
    print("   Swap demo_ai_agent → ai_agent for real Claude analysis")
    print("=" * 60)
    g.run_network()
```

---

## SLOT GUIDE

| SLOT | What to change | Example |
|------|----------------|---------|
| Feed | `feed_name=` or `RSSSource(url)` | `"reddit_python"` or `"https://hnrss.org/frontpage"` |
| Filter | conditions in `filter_unwanted()` | drop if "job" in title |
| Analyze | which prompts you import and call | add `URGENCY_DETECTOR` |
| Route | conditions in `route()` | send HIGH urgency to out_2 |
| Output | `display()` print format, archive path | add emoji, change filename |
| Demo→Live | swap `demo_ai_agent` → `ai_agent` | requires `ANTHROPIC_API_KEY` |

---

## EXAMPLE PROMPT FOR CLAUDE

> "Use the DisSysLab article pipeline template to build an app that monitors 
> Python job postings from Hacker News. Filter out articles that aren't job 
> postings. Classify each posting as junior, mid-level, or senior using the 
> TOPIC_CLASSIFIER prompt. Send junior postings to console, all postings to 
> archive, and senior postings to an email alert."

Claude should fill in the SLOTs and produce a working app with no further help.
