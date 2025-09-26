from dsl import Graph
from typing import Optional
import os

from openai import OpenAI


def from_list(items):
    for item in items:
        yield item


def to_list(v, target):
    target.append(v)

# =================================================
#        Get the OpenAI key                       |
# =================================================


def _resolve_openai_key() -> Optional[str]:
    try:
        from dsl.utils.get_credentials import get_openai_key
        return get_openai_key()
    except Exception:
        return os.environ.get("OPENAI_API_KEY")


class OpenAIAgent:
    """
    Generic LLM transform. System prompt is supplied per-call via params.
    """

    def __init__(self, *, default_model: str = "gpt-4.1-mini", default_temperature: float = 0.7):
        key = _resolve_openai_key()
        if not key:
            raise ValueError(
                "OPENAI_API_KEY not found. Export it or implement dsl/utils/get_credentials.py"
            )
        self.client = OpenAI(api_key=key)
        self.default_model = default_model
        self.default_temperature = default_temperature

    def fn(
        self,
        msg: str,
        *,
        system_prompt: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        mdl = model or self.default_model
        temp = self.default_temperature if temperature is None else temperature
        r = self.client.responses.create(
            model=mdl,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str(msg)},
            ],
            temperature=temp,
        )
        return r.output_text.strip()


agent = OpenAIAgent()
system_prompt = "Determine sentiment score in -10..+10 with -10 most negative, +10 most positive, and give a brief reason."

reviews = [
    "The movie was great. The music was superb!",
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]

results = []
g = Graph(
    edges=[("src", "my_agent"), ("my_agent", "snk")],
    nodes={
        "src": (from_list, {"items": reviews}),
        "my_agent": (agent.fn, {"system_prompt": system_prompt}),
        "snk": (to_list, {"target": results}),
    },
)
g.compile_and_run()

if __name__ == "__main__":
    for result in results:
        print(result)
        print("")
