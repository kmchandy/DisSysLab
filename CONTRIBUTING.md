# Contributing to DisSysLab

Thank you for considering a contribution. DisSysLab is a small,
actively-maintained project; honest expectations up front:

- **One maintainer (K. Mani Chandy) reads issues regularly. Pull
  requests are handled when there is time.** Please open an issue
  to discuss a proposed change before writing code — that
  protects your time as much as mine.
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
- A concrete use case from a gallery office or a recipe.
- Alternatives you have considered.
- Whether the feature could be a gallery office rather than a
  framework change.

The bar for new framework features is high: it has to serve
multiple gallery offices, and the implementation has to stay
small.


## Running the tests

```bash
git clone https://github.com/kmchandy/DisSysLab.git
cd DisSysLab
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/
```

The full regression suite should pass in under 30 seconds. If it
does not, your environment is misconfigured before any change is
made. `dsl doctor` is the faster first check: it verifies
dependencies and runs a built-in self-test without needing pytest.

### Offices that are still being built

Two tests sweep every office under `dissyslab/gallery/` — one
parses each one, one compiles each one. An office you are still
working on will therefore fail the suite, which is misleading,
because the sentence above tells the next person their
environment is broken.

Drop a file named `WIP` in the office's own folder to opt out:

```bash
echo "salton_wind is not registered yet" > \
  dissyslab/gallery/apps/my_new_office/WIP
```

The office is then reported as XFAIL with that text as the
reason, instead of failing the run.

The two sweeps report independently, and the pair is useful: an
office that parses but does not compile shows up as one XPASS and
one XFAIL, which tells you how far it gets without your having to
run anything. Delete the marker when no XFAIL is left.

Keeping the opt-out in the office folder means an unfinished
office needs no edit to any tracked test file — which matters,
since an office still being built is usually untracked.


## Coding conventions

- Match the surrounding style. Do not run a project-wide
  formatter as part of a feature PR.
- Add a test for any new behaviour.
- Update the docstring on the function or class you change.
- Update `CHANGELOG.md` under `[Unreleased]` for user-visible
  changes.


## Where things live

See [`docs/EXTENDING.md`](docs/EXTENDING.md) for the layered
framework surface and the *"local office vs. framework library"*
decision rule. That doc is the one you want if you are unsure
whether your change belongs in your own office's `roles/` folder
or in the framework's `dissyslab/fn_lib/` or
`dissyslab/office/library.py`.


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
[`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). The reporting contact
is K. Mani Chandy (kmchandy@gmail.com).


## A note on bandwidth

The maintainer's day-job is teaching at Caltech. Acknowledgement
of an issue may take a few days; resolution may take longer. If
the issue is urgent for your use case, say so in the issue and
include enough context so that someone else who reads it can
pick it up.

Thank you for the time you spend writing a good issue or a good
PR. That is what makes the framework better.
