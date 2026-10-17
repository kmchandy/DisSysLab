# Language models in DisSysLab

An English role (a `.md` file in `roles/`) is run by a language model. The
model receives the role's text, followed by the message as JSON, and its
reply is checked against the role's `out:` line. Which model runs it is a
setting, not part of the role: the same office can run on Claude, on GPT,
or on a model on your own laptop.

Python roles use no model and need no key.

## The default: Claude

With nothing set, every English role uses Anthropic's Claude
(`claude-sonnet-4-5`). It needs one thing, a key in `ANTHROPIC_API_KEY`;
[GETTING_STARTED.md](GETTING_STARTED.md), part 5, shows how to put it in a
`.env` file. This is what the course uses.

## Choosing the model for every agent: `DSL_BACKEND`

To run a whole office on another model, set `DSL_BACKEND`, in the shell or
in `.env`:

```bash
export DSL_BACKEND=openai        # Windows PowerShell: $env:DSL_BACKEND="openai"
dsl run .
```

| `DSL_BACKEND` | Model | Needs |
|---|---|---|
| `anthropic` (or `claude`) | Claude, by Anthropic | `ANTHROPIC_API_KEY` |
| `openai` (or `gpt`) | GPT, by OpenAI | `OPENAI_API_KEY`; `OPENAI_MODEL` to pick one |
| `gemini`, `gemma` | Google's models, via AI Studio | `GEMINI_API_KEY` (or `GOOGLE_API_KEY`); `GEMINI_MODEL` |
| `openrouter` | many models, open and closed, via openrouter.ai | `OPENROUTER_API_KEY`; `OPENROUTER_MODEL` |
| `ollama` (or `qwen`) | a model on your own computer, through Ollama | Ollama running; `OLLAMA_MODEL` (default `qwen3:30b`); `OLLAMA_HOST` if not local |

`dsl doctor` shows which backend is active and whether its key is set.

Each name also comes in two other temperatures: `_creative` (1.0) and
`_precise` (0.1), as in `anthropic_precise` or `qwen_creative`. The plain
name is 0.7. A classifier usually wants `_precise`; a writer may want
`_creative`.

## Choosing the model for one agent: `ai=`

An English role takes one argument in `office.md`, `ai=`, which chooses
the model for that agent only. The rest follow `DSL_BACKEND`.

```
agents:
    Qwen: qwen(ai="openrouter")
    GPT: gpt(ai="openai")
    Claude: claude(ai="anthropic")
    Riley: moderator
```

This is the `debate` office: three panellists on three different models,
and a moderator on the default. `ai=` never reaches the prompt; the role's
text is the same whichever model reads it.

`situation_room_pro` uses the same idea for cost: four annotators that
each add one short field run on the default, and only the writer, whose
output a person reads, names a stronger model.

## Running a model on your own computer

[Ollama](https://ollama.com) runs open models locally: free, private, and
offline once downloaded, but slower, and it needs a computer with enough
memory for the model.

```bash
# after installing Ollama from ollama.com:
ollama pull qwen3:8b
export DSL_BACKEND=ollama
export OLLAMA_MODEL=qwen3:8b
dsl run .
```

Smaller models make more mistakes of form: a reply that is not JSON, a
value not in the role's list. The guardrails catch these (each costs one
message, and the run summary counts them), so the run summary is also a
measure of how well a model follows your roles. See below.

## Comparing two models on the same office

The guardrails make a fair comparison easy, because a mistake of form is
counted rather than passed on. Run the same office twice:

```bash
dsl run . > claude.txt 2>&1
DSL_BACKEND=ollama dsl run . > local.txt 2>&1
```

and compare:

1. **Failures.** The run summary's `failed` column, and the first failure
   it quotes: replies that broke `out:`.
2. **Dropped fields.** The summary's note on fields a reply carried that
   `out:` did not declare.
3. **Decisions.** For a role that chooses from a list (`urgent | routine`),
   how often the two models agree, message by message. Where they
   disagree, which one is right is your judgement, not the framework's.

`inbox_sorter` (from the student guide) is a good office to try this on:
four messages, one decision each, and a file source, so both runs see
exactly the same input.

## Adding a backend of your own

A backend is any class with one method:

```python
class MyBackend:
    def complete(self, *, system, user, max_tokens=1024, temperature=1.0, model=None):
        # send `system` (the role's text) and `user` (the message as JSON)
        # to your model; return its reply as a string
        ...
```

Register it from a module of your own, and tell `dsl` to import that
module:

```python
# my_backend.py, somewhere on your PYTHONPATH
from dissyslab.backends import register_backend

register_backend("mine", lambda: MyBackend())
```

```bash
export DSL_BACKEND_MODULE=my_backend
export DSL_BACKEND=mine        # or ai="mine" on one agent
dsl doctor                     # shows: active: mine, DSL_BACKEND_MODULE: my_backend
```

The backend returns the raw reply. DisSysLab does the rest: it reads the
reply as JSON (unwrapping one code fence), checks it against `out:`, and
counts what fails. `dissyslab/backends/anthropic_backend.py` is the
reference implementation, and
[recipes/add-a-backend/](recipes/add-a-backend/) has a runnable example
with a scripted model that needs no key.

## Things to know

- **Cost is per message per English agent.** An office with four English
  annotators and a writer makes five model calls per article. Python
  roles cost nothing; use them wherever no judgement is needed.
- **Rate limits.** Many agents running at once can exceed a provider's
  rate limit (`429`). Wait and run again, or use fewer English agents.
- **The prompt is your text.** DisSysLab adds nothing to a role's
  instruction: what to return is said by the role itself, in its last
  sentence (`dsl grammar roles`). If a model keeps returning the wrong
  shape, that sentence is the first thing to look at.
