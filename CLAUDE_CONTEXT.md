# DisSysLab — Context for Claude

You are helping a user build distributed systems using the DisSysLab framework. DisSysLab lets users build persistent, concurrent data processing applications using ordinary Python functions. The user describes what they want in natural language. You generate complete, runnable DisSysLab applications.

## How DisSysLab Works

Every DisSysLab app follows this pattern:

1. **Create component instances** (data sources, AI analyzers, output handlers)
2. **Write transform functions** (ordinary Python functions that process data)
3. **Wrap components into nodes** using `Source`, `Transform`, `Sink`, or `Split`
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
```
The function receives whatever the upstream node sent. Return a value to pass it downstream. **Return `None` to drop the message** (this is how filtering works).

**Sink** — consumes data, receives input, produces no output to other nodes.
```python
sink = Sink(fn=my_output.run, name="sink_name")
```

**Split** — routes each message to specific output ports based on your logic.
```python
splitter = Split(fn=my_routing_function, num_outputs=3, name="router")
```
The routing function returns a list of length `num_outputs`. Non-None elements are sent to the corresponding output port. None elements mean "skip this port."

```python
def route_by_sentiment(article):
    score = article["score"]
    if score > 0.2:
        return [article, article, None]    # positive → out_0 AND out_1
    elif score < -0.2:
        return [None, article, article]    # negative → out_1 AND out_2
    else:
        return [None, article, None]       # neutral → out_1 only

splitter = Split(fn=route_by_sentiment, num_outputs=3, name="sentiment_router")
```

Port references connect split outputs to downstream nodes:
```python
g = network([
    (source, sentiment),
    (sentiment, splitter),
    (splitter.out_0, archive_sink),
    (splitter.out_1, console_sink),
    (splitter.out_2, alert_sink)
])
```

## Network Topology

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
    (source1, processor), (source2, processor), (processor, sink)
])
```

**Fanout** — one node to multiple destinations (messages are copied automatically):
```python
g = network([
    (source, processor), (processor, sink1), (processor, sink2)
])
```

## Available Demo Components (no API keys needed)

### Demo Sources

```python
from components.sources.demo_rss_source import DemoRSSSource

# Available feeds: "hacker_news", "tech_news", "reddit_python"
rss = DemoRSSSource(feed_name="hacker_news")
source = Source(fn=rss.run, name="news")
```

```python
from components.sources.list_source import ListSource

data = ListSource(items=["item1", "item2", "item3"])
source = Source(fn=data.run, name="data")
```

### Demo AI Agents

```python
from components.transformers.prompts import SENTIMENT_ANALYZER, SPAM_DETECTOR, URGENCY_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_agent

# Sentiment — returns {"sentiment": "POSITIVE"|"NEGATIVE"|"NEUTRAL", "score": float, "reasoning": str}
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

# Spam — returns {"is_spam": bool, "confidence": float, "reason": str}
spam_detector = demo_ai_agent(SPAM_DETECTOR)

# Urgency — returns {"urgency": "HIGH"|"MEDIUM"|"LOW", "metrics": dict, "reasoning": str}
urgency_detector = demo_ai_agent(URGENCY_DETECTOR)
```

These use keyword matching to simulate AI. They return callables with the same interface as the real ai_agent.

### Sinks

```python
from components.sinks import MockEmailAlerter, JSONLRecorder

alerter = MockEmailAlerter(to_address="user@example.com", subject_prefix="[ALERT]")
sink = Sink(fn=alerter.run, name="email")

recorder = JSONLRecorder(path="output.jsonl", mode="w", flush_every=1, name="archive")
sink = Sink(fn=recorder.run, name="archive")

results = []
sink = Sink(fn=results.append, name="collector")

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
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.ai_agent import ai_agent

# Requires: export ANTHROPIC_API_KEY='your-key'
sentiment_analyzer = ai_agent(SENTIMENT_ANALYZER)
transform = Transform(fn=sentiment_analyzer, name="sentiment")
```

Available prompt constants (import from components.transformers.prompts):
- **Text analysis:** SENTIMENT_ANALYZER, EMOTION_DETECTOR, TONE_ANALYZER, READABILITY_ANALYZER
- **Content filtering:** SPAM_DETECTOR, URGENCY_DETECTOR, TOXICITY_DETECTOR, PROFANITY_FILTER
- **Classification:** TOPIC_CLASSIFIER, LANGUAGE_DETECTOR, INTENT_CLASSIFIER, PRIORITY_CLASSIFIER
- **Extraction:** ENTITY_EXTRACTOR, KEY_PHRASE_EXTRACTOR, CONTACT_EXTRACTOR, DATE_TIME_EXTRACTOR
- **Summarization:** TEXT_SUMMARIZER, BULLET_POINT_CREATOR, TITLE_GENERATOR, QUESTION_GENERATOR
- **Quality:** GRAMMAR_CHECKER, STYLE_CHECKER, PLAGIARISM_INDICATOR
- **Comparison:** DUPLICATE_DETECTOR, CONTRADICTION_DETECTOR
- **Specialized:** FACT_CHECKER, BIAS_DETECTOR, CALL_TO_ACTION_DETECTOR, SARCASM_DETECTOR

## Filtering Pattern

Any transform can filter messages by returning `None`:

```python
def keep_only_positive(article):
    if article["sentiment"] == "NEGATIVE":
        return None
    return article
```

## Code Generation Rules

When generating DisSysLab applications:

1. **Always include all imports at the top of the file.**
2. **Always include `if __name__ == "__main__":` guard around run_network().**
3. **Use demo components by default** unless the user asks for real APIs.
4. **Name every node** with a descriptive `name=` parameter.
5. **Add a header comment** explaining what the network does.
6. **Print the network topology** in ASCII before running.
7. **Use demo components for any AI analysis** (demo_ai_agent) unless the user specifically requests real AI.
8. **Keep transform functions simple and focused** — one function per concern.

## Example: Complete Generated App

```python
# Social Media Monitor
# Topology: hacker_news ─┐
#                         ├→ spam_filter → sentiment → display
#           tech_news   ─┘

from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_rss_source import DemoRSSSource
from components.transformers.prompts import SPAM_DETECTOR, SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_agent

hn = DemoRSSSource(feed_name="hacker_news")
tech = DemoRSSSource(feed_name="tech_news")

# AI components (demo — swap demo_ai_agent to ai_agent for real AI)
spam_detector = demo_ai_agent(SPAM_DETECTOR)
sentiment_analyzer = demo_ai_agent(SENTIMENT_ANALYZER)

def filter_spam(text):
    result = spam_detector(text)
    if result["is_spam"]:
        return None
    return text

def analyze_sentiment(text):
    result = sentiment_analyzer(text)
    return {"text": text, "sentiment": result["sentiment"], "score": result["score"]}

def display(article):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}
    print(f"  {icon.get(article['sentiment'], '❓')} [{article['sentiment']}] {article['text']}")

hn_source   = Source(fn=hn.run, name="hacker_news")
tech_source = Source(fn=tech.run, name="tech_news")
spam_gate   = Transform(fn=filter_spam, name="spam_filter")
sentiment   = Transform(fn=analyze_sentiment, name="sentiment")
output      = Sink(fn=display, name="display")

g = network([
    (hn_source, spam_gate),
    (tech_source, spam_gate),
    (spam_gate, sentiment),
    (sentiment, output)
])

if __name__ == "__main__":
    print("\n📰 Social Media Monitor\n")
    print("  hacker_news ─┐")
    print("               ├→ spam_filter → sentiment → display")
    print("  tech_news   ─┘\n")
    g.run_network()
    print("\n✅ Done!")
```