# Mock vs Real Components: Module 2 → Module 9

## Overview

This guide shows the **exact differences** between Module 2 (basic/mock) and Module 9 (real) networks.

**The key insight:** Same network topology, same interface - just swap the imports!

---

## Side-by-Side Comparison

### **Imports**

| Module 2 (Mock) | Module 9 (Real) |
|-----------------|-----------------|
| `from components.sources import MockRSSSource` | `from components.sources import RSSSource` |
| `from components.transforms import MockClaudeAgent` | `from components.transforms import ClaudeAgent` |
| `from components.sinks import MockEmailAlerter` | `from components.sinks import GmailAlerter` |

### **Prerequisites**

| Module 2 (Mock) | Module 9 (Real) |
|-----------------|-----------------|
| ✅ None - works immediately | ⚙️ Anthropic API key |
| ✅ No setup required | ⚙️ Gmail SMTP credentials (optional) |
| ✅ No internet needed | ⚙️ Internet connection |
| ✅ $0 cost | 💰 ~$0.10-0.20 for testing |

### **Sources**

**Module 2:**
```python
# Mock RSS - uses predefined test data
hn_data = MockRSSSource(feed_name="hacker_news", max_articles=5)
tech_data = MockRSSSource(feed_name="tech_news", max_articles=3)
```

**Module 9:**
```python
# Real RSS - fetches live feeds
hn_data = RSSSource(urls=["https://hnrss.org/newest"], max_articles=5)
tech_data = RSSSource(
    urls=["https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml"],
    max_articles=3
)
```

**Key Differences:**
- Mock: Returns hardcoded test articles (includes spam examples)
- Real: Fetches actual RSS feeds from the internet
- Interface: **Identical** - both have `.run()` method that yields text

---

### **Transforms (AI Agents)**

**Module 2:**
```python
# Mock AI - keyword matching
spam_detector = MockClaudeAgent(task="spam_detection")
sentiment_analyzer = MockClaudeAgent(task="sentiment_analysis")
urgency_detector = MockClaudeAgent(task="urgency_detection")
```

**Module 9:**
```python
# Real AI - Claude API
spam_detector = ClaudeAgent(
    prompt="Analyze if this is spam. Return JSON: {is_spam: bool, confidence: float}"
)
sentiment_analyzer = ClaudeAgent(
    prompt="Analyze sentiment. Return JSON: {sentiment: str, score: float}"
)
urgency_detector = ClaudeAgent(
    prompt="Detect urgency. Return JSON: {urgency: str, metrics: dict}"
)
```

**Key Differences:**
- Mock: Simple keyword matching (e.g., "free money" → spam)
- Real: Claude AI with sophisticated natural language understanding
- Interface: **Identical** - both have `.run(text)` method returning dict

---

### **Sinks (Email Alerts)**

**Module 2:**
```python
# Mock email - prints to console
spam_alerter = MockEmailAlerter(
    to_address="security@example.com",
    subject_prefix="[SPAM DETECTED]"
)
```

**Module 9:**
```python
# Real email - sends via Gmail SMTP
spam_alerter = GmailAlerter(
    to_address="security@example.com",
    subject_prefix="[SPAM DETECTED]"
)
```

**Key Differences:**
- Mock: Prints formatted email to console
- Real: Sends actual email via Gmail SMTP
- Interface: **Identical** - both have `.run(msg)` method

---

## Network Topology: 100% Identical

Both Module 2 and Module 9 use **exactly the same network structure:**

```python
g = network([
    # Fanin: Multiple sources merge into spam detector
    (hn_source, spam_detector),
    (tech_source, spam_detector),
    
    # Fanout: Spam detector broadcasts to two routers
    (spam_detector, to_spam_sink),
    (spam_detector, to_clean_pipeline),
    
    # Spam messages go to email alerter
    (to_spam_sink, spam_alerter),
    
    # Clean messages continue to main pipeline
    (to_clean_pipeline, sentiment_analyzer),
    
    # Fanout: Sentiment results go to archive and urgency analyzer
    (sentiment_analyzer, archive_recorder),
    (sentiment_analyzer, urgency_analyzer),
    
    # Urgency results go to console display
    (urgency_analyzer, display)
])
```

**This is the power of the component library pattern!**

---

## Upgrade Checklist: Module 2 → Module 9

### **Step 1: Change Imports**
```python
# OLD (Module 2):
from components.sources import MockRSSSource
from components.transforms import MockClaudeAgent
from components.sinks import MockEmailAlerter

# NEW (Module 9):
from components.sources import RSSSource
from components.transforms import ClaudeAgent
from components.sinks import GmailAlerter
```

### **Step 2: Setup API Keys**
```bash
# Anthropic API (required)
export ANTHROPIC_API_KEY='your-key-here'

# Gmail SMTP (optional - will fallback to console)
export GMAIL_ADDRESS='your-email@gmail.com'
export GMAIL_APP_PASSWORD='your-app-password'
```

### **Step 3: Update Component Creation**

**Sources:**
```python
# OLD:
hn_data = MockRSSSource(feed_name="hacker_news", max_articles=5)

# NEW:
hn_data = RSSSource(urls=["https://hnrss.org/newest"], max_articles=5)
```

**Transforms:**
```python
# OLD:
spam_detector = MockClaudeAgent(task="spam_detection")

# NEW:
spam_detector = ClaudeAgent(
    prompt="Analyze if this is spam. Return JSON: {is_spam: bool, confidence: float}",
    output_format="json"
)
```

**Sinks:**
```python
# OLD:
alerter = MockEmailAlerter(to_address="admin@example.com")

# NEW:
alerter = GmailAlerter(to_address="admin@example.com")
```

### **Step 4: Keep Everything Else the Same!**
- Network topology: **No changes**
- Routing functions: **No changes**
- Message format: **No changes**
- Decorator usage: **No changes**

---

## What Changes in Behavior?

| Aspect | Module 2 (Mock) | Module 9 (Real) |
|--------|-----------------|-----------------|
| **Data Source** | Hardcoded test articles | Live RSS feeds from internet |
| **Spam Detection** | Keyword: "free money" → spam | AI understands context and patterns |
| **Sentiment Analysis** | Counts positive/negative words | AI understands nuance and sarcasm |
| **Urgency Detection** | Counts "!" and "urgent" | AI understands implied urgency |
| **Email Alerts** | Printed to console | Sent to actual inbox |
| **Cost** | Free | ~$0.10-0.20 for testing |
| **Setup Time** | 0 minutes | ~15 minutes (API keys) |
| **Quality** | Good for learning | Production-ready |

---

## Teaching Progression

### **Module 2: Learn the Concepts**
Students focus on:
- Network topology
- Message passing
- Fanin/fanout patterns
- Content routing
- Component composition

**No distractions from:**
- API setup
- Authentication
- Rate limits
- Error handling for external services

### **Module 9: Production Reality**
Students learn:
- API integration
- Credential management
- Real-world data variability
- Error handling
- Cost monitoring

**Building on:**
- Same network concepts
- Same component interfaces
- Same message patterns

---

## Component Interface Contract

All mock/real pairs follow this contract:

### **Sources**
```python
class Source:
    def __init__(self, ...):
        # Component-specific initialization
        pass
    
    def run(self):
        # Generator that yields items
        for item in items:
            yield item
    
    def get_stats(self) -> dict:
        # Return statistics
        return {"count": ...}
```

### **Transforms**
```python
class Transform:
    def __init__(self, ...):
        # Component-specific initialization
        pass
    
    def run(self, text: str) -> dict:
        # Process text, return dict
        return {"result": ...}
    
    def get_usage_stats(self) -> dict:
        # Return usage statistics
        return {"calls": ...}
```

### **Sinks**
```python
class Sink:
    def __init__(self, ...):
        # Component-specific initialization
        pass
    
    def run(self, msg: dict):
        # Process message (no return)
        pass
    
    def finalize(self):
        # Cleanup
        pass
```

---

## Factory Functions: Same in Mock and Real

Both versions provide convenience factories:

```python
# Module 2 (Mock)
from components.sources.mock_rss_source import create_hacker_news_source
from components.transforms.mock_claude_agent import create_spam_detector
from components.sinks.mock_email_alerter import create_spam_alerter

# Module 9 (Real)
from components.sources.rss_source import create_hacker_news_source
from components.transforms.claude_agent import create_spam_detector
from components.sinks.gmail_alerter import create_spam_alerter

# Usage is identical!
hn_source = create_hacker_news_source(max_articles=5)
spam_detector = create_spam_detector()
alerter = create_spam_alerter()
```

---

## File Locations

### **Module 2 (Mock Network)**
```
modules/basic/network_example.py
```

### **Module 9 (Real Network)**
```
modules/real/real_network.py
```

### **Component Library (Used by Both)**
```
components/
├── sources/
│   ├── mock_rss_source.py      # Module 2
│   └── rss_source.py           # Module 9
├── transforms/
│   ├── mock_claude_agent.py    # Module 2
│   └── claude_agent.py         # Module 9
└── sinks/
    ├── mock_email_alerter.py   # Module 2
    └── gmail_alerter.py        # Module 9
```

---

## Testing Strategy

Both modules can be tested the same way:

```bash
# Test Module 2 (Mock) - No setup needed
cd modules/basic
python network_example.py

# Test Module 9 (Real) - Requires API keys
export ANTHROPIC_API_KEY='your-key'
cd modules/real
python real_network.py
```

---

## Summary: The Power of Consistent Interfaces

**What Makes This Work:**

1. ✅ **Same interface** across mock/real pairs
2. ✅ **Same network topology** in both modules
3. ✅ **Same message format** (dicts) throughout
4. ✅ **Same decorator usage** (source_map, transform_map, sink_map)
5. ✅ **Incremental learning** - concepts first, reality later

**What Students Learn:**

- **Module 2:** Distributed systems concepts without complexity
- **Module 9:** Production integration without re-learning concepts
- **Key Insight:** The network structure IS the knowledge - components are just implementations

---

## Next Steps

After completing both modules, students can:

1. **Mix and match** - Use real RSS with mock AI, or vice versa
2. **Build custom components** - Following the same interface patterns
3. **Extend the network** - Add new sources, transforms, or sinks
4. **Go to production** - Their Module 9 network is already production-ready!

---

*This component library pattern is the key to effective teaching: same concepts, different implementations.*