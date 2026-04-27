# Gallery

The gallery contains examples of distributed systems -- networks of agents executing
continuously. A system can be described either in plain English as ***an office of agents*** or
as a ***graph*** in Python. The gallery contains both kinds of examples. 

---

## If you want to describe an office of agents in English

You write job descriptions and an org chart in plain English.
A compiler turns your description into a running office of AI agents.
No programming required.

| Office | What it does |
|--------|-------------|
| [Situation Room](org_situation_room/) | Live politics & economics monitor — BlueSky + RSS |
| [Intelligence Briefing](org_intelligence_briefing/) | World news briefing, significant events only |
| [News Editorial](org_news_editorial/) | Two-agent editorial chain — analyst feeds editor |
| [News Monitor](org_news_monitor/) | Filters incoming articles for significance |
| [Two-Office News Network](org_two_office_news/) | News monitor + editorial office wired together |

**How to run any of these -- Example:**

```bash
dsl run gallery/org_intelligence_briefing/
```

The compiler reads your English documents, shows you the routing,
asks "Does this look right?", and starts your office.

---

## If you prefer using Python

You can also write a network of agents directly in Python — useful when
you want full control over agent behavior, custom transforms, or
stateful logic that the English office grammar doesn't yet cover.

A small collection of raw-Python example offices lives outside the
shipped gallery, in [`examples/python_offices/`](../../examples/python_offices/).
These are illustrative — read the source to see how to wire a non-trivial
network — and not maintained as a smooth Path A user experience.

---

## Sources and Sinks

The gallery examples use RSS feeds and BlueSky as sources, and
console display and file recording as sinks. These are just a few 
of the many examples of sources and sinks.

**Sources already in the framework:**

| Source | What it connects to |
|--------|-------------------|
| `rss_normalizer.py` | Any RSS feed — news, blogs, job boards, podcasts |
| `bluesky_jetstream_source.py` | BlueSky social media, live stream |
| `email_source.py` | Your email inbox |
| `file_source.py` | Files on disk — watch a directory for new files |
| `web_scraper.py` | arXiv, websites, and other scraped sources |
| `clock_source.py` | Timer — trigger events at intervals or daily |

**Sinks already in the framework:**

| Sink | What it connects to |
|------|-------------------|
| `intelligence_display.py` | Live color-coded terminal dashboard |
| `sink_jsonl_recorder.py` | JSON Lines file — one record per line |
| `file_writer.py` | Any file on disk |
| `gmail_alerter.py` | Gmail — send email alerts |
| `webhook_sink.py` | Any webhook endpoint |
| `http.py` | Any HTTP endpoint |
| `console_display.py` | Plain text to terminal |

**Building your own source or sink is straightforward:**

A source is any function or generator that yields messages — dicts with
whatever fields your agents need. A sink is any function that receives
a message and does something with it. The framework handles all the
threading and message passing.

```python
# A source — yields one message at a time, returns None when done
def my_source():
    for item in my_data:
        yield {"text": item, "source": "my_source"}

# A sink — receives a message and acts on it
def my_sink(msg):
    send_to_slack(msg["text"])
```

Wire them in with the rest of your network:

```python
src  = Source(fn=my_source)
sink = Sink(fn=my_sink)
g = network([(src, my_transform), (my_transform, sink)])
g.run_network()
```
## The Full Picture

The gallery examples use news feeds as sources and files/displays as sinks.
These are just the examples we built first — not the limits of what DSL can do.

**Any data stream can be a source:**
cameras, microphones, temperature sensors, GPS trackers,
email inboxes, Slack channels, stock feeds, weather APIs,
database change streams, IoT sensors, calendar events.

**Any action can be a sink:**
sending email or SMS, posting to Slack, updating a calendar,
writing to a database, controlling a camera or thermostat,
triggering a webhook, calling an API, moving a robot arm.

A DSL agent is just a function. If you can write a Python function
that reads from a sensor or acts on the world, you can wire it into
a DSL network. The framework handles the concurrency and message passing.

**Modify the examples in the gallery to build apps for your own goals**