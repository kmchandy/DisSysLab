# Working on DisSysLab

Instructions for a Claude session working on this repository. Read
this before touching anything.

## Start here

`docs/internals/STATUS.md` — one page: what is true now, what is open,
in what order. It is the only status document kept current. Then
`docs/internals/reference/architecture.md`, then the *overview* half of
whichever module you are about to change.

The measure of success, against which everything is prioritised:

> A first-year builds an app they care about, then studies the
> algorithms underneath it.

The course runs 4 January – 10 March 2027.

## Two filesystems, and why that matters

If you are running in a cloud container with a bridge to Mani's
desktop, there are **two separate copies of this repository**:

- **your clone**, in the container, where you edit, run tests, commit;
- **his clone**, on his Mac, reachable through the device bridge, which
  is the one that pushes to GitHub.

Nothing you commit reaches him unless you hand it over deliberately.
Confusing the two has cost this project several hours: work was
committed in the container while he ran `git push` on his machine and
was told everything was up to date.

**GitHub is the only sync point.** If you can push directly, most of
what follows is unnecessary — say so and set that up. Otherwise:

## The sharing protocol

**Fetch first, always.** Start every working block with
`git fetch origin` and reset onto it. Your "ahead of origin" count is
then exactly the work he has not seen. Forgetting this is the bug that
produces every other problem here.

**Bundles carry everything that belongs in git.**
`git bundle create <file> origin/main..HEAD`, delivered to his disk.
He runs `git fetch <bundle> HEAD && git merge FETCH_HEAD`, tests,
pushes.

**Never write a tracked file into his repository.** Writing a file to
his disk *and* shipping the same file in a bundle guarantees his
working tree diverges from his HEAD, which blocks the merge. This
happened three times before the rule was written. If he should read
something before merging, send it as a chat attachment.

**Direct writes only for what git does not track** — drafts, generated
workbooks, messages — and say so each time.

**One bundle in flight.** Build it, wait for him to apply and push,
fetch, then continue. Do not stack a second bundle on the first.

**Re-stage before editing anything he may have touched.** One call,
and it prevents overwriting his edits. It has been skipped twice, and
both times cost more than the call would have.

## Hard constraints of the bridge

**Never run git on his machine.** `device_bash` cannot delete files,
so any command that leaves `.git/index.lock` leaves it for ever, and
every later git command fails. Even `git status` writes the index. If
you need his repository's state, read files, not git.

**`device_bash` cannot delete.** To remove something, move it into a
`_to_delete/` folder under the same mounted folder and tell him.

**His Cowork Linux VM has no network** and does not have `dissyslab`
installed. It is a sandbox for file work, not a place to run the
framework. He runs `dsl` from his Mac Terminal.

**Resolve merge conflicts by writing files, not by running git.** Strip
the markers, keep the right side, tell him to `git add` and commit.

## Standing habits

**When a document and the code disagree, do not only fix the
document.** Ask what would have caught it, and add that.
`tests/integration/test_docs_match_code.py` exists for this; every
section of it came from a divergence that shipped.

**Verify claims about the code by running them.** This document's own
predecessors asserted that a line parsed when it did not, and that a
class existed under a name it did not have. Both were caught by
running the thing rather than reading it.

**A branch never taken is a branch never tested.** A graceful fallback
is very good at hiding the path everyone actually uses.

**Prefer the smallest reversible step**, and say plainly what was not
done.
