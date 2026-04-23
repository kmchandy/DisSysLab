# dissyslab/components/transformers/ai_agent.py

"""
Real AI Agent - Uses the active DisSysLab backend for analysis.

Usage:
    from dissyslab.components.transformers.ai_agent import ai_agent

    analyzer = ai_agent("Analyze the sentiment. Return JSON: {sentiment, score}")
    result = analyzer("I love this!")
    # Returns dict if the model returns JSON, string otherwise

Requirements:
    - ANTHROPIC_API_KEY environment variable (for the default backend)
    - anthropic package: pip install anthropic

The underlying model is selected by the active backend
(`dissyslab.backends.get_backend()`). The default is Claude; students
and other backends can be swapped in via the DSL_BACKEND env var
without changing this file.
"""

import json
import re

from dissyslab.backends import get_backend


def ai_agent(prompt: str):
    """
    Creates an AI transform function from a prompt string.

    Calls the active backend with the given system prompt. If the
    model returns valid JSON, returns a parsed dict. If it returns
    plain text, returns a string. The prompt controls the output
    format.

    Args:
        prompt: System prompt describing the task and desired output format.

    Returns:
        Callable: fn(msg) -> dict | str
            Accepts a string or dict as input.
            Returns a dict if the model's response is valid JSON,
            otherwise returns a plain string.

    Raises:
        ValueError: If the active backend cannot be initialized
            (e.g. ANTHROPIC_API_KEY not set for the default backend).

    Example — JSON output:
        >>> agent = ai_agent(
        ...     "Analyze sentiment. Return JSON: {\"sentiment\": \"POSITIVE\"|\"NEGATIVE\"|\"NEUTRAL\", \"score\": -1.0 to 1.0}"
        ... )
        >>> result = agent("I love this framework!")
        >>> result["sentiment"]
        'POSITIVE'

    Example — plain text output:
        >>> reporter = ai_agent(
        ...     "Summarize these articles as a short daily digest. Return plain text, not JSON."
        ... )
        >>> summary = reporter(batch)   # batch can be a dict or string
        >>> print(summary)
    """
    backend = get_backend()

    def analyze(msg) -> dict | str:
        """
        Send msg to the model and return the response.

        Args:
            msg: Input to analyze. Accepts a string or a dict.
                 Dicts are serialized to JSON before sending.

        Returns:
            dict if the model's response is valid JSON, str otherwise.
        """
        # Accept dict or string — serialize dict to JSON string for the model
        text = json.dumps(msg) if isinstance(msg, dict) else str(msg)

        if not text or not text.strip():
            return {}

        raw = backend.complete(
            system=prompt,
            user=text,
            max_tokens=1024,
            temperature=1.0,
        )

        response_text = raw.strip()

        # Strip markdown code fences if present
        if response_text.startswith("```"):
            response_text = re.sub(r"^```[a-z]*\n?", "", response_text)
            response_text = re.sub(r"\n?```$",        "", response_text)
            response_text = response_text.strip()

        if not response_text:
            print(
                f"[ai_agent] Warning: empty response from model for input: {text[:80]!r}")
            return {}

        # Try to parse as JSON — return dict if successful, string otherwise
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return response_text

    return analyze


if __name__ == "__main__":
    try:
        print("Testing ai_agent...")
        print("-" * 70)

        agent = ai_agent("""
            Analyze the sentiment of this text.
            Return JSON: {"sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
                          "score": -1.0 to 1.0}
        """)

        result = agent("This framework is amazing!")
        print(f"Input:     This framework is amazing!")
        print(f"Sentiment: {result['sentiment']}  score: {result['score']}")
        print("-" * 70)
        print("✓ ai_agent is working!")

    except ValueError as e:
        print(f"\n❌ Cannot test: {e}")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
