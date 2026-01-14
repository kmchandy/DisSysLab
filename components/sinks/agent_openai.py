# dsl.extensions.agent_openai

from dsl import Graph
from typing import Optional
import os
import json

from openai import OpenAI

# =================================================
#        Get the OpenAI key                       |
# =================================================
try:
    from openai import OpenAI  # imported only when this module is used
except ImportError as e:
    raise RuntimeError(
        "OpenAI support requires: pip install 'DisSysLab[llm]'") from e


def _resolve_openai_key() -> str:
    try:
        from dsl.utils.get_credentials import get_openai_key
        return get_openai_key()
    except Exception:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ValueError(
                "OPENAI_API_KEY not found. Put it in your env or .env.")
        return key

# =================================================
#               Agent OpenAI                       |
# =================================================


class AgentOpenAI:
    """
    Instantiate with parameter system_prompt
    """

    def __init__(self,
                 *,
                 system_prompt: str,
                 name: str = None,
                 default_model: str = "gpt-4.1-mini",
                 default_temperature: float = 0.7):
        key = _resolve_openai_key()
        if not key:
            raise ValueError(
                "OPENAI_API_KEY not found. Export it or implement dsl/utils/get_credentials.py"
            )
        self.system_prompt = system_prompt
        self._name = name or self.__class__.__name__
        self.client = OpenAI(api_key=key)
        self.default_model = default_model
        self.default_temperature = default_temperature

    @property
    def __name__(self):  # so graph builder can read a.__name__
        return self._name

    def __call__(
        self,
        msg: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        mdl = model or self.default_model
        temp = self.default_temperature if temperature is None else temperature
        r = self.client.responses.create(
            model=mdl,
            input=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": str(msg)},
            ],
            temperature=temp,
        )
        return r.output_text.strip()
    fn = __call__
    run = __call__

    def enrich_dict(self, msg: dict) -> dict:
        """
        Call the agent with msg["text"] and update msg with the parsed JSON result
        """
        ai_response_str = self.__call__(msg["text"])
        ai_dict = json.loads(ai_response_str)
        # enrich the message by adding ai_dict fields
        msg.update(ai_dict)
        return msg
