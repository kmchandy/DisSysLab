# My First Office

This is your starter office. It watches Hacker News and writes a
one-sentence briefing for each story to your console.

## What's in here

```
my_first_office/
    office.md          ← the org chart: source, agent, sink
    roles/
        analyst.md     ← what the agent does, in plain English
```

## Run it

```bash
dsl run gallery/my_first_office/
```

The compiler shows you the routing and asks "Does this look right?"
Type `yes` and your office starts.

## Make it yours

**Change the focus** — edit `roles/analyst.md`. Rewrite Alex's job
for whatever audience you care about:

> "You are a Hacker News analyst. Your readers are first-year CS
> students learning Python, AI, and data science. For each story,
> write one sentence on why it matters to that audience."

**Add a source** — edit `office.md`. Add a line to Sources and a
line to Connections:

```
Sources: hacker_news(max_articles=10, poll_interval=600),
         bbc_world(max_articles=10, poll_interval=600)

Connections:
hacker_news's destination is Alex.
bbc_world's destination is Alex.        ← new line
Alex's briefing is console_printer.
```

**Add live social media** — replace `hacker_news` with `bluesky`:

```
Sources: bluesky(max_posts=None, lifetime=None)
```

BlueSky posts arrive seconds apart. Your office never sleeps.

**Run without recompiling** — after the first compile, an `app.py`
is saved here. Run it directly next time:

```bash
python3 gallery/my_first_office/app.py
```
