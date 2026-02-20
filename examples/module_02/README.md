# Module 2: AI Integration

*Your first real-world AI-powered distributed system.*

---

## Files in This Module

| File | What it does |
|------|-------------|
| `README.md` | This guide |
| `example_demo.py` | Demo version: DemoRSSSource → sentiment → entity extraction → display (no API key) |
| `example_real.py` | Real version: BlueSky → Claude AI sentiment → entity extraction → JSONL + display |
| `test_module_02.py` | Test suite — run with `python3 -m pytest examples/module_02/test_module_02.py -v` |

Run any example from the DisSysLab root:
```bash
python3 -m examples.module_02.example_demo
python3 -m examples.module_02.example_real    # requires ANTHROPIC_API_KEY
```

---

In Module 1 you built a pipeline with demo components — keyword-based spam detection, simulated sentiment analysis, fake RSS data. It worked, and you learned the pattern. Now you're going to do the same thing with real data and real AI. The code looks almost identical. The results will be dramatically better.

This module uses **BlueSky** (a public social media platform) as a live data source and **Claude AI** for real sentiment analysis and entity extraction. Your app will monitor real posts from real people in real time, analyze them with real AI, and save the results to a file.

---

## Part 1: Setup (10 minutes)

You need two things: an Anthropic API key and the component files in your Claude Project.

### Get Your Anthropic API Key

You already have a Claude account from Module 1. Now you need an API key so your Python code can call Claude programmatically.

1. Go to [console.anthropic.com](https://console.anthropic.com).
2. Sign in with the same account you use for claude.ai.
3. Click **Settings** in the left sidebar, then **API Keys**.
4. Click **Create Key**.
5. Give it a name like "DisSysLab" and click **Create**.
6. **Copy the key immediately** — you won't see it again. It looks like `sk-ant-api03-...`.
7. Set it as an environment variable in your terminal:

**macOS / Linux:**
```bash
export ANTHROPIC_API_KEY='sk-ant-api03-your-key-here'
```

To make this permanent, add the export line to your `~/.zshrc` (macOS) or `~/.bashrc` (Linux) file.

**Verify it works:**
```bash
python3 -c "
from anthropic import Anthropic
client = Anthropic()
msg = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=20,
    messages=[{'role': 'user', 'content': 'Say OK'}]
)
print(msg.content[0].text)
"
```

If you see "OK" — you're ready.

### Upload Component Files to Your Claude Project

In Module 1, your Claude Project had only `CLAUDE_CONTEXT.md`. For Module 2, Claude needs to see the real component source code so it generates correct imports and constructor parameters.

1. Open your **DisSysLab** project on [claude.ai](https://claude.ai).
2. Go to the project's **Files** section.
3. Upload these files from your DisSysLab repository:
   - `components/sources/bluesky_jetstream_source.py`
   - `components/transformers/ai_agent.py`
   - `components/transformers/prompts.py`
   - `components/sinks/jsonl_recorder.py`

`CLAUDE_CONTEXT.md` should already be there from Module 1. If not, upload it too.

That's the complete setup. You won't need to do this again.

---

## Part 2: Try the Demo First (5 minutes)

Before using real AI, run the demo version to see the pipeline shape:

```bash
python3 -m examples.module_02.example_demo
```

This uses `DemoRSSSource` and `demo_ai_agent` — the same demo components from Module 1. No API key needed. The output shows the pipeline working: articles flow through sentiment analysis, then entity extraction, then display.

---

## Part 3: Run With Real AI (5 minutes)

Now run the real version:

```bash
python3 -m examples.module_02.example_real
```

The real version looks like this:

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource
from components.transformers.prompts import SENTIMENT_ANALYZER, ENTITY_EXTRACTOR
from components.transformers.ai_agent import ai_agent
from components.sinks import JSONLRecorder

# --- Live data source ---
bluesky = BlueSkyJetstreamSource(filter_keywords=["AI", "machine learning"], max_posts=5)

# --- Real AI agents ---
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)
entity_extractor = ai_agent(ENTITY_EXTRACTOR)

# --- Transform functions ---
def analyze_sentiment(post):
    text = post["text"] if isinstance(post, dict) else post
    result = sentiment_analyzer(text)
    return {
        "text": text,
        "sentiment": result.get("sentiment", "UNKNOWN"),
        "score": result.get("score", 0.0),
        "reasoning": result.get("reasoning", "")
    }

def extract_entities(article):
    result = entity_extractor(article["text"])
    article["people"] = result.get("people", [])
    article["organizations"] = result.get("organizations", [])
    article["locations"] = result.get("locations", [])
    return article

def print_article(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    emoji = icon.get(article["sentiment"], "❓")
    people = ", ".join(article.get("people", [])) or "none"
    locations = ", ".join(article.get("locations", [])) or "none"
    print(f"  {emoji} [{article['sentiment']:>8}] {article['text'][:80]}")
    print(f"     People: {people} | Places: {locations}")
```

The network:

```
  bluesky  →  sentiment  →  entities  →  display
                                       →  archive (JSONL file)
```

Each post flows through two AI analyses. The sentiment transform adds sentiment fields. The entity transform adds people, organizations, and locations. The display sink shows results on screen. The archive sink saves everything to a JSONL file.

---

## Part 4: Side-by-Side — Demo vs Real (10 minutes)

Put the demo code next to the real code. Notice:

**What changed:**

| | Demo (Module 1) | Real (Module 2) |
|---|---|---|
| Source | `DemoRSSSource(feed_name="hacker_news")` | `BlueSkyJetstreamSource(filter_keywords=["AI"], max_posts=5)` |
| AI | `demo_ai_agent(SENTIMENT_ANALYZER)` | `ai_agent(SENTIMENT_ANALYZER)` |
| Call | `spam_detector(text)` | `sentiment_analyzer(text)` |

**What didn't change:**

- The import for prompts is identical: `from components.transformers.prompts import SENTIMENT_ANALYZER`
- The transform functions have the same structure — call the analyzer, get a dict back, use the fields.
- The network definition is the same — `network([(source, transform), ...])`.
- The `run_network()` call is identical.
- Filtering with `None` works the same way.

The swap from demo to real is: `demo_ai_agent` → `ai_agent`. That's it.

---

## Part 5: The Prompt Library (10 minutes)

The `SENTIMENT_ANALYZER` and `ENTITY_EXTRACTOR` prompts are two of 30+ pre-built prompts in `components/transformers/prompts.py`. See all available prompts:

```bash
python3 -m components.transformers.prompts
```

Prompts are Python constants. Import the ones you need:

```python
from components.transformers.prompts import (
    SENTIMENT_ANALYZER,    # Positive/negative/neutral
    ENTITY_EXTRACTOR,      # People, places, organizations
    SPAM_DETECTOR,         # Spam detection
    URGENCY_DETECTOR,      # Urgency levels
    TOPIC_CLASSIFIER,      # Topic categories
    TONE_ANALYZER,         # Formal/casual/sarcastic
    # ... 25+ more
)
```

Every prompt follows the same pattern: it tells Claude what to analyze and what JSON format to return. Your transform function receives that JSON as a Python dict. You don't need to understand prompt engineering to use these — just import a constant and pass it to `ai_agent()` or `demo_ai_agent()`.

---

## Part 6: Make It Yours (15 minutes)

### Experiment 1: Change the search keywords

```python
bluesky = BlueSkyJetstreamSource(filter_keywords=["climate", "climate change"], max_posts=5)
```

Or ask Claude:

> Change my app to monitor BlueSky for posts about climate change instead of AI.

### Experiment 2: Swap the AI analysis

Replace sentiment analysis with urgency detection:

```python
from components.transformers.prompts import URGENCY_DETECTOR
urgency_detector = ai_agent(URGENCY_DETECTOR)

def analyze_urgency(post):
    text = post["text"] if isinstance(post, dict) else post
    result = urgency_detector(text)
    return {"text": text, "urgency": result.get("urgency", "LOW")}
```

Same pipeline, different prompt. Now your app detects urgent posts instead of emotional ones.

### Experiment 3: Add a filter

Add a filter after sentiment analysis that drops neutral posts:

```python
def only_strong_sentiment(article):
    """Keep only positive and negative — drop neutral."""
    if article["sentiment"] == "NEUTRAL":
        return None
    return article
```

The `None` pattern from Module 1 works identically with real data.

### Experiment 4: Chain multiple AI analyses

Add topic classification after entity extraction:

```python
from components.transformers.prompts import TOPIC_CLASSIFIER
topic_classifier = ai_agent(TOPIC_CLASSIFIER)

def classify_topic(article):
    result = topic_classifier(article["text"])
    article["topic"] = result.get("primary_topic", "unknown")
    return article
```

Your pipeline now runs three AI analyses in sequence: sentiment → entities → topic. Each transform enriches the dict, and the sink gets the fully enriched result.

### Experiment 5: Compare demo vs real quality

Run both:
```bash
python3 -m examples.module_02.example_demo
python3 -m examples.module_02.example_real
```

The demo uses keyword matching. The real version uses Claude AI. Notice how real AI understands nuance, sarcasm, and context that keyword matching misses entirely.

---

## Cost Awareness

Each AI call costs a fraction of a cent. For Module 2's example (5 posts × 2 AI calls each = 10 API calls), the total cost is roughly $0.02-0.05. You can monitor your spending at [console.anthropic.com](https://console.anthropic.com) under **Usage**.

When experimenting, keep `max_posts` small (5-10) to minimize costs. Increase it once you're satisfied with your pipeline.

---

## What You've Learned

- **Real components have the same interface as demo components.** The swap is `demo_ai_agent` → `ai_agent`.
- **The Prompt → JSON → Python pattern.** A prompt constant defines what AI does. JSON structures the output. Your Python function uses the result as a dict.
- **The prompt library** has 30+ pre-built prompts ready to import and use.
- **Enrichment pipelines** — each transform adds fields to the data dict. The final result contains everything.
- **Live data is different.** Results vary because the data is real. AI analysis captures nuance that keyword matching misses.

## What's Next

**[Module 3: Multiple Sources, Multiple Destinations](../module_03/)** — pull from BlueSky *and* an RSS feed at the same time (fanin), and send results to both a file *and* email alerts (fanout). Your app goes from a single pipeline to a real monitoring system.