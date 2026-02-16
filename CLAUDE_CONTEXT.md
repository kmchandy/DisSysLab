# DisSysLab — Context for Claude

You are helping a user build distributed systems using the DisSysLab framework. DisSysLab lets users build persistent, concurrent data processing applications using ordinary Python functions. The user describes what they want in natural language. You generate complete, runnable DisSysLab applications.

## How DisSysLab Works

Every DisSysLab app follows this pattern:

1. **Create component instances** (data sources, AI analyzers, output handlers)
2. **Write transform functions** (ordinary Python functions that process data)
3. **Wrap components into nodes** using `Source`, `Transform`, or `Sink`
4. **Connect nodes into a network** using `network([(from, to), ...])`
5. **Run** with `g.run_network()`

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink

# Nodes execute concurrently in separate threads.
# Messages flow through queues between connected nodes.
# The framework handles all threading, synchronization, and shutdown.
```

## Node Types

**Source** — generates data, has no input from other nodes.
```python
source = Source(fn=my_source.run, name="source_name")
```
The function is called repeatedly. Each call returns one item. Return `None` to signal completion.

**Transform** — processes data, receives one input, produces one output.
```python
transform = Transform(fn=my_function, name="transform_name")
# or with extra parameters:
transform = Transform(fn=my_function, params={"threshold": 0.5}, name="transform_name")
```
The function receives whatever the upstream node sent. Return a value to pass it downstream. **Return `None` to drop the message** (this is how filtering works).

**Sink** — consumes data, receives input, produces no output to other nodes.
```python
sink = Sink(fn=my_output.run, name="sink_name")
```

## Network Topology

Connect nodes with a list of `(from_node, to_node)` edges:

```python
g = network([
    (source, transform1),
    (transform1, transform2),
    (transform2, sink)
])
```

**Fanin** — multiple sources into one node (messages merge automatically):
```python
g = network([
    (source1, processor),
    (source2, processor),
    (source3, processor),
    (processor, sink)
])
```

**Fanout** — one node to multiple destinations (messages are copied automatically):
```python
g = network([
    (source, processor),
    (processor, sink1),
    (processor, sink2)
])
```

Any acyclic directed graph is valid: pipelines, fanin, fanout, diamonds, trees, complex DAGs.

## Available Mock Components (no API keys needed)

### Mock Sources

```python
from components.sources.mock_rss_source import MockRSSSource

# Available feeds: "hacker_news", "tech_news", "reddit_python"
rss = MockRSSSource(feed_name="hacker_news")
# rss.run() returns one article string per call, None when exhausted.
# Optional: max_articles=5 to limit count.
source = Source(fn=rss.run, name="news")
```

```python
from components.sources.list_source import ListSource

data = ListSource(items=["item1", "item2", "item3"])
source = Source(fn=data.run, name="data")
```

### Mock AI Agents

```python
from components.transformers.mock_claude_agent import MockClaudeAgent

# Spam detection — returns {"is_spam": bool, "confidence": float, "reason": str}
spam_detector = MockClaudeAgent(task="spam_detection")

# Sentiment analysis — returns {"sentiment": "POSITIVE"|"NEGATIVE"|"NEUTRAL", "score": float, "reasoning": str}
sentiment_analyzer = MockClaudeAgent(task="sentiment_analysis")

# Urgency detection — returns {"urgency": "HIGH"|"MEDIUM"|"LOW", "metrics": dict, "reasoning": str}
urgency_detector = MockClaudeAgent(task="urgency_detection")
```

These use keyword matching to simulate AI. They have the same `.run(text)` interface as the real ClaudeAgent.

### Mock Filters (simpler alternatives)

```python
from components.transformers import MockAISpamFilter, MockAISentimentAnalyzer, MockAINonUrgentFilter

# These return the text directly (or None to filter), not dicts.
# MockAISpamFilter().run(text) → text or None (if spam)
# MockAISentimentAnalyzer().run(text) → {"sentiment": str, "score": float, "reasoning": str}
# MockAINonUrgentFilter().run(text) → text or None (if not urgent)
```

### Sinks

```python
from components.sinks import MockEmailAlerter, JSONLRecorder

# Console email (prints to screen, no real email)
alerter = MockEmailAlerter(to_address="user@example.com", subject_prefix="[ALERT]")
sink = Sink(fn=alerter.run, name="email")

# JSON Lines file recorder
recorder = JSONLRecorder(path="output.jsonl", mode="w", flush_every=1, name="archive")
sink = Sink(fn=recorder.run, name="archive")

# Simple: collect into a Python list
results = []
sink = Sink(fn=results.append, name="collector")

# Simple: print to console
sink = Sink(fn=print, name="display")
```

## Available Real Components (require API keys)

### Real Sources

```python
from components.sources.rss_source import RSSSource

rss = RSSSource("https://news.ycombinator.com/rss")
source = Source(fn=rss.run, name="hackernews")
```

```python
from components.sources.bluesky_jetstream_source import BlueSkyJetstreamSource

bluesky = BlueSkyJetstreamSource(search_keywords=["python"], max_posts=50)
source = Source(fn=bluesky.run, name="bluesky")
```

### Real AI Agent

```python
from components.transformers.claude_agent import ClaudeAgent
from components.transformers.prompts import get_prompt

# Requires: export ANTHROPIC_API_KEY='your-key'
agent = ClaudeAgent(get_prompt("sentiment_analyzer"))
transform = Transform(fn=agent.run, name="sentiment")
```

Available prompts (use with `get_prompt("key")`):
- **Text analysis:** sentiment_analyzer, emotion_detector, tone_analyzer, readability_analyzer
- **Content filtering:** spam_detector, urgency_detector, toxicity_detector, profanity_filter
- **Classification:** topic_classifier, language_detector, intent_classifier, priority_classifier
- **Extraction:** entity_extractor, key_phrase_extractor, contact_extractor, date_time_extractor
- **Summarization:** text_summarizer, bullet_point_creator, title_generator, question_generator
- **Quality:** grammar_checker, style_checker, plagiarism_indicator
- **Comparison:** duplicate_detector, contradiction_detector
- **Specialized:** fact_checker, bias_detector, call_to_action_detector, sarcasm_detector

### Real Sinks

```python
from components.sinks.email_sink import EmailSink
from components.sinks.webhook_sink import WebhookSink
from components.sinks.file_writer import FileWriter
```

## Filtering Pattern

Any transform can filter messages by returning `None`:

```python
def keep_only_positive(article):
    if article["sentiment"] == "NEGATIVE":
        return None    # Dropped — never reaches downstream nodes
    return article     # Passed through
```

This is the primary way to filter, route, and control data flow in DisSysLab.

## Writing Transform Functions

Transforms are ordinary Python functions. The function receives whatever the upstream node sent (string, dict, any Python object) and returns whatever the downstream node should receive.

```python
# Simple: receives string, returns string
def to_uppercase(text):
    return text.upper()

# Analysis: receives string, returns dict
def analyze(text):
    result = sentiment_analyzer.run(text)
    return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

# Filter: receives anything, returns it or None
def filter_spam(text):
    result = spam_detector.run(text)
    if result["is_spam"]:
        return None
    return text

# Enrichment: receives dict, adds fields, returns dict
def add_urgency(article):
    result = urgency_detector.run(article["text"])
    article["urgency"] = result["urgency"]
    return article
```

If a function needs extra parameters beyond the input message, use `params`:
```python
def scale(value, factor):
    return value * factor

transform = Transform(fn=scale, params={"factor": 2.5}, name="scaler")
```

## Code Generation Rules

When generating DisSysLab applications:

1. **Always include all imports at the top of the file.**
2. **Always include `if __name__ == "__main__":` guard around run_network().**
3. **Use mock components by default** unless the user asks for real APIs.
4. **Name every node** with a descriptive `name=` parameter.
5. **Add a header comment** explaining what the network does.
6. **Print the network topology** in ASCII before running, so the user can see the structure.
7. **Use mock components for any AI analysis** (MockClaudeAgent) unless the user specifically requests real AI. Comment where to swap to real.
8. **Keep transform functions simple and focused** — one function per concern.
9. **Test functions in isolation where possible** by showing example input/output in comments.

## Example: Complete Generated App

```python
# Social Media Monitor
# Topology: hacker_news → spam_filter → sentiment → display
#           tech_news  →↗

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.mock_rss_source import MockRSSSource
from components.transformers.mock_claude_agent import MockClaudeAgent

# Sources
hn = MockRSSSource(feed_name="hacker_news")
tech = MockRSSSource(feed_name="tech_news")

# AI components (mock — swap to ClaudeAgent for real AI)
spam_detector = MockClaudeAgent(task="spam_detection")
sentiment_analyzer = MockClaudeAgent(task="sentiment_analysis")

def filter_spam(text):
    """Drop spam articles. Return None = message dropped."""
    result = spam_detector.run(text)
    if result["is_spam"]:
        return None
    return text

def analyze_sentiment(text):
    """Add sentiment analysis to each article."""
    result = sentiment_analyzer.run(text)
    return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

def display(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    print(f"  {icon.get(article['sentiment'], '❓')} [{article['sentiment']}] {article['text']}")

# Build network
hn_source   = Source(fn=hn.run, name="hacker_news")
tech_source = Source(fn=tech.run, name="tech_news")
spam_gate   = Transform(fn=filter_spam, name="spam_filter")
sentiment   = Transform(fn=analyze_sentiment, name="sentiment")
output      = Sink(fn=display, name="display")

g = network([
    (hn_source, spam_gate),      # Fanin: two sources
    (tech_source, spam_gate),    #   merge into one filter
    (spam_gate, sentiment),      # Pipeline: filter then analyze
    (sentiment, output)          # Output results
])

if __name__ == "__main__":
    print("\n📰 Social Media Monitor\n")
    print("  hacker_news ─┐")
    print("               ├→ spam_filter → sentiment → display")
    print("  tech_news   ─┘\n")
    g.run_network()
    print("\n✅ Done!")
```
