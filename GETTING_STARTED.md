# Getting Started with DisSysLab

DisSysLab (DSL) is a Python framework for building an **office of AI
agents** that runs continuously — monitoring news, email, calendars, and
other data sources, and taking action on what it finds.

You can use DSL in two ways.

---

## Path A — Describe your office in plain English

You describe what the office does in plain English. Claude generates the
two files DSL needs. You save them in a folder, run one command, and
your office is live. No Python required on your part.

**To use Path A:**

1. Open a new chat with [Claude](https://claude.ai).
2. Paste the contents of [`CLAUDE_CONTEXT_OFFICE.md`](CLAUDE_CONTEXT_OFFICE.md)
   into the chat.
3. Describe the office you want — what sources, what topics, what
   outputs. Claude will generate the office file and role files.
4. Save those files in a folder on your computer.
5. Run your office (see Installation below).

---

## Path B — Build a custom app in Python

You write ordinary Python functions for data sources, processing logic,
and outputs. DSL handles threading, message passing, and shutdown.

**To use Path B:**

1. Open a new chat with [Claude](https://claude.ai).
2. Paste the contents of [`CLAUDE_CONTEXT_APP.md`](CLAUDE_CONTEXT_APP.md)
   into the chat.
3. Describe the app you want. Claude will generate a complete working
   Python file.

---

## Installation

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
pip install -e .
```

`pip install -e .` installs DisSysLab in editable mode and puts the
`dsl` command on your PATH, so you can run offices from anywhere.

Get an Anthropic API key and put it in a `.env` file — about three
minutes start to finish. Follow [`API_KEY_SETUP.md`](API_KEY_SETUP.md)
for the exact steps and common pitfalls (TextEdit corrupting `.env`,
venv/PATH mismatches, and so on).

Run `dsl doctor` from your office folder to sanity-check everything —
Python version, dependencies, `.env` format, and whether
`ANTHROPIC_API_KEY` is loaded.

---

## Run your first office

Try a gallery example:

```bash
dsl run gallery/org_intelligence_briefing/
```

Or run the office Claude wrote for you:

```bash
dsl run path/to/my_office/
```

Press `Ctrl+C` to stop.

---

## What's next

- Browse [`gallery/`](gallery/) — a growing set of working offices you can run as-is or adapt.
- Take the [5-minute micro-course](https://kmchandy.github.io/DisSysLab/office_microcourse.html) for a visual walkthrough.
- Read the full [`README.md`](README.md) for the overall picture.

---

*DSL is an open research project exploring natural language interfaces
to persistent distributed systems.*
