# components//transforms/claude_agent.py

"""
ClaudeAgent: AI-powered transform using Anthropic's Claude API

This component wraps the Anthropic API to create AI-powered transforms
for tasks like sentiment analysis, spam detection, content classification, etc.
"""

import os
import json
from typing import Optional, Dict, Any
from anthropic import Anthropic


class ClaudeAgent:
    """
    AI-powered transform agent using Claude API.

    This class wraps ordinary Python functions to use Claude AI for analysis.
    It's designed to work seamlessly with the DSL's transform_map decorator.

    Example:
        >>> spam_detector = ClaudeAgent(
        ...     prompt="Analyze if this message is spam. Return JSON: {is_spam: bool, confidence: float}",
        ...     output_format="json"
        ... )
        >>> result = spam_detector.run("Click here for free money!")
        >>> # Returns: {"is_spam": True, "confidence": 0.95}
    """

    def __init__(
        self,
        prompt: str,
        model: str = "claude-sonnet-4-20250514",
        output_format: str = "json",
        max_tokens: int = 1024,
        temperature: float = 1.0,
        api_key: Optional[str] = None
    ):
        """
        Initialize the Claude Agent.

        Args:
            prompt: System prompt that defines the task for Claude
            model: Claude model to use (default: claude-sonnet-4-20250514)
            output_format: Expected output format ("json" or "text")
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 to 1.0)
            api_key: Anthropic API key (if None, reads from ANTHROPIC_API_KEY env var)

        Raises:
            ValueError: If API key is not provided and not in environment
        """
        self.prompt = prompt
        self.model = model
        self.output_format = output_format
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Get API key from parameter or environment
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found. Either:\n"
                "1. Set environment variable: export ANTHROPIC_API_KEY='your-key'\n"
                "2. Pass api_key parameter: ClaudeAgent(api_key='your-key', ...)\n"
                "See setup/01_anthropic_setup.md for detailed instructions."
            )

        # Initialize Anthropic client
        self.client = Anthropic(api_key=self.api_key)

        # Track usage for debugging
        self.call_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def run(self, text: str) -> Any:
        """
        Process text using Claude API.

        This is the main method called by the DSL's transform_map decorator.

        Args:
            text: Input text to analyze

        Returns:
            Parsed result (dict if output_format="json", str otherwise)

        Raises:
            Exception: If API call fails or JSON parsing fails
        """
        try:
            # Create the message
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.prompt,
                messages=[
                    {"role": "user", "content": text}
                ]
            )

            # Update usage statistics
            self.call_count += 1
            self.total_input_tokens += message.usage.input_tokens
            self.total_output_tokens += message.usage.output_tokens

            # Extract response text
            response_text = message.content[0].text

            # Parse based on output format
            if self.output_format == "json":
                # Try to parse as JSON
                try:
                    # Claude sometimes wraps JSON in markdown code blocks
                    if response_text.strip().startswith("```"):
                        # Extract JSON from code block
                        lines = response_text.strip().split("\n")
                        json_lines = [
                            l for l in lines if not l.strip().startswith("```")]
                        response_text = "\n".join(json_lines)

                    return json.loads(response_text)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"Failed to parse JSON response from Claude.\n"
                        f"Response: {response_text}\n"
                        f"Error: {e}"
                    )
            else:
                return response_text

        except Exception as e:
            print(f"[ClaudeAgent] Error calling API: {e}")
            raise

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for this agent.

        Returns:
            Dictionary with call_count, input_tokens, output_tokens, estimated_cost
        """
        # Pricing for Claude Sonnet 4 (as of Jan 2025)
        input_cost_per_million = 3.00
        output_cost_per_million = 15.00

        input_cost = (self.total_input_tokens / 1_000_000) * \
            input_cost_per_million
        output_cost = (self.total_output_tokens / 1_000_000) * \
            output_cost_per_million
        total_cost = input_cost + output_cost

        return {
            "call_count": self.call_count,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "estimated_cost_usd": round(total_cost, 4)
        }

    def print_usage_stats(self):
        """Print usage statistics in a readable format."""
        stats = self.get_usage_stats()
        print("\n" + "=" * 60)
        print("Claude Agent Usage Statistics")
        print("=" * 60)
        print(f"API Calls:       {stats['call_count']}")
        print(f"Input Tokens:    {stats['input_tokens']:,}")
        print(f"Output Tokens:   {stats['output_tokens']:,}")
        print(f"Estimated Cost:  ${stats['estimated_cost_usd']:.4f} USD")
        print("=" * 60 + "\n")


# ============================================================================
# Convenience Factory Functions
# ============================================================================

def create_spam_detector() -> ClaudeAgent:
    """
    Create a spam detection agent.

    Returns:
        ClaudeAgent configured for spam detection
    """
    return ClaudeAgent(
        prompt="""Analyze if the given text is spam.

Spam indicators include:
- Promotional language (buy now, limited time, act now)
- Requests for money or personal information
- Suspicious links or offers
- Too-good-to-be-true claims

Return JSON format:
{
    "is_spam": true/false,
    "confidence": 0.0-1.0,
    "reason": "brief explanation"
}""",
        output_format="json"
    )


def create_sentiment_analyzer() -> ClaudeAgent:
    """
    Create a sentiment analysis agent.

    Returns:
        ClaudeAgent configured for sentiment analysis
    """
    return ClaudeAgent(
        prompt="""Analyze the sentiment of the given text.

Determine if the text expresses positive, negative, or neutral sentiment.
Provide a score from -1.0 (very negative) to +1.0 (very positive).

Return JSON format:
{
    "sentiment": "POSITIVE" | "NEGATIVE" | "NEUTRAL",
    "score": -1.0 to +1.0,
    "reasoning": "brief explanation of the sentiment"
}""",
        output_format="json"
    )


def create_urgency_detector() -> ClaudeAgent:
    """
    Create an urgency detection agent.

    Returns:
        ClaudeAgent configured for urgency detection
    """
    return ClaudeAgent(
        prompt="""Analyze the urgency level of the given text.

Urgency indicators include:
- Time-sensitive language (urgent, asap, immediately, now)
- Critical or emergency terms
- Deadlines or countdowns
- Exclamation marks and ALL CAPS

Return JSON format:
{
    "urgency": "HIGH" | "MEDIUM" | "LOW",
    "metrics": {
        "urgency_score": 0-10,
        "time_sensitive": true/false,
        "requires_immediate_action": true/false
    },
    "reasoning": "brief explanation"
}""",
        output_format="json"
    )

# components/transformers/claude_agent.py

def create_spam_filter():
    """
    Create a spam filter function that returns None for spam, text for non-spam.
    
    This wraps create_spam_detector() to provide a clean filtering interface.
    Returns None for spam (filtered out), or the original text for valid messages.
    
    Returns:
        Callable that takes text and returns text or None
        
    Example:
        >>> from components.transformers.claude_agent import create_spam_filter
        >>> from dsl.blocks import Transform
        >>> 
        >>> spam_filter = Transform(fn=create_spam_filter(), name="spam_filter")
    """
    # Reuse the existing spam detector
    detector = create_spam_detector()
    
    # Wrapper function that filters
    def spam_filter(text: str) -> Optional[str]:
        """Returns None if spam, original text if not spam."""
        try:
            result = detector.run(text)
            
            # If spam, return None (filters out message)
            if result.get("is_spam", False):
                return None
            
            # Not spam, return original text
            return text
            
        except Exception as e:
            print(f"[spam_filter] Error: {e}")
            # On error, let message through (fail open for teaching)
            return text
    
    return spam_filter