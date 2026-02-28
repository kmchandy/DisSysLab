# Module 09: Building Components - Sources & Sinks
## Complete Implementation Plan

---

## Overview

**Scope:** 3 Sources + 3 Sinks + 3 Examples
**Time:** 2-3 hours for students
**Files:** ~24 files
**Philosophy:** Depth over breadth - Master the pattern

---

## File Structure

```
DisSysLab/
├── components/
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── demo_file.py          # Demo CSV/JSON reader
│   │   ├── file_source.py        # Real file reader
│   │   ├── demo_bluesky.py       # Demo BlueSky posts
│   │   ├── bluesky.py            # Real BlueSky API
│   │   ├── demo_email.py         # Demo email inbox
│   │   └── email_source.py       # Real IMAP email
│   │
│   └── sinks/
│       ├── __init__.py
│       ├── demo_file_writer.py   # Demo file writer
│       ├── file_writer.py        # Real file writer
│       ├── demo_email_sender.py  # Demo email sender
│       ├── email_sender.py       # Real SMTP sender
│       ├── demo_webhook.py       # Demo HTTP POST
│       └── webhook.py            # Real webhook sender
│
└── examples/
    └── module_09/
        ├── README.md
        ├── API_SETUP.md
        ├── TEMPLATES.md
        ├── sample_data/
        │   ├── sample_customers.csv
        │   ├── sample_events.json
        │   └── sample_emails.json
        ├── demo_example_01_file_pipeline.py
        ├── example_01_file_pipeline.py
        ├── demo_example_02_social_monitor.py
        ├── example_02_social_monitor.py
        ├── demo_example_03_email_automation.py
        └── example_03_email_automation.py
```

---

## Module Goals

**By the end of Module 09, students will:**
1. ✅ Understand what Sources and Sinks are
2. ✅ Know how to build both demo and real versions
3. ✅ Build 3 complete applications
4. ✅ Have templates for creating their own connectors
5. ✅ Feel confident: "I can connect to the real world!"

**Success Metrics:**
- 90% run Example 1 (File Pipeline)
- 70% run Example 2 (BlueSky Monitor)
- 40% run Example 3 (Email Automation)
- Students say: "I can build real apps now!"

---

## The Three Source Types

### SOURCE 1: File Source (CSV/JSON) - EASIEST ⭐

**Purpose:** Universal data loading, foundation for all data work

**Demo Version:** `demo_file.py`
- Pre-loaded sample data (customers.csv, events.json)
- No setup required
- Returns consistent dict format

**Real Version:** `file_source.py`
- Reads any CSV/JSON/JSONL file
- Auto-detects format
- Error handling for encoding, missing files

**Sample Data Included:**
- `sample_customers.csv` (50 rows)
- `sample_events.json` (100 events)

**Return Format:**
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

### SOURCE 2: BlueSky - MEDIUM ⭐⭐

**Purpose:** Real-time social media monitoring, modern API patterns

**Demo Version:** `demo_bluesky.py`
- 30 pre-loaded realistic posts
- Mix of topics and sentiments
- No API needed

**Real Version:** `bluesky.py`
- Free BlueSky API
- Simple authentication (app password)
- No OAuth complexity

**Sample Data:** 30 posts covering:
- Software development (10)
- Product feedback (8)
- Tech news (7)
- Casual posts (5)

**Return Format:**
```python
{
    "text": "Just shipped our new API!",
    "author": "dev_sarah",
    "author_display": "Sarah Chen",
    "timestamp": "2026-02-08T14:22:00Z",
    "likes": 42,
    "reposts": 5,
    "url": "https://bsky.app/...",
    "hashtags": ["api", "developers"],
    "language": "en"
}
```

---

### SOURCE 3: Email Inbox - HARD ⭐⭐⭐

**Purpose:** Email automation, IMAP protocol, complex data parsing

**Demo Version:** `demo_email.py`
- 15 pre-loaded realistic emails
- Meeting requests, inquiries, spam, newsletters
- No email account needed

**Real Version:** `email_source.py`
- IMAP protocol
- Works with Gmail, Outlook, any IMAP server
- Handles attachments, HTML parsing

**Sample Data:** 15 emails:
- Meeting requests (5)
- Customer inquiries (4)
- Order confirmations (2)
- Newsletters (2)
- Spam (2)

**Return Format:**
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

## The Three Sink Types

### SINK 1: File Writer - EASIEST ⭐

**Purpose:** Data persistence, export, logging

**Demo Version:** `demo_file_writer.py`
- Prints to console instead of writing
- Shows file structure
- No file I/O

**Real Version:** `file_writer.py`
- Supports JSON, JSONL, CSV, text
- Streaming and buffering modes
- Auto-creates directories

**Formats Supported:**
- JSON: Pretty-printed array
- JSONL: One JSON object per line (streaming)
- CSV: With headers
- Text: Plain text

---

### SINK 2: Email Sender - MEDIUM ⭐⭐

**Purpose:** Notifications, alerts, reports, automation

**Demo Version:** `demo_email_sender.py`
- Prints formatted email to console
- Shows plain text and HTML
- No email sent

**Real Version:** `email_sender.py`
- SMTP protocol
- Works with Gmail, SendGrid, any SMTP
- Plain text and HTML emails

**Features:**
- Template subjects
- HTML formatting
- Multiple recipients
- Error handling

---

### SINK 3: Webhook - MEDIUM ⭐⭐

**Purpose:** Modern integrations (Slack, Discord, Zapier, custom APIs)

**Demo Version:** `demo_webhook.py`
- Prints HTTP POST details
- Shows JSON payload
- No network calls

**Real Version:** `webhook.py`
- Real HTTP POST
- Automatic retries with backoff
- Works with Slack, Discord, Zapier

**Popular Integrations:**
- Slack notifications
- Discord messages
- Zapier triggers
- Custom webhooks

---

## The Three Examples

### EXAMPLE 1: File Pipeline - EASY ⭐

**Goal:** Immediate success, understand Source → Transform → Sink

**Network:**
```
CSV File → [Filter Active] → [Summarize] → File Output
```

**What It Does:**
1. Reads 50 customers from CSV
2. Filters to active customers (Python)
3. Adds summary field
4. Writes to JSON file

**Time:** 5 seconds (demo), 10 seconds (real)

**Learning:**
- Source → Transform → Sink pattern
- Filtering (return None)
- Data enrichment
- File formats

---

### EXAMPLE 2: Social Media Monitor - MEDIUM ⭐⭐

**Goal:** Real-time data, multiple transforms, multiple outputs

**Network:**
```
BlueSky → [Spam Filter] → [Sentiment] → File
                                       → Dashboard
                                       → Webhook
```

**What It Does:**
1. Monitors BlueSky posts
2. Filters spam (AI)
3. Analyzes sentiment (AI)
4. Outputs to 3 sinks (file, dashboard, webhook)

**Time:** 10 seconds (demo), 60 seconds (real)
**Cost:** ~$0.03-0.05 (real version with Claude)

**Learning:**
- API sources (BlueSky)
- Multiple AI agents
- Fanout to multiple sinks
- Real-time monitoring

---

### EXAMPLE 3: Email Automation - HARD ⭐⭐⭐

**Goal:** Complete automation loop, complex AI parsing, production system

**Network:**
```
Email Inbox → [Extract Meetings] → [Parse DateTime] → [Send Confirmation]
```

**What It Does:**
1. Reads email inbox (IMAP)
2. AI extracts meeting requests
3. AI parses dates/times
4. Sends confirmation emails (SMTP)

**Time:** 10 seconds (demo), 90 seconds (real)
**Cost:** ~$0.02-0.03 (real version with Claude)

**Learning:**
- Complex sources (IMAP)
- Complex sinks (SMTP)
- AI data extraction
- Complete automation loop
- Production considerations

---

## Documentation Files

### README.md (~500 lines)

**Structure:**
1. Welcome (5 min)
2. Quick Start (5 min) - Run Example 1 immediately
3. Understanding Sources (20 min)
4. Understanding Sinks (20 min)
5. Examples Walkthrough (60 min)
6. Building Your Own (30 min)
7. Next Steps (5 min)

**Teaching Philosophy:**
- Start with action (run Example 1 first!)
- Explain after success
- Progressive complexity
- Clear next steps

---

### API_SETUP.md (~300 lines)

**Detailed setup guides for:**

1. **BlueSky (5 min)** ⭐ EASY
   - Create account
   - Generate app password
   - Test connection
   - Troubleshooting

2. **Gmail IMAP (15 min)** ⭐⭐⭐ HARD
   - Enable IMAP
   - Enable 2FA
   - Generate app password
   - Test connection
   - Common issues

3. **Gmail SMTP (10 min)** ⭐⭐ MEDIUM
   - Same app password as IMAP
   - Configure SMTP
   - Test sending
   - Troubleshooting

4. **Slack Webhook (5 min)** ⭐ EASY
   - Create webhook URL
   - Test POST
   - Format messages

---

### TEMPLATES.md (~200 lines)

**Copy-paste templates for:**

1. **Source Templates**
   - Simple list source
   - File reader source
   - API reader source
   - Paginated API source

2. **Sink Templates**
   - Simple collector sink
   - File writer sink
   - API poster sink
   - Batch writer sink

3. **Common Patterns**
   - Pagination handling
   - Rate limiting
   - Error recovery
   - Retry logic

---

## Implementation Priority (Build Order)

### Week 1: Foundation
1. README.md (structure outline)
2. Sample data files
3. demo_file.py + file_source.py
4. demo_file_writer.py + file_writer.py
5. demo_example_01 + example_01
6. Test Example 1 thoroughly

### Week 2: Social Media
7. API_SETUP.md (BlueSky section)
8. demo_bluesky.py + bluesky.py
9. demo_webhook.py + webhook.py
10. demo_example_02 + example_02
11. Test Example 2 with real BlueSky

### Week 3: Email
12. API_SETUP.md (Gmail section)
13. demo_email.py + email_source.py
14. demo_email_sender.py + email_sender.py
15. demo_example_03 + example_03
16. Test Example 3 with real Gmail

### Week 4: Polish
17. Complete README.md (all sections)
18. Complete API_SETUP.md (all APIs)
19. TEMPLATES.md
20. Student beta test
21. Fix issues from beta
22. Release!

---

## Success Metrics

**Module 09 succeeds if:**

📊 **Usage Metrics:**
- 90% run demo Example 1
- 70% run real Example 1
- 50% run demo Example 2
- 30% run real Example 2
- 20% attempt Example 3

📊 **Learning Metrics:**
- Can explain Source vs Sink
- Can identify demo vs real
- Can create custom Source
- Feel confident with external systems

📊 **Feedback Metrics:**
- "I can build real apps!"
- Request more connector types
- Share projects they built

📊 **Quality Metrics:**
- Zero critical bugs in demos
- Clear error messages in real
- API guides work first-time
- Examples run without modification

---

## File Count Summary

**Components:** 12 files
- Sources: 6 (3 demo + 3 real)
- Sinks: 6 (3 demo + 3 real)

**Examples:** 6 files
- Demo versions: 3
- Real versions: 3

**Sample Data:** 3 files
- sample_customers.csv
- sample_events.json
- sample_emails.json (or embedded in demo_email.py)

**Documentation:** 3 files
- README.md
- API_SETUP.md
- TEMPLATES.md

**Total:** ~24 files

---

## Estimated Build Time

- **Components:** 3-4 days
- **Examples:** 2-3 days
- **Documentation:** 2-3 days
- **Testing & Polish:** 2-3 days
- **Total:** 2-3 weeks

---

## Notes

- All code goes in DisSysLab/components/sources and DisSysLab/components/sinks
- Examples go in DisSysLab/examples/module_09/
- Demo versions always work offline, no setup
- Real versions require free APIs (except email needs existing account)
- Students can run demos immediately, real versions optionally
- Focus on teaching patterns, not building comprehensive library

---

## Ready to Build!

Next step: Create markdown files one at a time for review.

Order:
1. README.md
2. API_SETUP.md
3. TEMPLATES.md
