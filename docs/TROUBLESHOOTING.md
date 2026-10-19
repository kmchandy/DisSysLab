# Troubleshooting

Common errors when installing or running DisSysLab, with the
remedy for each. The first thing to try, in almost every case, is:

```bash
dsl doctor
```

`dsl doctor` says whether DisSysLab works here and whether your API key
is set. `dsl doctor .`, in an office folder, also says whether that
office can run: `dsl check`, the key if it has LLM agents, and the files
its sources read. `dsl doctor --full` adds every dependency, the `.env`
it read, and any optional integrations (Gmail, Slack, webhook URLs). If
the entry below mentions a fix, run `dsl doctor` afterward to confirm it
took.

If the error you're seeing isn't here, open an issue on
[GitHub](https://github.com/kmchandy/DisSysLab/issues) — that's the
fastest way both to get an answer and to flag a gap in this page.

---

## Install errors

### `error: externally-managed-environment`

You ran `pip install dissyslab` against a system Python (often on a
recent Mac with Homebrew, or a Debian-based Linux). Modern Python
distributions block global pip installs to keep system tools from
breaking.

**Fix:** create a virtual environment first.

```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install dissyslab
```

The 60-second snippet in the [README](../README.md) does this in
one line. From here on, every `dsl` command runs against the venv,
not your system Python.

### Pillow / numpy / scipy fails to build a wheel on Python 3.13

DisSysLab pins these for image-processing offices, and on Python
3.13 some platforms still don't have prebuilt wheels, so pip falls
back to building from source — which fails on machines without a C
toolchain.

**Fix:** use Python 3.11 or 3.12 for now.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install dissyslab
```

If you don't have an older Python installed, on Mac:
`brew install python@3.12`. On Ubuntu/Debian: `sudo apt install
python3.12 python3.12-venv`.

### `command not found: dsl` after pip install

The `dsl` script is installed into the venv's `bin/` directory.
You'll see this error if (a) you didn't activate the venv, or (b)
you installed into one venv and are running from a different
shell.

**Fix:** activate the venv that contains dissyslab.

```bash
source .venv/bin/activate
which dsl       # should print a path inside .venv/bin
which python    # should print a path inside .venv/bin
```

If `which dsl` and `which python` print paths in different
directories, your shell is using two different Python
installations. Reactivate the right venv.

---

## API-key errors

### `dsl run` failed: `ANTHROPIC_API_KEY isn't set`

Your office can't reach Claude because it can't find the key.

**Fix:** set it for the current shell.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or, more permanently, put it in a `.env` file in your course folder
(or the office folder; `dsl` looks in the folder you run it from and
every folder above it):

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

Run `dsl doctor` from inside the office folder: it names the `.env` it
found and says whether the key is set.

### `Anthropic rejected the API key (HTTP 401)`

The key is set but the server rejects it. Almost always one of:

- The key was copied with extra whitespace or quotes. Re-copy it
  from `console.anthropic.com` → Settings → API Keys, paste it
  raw, no surrounding quotes.
- The key was revoked or the project it belongs to is suspended.
  Generate a new key.
- The key is for the wrong workspace. If you have multiple
  Anthropic workspaces, make sure the key belongs to the one with
  budget.

After fixing, run `dsl doctor` to confirm.

### Office runs but shows nothing

Read the run summary first: it counts, for every agent, the messages it
received and sent, so it shows where they stopped.

- **The source sent nothing.** Its `sent` count is 0, and the run ends
  with `the office ran but produced nothing`, naming the source. A file
  path that does not exist, a feed that returned nothing, or credentials
  that expired.
- **A router sent everything elsewhere.** The router's `sent` count is
  right, but the screen is not where those messages went. `dsl draw .`
  shows where each outbox leads. While developing, send rejects to a
  `jsonl_recorder` rather than `discard`, so you can read them.
- **A poll-based source is waiting.** `bbc_world(poll_interval=600)`
  waits ten minutes between checks. Use a small `max_articles` and no
  `poll_interval` while testing.

## Office errors

These are the messages from `dsl check` and `dsl run` about the office
itself. [GETTING_STARTED.md](GETTING_STARTED.md), part 4, breaks an
office on purpose to show each one, and how to read it.

### `problem: line N: ...` from `dsl check`, or `cannot start`

The office is wrong at that line of `office.md` (or of the role file it
names). The message says what is wrong and suggests the nearest name.
`dsl run` refuses an office with a problem; fix it and check again.

### `failed on N message(s) and they were not processed`

A role's reply did not fit its `out:` line (the first failure says how),
or a Python role raised an exception (the traceback ends at the line of
your file that raised it). Each failure costs that one message; the
office carries on, and `dsl run` exits non-zero.

### `Stalled: X holds ... it will never arrive`

An agent holds work it can never finish: a gate whose `done` never comes,
a synchronizer group missing a message. The lines below it follow the
connections backwards from what it is waiting for; look for the agent
you expected on that path and cannot find. Usually a message was lost
earlier (a failure above it), or a connection is missing.

### `dsl run` keeps running

An office with a live source (a feed with `poll_interval`, `gmail`,
`webhook`) runs until you stop it. Press Ctrl-C: it says
`Stopped (Ctrl-C).`, prints the run summary, and exits.

---

## Networking errors

### `OSError: Address already in use` (webhook source)

The port your webhook source wants to bind is held by another
process. Most often: you Ctrl-C'd a previous run and the OS is
still holding the socket in TIME_WAIT for ~30 seconds.

**Fix:** wait 30 seconds and retry, or pick a different port.

```
sources:
    hook: webhook(port=9001)
```

If the port is held by a different application entirely, find
which one:

```bash
lsof -i :8000     # Mac/Linux
netstat -ano | findstr :8000    # Windows
```

### ngrok URL prints, but no requests reach my laptop

The tunnel is up but the upstream service can't reach it. Common
causes:

- **You typed the URL without the path.** The webhook source
  listens on `/webhook` by default, so the upstream service must
  POST to `https://abc123.ngrok.app/webhook`, not the bare URL.
- **The upstream service is sending GET, not POST.** The webhook
  source only accepts POST. Check the upstream service's logs.
- **A corporate firewall is rewriting the request.** Try the
  Cloudflare Tunnel alternative shown in the
  [receive-webhooks recipe](recipes/receive-webhooks.md).

Test your tunnel with curl from another machine before pointing a
real upstream service at it:

```bash
curl -X POST https://abc123.ngrok.app/webhook \
  -H 'Content-Type: application/json' \
  -d '{"title":"test","text":"hello"}'
```

---

## Gmail errors

### `Gmail rejected the login` / IMAP `AUTHENTICATIONFAILED`

Gmail requires an *app password*, not your regular Google
password. You also need 2-Step Verification turned on.

**Fix:** generate an app password.

1. Go to `myaccount.google.com` → Security → 2-Step Verification.
   Turn it on if it isn't already.
2. Same page → App passwords → generate one for "Mail" on "Other".
3. Copy the 16-character password (it shows once).
4. `export GMAIL_USER='you@gmail.com'`
5. `export GMAIL_APP_PASSWORD='<the 16-char password>'`

Then run `dsl doctor` to confirm both env vars are visible.

The full walkthrough is in the
[monitor-your-inbox recipe](recipes/monitor-your-inbox.md).

---

## Platform-specific notes

### Windows

- Use `.venv\Scripts\activate` instead of `source .venv/bin/activate`.
- `pbpaste` doesn't exist. Use `Get-Clipboard` in PowerShell, or
  paste the key directly: `setx ANTHROPIC_API_KEY "sk-ant-..."`.
  After `setx`, open a new shell — the variable doesn't appear in
  the shell that ran the command.
- If `dsl` isn't found after activation, run
  `python -m dissyslab.cli ...` instead (`python -m dissyslab.cli doctor`).

### Apple Silicon (M1/M2/M3)

DisSysLab runs natively on arm64. If you have an Intel Python
installed (e.g. via the official Mac installer rather than
Homebrew), some scientific wheels may build slowly. Easiest fix is
to use Homebrew Python: `brew install python@3.12`.

---

## When the error isn't on this page

`dsl run` prints the full Python traceback for unmapped errors.
Read the **last line** of the traceback first — that's the actual
exception, with a class name like `ValueError`, `RuntimeError`, or
the name of an external service. The lines above it are the call
chain; usually the first line that mentions a file under
`dissyslab/` (not under `anthropic/` or `requests/`) is where the
real problem is.

Search the traceback's last line on
[GitHub issues](https://github.com/kmchandy/DisSysLab/issues). If
nothing matches, open a new one with the full traceback, your
office's `office.md`, and the output of `dsl doctor`. We aim to
turn each new issue into an entry on this page.
