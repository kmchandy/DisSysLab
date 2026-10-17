# Sort your own inbox

**Goal.** Run the inbox sorter you built in
[GETTING_STARTED.md](../GETTING_STARTED.md), part 6, on your real Gmail
instead of a file. One line of `office.md` changes.

Needs: an Anthropic key, and Gmail credentials (below).

## 1. Gmail credentials, once

Gmail uses an **app password**, a 16-character password you make once for
DisSysLab.

1. Go to myaccount.google.com, then Security, and turn on **2-Step
   Verification** (app passwords need it).
2. On the same page, open **App passwords** and make one for "Mail".
3. Add two lines to the `.env` file in your course folder, next to your
   Anthropic key:

```
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

`dsl doctor` shows both as `[SET ]`.

## 2. Swap the source

Copy your inbox sorter (or the finished one) and change the one source
line:

```bash
dsl init inbox_sorter my_inbox
cd my_inbox
```

In `office.md`, replace

```
    inbox: file_source(path="messages.jsonl")
```

with

```
    inbox: gmail(max_emails=10, unread_only=True)
```

Keep the name `inbox`, and nothing else in the office changes: the
connections say `inbox -> Tri`, and the triage role reads `subject` and
`text`, which every Gmail message has.

```bash
dsl check .
dsl run .
```

The source checks your inbox every 60 seconds and runs until you press
Ctrl-C. Reading mail does not mark it read.

## What each email becomes

```python
{
    "source":    "gmail",
    "subject":   "Re: PS3 office hours",
    "title":     "Re: PS3 office hours",
    "text":      "Hi, I'll be there at...",
    "sender":    "Sara Lin <sara@example.edu>",
    "url":       "https://mail.google.com/...",
    "timestamp": "Wed, 29 Apr 2026 14:21:32 -0700",
    "uid":       "1234",
}
```

## Make it yours

- **What counts as urgent** is one paragraph of `roles/triage.md`. For
  your own mail you might write: urgent means it is from your advisor,
  mentions a deadline in the next two days, or proposes a meeting time.
- **Check less often:** `gmail(poll_interval=3600, max_emails=50)`.
- **Another folder:** `gmail(folder="[Gmail]/All Mail")`.
- **Send urgent mail to your phone:** add a Slack or email sink to the
  `Rex.urgent` line; see [send-messages-outside.md](send-messages-outside.md).

## A note `dsl check` will give you

If you send urgent mail on to a sink that acts outside your computer,
such as Slack or email, `dsl check` notes that text from `inbox` can
reach it. That is true: anyone who emails you is writing to a model, and
through it to that sink. The email's whole text travels with the message,
because the triage role is an annotator: it only adds `urgency`.

If you want only a short alert to leave your computer, put an **author**
in front of that sink. An author sends new messages holding only the
fields its `out:` lists, so the email's text stops there, and the note
goes away. `roles/alert.py`:

```python
"""
---
kind: author
in: subject, sender
out: alert
---
"""


class Alert:
    def __call__(self, item):
        return [{"alert": f"Urgent: {item['subject']} (from {item['sender']})"}]
```

```
agents:
    Tri: triage
    Rex: router(on="urgency")
    Short: alert

connections:
    inbox -> Tri -> Rex
    Rex.urgent -> urgent, console_printer, Short
    Short -> phone
    Rex.routine -> later
```

(`phone: slack_sink` under `sinks:`, with `SLACK_WEBHOOK_URL` in `.env`;
see [send-messages-outside.md](send-messages-outside.md).) A subject line
is still written by whoever sent the email, but now it is the only thing
that is.
