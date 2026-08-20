# Start here

**Distributed systems, January 4 – March 10, 2027**

You will build a system that watches something you care about and reacts to
it — and then you will take the floor apart and study what holds it up.

That order matters. Most courses in this subject give you the algorithms first
and ask you to believe they are useful. Here you build something that works in
the first week, and the algorithms arrive later as answers to questions your
own program has already raised: *how does it know it has finished? what
happens if it crashes halfway? how would I tell "still working" from "stuck
forever"?*

You need to know some Python. You do not need to know anything about
distributed systems, concurrency, or parallel programming. That is what the
course is for.

---

## 1. What you are building

An **office**: a network of agents, each with one job, that runs continuously.

- **Sources** fetch from the world — a news feed, a weather service, a folder
  of photos, a webhook, your inbox.
- **Agents** transform the stream — filter, classify, extract, summarise,
  compute.
- **Sinks** act — write a file, print, post, send.

You describe the office in English. An AI agent assembles it from a tested
library rather than writing the concurrency machinery from scratch. The
machinery — passing messages between agents, knowing when the whole office has
finished, saving state so it can resume after a crash — is the part that is
genuinely hard to get right, and it is already written and tested. You are
composing, not re-deriving.

---

## 2. Setting up (do this before the first class)

Everything below is done by talking to **Cowork** (the Claude desktop app).
The full walkthrough is [`SETUP.md`](SETUP.md), next to this file; here is
the short version.

**Choose "on your computer," not "in the cloud,"** when you start a task in
Cowork. A cloud task runs on a machine that is thrown away afterwards, so the
work you do today would not be there tomorrow.

Then say:

> Install the Python package `dissyslab` for me, then run `dsl list` and show
> me what offices come with it.

Then see one work:

> Make me my own copy of the `periodic_brief` office in a folder called
> `my_brief`, then run it and open the result.

Ten to twenty seconds later you have an HTML page with real news and real
weather. **No API key, no account, no model download, and nothing to install
beyond `dissyslab` itself.** If anything goes wrong, say *"run `dsl doctor`
and tell me what it says."*

(Stock prices are one line away — `stocks(ticker="AAPL")` — but they need
`pip install "dissyslab[market]"` first, because market data comes from
Yahoo and every user fetches their own. Not needed for anything in this
course unless you choose a markets project.)

You are set up. Bring a laptop that does this to the first class.

---

## 3. Getting the skill

A **skill** is a folder of instructions that teaches your AI agent how to do
something specific — here, how to build offices correctly. Without it your
agent will improvise, and improvised concurrency is exactly what this course
is trying to spare you.

There are two ways to give it to your agent. Try the first; if anything about
it is unclear, the second always works.

**Either — install the bundle.** Download
[`office-builder.skill`](../skills/office-builder.skill) from the repository
and add it to Cowork as a skill. Your agent then picks it up automatically
whenever you ask for something that sounds like an office.

**Or — point your agent at it.** Clone the repository (you will want it anyway
for the examples) and say:

> Clone https://github.com/kmchandy/DisSysLab. Read
> `skills/office-builder/SKILL.md` and its `references/` folder, and follow it
> when you build offices for me.

**Then check it took — and check properly.** Installing a skill can fail
quietly: the button reports success, or offers to update again, and the old
version stays loaded. Ask your agent:

> Does your office-builder skill list the roles that ship with dissyslab, and
> what does it say to do if `dsl check` is missing from my installed version?

You want **both** halves. It should name roles like `relevance_filter` and
`synchronizer` and say there are nineteen; and it should say to report the
missing command and carry on **without patching your installation**. If you
get only vague agreement, or an answer to one half, it has an old version or
none. Remove the skill and add it again, or use the clone route above.

Ask something only the current skill knows. "What does `dsl check` do?" is a
bad test — every version answers that, so it tells you a skill is loaded, not
which one.

*Building sensing offices — classifying photos, recordings, or sensor
readings? Also add [`sensor-office-builder.skill`](../skills/sensor-office-builder.skill).*

---

## 4. How to work with the skill

The `office-builder` skill teaches your AI agent how offices are built. You do
not read it — you talk, and it does the assembling. What is worth knowing is
what to say.

**To build something new**, describe what you want watched and what should
happen:

> I want an office that checks the campus events page every hour, keeps only
> the events about music, and writes them to a file.

**To change something**, say what should be different:

> Add a second source for the student newspaper.
> Make the filter also keep anything mentioning free food.
> Send the output to a JSONL file as well as the display.

**To check it before running it:**

> Run `dsl check` on my office.

Do this every time. If your agent tells you `dsl check` is not in your
installed version, that is expected and not your fault — it is newer than the
last release. Ask it to carry on without the check, or to install the current
version from GitHub. **Do not let it "fix" your installation by editing the
installed package**; that gives you a copy of the tool nobody else has, and
problems nobody else can reproduce. It reads your org chart and reports every structural
problem at once — an agent nothing can reach, work that reaches no sink, a
sink nothing feeds, a port nothing writes to. It takes a second and it saves
afternoons.

**When it misbehaves:**

> My office hangs — help me work out which agent is waiting and what for.
> My office ran but produced nothing.

### Read what it wrote

This is the part students skip and should not. Open `office.md`. It is not
code — it is four sections of English:

```
Sources: bbc_world(max_articles=5), npr_news(max_articles=5)
Sinks: brief_html

Agents:
Sasha is a deduplicator(by="url").
Riley is a writer.

Connections:
bbc_world's destination is Sasha.
npr_news's destination is Sasha.
Sasha's out is Riley.
Riley's out is brief_html.
```

You should be able to follow that. If you cannot follow what the agent built
for you, say so and ask it to explain or simplify — an office you do not
understand is not yours, and this course grades what you understand.

Each agent's job lives in `roles/<name>.md` (English, run by a language model)
or `roles/<name>.py` (Python, exact and free). Use English when the job needs
judgment. Use Python when the job is exact — a threshold, an average, a
deduplication. Python roles cost nothing per message; English roles call a
model every time.

### Writing `office.md` yourself

You never have to. But reading one is how you check the agent's work, and by
the end of the course you should be able to write one without help — that is
most of what "you understand your own office" means.

**[`docs/BUILD_APPS.md`](../docs/BUILD_APPS.md)** has the full grammar, the
component catalogue and worked examples. Reach for it when the agent has built
something and you want to know why it wired it that way.

---

## 5. The catalogue — every example that ships

About forty, and they all run. `dsl list` is the authority — if this page and
`dsl list` disagree, believe `dsl list`. Read the ones near what you want to build, copy the shape, and
change it. Copying a working shape beats composing from scratch.

`dsl list` shows them all. To take one:

```
dsl init <name> <your_folder_name>
```

Always make a copy. Never edit a shipped office in place.

### Start here — the four teaching shapes

| Example | Shape | Why it is worth reading |
|---|---|---|
| **`my_first_office`** | one source, one agent, one sink | The smallest complete office. Watches Hacker News, writes a sentence. |
| **`periodic_brief`** | many sources → one sink, no agents | The simplest useful thing. No LLM, no key, runs in seconds. |
| **`situation_room`** | fan-out → four enrichers → synchroniser → writer | The workhorse. Three feeds, four parallel judgments, recombined. Has *no role files at all* — the whole application is one file. |
| **`debate`** | a loop with a gate | Three models argue until they agree. Shows why cycles need something to stop them. |

### Watching the world

`situation_room` · `situation_room_pro` · `situation_room_requests` — news
into a briefing, at three levels of ambition
`competitor_watch` — tech news filtered for mentions of named companies
`arxiv_radar` — new papers in five CS categories, rated
`web_monitor` — one page, watched for new content
`org_news_filter` · `org_news_editorial` · `org_intelligence_briefing` ·
`org_situation_room` — small two-agent versions of the above, good for reading

### Your own day

`periodic_brief` · `periodic_brief_pro` — one morning page: news, weather,
tickers
`weather_monitor` — a short weather briefing on a schedule
`wardrobe_assistant` — calendar + weather → what to wear
`inbox_triage` · `gmail_monitor` — unread email, rated and summarised *(needs
Gmail credentials)*

### Money and markets

`stocks_monitor` — one ticker, in plain English, every few minutes
`kalshi_market_watch` — prediction markets, polled and briefed
`investment_club` · `trading_room` · `returns_desk` — multi-agent takes on the
same territory

### Work and operations

`job_hunter` — four job feeds → screen → match → tailored materials
`new_grad_jobs` — the monthly "Who's Hiring" thread, filtered
`lead_qualifier` — form submissions, scored *(webhook)*
`ticket_router` — support tickets, classified and routed *(webhook)*
`shipment_release` — a release-gate pipeline
`webhook_listener` — the bare pattern behind the three above

### The physical world

`room_climate_monitor` — temperature and humidity, with alerting
`salton_sea_dashboard` — a real environmental monitoring demo (H₂S and wind)
`loudness_monitor` — an audio stream, thresholded — *no model needed, just a
moving average*
`backyard_birds` — bird species from recordings *(needs `birdnetlib`)*
`wildlife_watcher` — animals in camera-trap photos *(needs `torch`)*

### Learning and argument

`debate` — three models, a moderator, and a gate
`adaptive_tutor` — a tutor that adapts to one learner

### Looking under the floor

`recovery_demo` — estimates π by Monte Carlo, and demonstrates
**distributed snapshot checkpoint-recovery**. We will come back to this one in
detail; it is the course's central algorithm running in about forty lines.

### Longer projects, if you want one

`mac_speed_suite` — describe a trading strategy in English; it implements it,
tests it against history, stress-tests it, and ranks the results
`paper_trader` — runs a strategy forward on live prices, on paper, never a
real order

These two have their own skills and their own libraries. They are more than a
first project, but they are there if markets are your thing. **They need the
repository cloned** — both read ten years of price CSVs that do not travel in
the installed package.

---

## 6. Choosing your project

You will build one office of your own and keep improving it all term. Choose
by this test: **is it something you would actually check?**

Good signs — you keep a browser tab open on it; you check a price, a deadline,
a forum, a forecast by hand; you have a folder of photos or recordings you
have never sorted; something at your club, team, or lab gets watched manually.

Bad signs — it sounds impressive; it needs data you do not have; you would not
look at the output twice.

Small and real beats large and hypothetical. "Tell me when a practice room
frees up" is a better project than "a platform for campus resource
management."

---

## 7. What we study, and why in that order

Once your office runs, you have a small distributed system you understand
completely, because you built it. Then the questions get sharp:

- **How does an office know it has finished?** No single agent can see the
  whole system. Each one only knows its own inboxes. There is a real algorithm
  for this, and a subtle way to get it wrong that hangs the whole office
  forever — which happened in this framework, was diagnosed, and was fixed.
- **How do you photograph a system whose parts are all still moving?** You
  want to save state so you can restart after a crash, but there is no moment
  when everything is still. The answer is the Chandy–Lamport distributed
  snapshot, and `recovery_demo` runs it.
- **How do you tell "still working" from "stuck forever"?** Some faults you
  can see in the org chart before running anything; `dsl check` finds those.
  Others depend on which messages actually arrived and in what order, and no
  amount of staring at the diagram will reveal them. That boundary — what is
  knowable from the structure versus only from the execution — is one of the
  deep ideas here, and you will meet it the first time your office hangs.

That is the shape of the term: build something you care about, then find out
what it takes to make it correct.

---

## Before the first class

1. Cowork installed, set to run **on your computer**.
2. `dissyslab` installed; `dsl doctor` reports healthy.
3. `periodic_brief` copied and run; you have looked at `brief.html`.
4. `dsl list` skimmed, and **three examples noted** that interest you.
5. One sentence written down: *the thing I would like to have watched.*

Bring number 5 to the first class. It does not have to be right — it has to be
yours.
