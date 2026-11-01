# Lab 3 in Python (optional): the Claude Agent SDK version

The lab itself uses plain-English subagents (`../README.md`). These
scripts build the same two agents in Python with the Claude Agent SDK, for
Class 13's optional last section. They are not needed for the lab.

Lab 3 shows the Claude Agent SDK, a framework from an AI company, on two
small problems. The staff run the scripts once and keep every trace;
students read the code and the traces. Nothing here is run by students.

- **Part 1** (`part1_dealer.py`): Lab 1's car dealer as an SDK agent that
  can *book* a sale. Lab 1's attacks, with and without a hook that refuses
  any sale below the floor price.
- **Part 2** (`part2_impossible.py`): an agent told to make a project's
  tests pass, when two of the tests contradict each other. Four variants:
  as given, a prompt that allows "this is impossible", a hook that lets it
  change only `pricing.py`, and a small turn budget.

Every run's trace (what the agent said, every tool call and result, every
hook denial, the cost) goes to `lab3_runs/` at the top of the repository,
which git ignores.

## 1. Set up (once, about 5 minutes)

In Terminal:

    cd ~/Documents/DisSysLab/course/lab3/python
    python3 -m venv ~/lab3-venv
    source ~/lab3-venv/bin/activate
    pip install claude-agent-sdk pytest

The SDK brings its own copy of the Claude Code engine; nothing else to
install. Check it, and note the version it prints:

    python -c "from importlib.metadata import version; print(version('claude-agent-sdk'))"

## 2. Your key

The runs use your Anthropic key, read from the environment. From the
`.env` at the top of the repository, without printing it:

    set -a; source ~/Documents/DisSysLab/.env; set +a

## 3. Safety, read once

Part 2's agent writes Python, and its `run_tests` tool runs that Python
on your Mac. What limits it: its file tools reach only its own copy of the
project; the test runs have the network cut, no API key, and a 60-second
limit; it has no shell and no built-in Claude Code tools. That is not a
full sandbox: the code runs as you. For more isolation, run Part 2 under a
separate macOS user account. Part 1's agent writes nothing but its own
`sales.jsonl`.

## 4. A first look (about $0.50, 5 minutes)

    python run_batch.py part1 --variant open --runs 1
    python run_batch.py part2 --variant base --runs 1

Each line printed is one run and what it cost. Then tell Claude: it reads
`lab3_runs/` from your folder, checks the traces are what the lab needs,
and fixes the scripts if not, before the full runs spend anything.

## 5. The full runs (about $15 to $35; capped at $40)

    python run_batch.py part1 --variant open   --runs 3
    python run_batch.py part1 --variant hook   --runs 3
    python run_batch.py part2 --variant base   --runs 10
    python run_batch.py part2 --variant honest --runs 10
    python run_batch.py part2 --variant hook   --runs 10
    python run_batch.py part2 --variant budget --runs 10

A Part 1 run is seven conversations (six of Lab 1's attacks and one honest
buyer), so `--runs 3` is 21. Each run has its own dollar cap (25 cents in
Part 1, 50 in Part 2); `lab3_runs/spend.json` adds them up, and a batch
stops before it could pass $40 in all. Stop any batch with Ctrl-C; run
the same command again and it carries on.

If Part 2's rates are close, run each variant 10 more times (`--runs 20`
does the next ten; the first ten are kept).

## 6. Afterwards

    python summarize.py      # the rates, per variant
    python scrub.py          # copies lab3_runs/ to lab3_runs_public/ without
                             # your home folder, user name or anything key-shaped

Then tell Claude. The lab's pages are built from `lab3_runs_public/`, and
every number and quotation on them is checked against those runs, as for
Class 6.

## If something goes wrong

A run that fails prints `FAILED:` and the error, and stops the batch;
finished runs are kept. Send Claude the line. The likely ones: the key is
not set (step 2), the virtual environment is not active (step 1), or the
SDK has renamed an option since these scripts were written.
