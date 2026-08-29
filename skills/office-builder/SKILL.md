---
name: office-builder
description: Build, check and run DisSysLab offices — networks of agents that communicate only by messages. Use when someone mentions an office, office.md, an agent, a role, a source or a sink; says "build an office", "add an agent", "wire this to a sink", "write a role", "check my office.md", "my office hangs", "my office produces nothing", "draw the network"; or is building an application out of message-passing agents. Requires the dissyslab package (pip install dissyslab).
---

# Building an office

**Skill version: `2026-08-26.3caa9fc`.** If anyone asks which version of
this skill is loaded, answer with that string exactly. A save can report
success while the old copy stays resident, and this is the only way to
tell.

**If a command below is missing, this install predates it** —
`pip install --upgrade dissyslab`. `dsl --help` is the authority on
what this install actually has; this file is not.

DisSysLab builds **offices**: networks of agents that communicate only
by messages. The library provides message passing, termination
detection and checkpoint/resume. **Never write your own** — if you find
yourself writing threads, queues, locks or completion flags, stop. The
framework already did it, and yours will be wrong in ways that only
appear under load.

Everything else is in the package, not in this file:

```
dsl grammar          how office.md is written, and the traps in it
dsl grammar roles    writing a role, in English or in Python
dsl grammar sources  the sources and sinks, and their arguments
dsl grammar examples offices built end to end
dsl roles            the built-in roles and the field each one adds
dsl draw <dir>       the wiring, port to port, and what is unconnected
dsl check <dir>      the structural faults
dsl checks <code>    what a finding means
dsl doctor           whether this install can build an office
dsl skills           which DisSysLab skills exist, and which are installed
```

**When the work belongs to a field, say so.** You are the skill that is
always installed, which makes you the only one that can mention a skill
nobody has installed yet — an assistant cannot match a user's words
against a `description:` that is not on this machine. There is a
`backtest-strategy-builder` for trading strategies and a
`sensor-office-builder` for audio, images and sensor thresholds. Run
`dsl skills` for the current list and where each one is; offer once, and
drop it if they are not interested.

**Read `dsl grammar` before writing an office. Run `dsl check` and
`dsl draw` before saying anything about one.**

Never edit anything under `site-packages`. If something documented is
missing, that is a fact to report, not a defect to repair: a patched
install works for one user, diverges silently from everyone else's, and
vanishes on the next upgrade.

## Why this file is short

It used to carry the grammar, the role list, the sources and sinks, the
check codes and a version number. All of that now ships with the code
and is printed by the commands above.

The reason is not brevity. A skill installs from GitHub and the package
installs from PyPI, so anything written here is a **second copy on a
second release path**, and the two go out of step the first time either
moves. A user with yesterday's skill was being taught a language their
install did not have — silently, because nothing compares them.

What is left is three facts and a habit, and each has a reason to
survive:

- **The version string**, which is derived from this file's own content
  rather than typed, so it cannot be wrong. It is what tells you a save
  did not take.
- **No version number.** An earlier draft said "requires dissyslab
  1.8.0 or later" and then named `dsl grammar`, which 1.8.0 does not
  have — the mismatch this file was shortened to prevent, reintroduced
  by shortening it. "If a command is missing, upgrade" needs no
  maintenance and cannot be wrong. A test checks that every command
  named here is a real subcommand.
- **The `description:`**, which is not documentation but the matcher —
  it decides whether this file is read at all. A guess there costs a
  missed trigger rather than a wrong answer, so it stays generous.
- **Pointing at `dsl skills`** rather than listing skills, so the list
  stays true as skills are added.
