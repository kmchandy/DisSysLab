# dsl/utils/get_credentials.py
"""
Get API credentials for AI services (OpenAI, Anthropic) from environment variables or .env file.

This utility helps students configure API keys for building AI-powered distributed systems.

Usage:
    >>> from dsl.utils.get_credentials import get_anthropic_client, get_openai_client
    >>> 
    >>> # For Claude AI
    >>> client = get_anthropic_client()
    >>> 
    >>> # For OpenAI
    >>> client = get_openai_client()
"""

import os
from dotenv import load_dotenv


def get_anthropic_client(verbose: bool = False):
    """
    Load Anthropic API key from .env or environment variable and return a configured client.

    Parameters:
        verbose: If True, prints where the API key was loaded from.

    Returns:
        An instance of Anthropic client.

    Raises:
        ValueError: If no valid key is found.
        ImportError: If anthropic package is not installed.

    Example:
        >>> client = get_anthropic_client()
        >>> response = client.messages.create(
        ...     model="claude-sonnet-4-20250514",
        ...     max_tokens=1000,
        ...     messages=[{"role": "user", "content": "Hello!"}]
        ... )
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        raise ImportError(
            "Anthropic package not installed. Install with: pip install anthropic"
        )

    # Load .env file if present
    load_dotenv()

    # Attempt to retrieve API key
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "Missing Anthropic API key. Please set ANTHROPIC_API_KEY in your environment or .env file.\n"
            "Get your key at: https://console.anthropic.com/settings/keys"
        )

    if verbose:
        print("✅ Loaded Anthropic API key from environment")

    return Anthropic(api_key=key)


def get_openai_client(verbose: bool = False):
    """
    Load OpenAI API key from .env or environment variable and return a configured client.

    Parameters:
        verbose: If True, prints where the API key was loaded from.

    Returns:
        An instance of OpenAI client.

    Raises:
        ValueError: If no valid key is found.
        ImportError: If openai package is not installed.

    Example:
        >>> client = get_openai_client()
        >>> response = client.chat.completions.create(
        ...     model="gpt-4",
        ...     messages=[{"role": "user", "content": "Hello!"}]
        ... )
    """
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "OpenAI package not installed. Install with: pip install openai"
        )

    # Load .env file if present
    load_dotenv()

    # Attempt to retrieve API key
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "Missing OpenAI API key. Please set OPENAI_API_KEY in your environment or .env file.\n"
            "Get your key at: https://platform.openai.com/api-keys"
        )

    if verbose:
        print("✅ Loaded OpenAI API key from environment")

    return OpenAI(api_key=key)


def get_anthropic_key() -> str:
    """
    Load Anthropic API key from .env or environment variable.

    Returns:
        The API key as a string.

    Raises:
        ValueError: If no key is found.
    """
    load_dotenv()
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError(
            "Missing Anthropic API key. Please set it in your .env or environment variables.\n"
            "Get your key at: https://console.anthropic.com/settings/keys"
        )
    return key


def get_openai_key() -> str:
    """
    Load OpenAI API key from .env or environment variable.

    Returns:
        The API key as a string.

    Raises:
        ValueError: If no key is found.
    """
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "Missing OpenAI API key. Please set it in your .env or environment variables.\n"
            "Get your key at: https://platform.openai.com/api-keys"
        )
    return key


# Convenience: Load keys on module import (optional)
# Students can use: from dsl.utils.get_credentials import ANTHROPIC_API_KEY
try:
    ANTHROPIC_API_KEY = get_anthropic_key()
except ValueError:
    ANTHROPIC_API_KEY = None

try:
    OPENAI_API_KEY = get_openai_key()
except ValueError:
    OPENAI_API_KEY = None


__all__ = [
    "get_anthropic_client",
    "get_anthropic_key",
    "get_openai_client",
    "get_openai_key",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
]
