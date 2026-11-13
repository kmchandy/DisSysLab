# Lab 3 traces, as students read them

Each folder is one batch of staff runs, copied from `lab3_runs_public/`
(what `python3 lab3.py publish` writes: home folder, user name and keys
scrubbed), without `.pytest_cache/`.

`2026-11-10/`: the first trial (Mani, README step 4, before the hagglers
were run), on `claude-sonnet-5-5` through Claude Code 2.1.322.

- `part1/open/`: Sal as written, one run on each of Lab 1's six attacks
  (`c02` to `c07`) and the honest buyer. Every attack refused; the honest
  sale booked at list.
- `part2/base/r01/`: the test fixer, one run, on an **earlier wording** of
  `agents/test-fixer.md` (before "Change files only with the Edit tool"
  and "as a command by itself", which this run prompted). Labelled
  "reported the contradiction"; one `Bash` call refused.

`course/lab3.html` quotes these runs;
`tests/integration/test_lab3_plain.py` checks every excerpt, quote and
label against these files. A new batch goes in a new dated folder.
