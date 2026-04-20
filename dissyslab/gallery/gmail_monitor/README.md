# Gmail Monitor

Monitors your Gmail inbox for important emails and summarizes each one
that needs your attention. Newsletters, promotions, and automated
notifications go to the recycle bin.

## What it does

- Polls your inbox every minute for unread messages
- An analyst agent decides whether each message is important and, if so,
  writes a one-sentence summary with the suggested action
- Output streams to your terminal and to `gmail_monitor.jsonl`

## Try it

```bash
dsl init gmail_monitor my_gmail
cd my_gmail
dsl run .
```

## Make it yours

- Change the polling interval or maximum emails in `office.md`:
  `Sources: gmail(poll_interval=60, max_emails=5, unread_only=True)`
- Rewrite the analyst in `roles/analyst.md` to fit your definition of
  "important" — work emails only, urgent threads, replies from specific
  people
- Add a second agent that drafts replies for emails that need one
