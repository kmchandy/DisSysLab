# Language models in DisSysLab

Every agent role in DisSysLab is, by default, a Claude prompt: when an
agent receives a message, it sends the message to an LLM along with
the role's prompt and routes the reply based on the LLM's `send_to`
field. The LLM is hidden behind a one-method interface — a Backend —
which means you can swap Claude for any other LLM (OpenAI, Gemini,
local SLMs via Ollama, ...) without touching your office files.

This guide covers four things:

1. **The default**: what runs out of the box.
2. **Switching the backend** for a whole office (`DSL_BACKEND`).
3. **Mixing backends inside one office** (one role on Claude, another
   on a local SLM).
4. **Comparing models** — running the same office under different
   backends and measuring the difference.

If your goal is simply to use Claude, only section 1 applies. The
rest is for when you start asking "what if I used a different model
here?"

---

## 1. The default — Claude

A fresh `pip install dissyslab` ships configured to use Anthropic's
Claude API. You set one environment variable:

```bash
echo "ANTHROPIC_API_KEY=<your-key>" > .env
```

and `dsl run <office>` works. There is nothing else to configure.
Every agent in every office calls Claude through the same backend.

`dsl doctor` will show you the active backend:

```
Backend:
  active: anthropic  (default)
```

The default model is `claude-sonnet-4-...` (set in
`dissyslab/backends/anthropic_backend.py`). You can override it
per-call by passing `model=...` into a role's `complete()` call, but
in practice the default is what every gallery office uses.

---

## 2. Switching to a different model

To use a different LLM for an entire office, you do three things:

1. Write a small Python class that implements the **Backend Protocol**
   (one method, `complete()`).
2. Register it under a name with `register_backend("name", lambda:
   YourBackend())`.
3. Set two environment variables before `dsl run`:

   ```bash
   export DSL_BACKEND_MODULE=path.to.your.module   # tells dsl to import it
   export DSL_BACKEND=name                         # tells dsl to use it
   ```

You do not fork DisSysLab. The above works against a stock
`pip install dissyslab`.

`dsl doctor` will confirm the wiring:

```
Backend:
  active: openai
  DSL_BACKEND_MODULE: my_openai_backend
```

### The Backend Protocol

From `dissyslab/backends/base.py`:

```python
class Backend(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 1.0,
        model: Optional[str] = None,
    ) -> str:
        ...
```

That's the entire interface. Take a system prompt and a user message,
return raw text. The runtime parses JSON or strips markdown fences
on its own — your backend never has to.

The reference implementation, `dissyslab/backends/anthropic_backend.py`,
is under 80 lines including docstrings.

---

## 3. Worked examples

Three examples below — OpenAI, Gemini, and Ollama (a local SLM
server). Each is a self-contained Python file you save somewhere on
your `PYTHONPATH` (e.g. your home directory) and reference via
`DSL_BACKEND_MODULE`.

### OpenAI (~30 lines)

Save as `~/my_openai_backend.py`:

```python
import os
from typing import Optional
from openai import OpenAI                       # pip install openai
from dissyslab.backends import register_backend


class OpenAIBackend:
    """OpenAI Chat Completions wrapped in the Backend Protocol."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, model: Optional[str] = None) -> None:
        self._default_model = model or self.DEFAULT_MODEL
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not set. Get a key at "
                    "https://platform.openai.com/api-keys "
                    "then export OPENAI_API_KEY=sk-..."
                )
            self._client = OpenAI(api_key=api_key)
        return self._client

    def complete(self, *, system, user,
                 max_tokens=1024, temperature=1.0, model=None) -> str:
        resp = self._get_client().chat.completions.create(
            model=model or self._default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        )
        return resp.choices[0].message.content


# Registers the backend at import time. dsl will import this module
# when DSL_BACKEND_MODULE=my_openai_backend.
register_backend("openai", lambda: OpenAIBackend())
```

Then in your shell:

```bash
pip install openai
export OPENAI_API_KEY=sk-...
export PYTHONPATH=$HOME:$PYTHONPATH
export DSL_BACKEND_MODULE=my_openai_backend
export DSL_BACKEND=openai

dsl run my_office
```

Every agent in every office now talks to GPT-4o-mini instead of
Claude, with no other changes.

### Gemini (~35 lines)

Same shape, different SDK. Save as `~/my_gemini_backend.py`:

```python
import os
from typing import Optional
import google.generativeai as genai            # pip install google-generativeai
from dissyslab.backends import register_backend


class GeminiBackend:
    DEFAULT_MODEL = "gemini-1.5-flash"

    def __init__(self, model: Optional[str] = None) -> None:
        self._default_model = model or self.DEFAULT_MODEL
        self._configured = False

    def _ensure_configured(self) -> None:
        if self._configured:
            return
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GOOGLE_API_KEY not set. Get a key at "
                "https://aistudio.google.com/app/apikey"
            )
        genai.configure(api_key=api_key)
        self._configured = True

    def complete(self, *, system, user,
                 max_tokens=1024, temperature=1.0, model=None) -> str:
        self._ensure_configured()
        m = genai.GenerativeModel(
            model_name=model or self._default_model,
            system_instruction=system,
        )
        resp = m.generate_content(
            user,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature":       temperature,
            },
        )
        return resp.text


register_backend("gemini", lambda: GeminiBackend())
```

Same wiring (`DSL_BACKEND_MODULE` + `DSL_BACKEND`), just `gemini`
instead of `openai`.

### Local SLM via Ollama (~30 lines)

[Ollama](https://ollama.com) is a local model server. Free, no API
key, runs on your laptop. Pull a small instruction-tuned model first:

```bash
# macOS:
brew install ollama
brew services start ollama

# Then any platform:
ollama pull llama3.2:3b   # 3B params; smaller models often fail JSON
ollama list
```

Save as `~/my_ollama_backend.py`:

```python
import requests
from typing import Optional
from dissyslab.backends import register_backend


class OllamaBackend:
    DEFAULT_MODEL = "llama3.2:3b"

    def __init__(self, host="http://localhost:11434",
                 model: Optional[str] = None) -> None:
        self.host = host
        self._default_model = model or self.DEFAULT_MODEL

    def complete(self, *, system, user,
                 max_tokens=1024, temperature=1.0, model=None) -> str:
        # Smaller models often need a stronger nudge toward valid JSON.
        # Larger models (8B+) usually don't need this and you can
        # delete the next two lines.
        nudge = "\n\nReply with valid JSON only. No commentary."
        system = system + nudge

        r = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": model or self._default_model,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": temperature,
                },
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


register_backend("ollama", lambda: OllamaBackend())
```

Wiring:

```bash
export PYTHONPATH=$HOME:$PYTHONPATH
export DSL_BACKEND_MODULE=my_ollama_backend
export DSL_BACKEND=ollama

dsl doctor                          # confirm "active: ollama"
dsl run dissyslab/gallery/my_first_office/
```

No API key, no per-call cost. Useful when you want to iterate
without running a meter, and necessary when you want to run
DisSysLab on a machine without internet access.

---

## 4. Per-role model choice

`DSL_BACKEND` switches the backend for *every* agent in *every*
office. Sometimes you want one role on Claude (because it's hard
and quality matters) and another role on a local SLM (because it's
cheap and fast and the task is easy).

DisSysLab supports this via `nl_role(prompt, AI="...")`. The `AI`
argument names a registered backend; that role calls *that* backend
regardless of `DSL_BACKEND`.

To use this in an office, drop a Python role file into your
office's `roles_lib/` folder:

```python
# my_office/roles_lib/correspondent_slm.py
from dissyslab.office_v2 import nl_role

role = nl_role(
    prompt="""You are a correspondent. You receive an article and
decide whether it is significant enough to forward to the analyst.

If significant, send to analyst. Otherwise send to discard.""",
    AI="ollama",
)
```

Now in `office.md`:

```
Agents:
Alex is a correspondent_slm.   # uses Ollama (explicit AI="ollama" wins)
Morgan is an analyst.          # uses whatever DSL_BACKEND says
```

The library loader treats `*.py` files in `roles_lib/` as having a
`role` attribute that is an `AgentRoleEntry`. The `AI` argument is
captured at registration time and used whenever that role's agent
runs.

For this to work, the `ollama` backend must be registered. The
cleanest way: keep `DSL_BACKEND_MODULE=my_ollama_backend` in your
shell so the registration runs, then either leave `DSL_BACKEND`
unset (the rest of the office uses Claude) or set it to whatever
backend you want for the *non*-ollama roles.

### Why .md role files follow DSL_BACKEND automatically

Roles loaded from plain `.md` files in `roles/` or `roles_lib/`
always call `nl_role(prompt)` with no `AI` argument. When `AI` is
unset, the role defers the backend choice to run time and uses
whichever backend `DSL_BACKEND` names (or anthropic if `DSL_BACKEND`
is unset). That's what makes a single `export DSL_BACKEND=ollama`
flip every gallery role to ollama with no `.py` overrides needed —
useful when you want to run the whole office on a different model
without touching its files.

The two contrasting rules:

| How the role was built | Backend at run time |
| --- | --- |
| `nl_role(prompt)` (no `AI`) — what `.md` files do | follows `DSL_BACKEND` (or anthropic if unset) |
| `nl_role(prompt, AI="X")` — explicit `.py` files | locked to backend `X`, regardless of `DSL_BACKEND` |

---

## 5. Comparing models in the same office

The most informative thing you can do with multiple backends is run
the same office twice and look at the outputs side by side. The
recipe below uses the gallery's `my_first_office` (HackerNews →
Alex(analyst) → console_printer) but works with any office.

### Setup

Edit the office to write to a file instead of the console, so you
can compare runs offline. In `dissyslab/gallery/my_first_office/office.md`:

```
Sinks: jsonl_recorder(path="output.jsonl")

Connections:
hacker_news's destination is Alex.
Alex's briefing is jsonl_recorder.
```

(The `path` argument names the output file, relative to wherever
you run `dsl run` from.)

### Run with the LLM

```bash
unset DSL_BACKEND                          # use the default (Claude)
dsl run dissyslab/gallery/my_first_office/
# Ctrl-C after ~10 messages
mv dissyslab/gallery/my_first_office/output.jsonl ~/output_llm.jsonl
```

### Run with the SLM

```bash
export DSL_BACKEND_MODULE=my_ollama_backend
export DSL_BACKEND=ollama
dsl run dissyslab/gallery/my_first_office/
# Ctrl-C after ~10 messages
mv dissyslab/gallery/my_first_office/output.jsonl ~/output_slm.jsonl
```

### Compare

Four things are worth measuring:

1. **JSON validity.** What fraction of replies parsed cleanly?
   Claude is essentially 100%; SLMs vary by size.
2. **Routing accuracy.** Did the agent's `send_to` choice make
   sense for the input? Eyeball 10–20 messages.
3. **Output quality.** Pick five articles seen by both backends
   and read the `text` and `significance` fields side by side.
4. **Latency.** Wall-clock time per message. Claude is API-bounded
   (~1–3s typical); Ollama is CPU/GPU-bounded on your laptop and
   varies wildly with model size and hardware.

A small Python script for the validity check:

```python
import json
from pathlib import Path

for label, path in [("LLM", "output_llm.jsonl"),
                    ("SLM", "output_slm.jsonl")]:
    lines = Path.home().joinpath(path).read_text().splitlines()
    valid = 0
    for ln in lines:
        try:
            obj = json.loads(ln)
            if "send_to" in obj and "text" in obj:
                valid += 1
        except json.JSONDecodeError:
            pass
    print(f"{label}: {valid}/{len(lines)} messages produced valid output")
```

### If the SLM struggles

- **Bigger model.** `ollama pull llama3.2` defaults to 3B; some
  models also come in 7B and 8B variants. Bigger = better JSON
  but slower.
- **Lower temperature.** `temperature=0.1` in the backend's
  `complete` method makes the model more rule-following.
- **Stronger prompt nudge.** Spell out the contract: "You MUST
  reply with a JSON object containing exactly the keys 'send_to'
  and 'text'." Some models respond well to "MUST."
- **Different model family.** `qwen2.5:3b`, `phi3.5`, `gemma2:2b`
  vary in their structured-output reliability. If one struggles,
  try another at the same parameter count.

### What "win" means

Quality almost always favors larger models. The interesting
question is rarely "which is better" but "is the SLM good enough
for *this* office?" An office that filters articles by
significance is much more SLM-tolerant than one that writes
journalism in three paragraphs. Reporting that distinction is
where a comparison study earns its keep.

---

## 6. Tradeoffs and caveats

**Run-time prompts ask the agent for JSON.** When an agent receives
a message, it sends a prompt that ends with `Return JSON only ...
{"send_to": "...", "text": "..."}` and the runtime parses the
reply. A backend that produces meandering prose, hallucinates extra
fields, or wraps replies in conversational filler will route
messages incorrectly. Models in the GPT-4o / Claude Sonnet /
Gemini 1.5 tier handle this reliably; smaller local models often
need a system-prompt nudge ("Reply with JSON only, no commentary")
and are usually unreliable below 2–3B parameters.

(Note: there are no *build-time* LLM calls. The compiler that
turns `office.md` into Python is hand-written; only run-time
agent calls go through the backend.)

**Cost and latency are yours to manage.** Some backends charge
per token and rate-limit aggressively. The shipped CLI does not
estimate costs across providers — partly because per-provider
price tables are brittle. If you need cost tracking, wrap your
`complete` method to log token counts.

**The Protocol may grow.** If a future DisSysLab needs streaming,
tool calls, or vision, the Protocol will gain optional methods.
Backends that only implement `complete` will keep working —
additions are designed to be opt-in.

---

## See also

- [`dissyslab/backends/base.py`](https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/backends/base.py)
  — the Protocol definition.
- [`dissyslab/backends/anthropic_backend.py`](https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/backends/anthropic_backend.py)
  — the reference implementation.
- [`examples/custom_backend/`](https://github.com/kmchandy/DisSysLab/tree/main/examples/custom_backend)
  — a runnable mock backend that demonstrates the registration
  pattern end-to-end without any external LLM.
- [`docs/BUILD_APPS.md`](BUILD_APPS.md) — how to build offices
  that run on whichever backend you've configured here.
