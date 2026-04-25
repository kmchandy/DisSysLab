# Getting Started with DisSysLab

In the next **10 minutes** you will install DisSysLab, get an
Anthropic API key, and run your first office of AI agents. You
will edit one file, re-run, and see the behavior change. No
Python programming is required.

If anything goes wrong along the way, skip to
[**If something goes wrong**](#if-something-goes-wrong) at the
bottom — that section has a fix for every common error.

---

## What you'll build

A tiny **office** that watches Hacker News and, as new stories
arrive, writes one-sentence briefings to your terminal, like:

```
Researchers release a 7B model that runs on a Raspberry Pi 5
with usable latency — full weights and training code on GitHub.
```

A few minutes after that, you'll swap to a richer office —
**org_situation_room** — that scans Bluesky and live news feeds
in real time, with two agents collaborating on what makes the cut.

An **office** in DisSysLab is a tiny team of AI agents wired to
a source (where data comes from) and a sink (where results go).
You describe each agent's role in plain English. DisSysLab takes
care of threading, message passing, and shutdown.

---

## Prerequisites

- **Python 3.9 or newer.** Check with `python3 --version`. Most
  Macs and modern Linux distributions already have it.
- **A terminal.** Terminal.app on Mac, any terminal on Linux,
  PowerShell or Windows Terminal on Windows.
- **An Anthropic account.** Free accounts work for this
  walkthrough. Get one at
  [console.anthropic.com](https://console.anthropic.com).

That's it. No git, no compiler, no special Python skills.

---

## 1. Install DisSysLab (2 minutes)

A virtual environment (venv) is strongly recommended. It keeps
DisSysLab and its dependencies isolated from the rest of your
system, so nothing else can break it — and uninstalling later is
just `rm -rf`.

Here are example steps for installation. Executing the steps may take a minute or two.

1. Make a folder called dsl_tutorial in your computer for your dsl work.
2. Go to that folder.
3. create a venv
4. activate the venv (on Windows: .venv\Scripts\activate)
5. install latest pip
6. install dissyslab
7. Verify that it worked

```bash
mkdir ~/dsl-tutorial 
cd ~/dsl-tutorial
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install dissyslab
dsl --version
```

## Troubleshooting
You should see a version number like `1.2.2` or higher. If you
see **"command not found: dsl"**, your venv didn't activate.
Re-run the `source .venv/bin/activate` line and try again.

If you see a version number lower than `1.2.3` then 
you have an older dsl earlier on your PATH that your shell is finding first. 
Execute the following steps: (1) Flush the command shell's cache and (2)
check which dsl is being used.

```bash
hash -r
which dsl
```

If the dsl is outside your .venv/bin/, then
 remove the stray install 

 ```bash
 deactivate
 pip uninstall dissyslab
 ``` 
 or reopen your terminal to pick up a clean PATH.

## Running dsl from now on

**From now on, whenever you open a new terminal to work on
DisSysLab, first run:**

```bash
cd ~/dsl-tutorial
source .venv/bin/activate
```

Otherwise your shell won't find the `dsl` command.

---

## 2. Get an API key (3 minutes)

DisSysLab's agents use Anthropic's Claude. You need an API key.

**The short version:**

1. Log in at
   [console.anthropic.com](https://console.anthropic.com).
2. Go to **Settings → API Keys → Create Key**. Copy the key
   (starts with `sk-ant-`) to your clipboard — Anthropic only
   shows it once.
3. Put the key into your shell's environment by entering:

   ```bash
   export ANTHROPIC_API_KEY=$(pbpaste)
   ```

   (The `pbpaste` command is Mac-specific. On Linux use
   `xclip -selection clipboard -o` or `xsel -b`; in Windows
   PowerShell use `Get-Clipboard`.)

   This sets the key for the current terminal only. To have it
   available every time, add the same `export` line to the end
   of `~/.zshrc` (or `~/.bashrc` on Linux).

   Do not paste the key into any other file.

   You will not see a response from the terminal when you execute the export command.

**Full instructions and troubleshooting** (TextEdit pitfalls,
paste mistakes, 401 errors) are in
[`API_KEY_SETUP.md`](API_KEY_SETUP.md). If anything confuses you,
open that file now. It takes about three minutes end to end.

---

## 3. Run your first office (2 minutes)

DisSysLab ships with a **gallery** of ready-to-run offices.
`dsl list` shows them all. A great starter is `my_first_office`
— it watches Hacker News and needs no keys beyond your Anthropic
one.

Make sure you're still in `~/dsl-tutorial` with your venv
activated (from §1) and your API key exported (from §2). Then:

1. Copy the my_first_office from the gallery into your local folder called **my_briefing**: 
   ```dsl init my_first_office my_briefing```
2. Go to the office in your local folder ```cd my_briefing```.
3. Run a check: ``` dsl doctor```
4. Run the new office called **my_briefing**: ```dsl run . ```

```bash
dsl init my_first_office my_briefing
cd my_briefing
dsl doctor
dsl run .
```

`dsl run` first prints the office's org chart and asks you to
confirm — something like:

```
Office: my_first_office

Agents:
  Alex          analyst           sends to: briefing

Routing:
  hacker_news       →  Alex
  Alex              [briefing]  →  console_printer

Does this look right? (yes / no):
```

Take a moment to read the preview before answering — this is
the entire office.

**Agents** are AI workers. "Alex is an analyst" means your
office has an agent named Alex whose job description is
`roles/analyst.md`. An agent has output mailboxes, or ports,
to which the agent sends messages. Alex has one mailbox:
`briefing`. You'll see the mailbox name in the routing
description, which specifies where messages go.

**Routing** shows what messages flow between sources, agents,
and sinks. `hacker_news → Alex` means messages from hacker_news
arrive at Alex. `Alex [briefing] → console_printer` means
messages Alex sends out to her `briefing` mailbox get printed
to your terminal.

In plain English: Hacker News stories come in. Alex writes a
one-sentence briefing for each. The briefing prints.

Type **`yes`** and press Enter (typing `no` cancels). Within
a minute you should see several briefings stream past — one
per story in the first Hacker News batch. Then the office
goes quiet: the Hacker News source polls on a fixed interval
(10 minutes by default), so the next batch won't appear until
that interval has elapsed. **That's normal — the office isn't
stuck.** Press **`Ctrl+C`** when you've seen enough.

If you'd rather see new batches more often, open `office.md`
in this folder and change `poll_interval=600` to a smaller
number (e.g. `60` for every minute). Save and re-run.

If the topology preview never appears, or you see an error
instead, jump to [**If something goes wrong**](#if-something-goes-wrong).

---

## 4. What just happened

Take a look at the folder you're in:

```
my_briefing/
├── office.md         ← the org chart: source, agent, sink
└── roles/
    └── analyst.md    ← what the agent does, in plain English
```

Open `office.md` — it says:

> The source is `hacker_news`. The source has additional parameters such as the number of articles to be pulled on each poll of the site and the sleep time between polls.
> The sink is `console_printer`.
> Your office has an agent called Alex who is an analyst.
> hacker_news goes to Alex. Alex's `briefing` mailbox goes to
> the console.

Open `roles/analyst.md` — it says:

> You are a Hacker News analyst. For each story, write one
> crisp sentence describing what it's about and why someone
> learning software might care. Send to briefing.

**That's it.** When you ran `dsl run .`, DisSysLab read those
two files, started a **source** that polls Hacker News for
new stories, passed each story to Alex whose behavior was the
plain-English role you just read, and forwarded Alex's
briefings to the console.

No Python was involved on your side. The Python is inside
DisSysLab, and you only had to describe what the office does.

---

## 5. Make a change — it's really yours (2 minutes)

Stop the office with `Ctrl+C` if it's still running.

Out of the box Alex summarizes every story for a generic reader.
Let's give her a specific audience: first-year computer-science
students learning Python, AI, and data science.

Open `roles/analyst.md` in any text editor. Replace the
existing role with:

```
# Role: analyst

You are a Hacker News analyst. Your readers are first-year
computer science students learning Python, AI, and data
science.

For each story, write one crisp sentence. If the story is
relevant to that audience — Python libraries, AI explainers,
data-science tools, programming education — explain why they
should care. If it's not relevant, briefly note what the story
is about and why CS students might want to skip it.

Send to briefing.
```

Save the file. Re-run:

```bash
dsl run .
```

Confirm the topology with **`yes`** again. Now the briefings
have a clear audience — Python releases and AI tutorials get
enthusiastic context; posts about obscure enterprise tooling
get a one-line "probably not for you" note.

You changed the office's behavior by editing a single plain-
English file. The wiring didn't change. No code, no rebuild
step. That's the whole idea.

`Ctrl+C` when you've had enough.

---

## 6. Try another office

```bash
dsl list
```

This prints every office that ships with DisSysLab. The richest
demo is `org_situation_room` — it scans **three** sources at
once (Bluesky's live firehose plus the BBC and Al Jazeera news
feeds), runs them through a two-agent pipeline (an analyst who
filters for significance, then an editor who rewrites each
keeper as a briefing), and shows the eight most recent
briefings in a live-updating display. It's the office in the
screenshot at the top of `README.md`.

Go back up to `~/dsl-tutorial`, copy the office, and run it.
Your exported API key is still set in this terminal, so the new
office picks it up automatically — no extra setup needed.

```bash
cd ~/dsl-tutorial
dsl init org_situation_room my_situation_room
cd my_situation_room
dsl run .
```

The topology preview will be longer this time — three sources,
two agents, two sinks (one of them the live display). Type
**`yes`** to start. Bluesky posts arrive seconds apart during
busy news cycles, so the display starts filling almost
immediately. Press `Ctrl+C` when you've seen enough.

Open `roles/analyst.md` and `roles/editor.md` to see how the
two agents' jobs are described. Edit either one — for example,
change Alex to filter for science news instead of politics —
and re-run. Same plain-English knob, same instant change.

---

## Where to go next

The three resources worth knowing about, in order:

1. **The gallery.** `dsl list` prints every shipped office, and
   each office's folder has a short README describing what it
   does. After `my_first_office` and `org_situation_room`, try
   `org_news_filter` (a single-agent variant) or
   `org_news_editorial` (a different two-agent shape).

2. **The visual micro-course.** A 5-minute slide walkthrough of
   the same concepts you just used:
   [office_microcourse.html](https://kmchandy.github.io/DisSysLab/office_microcourse.html).

3. **The main [README.md](README.md).** Broader overview of what
   an office is and how offices can compose into networks of
   offices.

---

## If something goes wrong

The first thing to do, always, is run `dsl doctor` from inside
the office folder. It checks your Python version, confirms
DisSysLab is installed, and tries to read your API key. Every
check either prints `[OK]` or a specific fix hint.

```bash
cd ~/dsl-tutorial/my_briefing
dsl doctor
```

Common cases:

### `command not found: dsl`

Your venv isn't activated. From your project folder:

```bash
source .venv/bin/activate
```

### `ANTHROPIC_API_KEY not set` or `401 authentication failed`

Your key isn't set in the current terminal, or the value that
*is* set is invalid. Common causes:

- You closed and reopened the terminal since running the
  `export` line in §2. Run it again. To avoid this in future,
  add the same `export` line to the end of `~/.zshrc`.
- The clipboard didn't contain the key when you ran `pbpaste`.
  Re-copy the key from
  [console.anthropic.com](https://console.anthropic.com) and
  re-run the `export` line.
- The key itself is revoked or wrong. Generate a fresh one and
  re-export.

You can confirm what's set right now with:

```bash
echo "${ANTHROPIC_API_KEY:0:10}…  (length ${#ANTHROPIC_API_KEY})"
```

A working key prints `sk-ant-api…  (length 108)` or similar.
An empty line means nothing is set.

Full fix list (including the older `.env` file approach) is in
[`API_KEY_SETUP.md`](API_KEY_SETUP.md).

### `dsl run` prints nothing for a long time

Some sources (RSS, Hacker News) poll every few minutes and then
sleep between polls. Wait at least 30 seconds. If still
nothing, check `dsl doctor` and then the office's `README.md`
— it will mention any extra setup (e.g. Gmail, calendar, or
stock API keys) the source needs.

### Anything else

Open an issue at
[github.com/kmchandy/DisSysLab/issues](https://github.com/kmchandy/DisSysLab/issues)
with:

- the command you ran,
- the full output,
- the result of `dsl doctor`,
- `python3 --version` and `pip show dissyslab | head -3`.

---

*Last reviewed for DisSysLab v1.2.2.*
