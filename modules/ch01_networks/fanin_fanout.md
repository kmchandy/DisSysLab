# 🧩 1.2 Fanout and Fanin

## 🎯 Goal

- Understand behavior of **fanout** (multiple output edges from a node) and **fanin** (multiple input edges to a node)
- See how decorators enable clean parallel processing patterns

---

## 💻 Example 1: Parallel Analysis Pipeline (Fanout)

Process social media posts through multiple independent analyzers in parallel.

```python
# modules/ch02_networks/parallel_analysis.py

from dsl import network
from dsl.decorators import msg_map

def from_posts():
    """Source: Social media posts"""
    posts = [
        "Just got promoted at work! Best day ever!",
        "Traffic is terrible today, stuck for 2 hours",
        "Had an amazing coffee this morning"
    ]
    for post in posts:
        yield {"text": post}

@msg_map(input_keys=["text"], output_keys=["sentiment"])
def sentiment_analyzer(text):
    """Analyzes sentiment"""
    positive = ['amazing', 'best', 'promoted', 'great']
    negative = ['terrible', 'stuck', 'worst', 'bad']
    
    text_lower = text.lower()
    if any(word in text_lower for word in positive):
        return "POSITIVE"
    elif any(word in text_lower for word in negative):
        return "NEGATIVE"
    return "NEUTRAL"

@msg_map(input_keys=["text"], output_keys=["word_count"])
def word_counter(text):
    """Counts words in text"""
    return len(text.split())

@msg_map(input_keys=["text"], output_keys=["has_exclamation"])
def excitement_detector(text):
    """Detects exclamation marks"""
    return "!" in text

# Sinks to collect results
sentiment_results = []
word_count_results = []
excitement_results = []

@msg_map(input_keys=["text", "sentiment"])
def collect_sentiment(text, sentiment):
    sentiment_results.append({"text": text[:30], "sentiment": sentiment})
    print(f"Sentiment: [{sentiment}] {text[:40]}...")

@msg_map(input_keys=["text", "word_count"])
def collect_word_count(text, word_count):
    word_count_results.append({"text": text[:30], "count": word_count})
    print(f"Word Count: {word_count} words in '{text[:40]}...'")

@msg_map(input_keys=["text", "has_exclamation"])
def collect_excitement(text, has_exclamation):
    excitement_results.append({"text": text[:30], "excited": has_exclamation})
    print(f"Excitement: {'YES' if has_exclamation else 'NO'} in '{text[:40]}...'")

"""
Network Structure (Fanout):

                    +-------------+
                    |  from_posts |
                    +-------------+
                    /      |      \
                   /       |       \
                  v        v        v
        +-----------+ +-----------+ +------------------+
        | sentiment | |   word    | |    excitement    |
        | analyzer  | |  counter  | |     detector     |
        +-----------+ +-----------+ +------------------+
              |             |                |
              v             v                v
        +-----------+ +-----------+ +------------------+
        |  collect  | |  collect  | |     collect      |
        | sentiment | |word_count | |   excitement     |
        +-----------+ +-----------+ +------------------+
"""

g = network([
    (from_posts, sentiment_analyzer),
    (from_posts, word_counter),
    (from_posts, excitement_detector),
    (sentiment_analyzer, collect_sentiment),
    (word_counter, collect_word_count),
    (excitement_detector, collect_excitement)
])

g.run_network()

print("\n=== Fanout Summary ===")
print(f"Processed {len(sentiment_results)} posts through 3 parallel analyzers")
```

**📍 Fanout:** Each post is broadcast to all three analyzers (sentiment, word count, excitement). They process independently in parallel.

---

## 💻 Example 2: Multi-Source Aggregation (Fanin)

Merge posts from multiple social media platforms into a unified processing pipeline.

```python
# modules/ch02_networks/multi_source_merge.py

from dsl import network
from dsl.decorators import msg_map
import time

def from_twitter():
    """Source: Twitter posts"""
    posts = [
        {"text": "Breaking: New tech announced!", "platform": "Twitter"},
        {"text": "Just had the best lunch ever", "platform": "Twitter"}
    ]
    for post in posts:
        yield post
        time.sleep(0.05)

def from_reddit():
    """Source: Reddit posts"""
    posts = [
        {"text": "This traffic is unbearable", "platform": "Reddit"},
        {"text": "Amazing discovery in science", "platform": "Reddit"},
        {"text": "Looking forward to the weekend", "platform": "Reddit"}
    ]
    for post in posts:
        yield post
        time.sleep(0.03)

def from_facebook():
    """Source: Facebook posts"""
    posts = [
        {"text": "Family vacation was incredible", "platform": "Facebook"},
        {"text": "Terrible customer service today", "platform": "Facebook"}
    ]
    for post in posts:
        yield post
        time.sleep(0.04)

@msg_map(input_keys=["text"], output_keys=["clean_text"])
def clean_text(text):
    """Cleans and normalizes text"""
    import re
    cleaned = re.sub(r'[^\w\s.,!?-]', '', text)
    return ' '.join(cleaned.split())

@msg_map(input_keys=["clean_text"], output_keys=["sentiment"])
def analyze_sentiment(clean_text):
    """Analyzes sentiment"""
    positive = ['amazing', 'best', 'incredible', 'forward']
    negative = ['terrible', 'unbearable', 'worst']
    
    text_lower = clean_text.lower()
    if any(word in text_lower for word in positive):
        return "POSITIVE"
    elif any(word in text_lower for word in negative):
        return "NEGATIVE"
    return "NEUTRAL"

results = []

@msg_map(input_keys=["platform", "text", "sentiment"])
def collect_results(platform, text, sentiment):
    """Collects and displays results from all platforms"""
    results.append({
        "platform": platform,
        "text": text,
        "sentiment": sentiment
    })
    print(f"[{platform:8}] [{sentiment:8}] {text[:45]}...")

"""
Network Structure (Fanin):

    +-------------+   +-------------+   +-------------+
    |from_twitter |   | from_reddit |   |from_facebook|
    +-------------+   +-------------+   +-------------+
            \                |                /
             \               |               /
              v              v              v
                    +----------------+
                    |  clean_text    |
                    +----------------+
                            |
                            v
                    +----------------+
                    |analyze_sentiment|
                    +----------------+
                            |
                            v
                    +----------------+
                    |collect_results |
                    +----------------+
"""

g = network([
    (from_twitter, clean_text),
    (from_reddit, clean_text),
    (from_facebook, clean_text),
    (clean_text, analyze_sentiment),
    (analyze_sentiment, collect_results)
])

g.run_network()

print("\n=== Fanin Summary ===")
platform_counts = {}
for result in results:
    platform = result['platform']
    platform_counts[platform] = platform_counts.get(platform, 0) + 1

for platform, count in platform_counts.items():
    print(f"{platform}: {count} posts")
print(f"Total: {len(results)} posts merged from {len(platform_counts)} platforms")
```

**📍 Fanin:** Posts from Twitter, Reddit, and Facebook are merged fairly into a single processing stream. The order is nondeterministic based on timing.

---

## 💻 Example 3: Dual Output Streams (Fanout to Different Destinations)

Process posts through two analyzers and send results to different outputs: real-time display and archival storage.

```python
# modules/ch02_networks/dual_output.py

from dsl import network
from dsl.decorators import msg_map
from dsl.connectors.sink_jsonl_recorder import JSONLRecorder

def from_posts():
    """Source: Social media posts"""
    posts = [
        "Just got promoted at work! Best day ever!",
        "Traffic is terrible today, stuck for 2 hours",
        "Had an amazing coffee this morning",
        "My package got lost in delivery again",
        "Excited to start my new project tomorrow"
    ]
    for post in posts:
        yield {"text": post, "id": hash(post) % 1000}

@msg_map(input_keys=["text"], output_keys=["sentiment", "keywords"])
def sentiment_with_keywords(text):
    """Extracts sentiment and key emotional words"""
    positive = ['amazing', 'best', 'promoted', 'great', 'excited']
    negative = ['terrible', 'stuck', 'worst', 'lost', 'bad']
    
    text_lower = text.lower()
    found_keywords = []
    
    for word in positive:
        if word in text_lower:
            found_keywords.append(f"+{word}")
    for word in negative:
        if word in text_lower:
            found_keywords.append(f"-{word}")
    
    pos_count = sum(1 for kw in found_keywords if kw.startswith('+'))
    neg_count = sum(1 for kw in found_keywords if kw.startswith('-'))
    
    if pos_count > neg_count:
        sentiment = "POSITIVE"
    elif neg_count > pos_count:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"
    
    return sentiment, found_keywords

@msg_map(input_keys=["text"], output_keys=["urgency", "metrics"])
def urgency_analyzer(text):
    """Analyzes urgency and calculates text metrics"""
    urgent_indicators = ['!', 'urgent', 'asap', 'immediately', 'critical']
    
    text_lower = text.lower()
    urgency_score = sum(1 for indicator in urgent_indicators if indicator in text_lower)
    
    if urgency_score >= 2:
        urgency = "HIGH"
    elif urgency_score == 1:
        urgency = "MEDIUM"
    else:
        urgency = "LOW"
    
    metrics = {
        "char_count": len(text),
        "word_count": len(text.split()),
        "urgency_score": urgency_score
    }
    
    return urgency, metrics

# Real-time display (prints to console)
@msg_map(input_keys=["id", "text", "sentiment", "keywords"])
def display_realtime(id, text, sentiment, keywords):
    """Displays sentiment analysis in real-time"""
    kw_str = ", ".join(keywords) if keywords else "none"
    print(f"[REALTIME] Post {id}: [{sentiment}] - Keywords: {kw_str}")
    print(f"           Text: {text[:50]}...")

# Archive to JSONL file (for later analysis)
archive_recorder = JSONLRecorder(
    path="urgency_analysis.jsonl",
    mode="w",
    flush_every=1,
    name="urgency_archive"
)

@msg_map(input_keys=["id", "text", "urgency", "metrics"])
def archive_to_file(id, text, urgency, metrics):
    """Archives urgency analysis to JSONL file"""
    record = {
        "id": id,
        "text": text,
        "urgency": urgency,
        "metrics": metrics
    }
    archive_recorder(record)
    print(f"[ARCHIVE]  Post {id}: [{urgency} urgency] - Archived to file")

"""
Network Structure (Fanout to Different Destinations):

                    +-------------+
                    |  from_posts |
                    +-------------+
                       /       \
                      /         \
                     v           v
         +-------------------+  +------------------+
         |   sentiment_with  |  |    urgency       |
         |     keywords      |  |    analyzer      |
         +-------------------+  +------------------+
                  |                      |
                  v                      v
         +-------------------+  +------------------+
         | display_realtime  |  | archive_to_file  |
         |   (console)       |  |    (JSONL)       |
         +-------------------+  +------------------+
"""

g = network([
    (from_posts, sentiment_with_keywords),
    (from_posts, urgency_analyzer),
    (sentiment_with_keywords, display_realtime),
    (urgency_analyzer, archive_to_file)
])

g.run_network()

# Finalize the file recorder
archive_recorder.finalize()

print("\n=== Dual Output Summary ===")
print("Sentiment analysis displayed in real-time")
print("Urgency analysis archived to: urgency_analysis.jsonl")
print("\nTo view archived data:")
print("  cat urgency_analysis.jsonl | jq '.'")
```

**📍 Fanout to Different Destinations:** Posts are analyzed in parallel - sentiment goes to console display, urgency goes to JSONL file for archival.
```

**📍 Diamond Pattern:** Posts fanout to two analyzers, then results fanin to aggregator. Each post generates two analysis results that merge nondeterministically.

---

## 🧠 Key Concepts

- **Fanout** broadcasts messages to multiple downstream processors for parallel analysis
- **Fanin** merges streams from multiple sources fairly and nondeterministically
- **Diamond patterns** combine fanout and fanin for parallel processing with aggregation
- The `msg_map` decorator enables clean, reusable components that compose easily
- Message order at fanin points is nondeterministic - depends on timing and scheduling

## 👉 Next
[Drop messages in streams](./README_3.md) by returning `None`.