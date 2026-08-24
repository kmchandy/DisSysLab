# Build your own office — a student's guide

You do not need to know anything about distributed systems to start. You need
to know some Python, and you need to be able to describe something you want
watched.

Everything below has been run start to finish on a clean machine. Where a step
has a catch, the catch is written down rather than left for you to hit.

---

## What you need

- **Cowork** (the Claude desktop app). You will talk to it; it will do the
  typing.
- **Python 3.10 or newer.** Ask Cowork to check: *"what Python version do I
  have?"*
- **No API key, to begin with.** The first office you run needs no key and no
  account. You will need one later, for offices where an agent has to read and
  judge text.

**One thing to get right at the start.** When you begin a task in Cowork you
can choose to run it *on your computer* or *in the cloud*. Choose **on your
computer**. A cloud task gets a fresh machine that is thrown away afterwards,
so the office you build today will not be there tomorrow. On your computer,
your work stays yours.

---

## Step 1 — let Cowork install it

Say this:

> The project is at https://github.com/kmchandy/DisSysLab. Install its Python
> package `dissyslab` for me, then run `dsl list` and show me what offices come
> with it.

**Name the repository, every time.** *"Install dissyslab"* on its own asks an
assistant to trust a name it cannot check. Given the address it can read the
project's own instructions, confirm the package it is about to install is this
one, and — in the next step — find the skill, which lives in that repository
and not on PyPI. The URL in step 4 has to come from somewhere; this is where.

You should get a list of forty offices — 31 applications and 9 smaller
examples: a morning brief, a news situation room, a bird-call classifier, a
stock watcher. These are working programs, not examples in a book.

If anything looks wrong, say: *"run `dsl doctor` and tell me what it says."*
That checks your Python, your dependencies, your backend and which DisSysLab
skills are installed, then builds and runs a small office as a self-test.

Run it again after installing the skill in step 4. Its **Skills** section is
how you know that step worked — see the note there about why you should not
just ask.

---

## Step 2 — watch one run

Say:

> Make me my own copy of the `periodic_brief` office in a folder called
> `my_brief`, then run it and open the result.

Cowork will run `dsl init periodic_brief my_brief`, then `dsl run .` inside it.
In ten to twenty seconds you get `brief.html` — real news headlines, real
weather, a few stock tickers. No key, no model download.

**The catch, and why the copy matters.** If you skip the copy and just run
`dsl run periodic_brief`, it works — but it writes `brief.html` *inside the
installed package*, somewhere in your Python site-packages, not in the folder
you are standing in. You will not find it. Make a copy first. Always.

---

## Step 3 — read what you just ran

Open `my_brief/office.md`. It is not code. It looks like this:

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

That is the whole program. **Sources** fetch things from the world. **Sinks**
do something with the result. **Agents** are workers, each with one job.
**Connections** is the network — who sends what to whom.

Each agent's job is described in `roles/<name>.md`, in English, or in
`roles/<name>.py`, in Python. Use English when the job needs judgment
("decide how urgent this article is"). Use Python when the job is exact
("throw away anything I have already seen"). Python roles cost nothing to run;
English roles call a language model.

Change something small and run it again. Add a third news source. Change the
number of articles. Break something on purpose and see what happens — that is
allowed and it is how you learn where the edges are.

---

## Step 4 — build your own

Now describe what *you* want. Say something like:

> I want an office that checks the campus events page every hour, keeps only
> the events about music, and writes them to a file. Build it as a DisSysLab
> office in a folder called `gig_watch`.

Cowork writes `office.md` and the role files. Read what it wrote before you
run it — you should be able to follow the network, because it is four
sections of English. If a piece is not what you meant, say so and it will
change it.

Good first projects are the ones you would actually check:

- something you keep refreshing a browser tab for
- a deadline or a price you are tired of watching by hand
- a folder of photos or recordings you want sorted

---

## Step 5 — check the wiring before you run

Say:

> Run `dsl check` on my office.

This reads your network and reports problems in it *without running
anything*. It catches the mistakes that would otherwise waste your afternoon:

- an agent nothing can reach, usually a name spelled two different ways
- an agent whose output goes nowhere, so its work is thrown away
- a sink nothing sends to, so the file you expected stays empty
- a role you named with no file behind it
- a feedback loop with nothing to stop it

It reports everything it finds at once, not just the first thing. If it says
`-- no problems`, your network is sound.

**What it cannot tell you.** `dsl check` reads the network, not the run. A
wiring diagram can be perfectly correct and the office can still get stuck,
because getting stuck can depend on what actually arrives and in what order.
That difference — what you can know from the diagram, versus what you can only
know from watching it run — is one of the real ideas in this subject, and you
have just met it on your own program.

---

## When it goes wrong

**It hangs and nothing happens.** Some agent is waiting for a message that is
not coming. Run `dsl check` first. If that is clean, the fault is in the
run, not the diagram — tell Cowork *"my office hangs, help me work out which
agent is waiting and what for."*

**It finishes but produces nothing.** Look at the per-agent message counts
`dsl run` prints at the end. The first agent showing zero is where the flow
stops. A sink that no connection feeds is the usual cause, and `dsl check`
names it.

**An English role does something odd.** Language models are literal. If the
job description is vague, the output will be too. Say what to keep, what to
add, and always where to send it.

---

## Honest limits

- Today an office runs on one machine, in one process, each agent in its own
  thread. Running offices in separate processes is being built.
- Checkpoint-and-resume exists and is real, but an office only gets it where
  the author has switched it on.
- There is no web interface. Offices produce files — HTML, JSONL, text.
- Offices that use English roles call a language model, which costs money.
  Every shipped office stops after a few cycles by default so you cannot run up
  a bill by accident. Leave those limits in place until you mean to remove them.

---

## Then the interesting part

Once your office runs, you have a small distributed system that you understand
completely, because you wrote it. The questions that follow are the real
subject:

- How does the office know it has *finished*, when no single agent can see the
  whole system?
- How do you take a photograph of a system whose parts are all still moving,
  so you can restart from it after a crash?
- If agents can wait on each other, how do you tell "still working" from
  "stuck forever"?

Those have real answers, they are decades old, and they are running inside the
thing you just built.
