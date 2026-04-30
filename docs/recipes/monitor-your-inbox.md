# How to monitor your inbox

**Goal.** An office that watches your Gmail inbox and only
surfaces the emails that matter — meeting requests, replies from
your advisor, urgent threads — and lets newsletters and
notifications drop into a file you can spot-check later.

## Run a working example

DisSysLab ships with a one-agent inbox-monitor office. Try it:

```bash
dsl init gmail_monitor my_inbox
cd my_inbox
dsl run .
```

Important emails stream to your terminal with a one-sentence
summary and a suggested action; everything else lands in
`gmail_monitor.jsonl`. Press `Ctrl+C` to stop.

The first time you run it, you'll need to set up Gmail
credentials — see the next section.

## One-time Gmail setup

Gmail uses an **app password** — a 16-character string you
generate once in your Google account settings. No OAuth, no
Google Cloud project, nothing to configure beyond two
environment variables.

1. Go to `myaccount.google.com` → Security → enable **2-Step
   Verification** (required to generate app passwords).
2. Same page → **App passwords** → generate a new password for
   "Mail".
3. In the shell where you'll run `dsl run`, set:

```bash
export GMAIL_USER='you@gmail.com'
export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'
```

You only do this once per machine. Add the two `export` lines to
your shell profile (`~/.zshrc`, `~/.bashrc`) so they're set every
time you open a terminal.

## Change what counts as "important"

Open `roles/analyst.md`. The criteria are at the top:

```
You are an email analyst who receives emails from Gmail.

Your job is to decide if each email is important and worth
summarizing — something that requires attention or action, as
opposed to newsletters, promotions, or automated notifications.
```

Rewrite it for whatever you care about. Two examples:

```
Your job is to forward only emails from my advisor or that
mention deadlines I haven't yet acknowledged. Send everything
else to discard.
```

```
Your job is to keep emails that contain a meeting request — a
proposed time, a calendar invite, or "are you free…". Send
everything else to discard.
```

Save and run `dsl run .` again. No rebuild — just edit and re-run.

## The pattern, in a sentence

The Gmail source polls your inbox on a schedule and yields one
message per email. An analyst agent decides which mailbox each
email goes to (`summary` for the keepers, `discard` for the
rest). The org chart in `office.md` wires those mailboxes to
sinks — terminal, file, email, Slack, anything from
[the sinks reference](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md).

## What each email looks like

The Gmail source emits the standard DisSysLab message shape, plus
a few Gmail-specific extras:

```python
{
    "source":    "gmail",
    "title":     "Re: PS3 office hours",      # email subject
    "text":      "Hi Mani, I'll be there...", # body
    "url":       "https://mail.google.com/mail/u/0/#search/rfc822msgid:...",
    "timestamp": "Wed, 29 Apr 2026 14:21:32 -0700",
    # Gmail extras:
    "subject":   "Re: PS3 office hours",
    "sender":    "Sara Lin <sara@example.edu>",
    "uid":       "1234",
}
```

Because `title` and `url` are present, role files written for
RSS feeds work unchanged on Gmail — a filter that says "decide
based on the title" filters on the email subject.

## Variations

**Poll less often.** Default is every 60 seconds. For a
once-a-morning summary, set `poll_interval=3600` (1 hour) or
larger:

```
Sources: gmail(poll_interval=3600, max_emails=50, unread_only=True)
```

**Watch a different folder.** Pass a folder name — the Gmail
source goes through IMAP, so labels behave like folders:

```
Sources: gmail(folder="[Gmail]/All Mail", poll_interval=300)
```

**Pipe importants to your phone.** Replace `console_printer`
with `slack_sink` (or `gmail_sink` to email-yourself the
distilled version). See
[How to send messages to the outside world](send-messages-outside.md).

**Two filters in series.** First filter on sender (only emails
from a list of people), then filter on content (only the ones
asking a question). Each filter is its own agent with its own
role file.

## See also

- [Sources and sinks reference](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
  — full Gmail source argument list, plus every sink you can
  route important emails to.
- [`gmail_monitor` in the gallery](https://github.com/kmchandy/DisSysLab/tree/main/dissyslab/gallery/gmail_monitor)
  — the working example used in this recipe.
- [How to filter for a topic](filter-for-a-topic.md) — same
  pattern applied to news feeds.
- [How to write a custom role](write-a-custom-role.md) —
  design the analyst agent that decides what counts as
  important.
- [How to send messages to the outside world](send-messages-outside.md)
  — route the keepers to email, Slack, or a file.
