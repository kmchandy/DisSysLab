# Add a model backend

How to plug a language model DisSysLab does not ship with into it,
without changing DisSysLab. [LANGUAGE_MODELS.md](../../LANGUAGE_MODELS.md)
lists the backends that are built in (Claude, GPT, Gemini, OpenRouter,
Ollama) and explains how offices choose one.

`mock_backend.py` is the smallest possible backend: about 25 lines, no
model at all. It always replies with the same sentence.

## Step 1: register it, and call it

From this folder:

```bash
python -c "import mock_backend; from dissyslab.backends import get_backend; \
           print(get_backend('mock').complete(system='hi', user='hello world'))"
```

```
[mock backend] received system=2 chars, user=11 chars. user-msg[:80]='hello world'
```

Importing the module ran its last line, `register_backend("mock", ...)`,
and from then on `mock` is a backend like any other.

## Step 2: use it in an office

`dsl` imports the module named in `DSL_BACKEND_MODULE` before it does
anything else, so it must be importable: put this folder on `PYTHONPATH`.

```bash
dsl init inbox_sorter sorter
cd sorter
export PYTHONPATH=..                  # the folder with mock_backend.py
export DSL_BACKEND_MODULE=mock_backend
export DSL_BACKEND=mock
dsl doctor                            # Backend: active: mock
dsl run .
```

```
Run summary (messages):
  sorter::Rex               sent      0   received      0
  sorter::Tri               sent      0   received      4   failed      4
  ...
  sorter::Tri failed on 4 message(s) and they were not processed.
    first failure: its reply does not fit its front matter: the reply is not JSON.
  The office finished; this work did not. `dsl run` exits non-zero.
```

Every message failed, because the mock's reply is a sentence, not the
JSON object the triage role asks for. This is what a model that does not
follow a role's instructions looks like, and why the guardrails exist:
nothing was passed on, every failure was counted, and the run ended
non-zero. (Instead of `DSL_BACKEND`, `Tri: triage(ai="mock")` in
`office.md` would use the mock for that one agent.)

## Step 3: make it real

Copy `mock_backend.py`, rename the class and the registered name, and
replace the body of `complete()` with a call to your model:

- `system` is the role's text, exactly as written in its `.md` file;
- `user` is the incoming message, as JSON;
- return the model's reply as a string.

DisSysLab does everything else: unwrapping one code fence, reading the
JSON, checking it against the role's `out:` line, and counting failures.
