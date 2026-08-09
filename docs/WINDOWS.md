# Running DisSysLab on Windows

**Status, stated plainly: Windows is not verified.** As of this
writing the framework has one known Windows failure (checkpoints,
below), and the fixes for two other reported Windows problems were
made by reading code, not by running anything on Windows. CI now
includes a Windows job, but it is advisory and its results are the
first real evidence either way.

If you are reading this because you agreed to test on Windows: you
are the verification. Thank you. What to report is at the bottom.

Linux and macOS are the supported platforms and both run in CI.

---

## Install

Do **not** use the one-line installer from the top-level README. It
is a shell script and assumes a Unix-like environment. Install
manually.

```powershell
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
py -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Three things that differ from the Unix instructions:

- Activation is `.venv\Scripts\activate`, not `source .venv/bin/activate`.
- The quotes around `".[dev]"` are required in PowerShell. In
  `cmd.exe` plain `pip install -e .[dev]` also works. Getting this
  wrong installs the framework without the test tools, and `pytest`
  is then not found — this is the most common setup problem, on any
  platform.
- Python 3.10 or newer. `py -0` lists what you have.

## Set UTF-8 mode

```powershell
$env:PYTHONUTF8 = "1"        # PowerShell, current session
setx PYTHONUTF8 1            # persist for future sessions
```

This is the single most useful thing on this page. Windows defaults
its text encoding to the system locale — usually cp1252 — while
DisSysLab's content is full of em dashes and box-drawing characters.
Python's UTF-8 mode makes file I/O default to UTF-8 regardless of
locale.

Every file-reading and file-writing call in the framework now names
its encoding explicitly, so in principle this should not be
necessary. It is recommended anyway, for two honest reasons: that
audit covered `open`, `write_text` and `read_text` and may have
missed another route to the same problem, and UTF-8 mode also covers
console output, which the audit did not touch at all.

For console output specifically, prefer Windows Terminal. In a
legacy `cmd.exe` window, run `chcp 65001` first, or the console
version of the brief may fail on characters it cannot encode even
though the HTML file it writes is correct.

## Check the install

```powershell
dsl doctor
```

This checks your Python version, dependencies, and backend, then
builds and runs a small three-agent office as a self-test. A clean
run means the framework genuinely works, not merely that it
imported. It also tells you whether `pytest` is available.

It should exit 0 without any API key. If it reports a missing
credential as a *failure* rather than as information, you are on an
old version.

Then:

```powershell
dsl run periodic_brief
```

This office makes no LLM calls and needs no key. It previously could
not run on Windows at all: it formatted dates with `%-d` and `%-I`,
which are glibc extensions that MSVC's `strftime` rejects. That is
fixed. If the brief renders, the fix holds.

## What is known to be broken

**Checkpoint and resume.** The tests in
`tests/unit/test_checkpoint_resume.py` fail on Windows. Something
still holds a file open when the temporary directory is removed, and
Windows — unlike POSIX — will not unlink an open file. Unfixed, and
not yet diagnosed; it needs someone on Windows to trace it.

Avoid `--snapshot-interval` and `--resume` on Windows for now, or
expect trouble. Everything else in the framework is independent of
this.

One leaked handle of exactly this kind was found and fixed while
investigating (`FileLineWriter` closed its file only in `finalize()`,
which an office killed mid-run never reaches). That was a real bug on
every platform — POSIX simply hid it. It is probably *not* the cause
of these test failures, since those tests use a different sink, but
it shows the shape of what to look for.

## What to report

Run the suite and send the summary line plus the failure names:

```powershell
pytest tests\ -q
```

Also useful:

- The output of `dsl doctor`.
- `git rev-parse --short HEAD`, so failures can be matched to code.
  A previous Windows report counted 477 tests where the current tree
  collects 543, and without a commit hash there was no way to tell
  which failures still existed.
- Whether `dsl run periodic_brief` renders.
- Whether you set `PYTHONUTF8=1`, and whether anything changed when
  you did.

Windows problems are worth reporting even when they look small. The
two already fixed — a date format and a file encoding — each stopped
a first-time user cold, and neither was visible from Linux.

Open an issue at https://github.com/kmchandy/DisSysLab/issues, or
email the maintainer if you would rather.
