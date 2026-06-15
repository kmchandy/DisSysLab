# Custom backend example

Demonstrates how to plug a non-Anthropic LLM into DisSysLab without
forking the package. See [`docs/LANGUAGE_MODELS.md`](../../LANGUAGE_MODELS.md)
for the full walkthrough, including OpenAI, Gemini, and Ollama
examples.

## What's here

- `mock_backend.py` — a 30-line backend that doesn't call any real
  LLM. Useful as a smoke test of the registration mechanism.

## Try it

From this folder:

```bash
export DSL_BACKEND_MODULE=mock_backend
export DSL_BACKEND=mock

python -c "from dissyslab.backends import get_backend; \
           print(get_backend().complete(system='hi', user='hello world'))"
```

Expected output:

```
[mock backend] received system=2 chars, user=11 chars. user-msg[:80]='hello world'
```

`dsl doctor` will also show that the active backend is `mock` and that
`DSL_BACKEND_MODULE` is set, so you can confirm the wiring before
running an office.

## What to adapt

Copy `mock_backend.py`, rename the class, replace the body of
`complete()` with a real API call, and change the `register_backend`
name. That's it — the rest of DisSysLab calls your backend through the
Protocol with no other changes.
