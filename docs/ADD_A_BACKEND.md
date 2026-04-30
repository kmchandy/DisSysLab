# How to add a new LLM backend

DisSysLab routes every LLM call through a tiny Protocol — a single
`complete(system, user, ...)` method. To use OpenAI, Gemini, a local
SLM via Ollama, or anything else, you write a class that implements
that one method, register it under a name, and set `DSL_BACKEND` to
that name.

You do **not** need to fork dissyslab. Everything below works against
a stock `pip install dissyslab`.

## The three steps

1. Write a class with a `complete` method.
2. In a small Python module, call `register_backend("name", lambda: YourBackend())`.
3. Set two environment variables before running `dsl run`:
   ```bash
   export DSL_BACKEND_MODULE=path.to.your.module   # tells dsl to import it
   export DSL_BACKEND=name                         # tells dsl to use it
   ```

`dsl doctor` will show you both env vars and the active backend so you
can confirm you got the wiring right.

## A working example you can run today

DisSysLab ships with a sample folder you can copy and adapt:

```bash
cp -r examples/custom_backend ~/my_backend
cd ~/my_backend
export DSL_BACKEND_MODULE=mock_backend
export DSL_BACKEND=mock
python -c "from dissyslab.backends import get_backend; print(get_backend().complete(system='hi', user='hello'))"
```

You'll see the mock backend's response — proof that an out-of-package
backend can be plugged in via env vars alone, no fork required.

## The Protocol

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

That's the whole interface. Take a system prompt and a user message,
return raw text. The caller (`ai_agent`, the build-time compiler)
parses JSON or strips markdown fences as needed — your backend never
has to.

The reference implementation is `dissyslab/backends/anthropic_backend.py`
— under 80 lines including docstrings.

## Worked example: an OpenAI backend (~30 lines)

Save as `my_openai_backend.py`:

```python
import os
from typing import Optional
from openai import OpenAI                       # pip install openai
from dissyslab.backends import register_backend


class OpenAIBackend:
    """OpenAI Chat Completions wrapped in the DisSysLab Backend Protocol."""

    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self, model: Optional[str] = None) -> None:
        self._default_model = model or self.DEFAULT_MODEL
        self._client: Optional[OpenAI] = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY not set in environment.\n"
                    "Get a key at https://platform.openai.com/api-keys "
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


# Register at import time. dissyslab will import this module if you
# set DSL_BACKEND_MODULE=my_openai_backend.
register_backend("openai", lambda: OpenAIBackend())
```

Then in your shell:

```bash
pip install openai
export OPENAI_API_KEY=sk-...
export DSL_BACKEND_MODULE=my_openai_backend
export DSL_BACKEND=openai

dsl run my_office
```

That's it — every agent in every office now talks to GPT-4o-mini
instead of Claude, with no other changes.

## Worked example: a Gemini backend (~35 lines)

Same shape, different SDK. Save as `my_gemini_backend.py`:

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
                "GOOGLE_API_KEY not set in environment.\n"
                "Get a key at https://aistudio.google.com/app/apikey"
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

Same `DSL_BACKEND_MODULE` + `DSL_BACKEND` wiring, just `gemini`
instead of `openai`.

## Worked example: a local SLM via Ollama (~25 lines)

If you have [Ollama](https://ollama.com) running locally with a model
pulled (`ollama pull llama3.2`), the backend is just:

```python
import requests
from typing import Optional
from dissyslab.backends import register_backend


class OllamaBackend:
    DEFAULT_MODEL = "llama3.2"

    def __init__(self, host="http://localhost:11434",
                 model: Optional[str] = None) -> None:
        self.host = host
        self._default_model = model or self.DEFAULT_MODEL

    def complete(self, *, system, user,
                 max_tokens=1024, temperature=1.0, model=None) -> str:
        r = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": model or self._default_model,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": temperature},
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

No API key, no per-call cost — useful for classroom use where you
want students to hit a shared local server.

## Caveats

**Build-time prompts expect strict JSON.** The compiler that turns
your `office.md` into Python (in `dissyslab/office/utils.py`) sends
prompts that ask the LLM for a JSON object and parses the reply. A
backend that produces meandering prose, hallucinates extra fields, or
wraps replies in conversational filler will fail at build time. Test
your backend against `dsl build <some_office>` first; if `dsl build`
works, `dsl run` will too. Models in the GPT-4o / Claude Sonnet /
Gemini 1.5 tier handle this reliably; smaller local models often
need a system-prompt nudge ("Reply with JSON only, no commentary").

**Cost and latency are yours to manage.** Some backends charge per
token and rate-limit aggressively. The shipped `dissyslab` CLI doesn't
estimate costs across providers — partly because adding multi-LLM
support is exactly what this doc enables, and per-provider price
tables are brittle. If you need cost tracking, wrap your `complete`
method to log token counts.

**The Protocol may grow.** If a future dissyslab needs streaming,
tool calls, or vision, the Protocol will gain optional methods.
Backends that only implement `complete` will keep working — additions
are designed to be opt-in.

## See also

- [`dissyslab/backends/base.py`](https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/backends/base.py)
  — the Protocol definition.
- [`dissyslab/backends/anthropic_backend.py`](https://github.com/kmchandy/DisSysLab/blob/main/dissyslab/backends/anthropic_backend.py)
  — the reference implementation.
- [`examples/custom_backend/`](https://github.com/kmchandy/DisSysLab/tree/main/examples/custom_backend)
  — a runnable mock backend that demonstrates the registration
  pattern end-to-end without any external LLM.
