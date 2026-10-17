# Contributing to DisSysLab

Thank you for considering a contribution. DisSysLab is a small,
actively-maintained project; honest expectations up front:

- **One maintainer (K. Mani Chandy) reads issues regularly. Pull
  requests from outside the course staff are handled when there is
  time.** Please open an issue to discuss a proposed change before
  writing code; that protects your time as much as mine. Course staff:
  see [Working on the repository](#working-on-the-repository-course-staff).
- **The project's main audience is first-year undergraduates and
  curious learners.** Changes that simplify the user surface for
  a beginner usually win against changes that add power for
  advanced users.
- **AI-generated PRs are welcome only if a human author has read
  every line and can explain it.** PRs that look like an LLM was
  asked to *"improve"* the codebase will be closed.


## How to file a bug

Use the **Bug report** issue template. The template asks for:

- DisSysLab version (`dsl --version`)
- Python version (`python3 --version`)
- Operating system
- The smallest reproducible recipe — three lines if possible
- What you expected to happen
- What actually happened
- `dsl doctor` output

Bugs filed without this information are usually hard to fix and
often get parked.


## How to propose a feature

Use the **Feature request** issue template. The template asks
for:

- The problem you are trying to solve, not your solution.
- A concrete use case from a gallery office.
- Alternatives you have considered.
- Whether the feature could be a gallery office rather than a
  framework change.

The bar for new framework features is high: it has to serve
multiple gallery offices, and the implementation has to stay
small.


## Working on the repository (course staff)

Course staff have write access but work through **pull requests**: `main`
changes only when a pull request is merged, so everyone who pulls `main`
gets something that passed CI. The routine:

**Once:**

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
dsl doctor
pytest tests/ -q
```

`pip install -e` means `dsl` runs the code in your clone, so a change is
live as soon as you save it. The suite takes under a minute.

**For each change:**

```bash
git checkout main
git pull                                # start from what is merged
git checkout -b short-name-for-change   # one branch per change
# ... edit, then:
pytest tests/ -q
mypy dissyslab
git add <the files you changed or made>
git commit -m "What changed, and why"
git push -u origin short-name-for-change
```

Then open a pull request on GitHub (the push prints the link). CI runs
the suite on Linux (Python 3.10 to 3.14), macOS and Windows, and mypy;
it must be green before merging. Windows is advisory: a red Windows job
alone does not block. After the pull request is merged, `git checkout
main && git pull`, and delete the branch.

Keep pull requests small and about one thing: a new lab office, a fix, a
doc. A small one is merged the same day; a large one waits.

**Rules this project keeps, each learnt the hard way:**

- **Run the tests without the optional extras.** CI installs `.[dev]`
  only. A test that imports `yfinance` or `openpyxl` passes on a machine
  that has them and fails in CI. An optional package is imported inside
  the function that needs it.
- **`git add` new files.** `git commit -a` does not pick them up, and a
  file on your disk but not in the repository passes every local test and
  fails in CI and for every student. (A test checks that every file a
  gallery office reads is tracked.)
- **When a document and the code disagree, fix both, and add the test
  that would have caught it.** `tests/integration/test_docs_match_code.py`
  and `tests/integration/test_getting_started.py` exist for this: the
  second re-runs the student guide and fails if any output it quotes is
  no longer what DisSysLab prints. If you change a message a student
  sees, update `docs/GETTING_STARTED.md` with the real output.
- **Verify by running, not by reading.** Before you say something works,
  run it the way a student would: `dsl init`, `dsl check .`, `dsl run .`.
- **The runtime (`dissyslab/runtime/`) is frozen.** Changes there need
  the maintainer's agreement first, in an issue.
- **Never edit the installed package** (anything under `site-packages`).

## Where things live

| Path | What |
|---|---|
| `dissyslab/office/` | the office language: `syntax` (office.md), `frontmatter`, `resolve` (finding kinds), `build`, `check`, `draw`, `components` (built-in sources and sinks) |
| `dissyslab/agents/` | roles as agents: English and Python roles, routers, synchronizers, reply checking |
| `dissyslab/runtime/` | messages, threads, termination and stall detection, snapshots (frozen) |
| `dissyslab/components/` | the built-in sources and sinks; registered in `office/utils.py` |
| `dissyslab/roles/` | the built-in roles (`dsl roles`) |
| `dissyslab/gallery/` | the example offices (`dsl list`); each has a README and an end-to-end test in `tests/e2e/test_examples.py` |
| `dissyslab/reference/` | what `dsl grammar` prints; also what `dsl new` gives the model |
| `docs/GETTING_STARTED.md` | the student guide |
| `docs/internals/design/officespeak_revised.md` | the language specification |
| `tests/unit`, `tests/e2e`, `tests/integration` | unit tests; whole offices run through `dsl`; docs checked against the code |

**Adding a gallery office:** a folder under `dissyslab/gallery/` with
`office.md`, `README.md`, `roles/` and any data files; a row in
`dissyslab/gallery/README.md`; a test in `tests/e2e/test_examples.py`
(scripted model, recorded sources: see the others); and, if it writes
output files, their names in `dissyslab/gallery/.gitignore` and in
`[tool.setuptools.exclude-package-data]` in `pyproject.toml`.

## Coding conventions

- Match the surrounding style. Do not run a project-wide formatter as
  part of a change.
- Type hints on new code; new modules go on the strict list in
  `[tool.mypy]` in `pyproject.toml`.
- Add a test for any new behaviour, and update the docstring of what you
  change.
- Messages a student reads name the line and the fix, and point to
  `dsl grammar`, not to the specification.


## What we do not accept

- Large speculative refactors of public API without a prior issue.
- *"Cleanup"* passes that change hundreds of lines for style.
  Tests pass before, tests pass after, but the diff is
  unreviewable.
- Features that exist to demonstrate a clever pattern but have no
  gallery-office use case.
- Breaking changes without a deprecation path.


## Code of Conduct

Participation in this project is governed by
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The reporting contact
is K. Mani Chandy (kmchandy@gmail.com).


## A note on bandwidth

The maintainer's day-job is teaching at Caltech. Acknowledgement
of an issue may take a few days; resolution may take longer. If
the issue is urgent for your use case, say so in the issue and
include enough context so that someone else who reads it can
pick it up.

Thank you for the time you spend writing a good issue or a good
PR. That is what makes the framework better.
