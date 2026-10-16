# Four worked examples

Four offices from the gallery, each showing one shape. Copy any of them
with `dsl init <name> <folder>` and run it there. Each `office.md` below is
the gallery's own file, word for word (a test keeps them identical).

## 1. One item at a time, with escalation: `returns_desk`

A gate admits one ticket. A Python clerk approves small refunds and
escalates the rest; a router sends each decision on; a Python manager
decides the escalated ones. Whichever finishes the ticket tells the gate
`done`, and the next ticket is admitted.

`dissyslab/gallery/returns_desk/office.md`:

```
# returns_desk: one refund at a time; small ones approved, large ones escalated.

sources:
    tickets: file_source(path="tickets.jsonl")

sinks:
    jsonl_recorder(path="outcomes.jsonl")
    console_printer

agents:
    Gate: gate
    Clerk: clerk(limit=50)
    Rex: router(on="clerk_decision")
    Manager: manager

connections:
    tickets -> Gate -> Clerk -> Rex
    Rex.approve -> jsonl_recorder, console_printer, Gate.done
    Rex.escalate -> Manager -> jsonl_recorder, console_printer, Gate.done
```

- **Escalation is two annotators,** each adding its own decision
  (`clerk_decision`, `manager_decision`), so every outcome carries its
  audit trail.
- **The gate's `done` comes from both branches.** If one branch could end
  without reaching `Gate.done`, the gate would wait for ever, and `dsl run`
  would report it as stalled.
- No model: the roles are Python, so the office runs with no key.

## 2. Join two streams: `room_climate_monitor`

Two sensors report independently. A synchronizer joins one temperature and
one humidity reading for the same minute; a checker decides; a router
sends alerts to the screen and the rest to `discard`.

`dissyslab/gallery/room_climate_monitor/office.md`:

```
# room_climate_monitor: alert when the room is both hot and humid.

sources:
    temp_sensor: file_source(path="temp.jsonl")
    humidity_sensor: file_source(path="humidity.jsonl")

sinks:
    console_printer
    discard

agents:
    Join: synchronizer(on="slot")
    Checker: checker(max_temp=80, max_humidity=60)
    Rex: router(on="alert")

connections:
    temp_sensor -> Join.temp
    humidity_sensor -> Join.humidity
    Join -> Checker -> Rex
    Rex.yes -> console_printer
    Rex.no -> discard
```

- **The key is a design decision.** Two sensors never stamp exactly the same
  time, so the readings carry `slot`, the minute they belong to, and the
  synchronizer joins on that.
- The synchronizer's inboxes, `temp` and `humidity`, exist because the
  connections name them.
- `file_source` stands in for the real sensors. Replacing it with a source
  in `sources/` changes two declaration lines and nothing else.

## 3. Fan out, enrich, join: `situation_room_pro`

Three news feeds. A deduplicator drops repeats. Four built-in annotators
analyse each article at the same time, each adding one field; a
synchronizer joins their copies by URL; a writer turns them into a
briefing.

`dissyslab/gallery/situation_room_pro/office.md`:

```
# situation_room_pro: news from three feeds, analysed four ways at once,
# joined, and written up as briefings by a stronger model.

sources:
    bbc_world(max_articles=3)
    npr_news(max_articles=3)
    al_jazeera(max_articles=3)

sinks:
    intelligence_display(title="headline", text="summary", color="severity")
    jsonl_recorder(path="briefings.jsonl")

agents:
    Sasha: deduplicator(by="url")
    Eve: entity_extractor
    Sam: severity_classifier
    Tom: topic_tagger
    Greta: geolocator
    Sync: synchronizer(on="url")
    Riley: writer(ai="anthropic")

connections:
    bbc_world, npr_news, al_jazeera -> Sasha -> Eve, Sam, Tom, Greta
    Eve -> Sync.entities
    Sam -> Sync.severity
    Tom -> Sync.topic
    Greta -> Sync.location
    Sync -> Riley -> intelligence_display, jsonl_recorder
```

- **Every role here is built in** (`dsl roles`); the office folder has no
  `roles/`.
- The four annotators each get their own copy of the article, so they work
  in parallel. Their copies agree on every original field, which is why the
  synchronizer can merge them; each adds a field no other adds.
- The writer names its model with `ai=`; the others use the default.

## 4. A loop with a gate: `debate`

Three models answer each question. A moderator judges how far they agree.
A Python referee either finishes the question or sends it back with the
moderator's note, up to two rounds. The gate keeps one question in the loop
at a time.

`dissyslab/gallery/debate/office.md`:

```
# debate: three models answer each question; a moderator judges agreement;
# a referee sends the question back for another round or finishes it.

sources:
    problems: file_source(path="problems.jsonl")

sinks:
    answers: jsonl_recorder(path="debate_answers.jsonl")
    transcript: jsonl_recorder(path="debate_transcript.jsonl")
    panel_display

agents:
    Gate: gate
    Qwen: qwen(ai="openrouter")
    GPT: gpt(ai="openai")
    Claude: claude(ai="anthropic")
    Sync: synchronizer(on="problem_id")
    Riley: moderator
    Ref: referee(max_rounds=2)
    Rex: router(on="next")

connections:
    problems -> Gate -> Qwen, GPT, Claude
    Qwen -> Sync.qwen
    GPT -> Sync.gpt
    Claude -> Sync.claude
    Sync -> Riley -> Ref -> Rex, panel_display
    Sync -> transcript
    Rex.continue -> Qwen, GPT, Claude
    Rex.finish -> answers, Gate.done
```

- **Let the model judge and Python keep the rules.** The moderator decides
  agreement; the round limit is in `roles/referee.py`, not in any prompt.
- **A loop needs an author.** The referee builds the next round's message
  fresh; an annotator can only add to the message it was given.
- The synchronizer's key, `problem_id`, repeats every round, which is safe
  because the gate keeps one question in progress.
- If the moderator's reply does not fit its front matter, that message is
  lost, the gate is never released, and `dsl run` reports the stall with the
  path that proves it.

## Choosing a shape

| You want | Use |
|---|---|
| keep some messages, drop others | a role adding a decision, then a router (`org_news_filter`) |
| several opinions on one item | fan-out to annotators, then a synchronizer (3) |
| one item finished before the next starts | a gate (1, 4) |
| another round until a condition holds | an author that builds the next round, a router, a gate (4) |
| combine two independent streams | a synchronizer on a key both carry (2) |
| reuse an office inside another | `office(path=...)` (`org_two_office_news`) |
