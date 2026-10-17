# DisSysLab documentation

**Start with [GETTING_STARTED.md](GETTING_STARTED.md).** It takes you from
installing DisSysLab to building your own office, one checked step at a
time, and shows the output you should see at each step.

The reference for the office language ships with DisSysLab, so it always
matches the version you have:

```bash
dsl grammar              # how office.md is written
dsl grammar roles        # roles, in English or in Python
dsl grammar sources      # every source and sink, and their arguments
dsl grammar examples     # four gallery offices explained in full
```

## In this folder

| Document | Read it when |
|---|---|
| [GETTING_STARTED.md](GETTING_STARTED.md) | first: install, run, break, and build an office |
| [recipes/](recipes/README.md) | you want to do one specific thing: filter news, write a Python role, read your inbox, send to Slack, nest offices |
| [SOURCES_AND_SINKS.md](SOURCES_AND_SINKS.md) | you want a source or sink's details: arguments, message shape, setup |
| [LANGUAGE_MODELS.md](LANGUAGE_MODELS.md) | you want a different model, for the whole office or one agent |
| [PATTERN_sense_think_respond.md](PATTERN_sense_think_respond.md) | your office watches sources, analyses each item several ways, and responds |
| [API_KEY_SETUP.md](API_KEY_SETUP.md) | `dsl doctor` says your key is missing or malformed |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | something fails and the message did not tell you enough |
| [WINDOWS.md](WINDOWS.md) | you are on Windows |
| [EXTENDING.md](EXTENDING.md) | you are deciding whether something belongs in your office or in DisSysLab itself |

## Find it by task

| I want to | Go to |
|---|---|
| copy an example office | `dsl list`, then `dsl init <office> <folder>` |
| find every problem in my office | `dsl check .` |
| see my office as a picture | `dsl draw . --mermaid` |
| know which roles are built in | `dsl roles`, then `dsl show <role>` |
| keep only some messages | [recipes/filter-for-a-topic.md](recipes/filter-for-a-topic.md) |
| write a rule instead of a prompt | [recipes/write-a-python-role.md](recipes/write-a-python-role.md) |
| join two streams of messages | `dsl grammar`, Coordinators; the gallery's `room_climate_monitor` |
| keep one item in progress at a time | `dsl grammar`, Coordinators; the gallery's `returns_desk` |
| run a loop until a condition holds | `dsl grammar examples`, the `debate` office |
| use an office inside another | [recipes/chain-offices.md](recipes/chain-offices.md) |
| read why my office stalled | [GETTING_STARTED.md](GETTING_STARTED.md), part 4 |
| send results by email or Slack | [recipes/send-messages-outside.md](recipes/send-messages-outside.md) |
| check whether my install works | `dsl doctor` |

Internals (how DisSysLab itself is built, for people changing it) are in
[internals/](internals/README.md); the language specification is
[internals/design/officespeak_revised.md](internals/design/officespeak_revised.md).
