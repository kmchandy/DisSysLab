# Module 09: Building Components - Sources & Sinks

Welcome to Module 09! After mastering AI-powered transforms in Module 08, you're ready to connect to the **real world**.

**By the end of this module, you'll build applications that:**
- 📊 Read data from files (CSV, JSON)
- 🐦 Monitor live social media (BlueSky)
- 📧 Read and send emails automatically
- 🔔 Send notifications to Slack/Discord
- 💾 Save results to files and databases

**You're about to learn how to make distributed systems that actually DO something!**

---

## What You'll Learn

### The Complete Picture

You already know **Transforms** (Module 08) - they process data.

Now you'll learn:
- **Sources** - Where data COMES FROM
- **Sinks** - Where data GOES TO

**The complete pattern:**
```
SOURCE → TRANSFORM → SINK
(input)  (process)   (output)
```

### Three Progressive Examples

**Example 1: File Pipeline** (5 minutes) ⭐ Easy
- Read CSV → Filter → Transform → Write JSON
- Everyone runs this first!

**Example 2: Social Media Monitor** (30 minutes) ⭐⭐ Medium
- BlueSky → Spam Filter → Sentiment → File + Dashboard + Alerts
- Real-time monitoring with multiple outputs

**Example 3: Email Automation** (60 minutes) ⭐⭐⭐ Advanced
- Email Inbox → Extract Meetings → Send Confirmations
- Complete automation loop

---

## Prerequisites

Before starting Module 09:
- ✅ Completed Modules 1-8
- ✅ Understand Sources, Transforms, Sinks (basic concept)
- ✅ Comfortable with Python and DSL
- ✅ Completed Module 08 (AI transforms)

**Time needed:** 2-3 hours total
**Cost:** $0.05-0.10 for real AI examples (optional)

---

## Quick Start - Run This Now!

**Don't read more - DO THIS:**

```bash
cd examples/module_09/
python3 demo_example_01_file_pipeline.py
```

**That's it!** You just built your first complete data pipeline.

**What happened?**
1. Read 50 customers from demo CSV
2. Filtered to active customers
3. Added summary field
4. Showed output (would write to file)

**Now run the REAL version:**

```bash
python3 example_01_file_pipeline.py
```

**Check the output:**

```bash
cat active_customers.json
# You created a real file!
```

✨ **You just went from demo → real in seconds!** This is the power of the pattern.

---

## Understanding Sources

### What Is a Source?

**A Source is where data comes FROM.**

Every distributed system starts with a Source. It could be:
- Files on disk
- API endpoints
- Databases
- Message queues
- Social media streams
- Email inboxes
- Sensors
- ...anything!

### The Source Interface

Any class with a `run()` method that yields items:

```python
class MySource:
    def run(self):
        for item in self.data:
            yield item  # Yield each item
        return None    # Signal completion
```

That's it! Simple pattern, powerful results.

### The Demo vs Real Pattern

This module teaches you a pattern for every connector:

**Demo Version:**
- Pre-loaded sample data
- No setup, no APIs, no credentials
- Works offline immediately
- Perfect for learning the pattern

**Real Version:**
- Connects to actual APIs/files/services
- Requires setup (usually free)
- Production-ready code
- What you'll use in real projects

**Same Interface:**
Both return identical data structures, so switching is ONE line of code!

```python
# Demo
from components.sources.demo_bluesky import DemoBlueSkySource
source = DemoBlueSkySource()

# Real (just change the import!)
from components.sources.bluesky import BlueSkySource
source = BlueSkySource(handle="you.bsky.social", app_password="...")
```

---

## The Three Source Types

### 1. File Source ⭐ EASIEST

**What:** Read CSV, JSON, JSONL files

**Demo:** Built-in sample data
- `sample_customers.csv` (50 customers)
- `sample_events.json` (100 events)

**Real:** Read any file from your filesystem

**When to use:**
- Data processing pipelines
- ETL (Extract, Transform, Load)
- Log analysis
- Batch processing

**Example:**

```python
from components.sources.demo_file import DemoFileSource

# Demo - uses built-in sample data
source = DemoFileSource(filename="customers", format="csv")

for customer in source.run():
    print(customer)
    # {'id': 1, 'name': 'Alice', 'email': '...', ...}
```

**Data format returned:**

```python
{
    "id": 1,
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "age": 28,
    "city": "New York",
    "status": "active"
}
```

---

### 2. BlueSky Source ⭐⭐ MEDIUM

**What:** Monitor BlueSky social media posts

**Demo:** 30 pre-loaded realistic posts
- Mix of topics (tech, product feedback, news)
- Mix of sentiments (positive, negative, neutral)
- No API needed

**Real:** Live BlueSky API (free!)
- Simple authentication (app password, no OAuth)
- 5-minute setup
- Generous rate limits

**When to use:**
- Brand monitoring
- Sentiment tracking
- Trend analysis
- Social listening
- Customer feedback

**Example:**

```python
from components.sources.demo_bluesky import DemoBlueSkySource

# Demo - 30 sample posts
source = DemoBlueSkySource(max_posts=30)

for post in source.run():
    print(f"@{post['author']}: {post['text']}")
    print(f"  Likes: {post['likes']} | Reposts: {post['reposts']}")
```

**Data format returned:**

```python
{
    "text": "Just shipped our new API!",
    "author": "dev_sarah",
    "author_display": "Sarah Chen",
    "timestamp": "2026-02-08T14:22:00Z",
    "likes": 42,
    "reposts": 5,
    "replies": 8,
    "url": "https://bsky.app/...",
    "hashtags": ["api", "developers"],
    "language": "en"
}
```

---

### 3. Email Source ⭐⭐⭐ HARD

**What:** Read emails from your inbox via IMAP

**Demo:** 15 pre-loaded realistic emails
- Meeting requests
- Customer inquiries
- Newsletters
- Spam

**Real:** Gmail, Outlook, any IMAP server
- IMAP protocol
- 15-minute setup (app password)
- Production-ready

**When to use:**
- Email automation
- Ticket systems
- Meeting scheduling
- Customer support
- Alert monitoring

**Example:**

```python
from components.sources.demo_email import DemoEmailSource

# Demo - 15 sample emails
source = DemoEmailSource(filter_unread=True)

for email in source.run():
    print(f"From: {email['from_name']}")
    print(f"Subject: {email['subject']}")
    print(f"Body: {email['body'][:100]}...")
```

**Data format returned:**

```python
{
    "from": "john@example.com",
    "from_name": "John Doe",
    "to": "me@example.com",
    "subject": "Meeting request",
    "body": "Full email text...",
    "date": "2026-02-08T09:30:00Z",
    "has_attachments": False,
    "labels": ["inbox", "important"],
    "message_id": "unique_id_123"
}
```

---

## Understanding Sinks

### What Is a Sink?

**A Sink is where data GOES TO.**

Every distributed system ends with one or more Sinks. Data flows to:
- Files on disk
- Databases
- Email recipients
- Webhooks (Slack, Discord)
- Cloud storage
- APIs
- Dashboards
- ...anywhere!

### The Sink Interface

Any class with `run(item)` and `finalize()` methods:

```python
class MySink:
    def run(self, item):
        # Process each item
        pass
        
    def finalize(self):
        # Cleanup (flush, close, etc.)
        pass
```

**Why two methods?**
- `run()`: Called for each item (one at a time)
- `finalize()`: Called once at the end (cleanup, close files, etc.)

---

## The Three Sink Types

### 1. File Writer ⭐ EASIEST

**What:** Write data to files (JSON, CSV, JSONL, text)

**Demo:** Prints to console instead of writing
- Shows what would be written
- No actual file I/O
- Perfect for learning

**Real:** Creates actual files on disk
- Multiple formats: JSON, JSONL, CSV, text
- Streaming or buffering
- Production-ready

**When to use:**
- Data export
- Logging
- Archiving
- Backups
- Reporting

**Example:**

```python
from components.sinks.demo_file_writer import DemoFileWriter

# Demo - prints instead of writing
writer = DemoFileWriter(filename="output.json", format="json")

writer.run({"id": 1, "name": "Alice"})
writer.run({"id": 2, "name": "Bob"})
writer.finalize()  # Shows what would be written
```

**Formats supported:**
- **JSON:** Pretty-printed array `[{...}, {...}]`
- **JSONL:** One JSON object per line (streaming)
- **CSV:** With headers
- **Text:** Plain text, one item per line

---

### 2. Email Sender ⭐⭐ MEDIUM

**What:** Send emails via SMTP

**Demo:** Prints formatted email to console
- Shows plain text and HTML versions
- No actual emails sent
- Safe for learning

**Real:** Actually sends emails
- Gmail, SendGrid, any SMTP server
- Plain text and HTML
- 5-10 minute setup

**When to use:**
- Alerts and notifications
- Reports and summaries
- Customer communications
- Automated responses
- Confirmations

**Example:**

```python
from components.sinks.demo_email_sender import DemoEmailSender

# Demo - prints instead of sending
sender = DemoEmailSender(
    from_email="bot@example.com",
    to_email="user@example.com"
)

sender.run({
    "subject": "Alert: High CPU",
    "body": "CPU usage is at 95%",
    "html": "<h1>Alert</h1><p>CPU usage is at 95%</p>"
})
```

**Email structure:**

```python
{
    "to": "recipient@example.com",  # Optional, uses default
    "subject": "Your subject here",
    "body": "Plain text version",
    "html": "<h1>HTML version</h1>"  # Optional
}
```

---

### 3. Webhook ⭐⭐ MEDIUM

**What:** HTTP POST to webhook URLs

**Demo:** Prints POST details to console
- Shows URL, headers, JSON payload
- No network calls
- Safe for learning

**Real:** Actually sends HTTP POST
- Slack, Discord, Zapier, custom APIs
- Automatic retries
- Production-ready

**When to use:**
- Slack/Discord notifications
- Zapier integrations
- Custom API integrations
- Real-time alerts
- Modern integrations

**Example:**

```python
from components.sinks.demo_webhook import DemoWebhook

# Demo - prints instead of POSTing
webhook = DemoWebhook(url="https://hooks.slack.com/...")

webhook.run({
    "text": "🚨 Alert: System down!",
    "channel": "#alerts"
})
```

**Popular formats:**

**Slack:**
```python
{
    "text": "Your message",
    "channel": "#general",
    "username": "Bot Name"
}
```

**Discord:**
```python
{
    "content": "Your message",
    "username": "Bot Name"
}
```

**Generic:**
```python
{
    "event": "user_signup",
    "data": {...}
}
```

---

## Example 1: File Processing Pipeline

**Time:** 5 minutes | **Difficulty:** ⭐ Easy | **Everyone runs this!**

### What You'll Build

```
CSV File → [Filter Active] → [Summarize] → JSON File
```

A complete data processing pipeline:
1. Read customers from CSV
2. Filter to active customers only
3. Add summary field to each
4. Write to JSON file

### The Network

```python
from dsl import network
from dsl.blocks import Source, Transform, Sink
from components.sources.demo_file import DemoFileSource
from components.sinks.demo_file_writer import DemoFileWriter

# Source: Read customers
customer_source = DemoFileSource(filename="customers", format="csv")
source = Source(fn=customer_source.run, name="customers")

# Transform 1: Filter active
def filter_active(customer):
    if customer.get("status") == "active":
        return customer
    return None  # Filter out

filter_node = Transform(fn=filter_active, name="filter")

# Transform 2: Add summary
def summarize(customer):
    customer["summary"] = f"{customer['name']} ({customer['age']}) from {customer['city']}"
    return customer

summarize_node = Transform(fn=summarize, name="summarize")

# Sink: Write to file
writer = DemoFileWriter(filename="active_customers.json", format="json")
sink = Sink(fn=writer.run, name="writer")

# Build network
g = network([
    (source, filter_node),
    (filter_node, summarize_node),
    (summarize_node, sink)
])

# Run!
g.run_network()
writer.finalize()
```

### What You Learn

✅ **Source → Transform → Sink pattern**
✅ **Filtering** (return None to filter out)
✅ **Data enrichment** (adding fields)
✅ **File I/O** (CSV → JSON)

### Try These Experiments

1. **Change the filter:** Filter by city or age instead
2. **Add another transform:** Calculate age groups
3. **Change format:** Try `format="csv"` in the sink
4. **Chain more:** Add sorting, grouping, statistics

### Demo → Real

To switch to real file I/O, change TWO lines:

```python
# Instead of:
from components.sources.demo_file import DemoFileSource
from components.sinks.demo_file_writer import DemoFileWriter

# Use:
from components.sources.file_source import FileSource
from components.sinks.file_writer import FileWriter
```

That's it! Same code, real files.

---

## Example 2: Social Media Monitor

**Time:** 30 minutes | **Difficulty:** ⭐⭐ Medium | **Most students run this**

### What You'll Build

```
BlueSky → [Spam Filter] → [Sentiment] → File
                                        → Dashboard
                                        → Webhook
```

A real-time social media monitoring system:
1. Monitor BlueSky posts
2. Filter spam (AI)
3. Analyze sentiment (AI)
4. Output to 3 destinations:
   - File (save all posts)
   - Dashboard (live display)
   - Webhook (alerts for negative posts)

### The Network (Simplified)

```python
# Source: BlueSky posts
bluesky = DemoBlueSkySource(max_posts=30)
source = Source(fn=bluesky.run, name="bluesky")

# Transform 1: Spam filter
ai_spam = demo_ai_transform(SPAM_DETECTOR)

def spam_filter(post):
    result = ai_spam(post["text"])
    if result["is_spam"] and result["confidence"] > 0.7:
        return None  # Filter spam
    post["spam_check"] = result
    return post

spam_node = Transform(fn=spam_filter, name="spam")

# Transform 2: Sentiment
ai_sentiment = demo_ai_transform(SENTIMENT_ANALYZER)

def analyze_sentiment(post):
    result = ai_sentiment(post["text"])
    post["sentiment"] = result["sentiment"]
    post["sentiment_score"] = result["score"]
    return post

sentiment_node = Transform(fn=analyze_sentiment, name="sentiment")

# Sink 1: File
file_writer = DemoFileWriter("monitored_posts.json", format="json")
file_sink = Sink(fn=file_writer.run, name="file")

# Sink 2: Dashboard
def display(post):
    icon = {"POSITIVE": "😊", "NEGATIVE": "😞", "NEUTRAL": "😐"}[post["sentiment"]]
    print(f"{icon} @{post['author']}: {post['text'][:60]}...")
    
dashboard_sink = Sink(fn=display, name="dashboard")

# Sink 3: Alerts (webhook)
webhook = DemoWebhook(url="https://hooks.slack.com/...")

def alert(post):
    if post["sentiment"] == "NEGATIVE":
        webhook.run({"text": f"⚠️ Negative: {post['text'][:50]}"})
        
alert_sink = Sink(fn=alert, name="alerts")

# Build network (fanout to 3 sinks)
g = network([
    (source, spam_node),
    (spam_node, sentiment_node),
    (sentiment_node, file_sink),      # Output 1
    (sentiment_node, dashboard_sink),  # Output 2
    (sentiment_node, alert_sink)       # Output 3
])

g.run_network()
```

### What You Learn

✅ **API sources** (BlueSky)
✅ **Chaining AI agents** (spam → sentiment)
✅ **Multiple outputs** (fanout pattern)
✅ **Real-time monitoring**

### Demo → Real

To use real BlueSky API:

```python
from components.sources.bluesky import BlueSkySource

bluesky = BlueSkySource(
    handle="your.handle.bsky.social",
    app_password="your-app-password"  # See API_SETUP.md
)
```

**Setup time:** 5 minutes (see API_SETUP.md)
**Cost:** ~$0.03-0.05 (if using real AI)

---

## Example 3: Email Automation

**Time:** 60 minutes | **Difficulty:** ⭐⭐⭐ Hard | **Study this!**

### What You'll Build

```
Email Inbox → [Extract Meetings] → [Parse DateTime] → [Send Confirmation]
```

A complete email automation system:
1. Read emails from inbox
2. AI detects meeting requests
3. AI parses dates/times
4. Sends confirmation emails

### Use Case

**Input email:**
```
From: john@company.com
Subject: Schedule demo?

Hi, I'd like to schedule a demo for next Tuesday at 2pm EST.
Could we set up a 30-minute call?
```

**Automated response:**
```
From: assistant@mycompany.com
To: john@company.com
Subject: Meeting Confirmed

Hi John,

I've scheduled our meeting:
Date: 2026-02-11
Time: 14:00 EST
Topic: Product demo
Duration: 30 minutes

Looking forward to it!
```

### What You Learn

✅ **Complex sources** (Email/IMAP)
✅ **Complex sinks** (Email/SMTP)
✅ **AI data extraction** (unstructured → structured)
✅ **Complete automation loop**
✅ **Production considerations** (testing, safety)

### Safety Warning

⚠️ **This automation SENDS EMAILS!**

Before running real version:
1. Test with demo first
2. Use a test email account
3. Review detected meetings manually
4. Add safety checks (whitelist senders)

**See the full example code for complete implementation and safety guidelines.**

---

## Building Your Own Connectors

Now you can create custom Sources and Sinks!

### Source Template

```python
class MyCustomSource:
    """Your custom data source."""
    
    def __init__(self, ...):
        # Setup: load data, connect to API, etc.
        self.data = ...
    
    def run(self):
        """Yield items one at a time."""
        for item in self.data:
            # Convert to consistent dict format
            yield {
                "field1": ...,
                "field2": ...,
            }
        return None  # Signal completion
```

### Sink Template

```python
class MyCustomSink:
    """Your custom data destination."""
    
    def __init__(self, ...):
        # Setup: open file, connect to API, etc.
        self.output = ...
    
    def run(self, item):
        """Process one item."""
        # Do something with item
        self.output.write(item)
    
    def finalize(self):
        """Cleanup at end."""
        self.output.close()
```

### Best Practices

1. **Consistent data format**
   - Always return dicts from Sources
   - Use same field names
   - Include timestamp, id when possible

2. **Error handling**
   - Don't crash on bad data
   - Log errors, continue processing
   - Provide helpful error messages

3. **Demo version first**
   - Create demo with sample data
   - Test the pattern
   - Then build real version

4. **Document your connector**
   - What does it return?
   - What credentials needed?
   - What are the rate limits?

**See TEMPLATES.md for more examples and patterns.**

---

## What's Next?

### You've Completed Module 09!

You can now:
- ✅ Build Sources (read data from anywhere)
- ✅ Build Sinks (write data anywhere)
- ✅ Build AI Transforms (Module 08)
- ✅ Build complete applications!

**You have all the pieces to build REAL distributed systems!**

### Module 10: How to Use DisSysLab

Next, you'll learn:
- Systematic development workflow
- How to start a project from scratch
- Testing and debugging strategies
- Building your own applications

### Module 12: Extended Toolkit

Later, you'll get more connectors:
- RSS feeds
- Reddit
- Databases (SQLite, PostgreSQL)
- Google Calendar
- Web dashboards

### Your Capstone Project

You're ready! Pick an application YOU want to build:
- Social media dashboard?
- Email automation system?
- News aggregator?
- Data processing pipeline?

**You have all the tools now!**

---

## Troubleshooting

### "Module not found"

**Problem:** Import errors

**Solution:**
```bash
# Make sure you're in the right directory
cd examples/module_09/

# Make sure DisSysLab is in your path
export PYTHONPATH=/path/to/DisSysLab:$PYTHONPATH
```

### "API authentication failed"

**Problem:** Can't connect to BlueSky/Gmail

**Solution:** Check API_SETUP.md for step-by-step setup

### "No data returned"

**Problem:** Source yields nothing

**Solution:**
- Check filters (are you filtering everything out?)
- Print debug info: `print(f"Source yielded: {item}")`
- Try with demo version first

### "File not found"

**Problem:** Can't find sample data

**Solution:**
- Make sure you're in `examples/module_09/` directory
- Sample data is in `sample_data/` subdirectory
- Or use demo versions (have embedded data)

---

## Summary

**Module 09 in Three Patterns:**

### Pattern 1: Source → Sink
```python
Source (data in) → Sink (data out)
```
Simplest: just move data

### Pattern 2: Source → Transform → Sink
```python
Source → Transform (process) → Sink
```
Classic: read, process, write

### Pattern 3: Source → Transforms → Sinks
```python
Source → Transform 1 → Transform 2 → Sink 1
                                    → Sink 2
                                    → Sink 3
```
Production: complex processing, multiple outputs

**You can build ANY of these now!**

---

**Ready to build? Start with Example 1:**

```bash
cd examples/module_09/
python3 demo_example_01_file_pipeline.py
```

**Then explore, experiment, and CREATE!**