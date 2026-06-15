import requests
from typing import Optional
from dissyslab.backends import register_backend


class OllamaBackend:
    # default model was "llama3.2:3b"
    DEFAULT_MODEL = "qwen2.5:7b" 

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