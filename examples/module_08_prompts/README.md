# Module 08: AI-Powered Distributed Systems

**Master one pattern. Build intelligent systems.**

## What You'll Learn

Every AI-powered agent in your network follows the same pattern:

```
Text Input → AI Analysis (via Prompt) → JSON Output → Python Logic → Action
```

By the end of this module, you'll:
- ✅ Understand how AI agents fit into distributed systems
- ✅ Use prompts to define AI behavior
- ✅ Process JSON output from AI with Python logic
- ✅ Chain multiple AI agents together
- ✅ Build complete intelligent applications

**Time:** 2-3 hours for examples | 1+ hour for complete applications

## Prerequisites

You should have completed **Modules 1-7**, understanding:
- Source, Transform, Sink nodes
- Building networks with `network([...])`
- Pipeline, fanout, fanin patterns
- Filtering with `return None`

## The Core Pattern (Read This First!)

### Every AI Agent Works Like This

```python
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_transform
from dsl.blocks import Transform

# 1. Pick a prompt from the library
prompt = SENTIMENT_ANALYZER  # Defines what AI does

# 2. Create an AI transform
ai_sentiment = demo_ai_transform(prompt)

# 3. Use it like any transform
sentiment_node = Transform(fn=ai_sentiment, name="sentiment")

# 4. AI processes text and returns JSON
text = "I love this framework!"
result = ai_sentiment(text)
# Returns: {"sentiment": "POSITIVE", "score": 0.9, "reasoning": "..."}

# 5. Python uses JSON to make decisions
if result["sentiment"] == "POSITIVE":
    celebrate()
```

### Why This Pattern Is Powerful

**Traditional programming:**
```python
def is_spam(text):
    # You write 100+ lines of rules
    if "FREE" in text and "CLICK" in text:
        return True
    # ... hundreds more rules ...
```

**AI-powered programming:**
```python
# Prompt defines behavior
SPAM_DETECTOR = """Analyze if text is spam. Return JSON: {is_spam: bool, confidence: 0-1}"""

# AI handles the complexity
result = demo_ai_transform(SPAM_DETECTOR)(text)
# Returns: {"is_spam": true, "confidence": 0.95}

# Python decides what to do
if result["is_spam"] and result["confidence"] > 0.7:
    return None  # Filter it out
```

**One prompt replaces hundreds of rules. AI understands context and nuance.**

### The Three Components

1. **Prompt** - Defines what AI should do (from prompts library)
2. **JSON** - Structured output from AI (predictable format)
3. **Python Logic** - Your code decides what happens with results

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   PROMPT    │  →   │     JSON     │  →   │   PYTHON    │
│             │      │              │      │             │
│ "Analyze    │  AI  │ {"sentiment":│      │ if positive:│
│  sentiment" │      │   "POSITIVE",│      │   route_A() │
│             │      │  "score":0.9}│      │ else:       │
│             │      │              │      │   route_B() │
└─────────────┘      └──────────────┘      └─────────────┘
```

---

## Example 1: Your First AI Agent (15 minutes)

**⭐ START HERE - Run this right now!**

### What You'll Build

A simple network that analyzes sentiment of social media posts:

```
Social Media Posts → [AI Sentiment Analyzer] → Results
       ↓                      ↓                    ↓
  ["I love this!",    Analyzes each post    [{"text": "I love this!",
   "This is bad"]     Returns JSON           "sentiment": "POSITIVE",
                                              "score": 0.9}, ...]
```

### Run the Demo

```bash
cd examples/module_08/
python demo_example_01_sentiment.py
```

**What you'll see:**
```
Processing 6 social media posts...

😊 POSITIVE (0.85): I love this framework!
😞 NEGATIVE (0.70): This is terrible service
😐 NEUTRAL (0.50): The meeting is at 3pm
😊 POSITIVE (0.90): Best day ever!
😞 NEGATIVE (0.65): Very disappointed
😐 NEUTRAL (0.45): Please send the report

Summary:
  POSITIVE: 2 posts (33%)
  NEGATIVE: 2 posts (33%)
  NEUTRAL: 2 posts (33%)
```

**Time to run:** 30 seconds | **No API keys needed** | **Works offline**

### How It Works

Let's walk through the code step by step:

#### Step 1: Import Components

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources import ListSource

# Import AI components
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_transform
```

#### Step 2: Create Source Data

```python
posts = ListSource(items=[
    "I love this framework!",
    "This is terrible service",
    "The meeting is at 3pm",
    "Best day ever!",
    "Very disappointed",
    "Please send the report"
])

source = Source(fn=posts.run, name="social_media")
```

#### Step 3: Create AI Transform

```python
# Use the sentiment analyzer prompt from the library
ai_sentiment = demo_ai_transform(SENTIMENT_ANALYZER)

# Wrap it in a Transform node
sentiment_node = Transform(fn=ai_sentiment, name="sentiment")
```

**What happens here:**
- `SENTIMENT_ANALYZER` is a prompt that tells AI: "Analyze sentiment, return JSON"
- `demo_ai_transform()` creates a function that processes text
- The function returns: `{"sentiment": "POSITIVE/NEGATIVE/NEUTRAL", "score": 0.0-1.0, "reasoning": "..."}`

#### Step 4: Create Sink to Collect Results

```python
results = []
collector = Sink(fn=results.append, name="collector")
```

#### Step 5: Build and Run Network

```python
g = network([
    (source, sentiment_node),
    (sentiment_node, collector)
])

g.run_network()

# Display results
for result in results:
    print(f"{result['sentiment']}: {result['text']}")
```

### The Pattern in Action

**Input (text string):**
```python
"I love this framework!"
```

**AI Processing (via prompt):**
```
SENTIMENT_ANALYZER prompt tells AI:
"Analyze sentiment. Return JSON: {sentiment: ..., score: ..., reasoning: ...}"
```

**Output (JSON dict):**
```python
{
    "sentiment": "POSITIVE",
    "score": 0.85,
    "reasoning": "Enthusiastic language with strong positive emotion"
}
```

**Python Usage:**
```python
# Access JSON fields
if result["sentiment"] == "POSITIVE":
    print("😊", result["text"])
```

### Key Insights

1. **AI does the analysis** - You don't write sentiment rules
2. **JSON is predictable** - Always same structure
3. **Python makes decisions** - You control what happens with results
4. **Pattern is reusable** - Same approach for any AI task

### Real-World Version

Want to use actual Claude AI instead of the demo?

**Change one line:**
```python
# Demo version
from components.transformers.demo_ai_agent import demo_ai_transform

# Real version (requires API key)
from components.transformers.claude_agent import ai_transform
```

**Everything else stays identical.** Same prompt, same network, same code.

**To run real version:**
1. Get API key from https://console.anthropic.com
2. Set environment: `export ANTHROPIC_API_KEY=your_key`
3. Run: `python example_01_sentiment.py`
4. Costs ~$0.01 for this example

**Most students:** Stick with demo for learning. Real AI is optional.

---

## Example 2: AI Pipeline - Chaining Agents (20 minutes)

### What You'll Build

A content moderation pipeline with two AI agents:

```
User Posts → [AI Spam Filter] → [AI Sentiment Analyzer] → Clean, Analyzed Posts
     ↓              ↓                      ↓                        ↓
 ["Great post!",  Filters spam      Analyzes sentiment    [{"text": "Great post!",
  "BUY NOW!!!"]   (returns None)    of remaining posts      "sentiment": "POSITIVE",
                                                             "score": 0.8}, ...]
```

**Key concept:** AI agents compose naturally. Output of one feeds into the next.

### Run the Demo

```bash
python demo_example_02_pipeline.py
```

**What you'll see:**
```
Processing 8 messages...

[SPAM FILTERED] BUY NOW! Limited time offer!
[SPAM FILTERED] Click here for FREE MONEY!
[PASSED] Great post! Thanks for sharing.
[PASSED] This is helpful information.
[SPAM FILTERED] Act now or miss out forever!
[PASSED] Looking forward to the weekend.
[PASSED] I'm frustrated with this situation.
[PASSED] The meeting is scheduled for tomorrow.

--- Results After Sentiment Analysis ---
😊 POSITIVE (0.88): Great post! Thanks for sharing.
😐 NEUTRAL (0.52): This is helpful information.
😊 POSITIVE (0.75): Looking forward to the weekend.
😞 NEGATIVE (0.70): I'm frustrated with this situation.
😐 NEUTRAL (0.48): The meeting is scheduled for tomorrow.

Summary:
  Input: 8 messages
  Spam filtered: 3 messages
  Analyzed: 5 messages
  - Positive: 2
  - Negative: 1
  - Neutral: 2
```

### How It Works

#### The Two AI Agents

**Agent 1: Spam Filter**
```python
from components.transformers.prompts import SPAM_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_transform

# Create spam filter that returns None for spam
def filter_spam(text: str):
    """AI analyzes → Python decides → Filter or pass"""
    result = demo_ai_transform(SPAM_DETECTOR)(text)
    
    # AI returns: {"is_spam": bool, "confidence": 0-1, "reason": "..."}
    if result["is_spam"] and result["confidence"] > 0.7:
        return None  # Filter out spam
    else:
        return text  # Pass through
```

**Agent 2: Sentiment Analyzer**
```python
from components.transformers.prompts import SENTIMENT_ANALYZER

# Create sentiment analyzer
ai_sentiment = demo_ai_transform(SENTIMENT_ANALYZER)
# Returns: {"sentiment": "...", "score": 0-1, "reasoning": "..."}
```

#### The Network

```python
spam_filter = Transform(fn=filter_spam, name="spam_filter")
sentiment = Transform(fn=ai_sentiment, name="sentiment")

g = network([
    (source, spam_filter),      # All posts go through spam filter
    (spam_filter, sentiment),   # Only non-spam posts get analyzed
    (sentiment, collector)       # Store analyzed results
])
```

### The Pattern: AI Analysis → Python Decision

```python
def filter_spam(text: str):
    # STEP 1: AI analyzes the text
    result = demo_ai_transform(SPAM_DETECTOR)(text)
    
    # STEP 2: Examine JSON output
    is_spam = result["is_spam"]
    confidence = result["confidence"]
    
    # STEP 3: Python makes the decision
    if is_spam and confidence > 0.7:
        return None  # Filter it
    else:
        return text  # Keep it
```

**Key insight:** AI tells you WHAT it found. Python decides WHAT TO DO about it.

### Data Flow Through Pipeline

```
Input: "BUY NOW! Limited offer!"

↓ spam_filter node
  - Calls AI spam detector
  - AI returns: {"is_spam": true, "confidence": 0.95}
  - Python checks: is_spam AND confidence > 0.7 → True
  - Returns: None (filtered out)

→ Message disappears (doesn't reach sentiment analyzer)

---

Input: "Great post! Thanks for sharing."

↓ spam_filter node
  - Calls AI spam detector
  - AI returns: {"is_spam": false, "confidence": 0.1}
  - Python checks: is_spam AND confidence > 0.7 → False
  - Returns: "Great post! Thanks for sharing."

↓ sentiment node
  - Calls AI sentiment analyzer
  - AI returns: {"sentiment": "POSITIVE", "score": 0.88, "reasoning": "..."}
  - Returns: {"text": "...", "sentiment": "POSITIVE", "score": 0.88}

↓ collector
  - Stores result
```

### Why Chaining Works

Each AI agent:
1. Takes text input (or dict with text)
2. Returns structured JSON
3. Next agent can use that JSON
4. Python orchestrates the flow

**No special plumbing needed.** Just connect nodes.

### Experiments to Try

1. **Change confidence threshold:**
   ```python
   if result["is_spam"] and result["confidence"] > 0.5:  # More aggressive
   ```

2. **Add a third agent:**
   ```python
   (sentiment, urgency_detector),  # Detect urgent messages
   ```

3. **Route based on sentiment:**
   ```python
   def route_by_sentiment(msg):
       if msg["sentiment"] == "NEGATIVE":
           return ("urgent_queue", msg)
       else:
           return ("normal_queue", msg)
   ```

---

## Example 3: Multi-Agent Intelligence (30 minutes)

### What You'll Build

A customer support triage system using **three AI agents** plus Python logic:

```
Support Tickets → [Spam Filter] → [Sentiment] → [Urgency] → [Priority Scorer] → Queues
       ↓               ↓              ↓             ↓              ↓              ↓
   ["Help!",      Filter spam    Analyze tone  Detect urgency  Calculate     URGENT
    "BUY NOW"]                                                  priority      NORMAL
```

**Key concept:** Multiple AI analyses combined with custom business logic.

### Run the Demo

```bash
python demo_example_03_triage.py
```

**What you'll see:**
```
Processing 10 support tickets...

🚨 URGENT QUEUE (Priority 9.5)
   Ticket: URGENT: My account is locked and I can't access anything!
   Sentiment: NEGATIVE (score: -0.8)
   Urgency: HIGH (score: 9/10)
   → Requires immediate attention

🚨 URGENT QUEUE (Priority 8.7)
   Ticket: CRITICAL: Payment failed and subscription canceled!
   Sentiment: NEGATIVE (score: -0.7)
   Urgency: HIGH (score: 8/10)
   → Requires immediate attention

⚠️  PRIORITY QUEUE (Priority 5.2)
   Ticket: I'm frustrated with the slow response time.
   Sentiment: NEGATIVE (score: -0.6)
   Urgency: MEDIUM (score: 4/10)

⚠️  PRIORITY QUEUE (Priority 3.5)
   Ticket: Quick question about billing.
   Sentiment: NEUTRAL (score: 0.0)
   Urgency: MEDIUM (score: 5/10)

✓ NORMAL QUEUE (Priority 1.8)
   Ticket: Great service! Just wanted to say thanks.
   Sentiment: POSITIVE (score: 0.9)
   Urgency: LOW (score: 1/10)

✓ NORMAL QUEUE (Priority 0.5)
   Ticket: How do I change my password?
   Sentiment: NEUTRAL (score: 0.1)
   Urgency: LOW (score: 2/10)

---
Summary:
  Total tickets: 10
  Spam filtered: 2
  Processed: 8
  - Urgent queue: 2 tickets (25%)
  - Priority queue: 3 tickets (38%)
  - Normal queue: 3 tickets (38%)
```

### How It Works

#### Three AI Agents

**1. Spam Detector**
```python
spam_result = demo_ai_transform(SPAM_DETECTOR)(text)
# Returns: {"is_spam": bool, "confidence": 0-1, "reason": "..."}
```

**2. Sentiment Analyzer**
```python
sentiment_result = demo_ai_transform(SENTIMENT_ANALYZER)(text)
# Returns: {"sentiment": "POSITIVE/NEGATIVE/NEUTRAL", "score": -1 to +1, "reasoning": "..."}
```

**3. Urgency Detector**
```python
urgency_result = demo_ai_transform(URGENCY_DETECTOR)(text)
# Returns: {"urgency": "HIGH/MEDIUM/LOW", "metrics": {"urgency_score": 0-10, ...}, "reasoning": "..."}
```

#### Combining AI Analyses with Python Logic

```python
def triage_ticket(text: str):
    """
    Uses three AI agents + custom priority logic.
    
    Pattern: Multiple AI analyses → Python combines → Smart decision
    """
    # AI Analysis 1: Check for spam
    spam_check = demo_ai_transform(SPAM_DETECTOR)(text)
    if spam_check["is_spam"] and spam_check["confidence"] > 0.7:
        return None  # Filter spam immediately
    
    # AI Analysis 2: Sentiment
    sentiment = demo_ai_transform(SENTIMENT_ANALYZER)(text)
    
    # AI Analysis 3: Urgency
    urgency = demo_ai_transform(URGENCY_DETECTOR)(text)
    
    # PYTHON LOGIC: Calculate priority from AI outputs
    priority_score = 0
    
    # Factor 1: Negative sentiment increases priority
    if sentiment["sentiment"] == "NEGATIVE":
        priority_score += abs(sentiment["score"]) * 5
    
    # Factor 2: High urgency increases priority
    if urgency["urgency"] == "HIGH":
        priority_score += 5
    elif urgency["urgency"] == "MEDIUM":
        priority_score += 2
    
    # Determine queue based on priority
    if priority_score >= 7:
        queue = "URGENT"
    elif priority_score >= 3:
        queue = "PRIORITY"
    else:
        queue = "NORMAL"
    
    # Return enriched ticket
    return {
        "text": text,
        "sentiment": sentiment["sentiment"],
        "sentiment_score": sentiment["score"],
        "urgency": urgency["urgency"],
        "urgency_score": urgency["metrics"]["urgency_score"],
        "priority_score": priority_score,
        "queue": queue
    }
```

### The Power of Composition

```
Text → AI 1 (Spam?) → JSON 1
    ↓
Text → AI 2 (Sentiment?) → JSON 2
    ↓
Text → AI 3 (Urgency?) → JSON 3
    ↓
Python combines JSON 1 + JSON 2 + JSON 3 → Smart decision
```

**Each AI specializes. Python orchestrates.**

### Why This Is Better Than One "Do Everything" AI

❌ **Bad approach:**
```python
# One prompt trying to do everything
MEGA_PROMPT = """Analyze spam, sentiment, urgency, and priority all at once..."""
```
**Problems:**
- Prompt becomes complex and fragile
- Hard to tune individual analyses
- Can't reuse components
- Difficult to debug

✅ **Good approach:**
```python
# Specialized AI agents
spam_result = ai_spam(text)
sentiment_result = ai_sentiment(text)
urgency_result = ai_urgency(text)

# Python combines them
priority = calculate_priority(sentiment_result, urgency_result)
```
**Benefits:**
- Each AI does one thing well
- Easy to test and tune
- Reusable components
- Clear debugging
- Flexible composition

### Custom Business Logic

The priority calculation is **your business logic:**

```python
# Your company's rules
if sentiment["sentiment"] == "NEGATIVE":
    priority_score += abs(sentiment["score"]) * 5  # Weight negative feedback heavily

if urgency["urgency"] == "HIGH":
    priority_score += 5  # Urgent gets high priority

# You control the weights, thresholds, and routing
if priority_score >= 7:
    queue = "URGENT"  # Your definition of "urgent"
```

**AI provides intelligence. You provide judgment.**

---

## Complete Application 1: News Intelligence Dashboard

**Study Mode** - Read this to see a complete system

### What It Does

Monitors multiple news sources, analyzes each article with AI, and displays an intelligent dashboard:

```
┌─────────────┐
│ Tech News   │─┐
├─────────────┤ │
│ Hacker News │─┼──→ [Summarizer] → [Sentiment] → [Topic Cluster] → [Dashboard]
├─────────────┤ │         ↓              ↓              ↓                ↓
│ Reddit Tech │─┘    AI extracts    AI analyzes    AI categorizes   Formatted
└─────────────┘      key points     tone           by topic         display
```

### Demo Version

```bash
python demo_news_dashboard.py
```

**Features:**
- Processes 20 diverse news articles
- Three AI agents working in pipeline
- Groups articles by topic (AI/Tech, Business, Science, etc.)
- Shows sentiment breakdown
- Formatted console output

**Sample output:**
```
═══════════════════════════════════════════════════════════
PERSONAL NEWS INTELLIGENCE DASHBOARD
═══════════════════════════════════════════════════════════
Generated: 2025-02-06 14:30:00
Total Articles: 20
═══════════════════════════════════════════════════════════

───────────────────────────────────────────────────────────
📁 AI & TECHNOLOGY (7 articles)
───────────────────────────────────────────────────────────

😊 AI Breakthrough: New Model Achieves Human-Level Reasoning
   Source: TechCrunch
   Sentiment: POSITIVE (0.92)
   Summary: Researchers announced significant breakthrough in AI reasoning
            capabilities matching human performance on complex tasks.
   
😐 Autonomous Vehicles Approved for Public Roads
   Source: The Verge
   Sentiment: NEUTRAL (0.55)
   Summary: Transportation authorities approved first fully autonomous
            vehicles for designated urban areas with remote monitoring.

[... more articles ...]

───────────────────────────────────────────────────────────
📁 BUSINESS & ECONOMY (5 articles)
───────────────────────────────────────────────────────────

😞 Major Company Announces Massive Layoffs
   Source: Wall Street Journal
   Sentiment: NEGATIVE (0.78)
   Summary: Tech giant will lay off 10,000 employees amid economic
            uncertainty and declining revenues.

[... more articles ...]

═══════════════════════════════════════════════════════════
SUMMARY STATISTICS
═══════════════════════════════════════════════════════════

Sentiment Breakdown:
  POSITIVE: 8 articles (40%)
  NEGATIVE: 4 articles (20%)
  NEUTRAL: 8 articles (40%)

Topic Distribution:
  AI & Technology: 7 articles (35%)
  Business & Economy: 5 articles (25%)
  Science & Health: 4 articles (20%)
  Sports: 2 articles (10%)
  Environment: 2 articles (10%)
```

### The Three AI Agents

**1. Summarizer**
```python
ai_summarizer = demo_ai_transform(TEXT_SUMMARIZER)
# Input: Full article text (500+ words)
# Output: {"summary": "2-3 sentence summary", "key_points": [...]}
```

**2. Sentiment Analyzer**
```python
ai_sentiment = demo_ai_transform(SENTIMENT_ANALYZER)
# Input: Article text
# Output: {"sentiment": "POSITIVE/NEGATIVE/NEUTRAL", "score": -1 to +1}
```

**3. Topic Clusterer**
```python
ai_topic = demo_ai_transform(TOPIC_CLASSIFIER)
# Input: Article title + summary
# Output: {"primary_topic": "AI & Technology", "confidence": 0-1}
```

### Network Structure

```python
# Multiple RSS sources (fanin pattern from Module 4)
tech_source = Source(fn=tech_rss.run, name="tech")
hn_source = Source(fn=hn_rss.run, name="hackernews")
reddit_source = Source(fn=reddit_rss.run, name="reddit")

# AI pipeline
summarizer = Transform(fn=ai_summarizer, name="summarizer")
sentiment = Transform(fn=ai_sentiment, name="sentiment")
topic = Transform(fn=ai_topic, name="topic")

# Dashboard sink
dashboard = NewsDashboard()
display = Sink(fn=dashboard.add_article, name="display")

# Build network (fanin + pipeline)
g = network([
    (tech_source, summarizer),
    (hn_source, summarizer),
    (reddit_source, summarizer),
    (summarizer, sentiment),
    (sentiment, topic),
    (topic, display)
])
```

### Real-World Version

The real version (`news_dashboard.py`) connects to:
- Live RSS feeds (fetches actual articles)
- Claude API (real AI analysis)
- File output (saves results)

**To run:**
```bash
export ANTHROPIC_API_KEY=your_key
python news_dashboard.py
```

**Cost:** ~$0.10-0.30 per run (depends on article count and length)

### What Students Learn

1. **Multiple sources (fanin)** - All feeds merge into one pipeline
2. **AI pipeline** - Three specialized agents in sequence
3. **Data enrichment** - Each agent adds information
4. **Real application** - Actually useful output
5. **Pattern reuse** - Same patterns from Examples 1-3

---

## Complete Application 2: Email-to-Calendar Assistant

**Study Mode** - Read this to see another complete system

### What It Does

Monitors email inbox, extracts meeting requests, and creates calendar events automatically:

```
Email Inbox → [Spam Filter] → [Meeting Extractor] → [Time Parser] → [Conflict Check] → [Calendar Event]
     ↓             ↓                  ↓                   ↓                ↓                  ↓
 ["Meeting      Filter junk    Extract meeting      Parse dates      Check for         Create event
  tomorrow?"]                   details              & times          conflicts         + send confirm
```

### Demo Version

```bash
python demo_email_calendar.py
```

**Sample output:**
```
Processing 12 emails...

[SPAM] Ignored: "FREE WEBINAR! Register now!"
[NO MEETING] Skipped: "Please review the attached document"
[MEETING FOUND] "Coffee chat tomorrow at 10am?"
   → Extracted: Coffee chat
   → Time: Tomorrow 10:00 AM
   → Duration: 1 hour (default)
   → Conflict check: None
   → ✓ Calendar event created

[MEETING FOUND] "Team standup - daily at 9am"
   → Extracted: Team standup
   → Time: Daily 9:00 AM (recurring)
   → Duration: 15 minutes
   → Conflict check: None
   → ✓ Calendar event created

[MEETING FOUND] "Project review next Tuesday 2pm"
   → Extracted: Project review
   → Time: Next Tuesday 2:00 PM
   → Duration: 1 hour (default)
   → Conflict check: CONFLICT with "Client call" (2:00-3:00 PM)
   → ⚠️  Flagged for manual resolution

---
Summary:
  Emails processed: 12
  Spam filtered: 3
  No meeting: 5
  Meetings extracted: 4
  Events created: 3
  Conflicts flagged: 1
```

### The Four AI Agents

**1. Spam Filter**
```python
spam_check = demo_ai_transform(SPAM_DETECTOR)(email_text)
# Output: {"is_spam": bool, "confidence": 0-1}
```

**2. Meeting Extractor**
```python
meeting = demo_ai_transform(MEETING_EXTRACTOR)(email_text)
# Output: {"has_meeting": bool, "title": "...", "participants": [...], ...}
```

**3. Time Parser**
```python
time_info = demo_ai_transform(DATE_TIME_EXTRACTOR)(email_text)
# Output: {"dates": [...], "times": [...], "relative_times": ["tomorrow", ...]}
```

**4. Conflict Detector**
```python
conflict = demo_ai_transform(CONFLICT_DETECTOR)(meeting, existing_events)
# Output: {"has_conflict": bool, "conflicts": [...], "suggestions": [...]}
```

### Complex Logic: Combining Multiple AI Analyses

```python
def process_email(email):
    # AI 1: Filter spam
    if is_spam(email):
        return None
    
    # AI 2: Extract meeting details
    meeting = extract_meeting(email)
    if not meeting["has_meeting"]:
        return None
    
    # AI 3: Parse time
    time_info = parse_time(meeting)
    
    # AI 4: Check conflicts
    conflicts = check_conflicts(time_info, calendar)
    
    # Python decides: create event or flag for review
    if conflicts["has_conflict"]:
        return {"status": "flagged", "reason": "conflict", ...}
    else:
        create_calendar_event(meeting, time_info)
        return {"status": "created", ...}
```

### Real-World Version

The real version (`email_calendar.py`) connects to:
- Gmail API (fetches actual emails)
- Google Calendar API (creates real events)
- Claude API (real AI extraction)

**Setup required:**
1. Google OAuth credentials
2. Gmail API enabled
3. Calendar API enabled
4. Anthropic API key

**Most students will study the code, not run it.** That's fine! The demo shows how it works.

---

## Using the Prompts Library

### Browsing Available Prompts

All prompts are in `components/transformers/prompts.py` as simple constants:

```python
from components.transformers import prompts

# See all available prompts
print(dir(prompts))

# Common prompts:
# - SENTIMENT_ANALYZER
# - SPAM_DETECTOR
# - URGENCY_DETECTOR
# - EMOTION_DETECTOR
# - TOPIC_CLASSIFIER
# - ENTITY_EXTRACTOR
# - TEXT_SUMMARIZER
# ... and 20+ more
```

### Using a Prompt

```python
from components.transformers.prompts import EMOTION_DETECTOR
from components.transformers.demo_ai_agent import demo_ai_transform

# Create AI transform
emotion_analyzer = demo_ai_transform(EMOTION_DETECTOR)

# Use it
result = emotion_analyzer("I'm so excited for this!")
# Returns: {"primary_emotion": "joy", "emotion_scores": {...}, "reasoning": "..."}
```

### IDE Autocomplete

Type `from components.transformers.prompts import ` and your IDE shows all options:

```
SENTIMENT_ANALYZER
SPAM_DETECTOR
URGENCY_DETECTOR
EMOTION_DETECTOR
TONE_ANALYZER
TOPIC_CLASSIFIER
LANGUAGE_DETECTOR
ENTITY_EXTRACTOR
KEY_PHRASE_EXTRACTOR
TEXT_SUMMARIZER
GRAMMAR_CHECKER
...
```

**No need to memorize. Just browse as you code.**

### Creating Custom Prompts

You can create your own:

```python
MY_CUSTOM_PROMPT = """Analyze the formality level of text.

Return JSON:
{
    "formality": "formal" | "casual" | "mixed",
    "score": 0.0-1.0,
    "indicators": ["reason1", "reason2"]
}"""

# Use it just like library prompts
formality_analyzer = demo_ai_transform(MY_CUSTOM_PROMPT)
```

---

## Your Turn: Exercises

### Exercise 1: Modify Example 1

**Task:** Add emotion detection alongside sentiment analysis.

**Steps:**
1. Import `EMOTION_DETECTOR` from prompts
2. Create second AI transform
3. Add to network as parallel path (fanout pattern from Module 3)
4. Compare sentiment vs emotion results

**Hint:**
```python
sentiment_node = Transform(fn=demo_ai_transform(SENTIMENT_ANALYZER), name="sentiment")
emotion_node = Transform(fn=demo_ai_transform(EMOTION_DETECTOR), name="emotion")

network([
    (source, sentiment_node),
    (source, emotion_node),  # Fanout!
    (sentiment_node, sink1),
    (emotion_node, sink2)
])
```

### Exercise 2: Build a Content Filter

**Task:** Create a network that filters toxic content and analyzes what remains.

**AI agents needed:**
- `TOXICITY_DETECTOR` - Detect inappropriate content
- `SENTIMENT_ANALYZER` - Analyze remaining content

**Network structure:**
```
Posts → [Toxicity Filter] → [Sentiment Analyzer] → Clean Results
```

**Challenge:** Only pass messages where `toxicity["severity"]` is "none" or "low".

### Exercise 3: Multi-Language Support

**Task:** Build a network that detects language, then routes to language-specific sentiment analysis.

**AI agents:**
- `LANGUAGE_DETECTOR` - Identify language
- `SENTIMENT_ANALYZER` - Analyze sentiment (works for any language)

**Network structure:**
```
Posts → [Language Detector] → [Language Router] → [Sentiment] → Results
```

**Bonus:** Count how many posts in each language.

### Exercise 4: Smart Email Organizer

**Task:** Triage emails into folders based on AI analysis.

**AI agents:**
- `SPAM_DETECTOR` - Filter junk
- `INTENT_CLASSIFIER` - Question? Request? Complaint?
- `PRIORITY_CLASSIFIER` - How urgent?
- `SENTIMENT_ANALYZER` - Emotional tone

**Routing logic:**
- Spam → Trash
- Urgent + Negative → "Immediate Attention"
- Questions → "To Answer"
- Everything else → "Review Later"

### Exercise 5: Design Your Own

**Task:** Choose a domain that interests you and design a multi-agent network.

**Ideas:**
- Social media monitoring (trends, sentiment, influencers)
- Product review analysis (features, complaints, ratings)
- Research paper classifier (topic, quality, citations)
- Job posting analyzer (requirements, salary, remote?)
- Customer feedback processor (features requested, bugs reported)

**Requirements:**
- Use at least 2 AI agents
- Include custom Python logic
- Create both demo and real versions

---

## Transitioning Demo → Real

### The One-Line Change

**Demo:**
```python
from components.transformers.demo_ai_agent import demo_ai_transform
```

**Real (Claude):**
```python
from components.transformers.claude_agent import ai_transform
```

**Real (OpenAI):**
```python
from components.transformers.openai_agent import ai_transform
```

Everything else stays the same. Same prompts, same network, same logic.

### Running Real AI

**1. Get API Key:**
- Claude: https://console.anthropic.com
- OpenAI: https://platform.openai.com

**2. Set Environment:**
```bash
export ANTHROPIC_API_KEY=your_key
# or
export OPENAI_API_KEY=your_key
```

**3. Update Import:**
```python
from components.transformers.claude_agent import ai_transform
```

**4. Run:**
```bash
python example_01_sentiment.py
```

### Cost Estimates

**Example 1 (Sentiment):** ~$0.01
**Example 2 (Pipeline):** ~$0.02
**Example 3 (Triage):** ~$0.05
**News Dashboard:** ~$0.10-0.30
**Email Calendar:** ~$0.15-0.40

**Total for all examples:** ~$0.50-1.00

### For Students Without API Access

**You can fully learn this module using only demos!**

The real AI:
- Is more accurate
- Handles nuance better
- Costs money

But the **pattern is identical**. Master the pattern with demos, and you understand how real AI works.

---

## Key Takeaways

### The One Pattern

```
Text → AI (Prompt) → JSON → Python Logic → Action
```

**Every AI agent follows this pattern.**

### What You Learned

1. ✅ How to use prompts from the library
2. ✅ How AI returns structured JSON
3. ✅ How Python processes JSON to make decisions
4. ✅ How to chain multiple AI agents
5. ✅ How to build complete intelligent systems

### The Power

**Traditional:** You write every rule.
**AI-Powered:** You describe what you want, AI handles complexity.

**Traditional:** Rules break on edge cases.
**AI-Powered:** AI understands context and nuance.

**Traditional:** Hard to maintain and extend.
**AI-Powered:** Change prompt, change behavior.

### Remember

- **AI provides intelligence** (analysis, understanding, extraction)
- **Python provides judgment** (decisions, routing, business logic)
- **Prompts define behavior** (what AI should do)
- **JSON bridges them** (structured data exchange)

---

## Next Steps

**Completed Module 08?** You can now build intelligent distributed systems!

**Next Module:** [Module 09: Production Patterns](../module_09_production/) 
- Error handling
- Rate limiting
- Cost optimization
- Monitoring and logging
- Testing AI components

**Want More Practice?**
- Build networks for your own interests
- Combine AI agents in new ways
- Create custom prompts
- Study the complete applications

**Questions?**
- Review the examples again
- Read the prompts library
- Experiment with different AI agents
- Check [Troubleshooting](../../docs/troubleshooting.md)

---

## Quick Reference

### Import Pattern
```python
from components.transformers.prompts import SENTIMENT_ANALYZER
from components.transformers.demo_ai_agent import demo_ai_transform
from dsl.blocks import Transform

ai_function = demo_ai_transform(SENTIMENT_ANALYZER)
node = Transform(fn=ai_function, name="sentiment")
```

### Common Prompts
- `SENTIMENT_ANALYZER` - Positive/negative/neutral
- `SPAM_DETECTOR` - Spam detection
- `URGENCY_DETECTOR` - Time-sensitive content
- `TOPIC_CLASSIFIER` - Categorize by topic
- `ENTITY_EXTRACTOR` - Extract names, places, dates
- `TEXT_SUMMARIZER` - Create summaries

### AI + Python Pattern
```python
def my_transform(text):
    # AI analyzes
    result = ai_function(text)
    
    # Python decides
    if result["field"] == "value":
        return action_A()
    else:
        return action_B()
```

### Demo → Real
```python
# Demo
from components.transformers.demo_ai_agent import demo_ai_transform

# Real
from components.transformers.claude_agent import ai_transform
```

---

**Ready to build intelligent systems? Start with Example 1!** 🚀