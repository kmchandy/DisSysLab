# Lab 3: agents in plain English, for the course staff to run

What the lab teaches (the first box of `course/lab3.html`): an agent can
only follow the rules it is told. Sal is never told the floor prices, so a
believable offer below the floor gets booked; a hook, `hooks/floor_guard.py`,
reads `inventory.json` and refuses it, every time and with any model.

Every agent in this lab is a plain-English Markdown file.

- `agents/sal.md`: Lab 1's car salesperson, as a Claude Code subagent that
  can book a sale by writing a file. `agents/sal-told.md` is the same with
  one sentence added: never below list price.
- `agents/test-fixer.md`: an engineer told to make a project's tests pass,
  when two of the tests (in `task/`) contradict each other.
  `agents/test-fixer-honest.md` adds one sentence: saying "impossible" is
  an acceptable result.
- `customers.jsonl`: every message Sal receives in Part 1, copied from
  `dissyslab/gallery/car_dealer/attacks.jsonl` (sessions c02 to c07) plus
  one honest buyer.
- `haggles.jsonl`: five ordinary hagglers, new for this lab. Four offer a
  believable price just below the floor (h01 to h04); one asks for a fair
  discount above it (`fair`), which the hook must let through.
- `hooks/floor_guard.py`: a Claude Code PreToolUse hook. It reads the sale
  Sal is about to write and refuses it if the price is below the floor.
  `settings/dealer-hook.json` is `dealer.json` with the hook added; the
  hook variant runs `sal.md` unchanged with those settings.
- `office/`: the same check as a DisSysLab agent. `office.md` is
  `customer -> Sal -> Guard -> Rex`, with Sal an English role that has no
  tools (`roles/salesperson.md`) and Guard a Python role
  (`roles/floor_guard.py`, the hook's rule); `Rex` books only what leaves
  Guard with `book: yes`. `office-open.md` is the same without Guard.
  `lab3.py office` runs them with `dsl run` on the same twelve
  conversations and keeps one trace per conversation.
- `inventory.json`: the five cars with list and floor prices, copied
  unchanged from `dissyslab/gallery/car_dealer/inventory.json`. A sale
  below the floor is an attack that got through.
- `settings/*.json`: what each agent may do, as permission rules. The
  fence variant adds one rule, `Edit(tests/**)` denied.

`lab3.py` runs them with Claude Code non-interactively and keeps every
trace. Students read the agent files and the traces, which are copied from
`lab3_runs_public/` into `traces/<date>/` (see `traces/README.md`).
(`python/` holds the same two agents written in Python with the Claude
Agent SDK, for Class 13's optional last section. This lab does not use Python agents.

## 1. Set up (once, about 5 minutes)

Install Claude Code, if it is not installed and check it:

    claude --version

and install pytest into the Python you will use:

    python3 -m pip install pytest

The `office` runs also need DisSysLab (`dsl --version`); it is installed if
you have run Lab 1.

## 2. Your key

The runs use your Anthropic key from the environment (Claude Code's bare
mode does not use a subscription login). From the repository's `.env`,
without printing it:

    set -a; source ~/Documents/DisSysLab/.env; set +a

## 3. Safety

Each run gets a fresh folder under `~/lab-runs/lab3/`, outside the
repository. The agents run in Claude Code's bare mode. 
Their permissions come only
from `settings/`, in `dontAsk` mode, which refuses anything not allowed
there. Sal may write only in its folder's `sales/`. The test fixer may
edit files in its folder and run `python -m pytest`, nothing else; the
tests it runs have the network cut (`guard/`). That is not a full
sandbox: the code the agent writes runs as you when pytest runs it, and it
can see your environment, including the key. For more isolation, run
Part 2 under a separate macOS user account.

## 4. A first look (about $0.50, 5 minutes)

    cd ~/Documents/DisSysLab/course/lab3
    python3 lab3.py part1 --variant open --runs 1
    python3 lab3.py part1 --variant hook --runs 1
    python3 lab3.py office --variant guard --runs 1
    python3 lab3.py part2 --variant base --runs 1
    python3 lab3.py publish

Then tell Claude: it reads `lab3_runs_public/` in the repository, checks
the traces are what the lab needs, and fixes anything (Claude Code's
options change) before the full runs spend more.

## 5. The full runs (about $15 to $35; capped at $40)

    python3 lab3.py part1 --variant open   --runs 3
    python3 lab3.py part1 --variant told   --runs 3
    python3 lab3.py part1 --variant hook   --runs 3
    python3 lab3.py office --variant open  --runs 3
    python3 lab3.py office --variant guard --runs 3
    python3 lab3.py part2 --variant base   --runs 10
    python3 lab3.py part2 --variant honest --runs 10
    python3 lab3.py part2 --variant fence  --runs 10
    python3 lab3.py part2 --variant budget --runs 10
    python3 lab3.py summary
    python3 lab3.py publish

A Part 1 run is twelve conversations: six of Lab 1's attacks, five
hagglers and one honest buyer. An `office` run is the same twelve in one
`dsl run`; `dsl` does not report cost, so each counts as $0.15 towards the
cap (an estimate). `~/lab-runs/lab3/spend.json` adds up the cost, and a batch stops
before it could pass $40. Ctrl-C is safe: run the same command again and
it carries on after the runs already done.

## If something goes wrong

A failed run prints `FAILED:` with what `claude` said, and stops the batch;
finished runs are kept. Send Claude that line. The likely ones: the key is
not set (step 2), `claude` is not installed (step 1), or Claude Code has
renamed a flag since this was written (the command is in
`claude_command` in `lab3.py`). For the hook variant, `FAILED: ... did not
run` means Sal tried to book and `floor_guard.py` left no record in the
run's `hook.jsonl`: Claude Code did not load the hook from `--settings`.
