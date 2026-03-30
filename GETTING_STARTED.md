# Getting Started with DisSysLab

Build your first office of AI agents in under 10 minutes.
No Python experience required.

---

## Step 1 — Install

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
pip install -r requirements.txt
```

---

## Step 2 — Set your API key

DisSysLab uses Claude to power your agents. You need an Anthropic API key.

Get one at [console.anthropic.com](https://console.anthropic.com) — it takes
about 2 minutes.

Then set it:

```bash
export ANTHROPIC_API_KEY='your-key-here'
```

To avoid setting this every time, add it to your shell profile
(`~/.zshrc` or `~/.bashrc`):

```bash
echo "export ANTHROPIC_API_KEY='your-key-here'" >> ~/.zshrc
```

---

## Step 3 — Run the starter office

DisSysLab includes a starter office that monitors Hacker News,
filters for interesting articles, and summarizes each one.

```bash
python3 office_compiler.py gallery/my_first_office/
```

The compiler reads your plain English files, shows you the routing,
and asks: **"Does this look right?"**

Type `yes` and your office starts running.

You'll see briefings appear as articles are processed. Press `Ctrl+C`
to stop.

---

## Step 4 — Make it yours

Open `gallery/my_first_office/roles/analyst.md` in any text editor.

Find this line:

```
Your job is to decide if each item is worth reading — something
a curious, informed person would find genuinely interesting or important.
```

Replace it with whatever you care about. For example:

```
Your job is to decide if each item is about artificial intelligence,
machine learning, or robotics.
```

Save the file and recompile:

```bash
python3 office_compiler.py gallery/my_first_office/
```

Your office now monitors your topic instead.

---

## Step 5 — Build from scratch with Claude

For a completely custom office, use Claude to write your files for you.

1. Open [CLAUDE_CONTEXT_OFFICE.md](CLAUDE_CONTEXT_OFFICE.md) on GitHub
2. Click **Raw** and copy the entire contents
3. Open [claude.ai](https://claude.ai) and paste it into a new conversation
4. Describe what you want:

```
I want to build an office that:
SOURCE: monitors BBC World News and Al Jazeera
PROCESSING: filters for articles about climate and energy policy,
            summarizes each as a briefing note with a priority rating
OUTPUT: live display in the terminal, save to file
```

Claude writes your role files and office file. Save them to a new
directory under `gallery/` and compile.

---

## Available sources

| Source | What it does |
|--------|-------------|
| `hacker_news` | Hacker News — tech, startups, programming |
| `bbc_world` | BBC World News |
| `al_jazeera` | Al Jazeera international news |
| `npr_news` | NPR News |
| `techcrunch` | TechCrunch — tech industry news |
| `bluesky` | Live BlueSky social media stream |

---

## Available outputs

| Output | What it does |
|--------|-------------|
| `console_printer` | Prints each briefing to the terminal |
| `intelligence_display` | Live scrolling dashboard |
| `jsonl_recorder` | Saves every briefing to a file |

---

## Common questions

**My office stopped — what happened?**
RSS sources stop after fetching their articles. To run continuously,
use `bluesky` as a source, or set `poll_interval=600` to re-poll
every 10 minutes:
```
Sources: hacker_news(max_articles=10, poll_interval=600)
```

**Can I run my office without recompiling?**
Yes. After the first compile, `app.py` is saved in your office directory.
Run it directly next time:
```bash
python3 gallery/my_first_office/app.py
```

**Something looks wrong in the routing table.**
Type `no` when the compiler asks. Edit your files and recompile.
No code to fix — just your plain English descriptions.

**I want to add another agent.**
Add one line to the `Agents:` section of `office.md` and one or more
lines to `Connections:`. Create a new role file in `roles/` if the
agent has a new type of job. Recompile.
