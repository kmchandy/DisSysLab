# Who reads what, and why `office.md` has a grammar

A design note. It records an argument that kept being re-derived while
writing the front door, and it settles two recurring questions: who is
supposed to write `office.md`, and why the language is small and rigid
rather than expressive.

Status: living. Extended when a new reader or a new surface appears.

---

## 1. Four readers, not one

Most of the difficulty in describing this project came from treating
"the reader" as a single person. There are four, and they want opposite
things from the same file.

### The user

Has an AI agent. Wants a system that runs. Should never author
`office.md`.

Hand-writing `office.md` when the agent will write it is hand-writing
HTML because one owns a page builder. The user does read the file — to
check that the agent built what they meant, and to see what changed
after a revision. **The office is the artifact of record; the agent is
the interface to it.** Read, never write.

This is the reader the README is for.

### The student

Also builds by talking, first. The pedagogy runs in the opposite
direction from authoring.

The course's measure of success is that *a first-year builds an app they
care about, then studies the algorithms underneath it*. The order
matters: the student produces a working office by conversation, and only
then opens it. So `office.md` is a **reading surface** for students, not
a writing surface. The same is true of the roles and, later, of
`dissyslab/core.py` — each is something to open once the student has a
reason to care what is inside.

A student without access to an agent is a real case in a class of
thirty. Provision for it belongs in `course/`, not on the front page.

### The contributor

Writes Python roles, library components, sources and sinks. Needs the
primitives, the registries, and the internals. This is the only reader
who works below the office boundary, and the third door on the front
page.

### The agent

The reader that is easy to forget, and the one that justifies the
grammar's existence.

`office.md` is small and rigid **not so that humans can write it, but so
that `dsl check` can catch what a language model got wrong before it
runs.** A more expressive language would be more pleasant to write by
hand and would defeat its own purpose: the narrower the grammar, the
more of a generated office can be checked statically. Every restriction
in the language is a class of generated fault that becomes detectable.

This inverts the usual reading of the design. The grammar is not a
concession to non-programmers. It is a type system for output nobody
proofread.

---

## 2. Consequences

**The front door is agent-first.** "Build offices by hand" is not a door
on the README, because hand-authoring was never the intended path. It
was removed for that reason, not because it moved elsewhere.

**The grammar reference is course material.** `docs/BUILD_APPS.md`
describes a language the user does not write and the student reads
rather than composes. It belongs with the material that teaches how the
system works, not with the reference a user consults.

**`dsl check` is a first-class part of the story, not a utility.** It is
the mechanism that makes generated concurrency trustworthy at all. A
README that mentions it only under "tools" has mis-stated what the
project is.

**Readability of `office.md` serves inspection, not authorship.** When
weighing a change to the language, the question is not "is this easier
to write?" but "does this keep the office legible to someone checking
it, and checkable by `dsl check`?" Those two, in that order.

---

## 3. What this does not settle

Whether the checks should extend beyond structure. `dsl check` reports
structural faults (W1–W8). Domain checks that run against a *generated*
component exist in one place — `gallery/apps/paper_trader/`, whose
bundled skill runs a contract, determinism and look-ahead check on a
strategy the skill's author never saw. Whether that pattern belongs in
the foundation skill, and what its office-level analogue would be, is
open.

See also: `../reference/architecture.md`, and
`termination_detection_design.md` for the properties `dsl check` cannot
reach.
