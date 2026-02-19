# components/transformers/ai_agent.py

"""
Real AI Agent - Uses Claude API for analysis

This module provides real AI transforms using Anthropic's Claude API.
Compare with demo_ai_agent.py to see the difference between demo and real.

Usage:
    from components.transformers.prompts import SENTIMENT_ANALYZER
    from components.transformers.ai_agent import ai_agent
    
    analyzer = ai_agent(SENTIMENT_ANALYZER)
    result = analyzer("I love this!")
    # Returns: {"text": "I love this!", "sentiment": "POSITIVE", "score": 0.9, ...}
    
Requirements:
    - ANTHROPIC_API_KEY environment variable
    - anthropic package: pip install anthropic
    - Costs ~$0.001-0.003 per message
"""

import os
import json
from anthropic import Anthropic


def ai_agent(prompt: str):
    """
    Creates a real AI transform function from a prompt.

    This calls Claude API for actual AI analysis using the provided prompt.
    Returns the same JSON format as demo_ai_agent, but with real AI intelligence.

    Args:
        prompt: Prompt constant from prompts.py (e.g. SENTIMENT_ANALYZER)

    Returns:
        Callable that takes text and returns enriched JSON dict

    Raises:
        ValueError: If ANTHROPIC_API_KEY not found in environment

    Example:
        >>> from components.transformers.prompts import SENTIMENT_ANALYZER
        >>> from components.transformers.ai_agent import ai_agent
        >>> 
        >>> analyzer = ai_agent(SENTIMENT_ANALYZER)
        >>> result = analyzer("I love this framework!")
        >>> print(result)
        {'text': 'I love this framework!', 
         'sentiment': 'POSITIVE', 
         'score': 0.92, 
         'reasoning': 'Enthusiastic language with strong positive emotion'}
    """
    # Check for API key
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

    # Create Anthropic client (reused across calls)
    client = Anthropic(api_key=api_key)

    # Track usage for cost awareness
    call_count = 0
    total_cost = 0.0

    def analyze(text: str) -> dict:
        """
        Analyzes text using Claude API.

        Args:
            text: Text to analyze

        Returns:
            Dict with original text plus AI analysis fields
        """
        nonlocal call_count, total_cost

        try:
            # Call Claude API
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                temperature=1.0,
                system=prompt,
                messages=[
                    {"role": "user", "content": text}
                ]
            )

            # Track usage
            call_count += 1
            input_tokens = message.usage.input_tokens
            output_tokens = message.usage.output_tokens

            # Estimate cost (Claude Sonnet 4 pricing)
            cost = (input_tokens / 1_000_000 * 3.00) + \
                (output_tokens / 1_000_000 * 15.00)
            total_cost += cost

            # Extract response text
            response_text = message.content[0].text

            # Handle markdown code blocks
            if response_text.strip().startswith("```"):
                lines = response_text.strip().split("\n")
                json_lines = [
                    l for l in lines if not l.strip().startswith("```")]
                response_text = "\n".join(json_lines)

            # Parse the JSON
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"\n[AI Error] Claude returned invalid JSON:")
                print(f"Response: {response_text}")
                print(f"Error: {e}\n")
                raise

            # Add original text to result (enrich the message)
            result["text"] = text

            return result

        except json.JSONDecodeError:
            raise

        except Exception as e:
            print(f"\n[AI Error] API call failed: {e}")
            print(f"This might be due to:")
            print(f"  - Invalid API key")
            print(f"  - Network issues")
            print(f"  - Rate limiting")
            print(f"  - Insufficient credits\n")
            raise

    return analyze


def print_usage_info():
    """Print information about API usage and costs."""
    print("\n" + "=" * 70)
    print("REAL AI USAGE INFORMATION")
    print("=" * 70)
    print("""
Using real AI (Claude API) costs money:
- Input:  ~$3.00 per million tokens (~750K words)
- Output: ~$15.00 per million tokens (~750K words)

Typical costs per message:
- Short message (1 sentence):  $0.0005 - $0.001
- Medium message (paragraph):  $0.001 - $0.002
- Long message (page):         $0.002 - $0.005

For learning and testing, use demo_ai_agent instead (FREE)!
    """)
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print_usage_info()

    try:
        from components.transformers.prompts import SENTIMENT_ANALYZER

        print("Testing real AI agent...")
        print("-" * 70)

        analyzer = ai_agent(SENTIMENT_ANALYZER)
        result = analyzer("This framework is amazing!")

        print(f"Input: This framework is amazing!")
        print(f"Output: {result}")
        print("-" * 70)
        print("✓ Real AI is working!")

    except ValueError as e:
        print(f"\n❌ Cannot test: {e}")
    except ImportError:
        print("\n❌ Cannot import prompts.py - make sure it exists")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
