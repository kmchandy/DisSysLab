# llm_builders.py
import json
from typing import Dict, Any
from openai import OpenAI


def openai_json_builder(
    *,
    model: str = "gpt-4.1-mini",
    response_format: Dict[str, Any] = {"type": "json_object"},
):
    """
    Returns a builder: system_prompt -> (text -> dict).
    The built callable sends: [system: system_prompt, user: text] and parses JSON.
    """
    client = OpenAI()

    def builder(system_prompt: str):
        def llm_fn(text: str) -> Dict[str, Any]:
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                response_format=response_format,
            )
            raw = getattr(resp, "output_text", None) or (
                # fallback if SDK exposes choices/messages instead
                resp.choices[0].message.content if hasattr(
                    resp, "choices") else ""
            )
            return json.loads(raw or "{}")
        return llm_fn

    return builder
