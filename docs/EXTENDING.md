# Where does it belong? Your office, or DisSysLab

Almost everything you write belongs in **your office's folder**. A few
things, once they have proved themselves in more than one office, belong
in **DisSysLab itself**, where every office can use them.

## In your office

| You want | Write | Where |
|---|---|---|
| a judgement: classify, summarize, decide | an English role (`.md`) | `roles/` |
| a rule, a count, a calculation, memory | a Python role (`.py`) with one class | `roles/` |
| code shared by several of your roles | a helper module whose name starts with `_` (`_common.py`) | `roles/` |
| a source DisSysLab does not have | one class, called with no arguments, returning the next message or `None` | `sources/` |
| a sink DisSysLab does not have | one class, called with each message | `sinks/` |
| a test of a Python role's logic | a `test_*.py` beside it, calling its `step` function | `roles/` |
| data an office reads | a `.jsonl`, `.json` or `.csv` file, read by `file_source` | the office folder |

A local role, source or sink may not reuse a built-in's name: to change a
built-in role, copy it into `roles/` under a new name (`dsl show <role>`
prints it). `dsl grammar roles` and `dsl grammar sources` have the
details; [recipes/write-a-python-role.md](recipes/write-a-python-role.md)
walks through a Python role, its tests, and its state.

**Start local, always.** A role in your `roles/` folder is yours to change
in a minute; one in DisSysLab is changed by a pull request and an upgrade.

## In DisSysLab

Move something into DisSysLab when **two or more offices** use the same
thing, unchanged, and it has tests:

| What | Where | Also |
|---|---|---|
| a built-in role | `dissyslab/roles/<name>.md` or `.py`, same format as a local role | `dsl roles` lists it automatically |
| a built-in source or sink | a class in `dissyslab/components/sources/` or `sinks/` | an entry in `dissyslab/office/utils.py`'s registry; a row in `docs/SOURCES_AND_SINKS.md` with an example (a test builds every documented example); its class in `dissyslab/office/trust.py` (does it carry other people's words? does it act outside the machine?) |
| a gallery office | `dissyslab/gallery/<name>/` | a row in the gallery README and a test in `tests/e2e/test_examples.py` |

The language itself (the office file, ports, routers, coordinators)
changes only through the specification,
[internals/design/officespeak_revised.md](internals/design/officespeak_revised.md).
[CONTRIBUTING.md](../CONTRIBUTING.md) has the pull-request routine and the
rules the project keeps.
