# Troubleshooting

Common errors when installing or running DisSysLab, with the
remedy for each. The first thing to try, in almost every case, is:

```bash
dsl doctor
```

`dsl doctor` checks your Python version, that every dependency is
importable, that your API key is set, and that any optional
integrations (Gmail, Slack, webhook URLs) are wired correctly. If
the entry below mentions a fix, run `dsl doctor` afterward to
confirm it took.

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

Or, more permanently, put it in a `.env` file inside the office
folder:

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
```

`dsl` loads `.env` automatically when it finds one. Run `dsl
doctor` from inside the office folder to confirm the key is
visible.

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

### Office runs but produces no output, no error

The office started, the agents are alive, the source is polling —
but nothing reaches the terminal. Two common causes:

- **The source has nothing to send yet.** A poll-based source like
  `bbc_world(poll_interval=600)` waits 10 minutes between polls,
  and only emits articles published since the last poll. Drop
  `poll_interval` to something small (e.g. `60`) for testing, or
  use a source like `hacker_news` that returns the current top
  stories on first call.
- **The agent's role description doesn't match what's coming in.**
  If a role says "filter for political news" and the source
  produces sports headlines, every message is discarded silently.
  Check the role description and the source independently.

A future `dsl run --debug` flag will print each agent's incoming
messages and outgoing responses; until then, `jsonl_recorder` is
the easiest way to see what's actually flowing through. Wire one
to the source's destination port and tail the file.

---

## Networking errors

### `OSError: Address already in use` (webhook source)

The port your webhook source wants to bind is held by another
process. Most often: you Ctrl-C'd a previous run and the OS is
still holding the socket in TIME_WAIT for ~30 seconds.

**Fix:** wait 30 seconds and retry, or pick a different port.

```
Sources: webhook(port=9001)
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
  `python -m dissyslab.cli ...` instead.

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
