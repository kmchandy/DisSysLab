# Build an office out of offices

**Goal.** Use a whole office as one agent of a bigger office. Each office
stays small enough to check and test on its own, and the bigger one is
just a few connections between them.

Needs: an Anthropic key and an internet connection, for the example.

## 1. The example

```bash
dsl init org_two_office_news two
cd two
ls -R
```

```
.:
README.md
news_editor
news_monitor
office.md

./news_editor:
office.md

./news_monitor:
office.md
roles

./news_monitor/roles:
topic_filter.md
```

Two offices live in their own folders inside the outer one.
`news_monitor` keeps articles on a topic; `news_editor` writes one
sentence about each. The outer `office.md` connects them:

```
sources:
    al_jazeera(max_articles=5)
    bbc_world(max_articles=5)

sinks:
    intelligence_display(title="title", text="summary")

agents:
    monitor: office(path="news_monitor")
    editor: office(path="news_editor")

connections:
    al_jazeera, bbc_world -> monitor.articles
    monitor.kept -> editor.articles
    editor.briefings -> intelligence_display
```

`monitor: office(path="news_monitor")` makes the office in that folder an
agent called `monitor`.

## 2. An office's ports: `inputs:` and `outputs:`

An office meant to sit inside another names its ports.
`news_monitor/office.md`:

```
inputs:
    articles

outputs:
    kept

sinks:
    discard

agents:
    Felix: topic_filter
    Rex: router(on="on_topic")

connections:
    articles -> Felix -> Rex
    Rex.yes -> kept
    Rex.no -> discard
```

- **Inside**, an input acts as a source (`articles -> Felix`) and an
  output as a sink (`Rex.yes -> kept`).
- **Outside**, they are the agent's ports, written with a dot:
  `bbc_world -> monitor.articles`, `monitor.kept -> editor.articles`.

Ports always have names, like a function's parameters: an office is
used by someone who did not write it, and `monitor.kept` says what comes
out.

## 3. Check and run

```bash
dsl check .
dsl draw .
dsl run .
```

`dsl check` checks the inner offices too. A port that does not exist is
reported with the ones that do:

```
two/office.md:
  problem: line 16: office monitor's outputs are kept; write monitor.<output> -> editor.articles. See `dsl grammar`, Nested offices.
```

An inner office cannot be run by itself (it has inputs nothing feeds);
run the outer one.

## 4. Make your own

Turn the inbox sorter ([GETTING_STARTED.md](../GETTING_STARTED.md),
part 6) into a part:

1. Make a folder `course_desk` with a subfolder `sorter`.
2. Copy `office.md` and `roles/` from your inbox sorter into `sorter/`.
3. In `sorter/office.md`, replace the source with an input, and the
   files with outputs:

   ```
   inputs:
       messages

   outputs:
       urgent
       later

   agents:
       Tri: triage
       Rex: router(on="urgency")

   connections:
       messages -> Tri -> Rex
       Rex.urgent -> urgent
       Rex.routine -> later
   ```

4. In `course_desk/office.md`, feed it and use its outputs:

   ```
   sources:
       inbox: file_source(path="messages.jsonl")

   sinks:
       console_printer
       later: jsonl_recorder(path="later.jsonl")

   agents:
       sort: office(path="sorter")

   connections:
       inbox -> sort.messages
       sort.urgent -> console_printer
       sort.later -> later
   ```

5. Copy `messages.jsonl` into `course_desk`, then `dsl check .` and
   `dsl run .` from `course_desk`.

The sorter can now be dropped into any office that has messages to sort.
