# A place for a domain to register a check

**Status: designed, not built.** Nothing described here exists. This is
the record of a decision about where domain checks should live, written
before the first one is enforced, because the first one decides the
shape of all of them.

---

## The problem

The README claims that domain checks "run against code the check's
author never saw." That is true of a check's *implementation* and not
yet of its *invocation*.

The one domain check that exists — look-ahead bias, in
`scripts/manual_checks/check_no_lookahead.py` — is invoked by a
sentence in `skills/backtest-strategy-builder/SKILL.md` telling an
assistant to run it. That makes it a request to a language model. If
the model does not run it, nothing anywhere records that fact, and the
office runs an unchecked strategy and produces a ranking that looks
exactly like a checked one.

The test that decides where a check belongs is: **what does silence
mean?** In a prompt, silence is ambiguous — it could be "checked and
clean" or "never ran", and the second is likelier precisely when
someone is in a hurry. In code on the path, silence means checked.

A second way to say it: the assistant is a builder, and a builder
should not also be the inspector. Every check that lives in a prompt
makes it both.

This matters more with each domain added. With one domain skill,
advisory checks are a known weakness. With five — trading, paper
trading, drug discovery, whatever follows — five fields' worth of
hard-won suspicions are all advisory, and the sentence in the README
gets weaker every time the project grows.

---

## What exists to build on

`check_wiring.py` is already a check engine, for one tier. It reads
`office.md`, computes the graph, and emits `Finding(code, severity,
subject, message, hint, gap)` objects that `dsl check` renders and
`dsl run` refuses on. The `draft` handling — the same finding read as
remaining work rather than as a fault — is the useful precedent: a
check's *verdict* and a check's *meaning* are separate, and the
context decides the second.

What it cannot do is anything requiring execution. Its own docstring
says so, and says knowing which faults are structural and which are
behavioural is itself the lesson. That boundary is the seam this
design runs along.

---

## Two tiers, two hooks

They run at different times, see different things, and should not be
forced into one interface.

### Structural checks — subject is the office

Computed from `office.md` alone. The W-codes are these. A domain adds
its own: a trading office where a strategy agent feeds an order sink
with no validation gate between them is a structural fault, decidable
without running anything.

The guardrail check is also this tier, and is the reason the tier
needs opening to contributors at all: an untrusted source (`web_scraper`,
RSS, news) reaching an acting sink (`webhook_sink`, `gmail_sink`,
`slack_sink`, `mcp_sink`) with no gate between them is reachability on
a graph already computed for W3 and W4.

Run by `dsl check`, so they hold for offices built by an assistant
that loaded no skill, by hand, or by a domain skill nobody has written
yet.

### Behavioural checks — subject is a callable and its parameters

Computed by running generated code against constructed inputs.
Look-ahead, determinism, finiteness, declared range, warm-up. No
judgment, but execution required.

---

## When behavioural checks run

This is the hard question, and the obvious answer is wrong.

The obvious answer is "at assembly, when the agent is constructed."
But `check_no_lookahead(compute_fn, params, bars)` needs bars, and at
assembly no data has flowed. Making the check fetch its own data
couples it to the source and means the check is verifying the strategy
against data the office will not use.

**The proposal is: at first use.** The `backtester` agent receives its
first message; that message carries the bars; before computing
anything the agent runs the checks registered against its contract,
using that message as the sample. The subject and the sample arrive
together, which is the whole difficulty resolved by waiting.

Memoized per `(function, params)`. Eleven backtesters share four
signal functions, so it is four runs, not eleven.

Measured cost, Donchian over 2,520 bars — ten years of daily data:

```
one full compute of the signal:        1.9 ms
check_no_lookahead, every day:         2.27 s   (2520 recomputes)
check_no_lookahead, every 10th day:    0.22 s
```

Nine seconds exhaustive for four families on a run that already does
walk-forward folds and a Monte Carlo distribution. There is no
performance argument for making this optional.

The cost of waiting for first use: the refusal is a run-time refusal,
not a build-time one. The office starts and then stops. That is worse
than failing at `dsl check` and better than not failing, and it is
still before any result exists. An office that stops this way must say
plainly which check failed on which agent and stop cleanly, using the
same shutdown path the timeout fix added.

---

## What a domain registers, and against what

Not against a role name. Against a **contract**.

`_signal_common.py` already defines what a signal function is: bars and
params in, one float per bar out, `signal[t]` depending only on
`bars[0..t]`. Every strategy claims that contract. A check registered
against the contract runs for every strategy that claims it, including
the ones written after the check.

Registering against a role name would mean a check on `mac_signal`
saying nothing about `donchian_signal`, which is exactly the
generality the design is for.

Sketch, not a proposal about syntax:

```python
@behavioural_check(contract="signal", name="no-lookahead")
def check_no_lookahead(fn, params, sample) -> Finding | None:
    ...
```

Findings reuse `Finding`. Codes get a namespace: `W*` stays the
framework's, a domain's checks carry the domain's prefix, so a report
says where a complaint came from and whom to argue with.

**Where the file lives:** in the office's own `roles/` folder,
alongside the roles the domain skill already writes there. No plugin
machinery, no entry points, nothing vendor-specific — the same
directory that already gets loaded. This matters for the project's
open-standard position: a domain skill is still a folder of Markdown
and Python, and its checks travel with the office rather than with a
vendor's packaging.

---

## Required, with the waiver in the file

Look-ahead should be required, not opt-out. The measurement removed
the performance argument, and no strategy has a legitimate reason to
fail it — the property is what makes a backtest mean anything.

Where a waiver is warranted at all, it belongs in `office.md`:

```
BT_DON_20 is a backtester(speed_name='donchian_20', checks=off).
```

Not a command-line flag. A flag is invisible six weeks later; the
office file is the artifact of record, `dsl check` can see the waiver,
and the run report can say *"this run skipped the look-ahead check on
two strategies"* — which is the honest thing for a report to say and
impossible if the waiver lived in someone's shell history.

The report should also say what *did* run. A check nobody can see the
result of is halfway back to being a prompt.

---

## Open questions

**Whether one registry or two.** Written here as two hooks because
they differ in subject and in timing. One registry with a subject kind
is fewer concepts and more indirection. Undecided.

**What a check may do.** A check is arbitrary Python executed at run
time. So is a role, so this adds no trust boundary that offices did
not already have — but it should be said out loud rather than
discovered.

**Slow checks.** A registry invites them. Timing each check and
reporting the cost is cheap insurance; a budget that refuses a check
over some duration is probably over-engineering before there is a
problem.

**Conflicting checks.** Two domains registering against the same
contract with different opinions. No opinion yet; it may not happen.

**`dsl checks`.** A listing subcommand, sibling of `dsl roles` and
`dsl list`: which checks are registered, from which domain, against
which contract. Probably wanted the day the second domain exists.

---

## What this does not fix

It does not make checks smarter. Code checks must be decidable, so
they catch a narrower class than a well-written prompt could describe.
A prompt can say "be suspicious if the result seems too good"; no
registry entry can.

It does not settle intent. Whether the strategy implements the rule
someone had in mind is not checkable, and the project's answer to that
is the conversation and the spreadsheet — devices that make intent
inspectable rather than checks that verify it.

It raises the stakes on the checkers themselves. A check that is wrong
is worse than a prompt that is wrong, because people stop looking. Any
check promoted into this registry needs a test that feeds it a
deliberately broken subject and asserts it fails — `check_no_lookahead`
does not currently have one.

And false positives would destroy the apparatus. A check that fires on
legitimate work trains people to skim the section it prints in, taking
the true findings with it. The same reason `dsl doctor` stopped
reporting an uninstalled domain skill as missing.

---

## Why this is worth building

It is the version of "a domain expert contributes their field's parts
and inherits the concurrency" in which *parts* includes the
suspicions. A chemist writes a check about molecule validity; it is
enforced by machinery they did not write, against strategies written
by someone they never met, in an office assembled by an assistant that
never read their skill.

It is also the pedagogy. The split between what can be checked from
the graph and what needs execution is the same split the course
teaches about deadlock — an office whose diagram is correct can still
hang. A student who has seen a structural check pass and a behavioural
check fail on the same office has met that distinction as a fact
rather than a claim.
