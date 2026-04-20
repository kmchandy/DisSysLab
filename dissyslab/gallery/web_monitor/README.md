# Web Monitor

Watches a web page for new content and summarizes anything newsworthy —
announcements, product launches, research findings, or significant updates.

## What it does

- Polls a URL every five minutes for the latest items on the page
- An analyst agent extracts the key information and decides whether each
  item is worth flagging
- Output streams to your terminal and to `web_monitor.jsonl`

## Try it

```bash
dsl init web_monitor my_web
cd my_web
dsl run .
```

## Make it yours

- Change the URL or polling interval in `office.md`:
  `Sources: web(url="https://example.com/news", poll_interval=300, max_items=3)`
- Rewrite the analyst in `roles/analyst.md` to look for specific content
  types (security advisories, release notes, price changes)
- Add a second agent that deduplicates repeated items or tracks a list
  of pages in parallel
