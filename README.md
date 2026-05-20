# DisSysLab

[![PyPI](https://img.shields.io/pypi/v/dissyslab)](https://pypi.org/project/dissyslab/)
[![Python](https://img.shields.io/pypi/pyversions/dissyslab)](https://pypi.org/project/dissyslab/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**Use English to build offices staffed by multiple agents that work for you continuously.**
A chatbot answers when you ask; but your office of agents works for you 
nonstop monitoring sources, filtering, analyzing, and pushing results to
your apps and devices.

**Mix and match agents that best fit your accuracy, task, budget, and privacy needs.**
An office can mix different types of agents: paid AI services such as Anthropic and OpenAI, ; free local AI such as Qwen on Ollama for roles where cost and privacy matter more than accuracy; task-specific small models; and Python functions. 

**Construct agent networks of arbitrary complexity ideal for your application.**
The network of agents in an office is specified by an org chart.
Different applications need different types of org charts.
Some are pipelines; some fan out to parallel agents;
some branch on conditions; some loop.
Build an office with the agent network ideal for your application.

**Notes**

The demos in this website terminate execution after processing
a fixed amount of data to limit bills for hosted AI. You can execute
apps forever by using free AI on your laptop or by specifying app
parameters based on cost constraints. 


My hypothesis is that offices for most apps can be specified in English; 
however, some offices may require users to write agents in Python. I hope
that the libraries in this framework are extensive enough that users will 
rarely need to write Python.

---

## Try it

This demo needs no API key and no model
download. [`periodic_brief`](dissyslab/gallery/apps/periodic_brief/)
pulls news, weather, and a few stock tickers and renders them into a
single, styled HTML page. It runs in a few seconds.

**One-line install** (macOS or Linux, requires Python 3.10+):

```bash
curl -sSf https://raw.githubusercontent.com/kmchandy/DisSysLab/main/install.sh | bash
```

The installer asks one question: which AI engine do you want?

- **Ollama** — free, local, private. Downloads a ~19 GB model
  (Qwen3) one time, takes 20–40 minutes. After that, $0 forever
  but slow: 15–60 min per office run on a typical Mac.
- **OpenRouter** — hosted Qwen-2.5-7B. Paste an API key from
  <https://openrouter.ai/keys>. A few cents covers a week of runs.
  Office runs finish in 1–5 minutes.
- **Claude** — Anthropic's hosted model. Paste an Anthropic key.
  Highest-quality output, ~25–50¢ per office run.

  **Note**: These costs are estimates. Check costs before running.

Pick an AI engine that fits. You can switch later by editing one line in
your shell rc file.

**Then: open a new terminal** (or run `source ~/.zshrc` on macOS /
`source ~/.bashrc` on Linux) so the new PATH takes effect.

**Now run your first office:**

```bash
dsl run periodic_brief
open brief.html
```

In 10 to 20 seconds you'll see a single HTML page with three news
headlines from BBC, three from NPR, current weather for Pasadena,
and three stock tickers.

To make your own editable copy of `periodic_brief` execute
```bash
dsl init periodic_brief my_brief
```
 You can then execute the office from your local folder by
 executing:

```bash
cd my_brief
dsl run .
```

`dsl list` shows offices that ship with DisSysLab.

## Your situation_room

First run `periodic_brief` and see it running end to end.
Then build your own situation room by running and then
modifying [`situation_room`](dissyslab/gallery/apps/situation_room/).
Three news feeds in. One intelligence digest out: articles deduplicated,
severity-classified, entity-extracted, topic-tagged, and geolocated.
Roles specified in English job descriptions.

```bash
dsl run situation_room
```

Speed and cost depend on the engine you picked at install time:

| Engine | Wall time per run | Cost per run |
|---|---|---|
| Ollama (local Qwen) | 15–30 min on a 32 GB Mac | $0 |
| OpenRouter (Qwen-2.5-7B) | 1–5 min, any laptop | pennies |
| Claude | 1–3 min, any laptop | tens of cents |

> *Numbers above are estimates and will drift as providers update
> prices. Check the provider's pricing page before relying on any
> specific figure. You specify the agent types in your office;
> the actual bill is between you and the providers of the services
> that the office uses.*

**About cost safety.** Every office in the gallery stops after a
few polling cycles by default — long enough to see a result,
short enough that you won't get a large bill. Set
`max_articles=N` and `max_readings=N` parameters in each office's
`office.md` to control execution. Remove these only when you want
your office to run continuously.

You should see a digest like
[this sample](dev/experiments/situation_room_sample_day_1.md):

```markdown
## [CRITICAL] Lebanon reports 39 killed in Israeli strikes

*politics · Lebanon · middle_east*

Lebanon reports that Israeli strikes killed 39 people. Fighting
continues between Israel and Hezbollah despite a ceasefire deal
announced last month.

[bbc_world](https://www.bbc.com/news/...)
```

---

## Make it yours

Change the roles, agents and org chart in
[`office.md`](dissyslab/gallery/apps/situation_room/office.md)
to fit your needs.
You may want to change one of the following:

**1. Sources** — swap a news feed for Gmail or a webhook; add or
remove a source entirely.

**2. Parallel thinkers** — add, remove, or replace the agents that
extract entities, severity, topic, location. Each one annotates
the message with one more fact.

**3. Writer** — change the prompt to produce a different style of
briefing: executive summary, technical alert, blog draft, customer
email.

**4. Sinks** — change where the result goes: terminal, markdown file,
or Slack channel.



## Examples of steps you may want to try

**Change parameters.** Bump article counts, swap a
feed, set a polling interval.

```
Sources: techcrunch(max_articles=10, poll_interval=600)
```

**Swap and add components.** Replace the terminal
display with a markdown file or add a topic filter agent.

```
Sinks: markdown_digest(path="~/digest.md")
```

**Write new job descriptions.** Describe new roles for your specific app.
See [`docs/BUILD_APPS.md`](docs/BUILD_APPS.md).

A worked example of the third tier — overriding *one* role to use
Claude while everything else stays on a cheap open model — is at
[`situation_room_pro`](dissyslab/gallery/apps/situation_room_pro/).
One file's difference.

---

## What's an office?

An office is a team of AI agents with **roles**, connected by an
**org chart**. You write each role in plain English — the same way
you'd describe a job to a new hire — and you write the org chart in
plain English too. The framework compiles your description into a
running concurrent system.

This is a very brief overview of how you specify offices. 
We describe specifics elsewhere.
Here's `situation_room`'s wiring (excerpted from
[`office.md`](dissyslab/gallery/apps/situation_room/office.md)):

```
Sources: bbc_world(max_articles=5), npr_news(max_articles=5),
         al_jazeera(max_articles=5)
Sinks: intelligence_display, jsonl_recorder_briefing(...)

Agents:
Sasha is a deduplicator(by="url").
Eve is an entity_extractor.
Sam is a severity_classifier.
Tom is a topic_tagger.
Greta is a geolocator.
Sync is a synchronizer.
Riley is a writer.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
al_jazeera's destination is Sasha.

Sasha's out is Eve, Sam, Tom, Greta.

Eve's out is Sync's entities.
Sam's out is Sync's severity.
Tom's out is Sync's topic.
Greta's out is Sync's location.

Sync's out is Riley.
Riley's out is intelligence_display, jsonl_recorder_briefing.
```

## The network of agents in the situation_room office
```
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ bbc_news │ │ npr_news │ │  al_jaz  │
        └────┬─────┘ └────┬─────┘ └────┬─────┘
             └────────────┼────────────┘
                          ▼         ← Asynchronous merge
                  ┌───────────────┐
                  │    Sasha      |
                  | deduplicator  │
                  └───────┬───────┘
                          ▼ broadcast 
      ┌─────────────┌─────────┐────────----──┐
      ▼             ▼           ▼            ▼
 ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
 │   Eve    | |    Sam   | |    Tom   | |  Greta   |
 | extract  | |determine | |  topic   | |determine |
 |entities  │ │ severity │ | tagger   | |location  |     
 └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
      ▼            ▼            ▼            ▼             ← Synchronous merge 
  ┌───────----------------------------------────────┐
  │                     Sync                        │
  │                 synchronizer                    │               
  └─────----------------──┬─────------------------──┘
                          ▼
                  ┌───────────────┐
                  │    Riley      │
                  │    writer     │ 
                  └───────┬───────┘
                          ▼
                      ┬───────┬
                publish     revise/discard
                      ▼          ▼
               ┌──────────┐ ┌──────────┐        
               │ display  │ │ archiv   │
               └──────────┘ └──────────┘
```

The office monitors the feeds listed as `Sources`.
The office output is displayed in the console as `intelligence_display` and
stored to a file `jsonl_recorder_briefing` as specified in `Sinks`.
The office has agents called Eve, Sam, Tom, Greta, Sync, and Riley.
The roles of agents in the office are deduplicator, entity_extractor, 
severity_classifier, topic_tagger, geo_locator, synchronizer, and
writer. 

**Connections** specifies the org chart or how information flows in the
office. The line `Eve is an entity_extractor` specifies that the agent
called `Eve` has the `entity_extractor` role.
In this office each role is filled by exactly one agent. 
In other offices, there may be multiple agents with the same role;
for example there may be an agent that identifies topics in news sources
and a different agent that identifies topics in competitors' websites,
and both agents may have the same job description.

An agent can have multiple inboxes in which incoming messages are placed
and multiple outboxes in which the agent places its outgoing messages.
The framework sends messages from outboxes to inboxes as specified in
`Connections`. Most agents have a single inbox called **in** and a single
outbox called **out**. A synchronizer can have multiple inboxes.

The line `Sasha's out is Eve, Sam, Tom, Greta.` says that messages from
Sasha's outbox are broadcast to the inboxes of Eve, Sam, Tom and Greta. 
Messages from multiple outboxes can feed the same inbox. For example,
messages from the three sources feed Sasha's inbox. The delay between
a message appearing in an outbox and its delivery to its connected inbox
is arbitrary. Performance issues are described later.

## Example of a role
Specify a role -- it's job description -- with sufficient detail 
that agents in the role do what you want them to do. Here is an example of
a job description for topic taggers

```
# Role: topic_tagger

You read one news article at a time and assign it to one of
a fixed set of topic categories.

Input shape. Each article is a JSON object with these keys:

- "source"    — name of the feed (string)
- "title"     — headline (string)
- "text"      — article body (string)
- "url"       — link to the article (string)
- "timestamp" — publication time (string)

Your job. Add one new field, "topic", whose value is one of
exactly these eight strings:

- "politics"      — government, elections, diplomacy, war.
- "business"      — markets, companies, industry, trade.
- "technology"    — software, hardware, AI, internet, science
  applied to commerce or daily life.
- "science"       — research findings in physics, biology,
  medicine, climate, space — when not tied to a product.
- "health"        — public health, medicine, healthcare
  policy, pandemics.
- "sports"        — competitive athletics and games.
- "entertainment" — film, TV, music, celebrity, gaming.
- "other"         — anything that does not clearly fit one of
  the seven above. Use this when you would have to guess.

Preserve every existing field exactly; only add the new
"topic" field.

Rules:

- Pick exactly one topic per article. Do not output a list.
- Use the exact spelling above (lowercase).
- When in doubt, prefer "other" rather than guessing.

Always send to out.

Output. Return a single JSON object that includes every
field of the input plus the new "topic" field, plus a
"send_to" field whose value is "out". Do not include
explanations, markdown code fences, or any text outside the
JSON object.

Example.

Input:

{"source": "techcrunch", "title": "AI startup raises $50M to automate code review", "text": "Series B funding led by Sequoia values the company at $400M...", "url": "https://techcrunch.com/2026/04/15/ai-startup", "timestamp": "2026-04-15T10:00:00Z"}

Output:

{"source": "techcrunch", "title": "AI startup raises $50M to automate code review", "text": "Series B funding led by Sequoia values the company at $400M...", "url": "https://techcrunch.com/2026/04/15/ai-startup", "timestamp": "2026-04-15T10:00:00Z", "topic": "technology", "send_to": "out"}
```



---

## Apps and examples

Modify examples of offices in the [`gallery`](dissyslab/gallery/).

- **[`gallery/apps/`](dissyslab/gallery/apps/)** — ready-to-run
  offices, organised by whether they need an API key.
  - [`periodic_brief`](dissyslab/gallery/apps/periodic_brief/) —
    no-key, no-LLM HTML brief: news + weather + tickers. The
    ten-second demo.
  - [`situation_room`](dissyslab/gallery/apps/situation_room/) —
    the headline office: three news feeds → intelligence digest.
    Nine plain-English agents in sense → think → respond.
  - [`situation_room_pro`](dissyslab/gallery/apps/situation_room_pro/)
    — same office, Claude as the writer for top quality,
    open-weight Qwen everywhere else.
  - See [`gallery/README.md`](dissyslab/gallery/README.md) for the
    full menu (inbox triage, ticket router, competitor watch, lead
    qualifier, new-grad jobs, etc.).

- **[`gallery/examples/`](dissyslab/gallery/examples/)** — smaller
  tech demos showing patterns (sub-offices, custom roles, custom
  sinks). Useful when you start writing your own offices.

`dsl list` from the terminal groups every office by section.

---


## Documentation

Running offices:

- **[`gallery/README.md`](dissyslab/gallery/README.md)** — the full
  app catalog, split into "runs on any laptop with no keys" and
  "shines on a hosted backend".
- **[`situation_room/README.md`](dissyslab/gallery/apps/situation_room/README.md)**
  — what the office does, what's in its office.md line by line, and
  the three-tier staircase for making it yours.
- **[Sample digest](dev/experiments/situation_room_sample_day_1.md)**
  — what a real morning's output looks like.

Building new offices:

- **[`docs/BUILD_APPS.md`](docs/BUILD_APPS.md)** — design and wire
  your own office, from idea to running system.
- **[`docs/LANGUAGE_MODELS.md`](docs/LANGUAGE_MODELS.md)** —
  switching, comparing, and mixing backends.
- **[`docs/SOURCES_AND_SINKS.md`](docs/SOURCES_AND_SINKS.md)** —
  every source and sink component the framework ships with.
- **[`docs/recipes/`](docs/recipes/)** — short copy-pasteable
  patterns for common tasks.
- **[`docs/MAKE_OFFICE.md`](docs/MAKE_OFFICE.md)** — the
  programmatic path: construct an office from Python.

Extending the framework:

- **[`dev/PROMPTING_FOR_SLMS.md`](dev/PROMPTING_FOR_SLMS.md)** — the
  role-decomposition pattern that makes small models reliable.

---

## Manual install (without the shell installer)

If you'd rather not run a `curl | bash`:

```bash
# 1. Install DisSysLab
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install dissyslab

# 2. Try periodic_brief now — no model, no key, just runs
dsl run periodic_brief
open brief.html
```

That gives you a working office in under a minute. To unlock the
heavier offices (`situation_room`, `inbox_triage`, etc.) pick an
engine and configure it:

```bash
# Option A: local, free, slow. ~19 GB one-time model download.
# Install Ollama from https://ollama.com/download, then:
ollama pull qwen3:30b
export DSL_BACKEND=ollama

# Option B: hosted Qwen-2.5-7B via OpenRouter. Pennies per run.
export DSL_BACKEND=openrouter
export OPENROUTER_API_KEY=sk-or-v1-...
export OPENROUTER_MODEL=qwen/qwen-2.5-7b-instruct

# Option C: Claude. ~25–50¢ per run, highest quality.
export DSL_BACKEND=claude
export ANTHROPIC_API_KEY=sk-ant-...

# Then run any office in the gallery
dsl run situation_room
```

Same result as the shell installer. Read each step before running it.

---

## Also: A Python Distributed Systems Framework for Teaching

DisSysLab is used in an introductory undergraduate class on distributed
systems. English job descriptions and org charts are compiled
to a Python famework of agents that can be run in threads or in
processes. Students work with both natural lanuage and Python to
build apps for their own personal interests. Then they learn 
algorithms used in distributed systems and investigate concurrency
concepts. 
See [`docs/MAKE_OFFICE.md`](docs/MAKE_OFFICE.md).

---

## Requirements

- macOS or Linux. Windows works for the core framework, but the
  shell installer assumes a Unix-like environment.
- Python 3.10 or newer.
- For running `situation_room` locally on Ollama: a Mac with 32 GB
  RAM (or comparable PC) and ~20 GB free disk. Smaller machines
  can still run the lighter offices or point `DSL_BACKEND` at
  OpenRouter or another hosted backend.

---

## License

MIT — see [LICENSE](LICENSE).

---