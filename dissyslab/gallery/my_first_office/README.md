# My First Office

This is your starter office. It monitors Hacker News, filters for
interesting articles, and summarizes each one in a single sentence.

## What's in here

```
my_first_office/
    office.md          ← the org chart: sources, agents, connections
    roles/
        analyst.md     ← decides what's worth reading
        editor.md      ← rewrites each article as one sentence
```

## Run it

```bash
dsl run gallery/my_first_office/
```

The compiler shows you the routing and asks "Does this look right?"
Type `yes` and your office starts.

## Make it yours

**Change the topic** — edit `roles/analyst.md`. Replace "worth reading"
with whatever you care about:

> "Your job is to decide if each item is about Python, machine learning,
> or open source software."

> "Your job is to decide if each item is about climate change,
> renewable energy, or environmental policy."

**Add a source** — edit `office.md`. Add a line to Sources and a
line to Connections:

```
Sources: hacker_news(max_articles=10, poll_interval=600),
         bbc_world(max_articles=10, poll_interval=600)

Connections:
hacker_news's destination is Alex.
bbc_world's destination is Alex.        ← new line
...
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