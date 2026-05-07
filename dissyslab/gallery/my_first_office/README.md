# My First Office

Your starter office. It watches Hacker News and writes a one-sentence
briefing for each story to your console.

**Tags:** hackernews, single-agent, starter

## What it does

```
hacker_news ──→  Alex  ──→  console
```

- Polls Hacker News every ten minutes for up to ten new stories
- Alex (an analyst) writes one sentence about each story
- Output streams to your terminal

## Files in this office

```
my_first_office/
    office.md          ← the org chart: source, agent, sink
    roles/
        analyst.md     ← what the agent does, in plain English
```

## Try it

```bash
dsl init my_first_office my_first_office
cd my_first_office
dsl run .
```

The compiler shows you the routing and asks "Does this look right?"
Type `yes` and your office starts.

### What each word means

- `dsl` — the command-line tool installed by `pip install dissyslab`.
- `init my_first_office my_first_office` — copies the `my_first_office`
  office out of the shipped gallery into a folder of the same name in
  your current directory. The first name is the office to copy; the
  second is whatever folder name you want on disk.
- `cd my_first_office` — move into that folder. `office.md` and
  `roles/analyst.md` are now sitting there for you to read and edit.
- `dsl run .` — build and run the office described in the current
  directory. The `.` means "right here".

This same three-step pattern works for every office in the gallery.

## Make it yours

**Change the focus.** Edit `roles/analyst.md`. Rewrite Alex's job for
whatever audience you care about:

> "You are a Hacker News analyst. Your readers are first-year CS
> students learning Python, AI, and data science. For each story,
> write one sentence on why it matters to that audience."

**Add a source.** Edit `office.md`. Add a line to Sources and a
line to Connections:

```
Sources: hacker_news(max_articles=10, poll_interval=600),
         bbc_world(max_articles=10, poll_interval=600)

Connections:
hacker_news's destination is Alex.
bbc_world's destination is Alex.        ← new line
Alex's briefing is console_printer.
```

**Add live social media.** Replace `hacker_news` with `bluesky`:

```
Sources: bluesky(max_posts=None, lifetime=None)
```

BlueSky posts arrive seconds apart. Your office never sleeps.

**Run without recompiling.** After the first `dsl run`, the
generated artifact lives at `build/run.py`. You can run it
directly without going through the `dsl` command:

```bash
python3 build/run.py
```

`dsl run` will rebuild `build/run.py` automatically when any
source file (`office.md`, `roles_lib/*`, `roles/*`) is newer
than the artifact, so editing a prompt and re-running picks
up the change without you doing anything.

**More to swap in.** See [`docs/SOURCES_AND_SINKS.md`](https://github.com/kmchandy/DisSysLab/blob/main/docs/SOURCES_AND_SINKS.md)
for the full list of sources and sinks shipped with the framework.

**Recipe.** [How to add a new RSS source](https://github.com/kmchandy/DisSysLab/blob/main/docs/recipes/add-an-rss-source.md)
walks through swapping the shipped feed for another one, or
registering a brand-new feed by name.

---

## The role

Alex's job description, in plain English:

```
# Role: analyst

You are a Hacker News analyst. For each story you receive, write
one crisp sentence describing what it's about and why someone
learning software might care.

Send to briefing.
```

## The org chart

The whole office, in one file:

```
# Office: my_first_office

Sources: hacker_news(max_articles=10, poll_interval=600)
Sinks: console_printer

Agents:
Alex is an analyst.

Connections:
hacker_news's destination is Alex.
Alex's briefing is console_printer.
```

## What you built

Alex runs in their own thread. Hacker News stories arrive every ten
minutes; Alex briefs each one as it comes in. This is a distributed
system — one agent, running continuously, processing a live data
stream. The next examples scale it up: more agents, more sources,
feedback loops, offices wired into networks.
