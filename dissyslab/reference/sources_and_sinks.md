# Sources and sinks

A **source** sends messages into the office; a **sink** receives them at the
end. Both are declared in `office.md` like any other name:

```
sources:
    bbc_world(max_articles=5)
    tickets: file_source(path="tickets.jsonl")

sinks:
    console_printer
    kept: jsonl_recorder(path="kept.jsonl")
    discard
```

A source has one outbox, `out`; a sink has one inbox, `in`. Every message
is a JSON object.

## The built-in ones

The list below was read from the installed package. To see where one is
defined, `dsl show <name>` prints its file.

### Sources

| Source | Arguments | Notes |
|---|---|---|
| `file_source` | `path` | one message per line of a `.jsonl` file (or a `.json` list); the stand-in for any real source while you build |
| `bbc_world`, `bbc_tech`, `npr_news`, `al_jazeera`, `hacker_news`, `techcrunch`, `mit_tech_review`, `nasa_news`, `venturebeat_ai` | `max_articles`, `poll_interval` | news feeds; each message has `source`, `title`, `text`, `url`, `timestamp` |
| `rss` | `url`, `name`, `max_articles`, `poll_interval` | any RSS feed |
| `arxiv_cs_ai`, `arxiv_cs_lg`, `arxiv_cs_cl`, `arxiv_cs_cv`, `arxiv_cs_ro` | `max_articles`, `poll_interval` | new papers, with `authors` and `abstract` |
| `python_jobs`, `remoteok`, `we_work_remotely` | `max_articles`, `poll_interval` | job feeds |
| `web_scraper` | `url`, selectors | a page's articles, by CSS selector |
| `weather` | `city`, `poll_interval`, `max_readings` | no key needed |
| `weatherapi` | `q`, `days`, `poll_interval`, `max_readings` | needs `WEATHERAPI_KEY` |
| `stocks` | `ticker`, `poll_interval`, `max_readings` | live prices; needs `pip install "dissyslab[market]"` |
| `csv_stock_history` | `tickers`, `filename_pattern`, `start`, `end` | daily history from CSV files you fetch with `dsl fetch-prices` |
| `kalshi` | `ticker`, `keyword`, ... | prediction markets |
| `bluesky` | `max_posts`, `filter_keywords`, ... | the public Bluesky firehose |
| `gmail` | `max_emails`, `unread_only`, `folder` | needs `GMAIL_USER` and `GMAIL_APP_PASSWORD` |
| `calendar` | `url`, `days_ahead` | an ICS feed (`CALENDAR_ICS_URL`) |
| `audio_folder` | `path`, `glob`, `max_files` | one message per audio file |
| `audio_clip`, `audio_mic` | ... | audio in chunks, from a file or the microphone |
| `image_folder` | `folder`, `max_images` | one message per image |
| `webhook` | `port`, `path`, `host` | messages POSTed to a local URL |
| `chat_page` | `title`, `port`, `open_browser` | a chat page in the browser: each turn a message with `session`, `turn`, `text`, `history` |
| `mcp_source` | `server`, `tool`, `args` | any tool with an MCP server |
| `console_input` | `prompt` | lines typed at the terminal |

Every source also takes `allow_empty=True`: see [Empty output](#empty-output).

### Sinks

| Sink | Arguments |
|---|---|
| `console_printer` | `verbose=False` |
| `discard` | *(none)* |
| `jsonl_recorder` | `path="anomaly_stream.jsonl"`, `mode="w"` |
| `markdown_digest` | `path="morning_digest.md"`, `title=None` |
| `intelligence_display` | `title=`, `text=`, `color=`, `lines=[...]`, `max_items=` -- the fields to show; see below |
| `gmail_sink` | `to` **(required)**, `subject="DisSysLab Alert"` -- without credentials it writes to `outbox.md` |
| `slack_sink` | `webhook_url_env="SLACK_WEBHOOK_URL"`, `username`, `icon_emoji` |
| `webhook_sink` | `url` or `webhook_url_env`, `headers`, `timeout`, `retry_count` |
| `mcp_sink` | `server`, `tool`, `args` |
| `chat_reply` | `text="reply"`, `port` -- shows the reply in the `chat_page`; the message must keep `session` and `turn` |

`intelligence_display` never guesses field names. Tell it which to show:

```
intelligence_display(title="headline", text="summary", color="severity")
intelligence_display(title="title", text="abstract", color="relevance",
                     lines=["authors", "paper_type", "reason"])
```

`color` names a field whose value is `CRITICAL`, `HIGH`, `MEDIUM` or `LOW`;
`lines` are printed one per line as `field: value`.

Two of the same kind need two names:
`kept: jsonl_recorder(path="kept.jsonl")` and
`dropped: jsonl_recorder(path="dropped.jsonl")`.

## Your own source or sink

A file in the office's `sources/` or `sinks/` folder, with exactly one
class and no DisSysLab import, like a Python role. It is constructed with
the arguments from `office.md`.

- A **source's** instance is called with no arguments and returns the next
  message, or `None` when it has no more.
- A **sink's** instance is called with each message.

```python
"""
---
out: tick
---
A source that sends a tick every second, ten times.
"""
import time


class Ticker:
    def __init__(self, count=10):
        self.left = count

    def __call__(self):
        if self.left == 0:
            return None
        self.left -= 1
        time.sleep(1)
        return {"tick": self.left}
```

`ticks: ticker(count=5)` under `sources:` uses it. A stand-in
(`file_source`) and a real source are interchangeable: only the declaration
line changes, never the connections.

## Notes that save time

**`discard` is a decision.** Routing a router's `no` branch to `discard`
says "deliberately dropped". Every name in a connection must be declared,
`discard` included.

**But while you are developing, send rejects somewhere readable.** A filter
that drops the wrong thing produces an office that checks clean, runs clean
and answers wrong, and if the rejects went to `discard` there is nothing to
look at:

```
sinks:
    kept: jsonl_recorder(path="kept.jsonl")
    rejected: jsonl_recorder(path="rejected.jsonl")
connections:
    Rex.yes -> kept
    Rex.no -> rejected
```

You cannot automate a check for "the answer is wrong", so build offices
whose wrong answers are visible.

**Paths are relative to the office's folder.** `dsl run .` works from inside
it; a run writes its output next to `office.md`. That is why gallery offices
are copied first (`dsl init`).

**Credentials.** `gmail`, `calendar`, `weatherapi`, `slack_sink` and
`gmail_sink` need them; the news feeds, `weather` and `file_source` do not.
`dsl doctor` checks what is set.

**Market data is yours to fetch.** Nothing in the package ships prices.
`dsl fetch-prices` downloads daily history once (it needs
`pip install "dissyslab[market]"`), and `csv_stock_history` reads it from
the shared market-data folder, the same before and after `dsl init`.

### Empty output

A source that produces nothing makes `dsl run` fail rather than finish
quietly, because an empty result that looks like success is worse than an
error. So does a source whose every message was an error report. When
nothing is a legitimate answer -- a feed with nothing new -- declare the
source with `allow_empty=True`.
