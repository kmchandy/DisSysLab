# dissyslab/components/transformers/ai_agent.py

"""
Real AI Agent - Uses Claude API for analysis

Usage:
    from dissyslab.components.transformers.ai_agent import ai_agent

    analyzer = ai_agent("Analyze the sentiment. Return JSON: {sentiment, score}")
    result = analyzer("I love this!")
    # Returns dict if Claude returns JSON, string otherwise

Requirements:
    - ANTHROPIC_API_KEY environment variable
    - anthropic package: pip install anthropic
    - Costs ~$0.001-0.003 per message
"""

import os
import json
import re
from anthropic import Anthropic


def ai_agent(prompt: str):
    """
    Creates an AI transform function from a prompt string.

    Calls the Claude API with the given system prompt. If Claude returns
    valid JSON, returns a parsed dict. If Claude returns plain text,
    returns a string. The prompt controls the output format.

    Args:
        prompt: System prompt describing the task and desired output format.

    Returns:
        Callable: fn(msg) -> dict | str
            Accepts a string or dict as input.
            Returns a dict if Claude's response is valid JSON,
            otherwise returns a plain string.

    Raises:
        ValueError: If ANTHROPIC_API_KEY not found in environment.

    Example — JSON output:
        >>> agent = ai_agent(
        ...     "Analyze sentiment. Return JSON: {"sentiment": "POSITIVE"|"NEGATIVE"|"NEUTRAL", "score": -1.0 to 1.0}"
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
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found in environment.\n\n"
            "To fix this:\n"
            "1. Get an API key from: https://console.anthropic.com\n"
            "2. Set environment variable: export ANTHROPIC_API_KEY='your-key-here'\n"
            "3. Or add to your shell profile (~/.bashrc or ~/.zshrc):\n"
            "   export ANTHROPIC_API_KEY='your-key-here'\n\n"
            "Note: This will cost real money (~$0.001-0.003 per message).\n"
            "For learning, use demo_ai_agent instead (no cost, no API key needed)."
        )

    client = Anthropic(api_key=api_key)
    call_count = 0
    total_cost = 0.0

    def analyze(msg) -> dict | str:
        """
        Send msg to Claude and return the response.

        Args:
            msg: Input to analyze. Accepts a string or a dict.
                 Dicts are serialized to JSON before sending to Claude.

        Returns:
            dict if Claude's response is valid JSON, str otherwise.
        """
        nonlocal call_count, total_cost

        # Accept dict or string — serialize dict to JSON string for Claude
        text = json.dumps(msg) if isinstance(msg, dict) else str(msg)

        if not text or not text.strip():
            return {}

        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            temperature=1.0,
            system=prompt,
            messages=[
                {"role": "user", "content": text}
            ]
        )

        call_count += 1
        input_tokens = message.usage.input_tokens
        output_tokens = message.usage.output_tokens
        total_cost += (input_tokens / 1_000_000 * 3.00) + \
                      (output_tokens / 1_000_000 * 15.00)

        response_text = message.content[0].text.strip()

        # Strip markdown code fences if present
        if response_text.startswith("```"):
            response_text = re.sub(r"^```[a-z]*\n?", "", response_text)
            response_text = re.sub(r"\n?```$",        "", response_text)
            response_text = response_text.strip()

        if not response_text:
            print(
                f"[ai_agent] Warning: empty response from Claude for input: {text[:80]!r}")
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
