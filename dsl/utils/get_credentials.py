'''
Scripts to get OpenAI API credentials from environment variables or a .env file.

'''
import os
from dotenv import load_dotenv
from openai import OpenAI


def get_openai_client(verbose: bool = False) -> OpenAI:
    """
    Load OpenAI API key from .env or environment variable and return 
    a configured OpenAI client.

    Parameters:
    - verbose: If True, prints where the API key was loaded from.

    Returns:
    - An instance of OpenAI client.

    Raises:
    - ValueError if no valid key is found.
    """
    # Load .env file if present
    load_dotenv()

    # Attempt to retrieve API key
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "Missing OpenAI API key. Please set OPENAI_API_KEY in your environment or .env file.")

    if verbose:
        print("✅ Loaded OpenAI API key from environment")

    return OpenAI(api_key=key)


def get_openai_key() -> str:
    """
    Load OpenAI API key from .env or environment variable.

    Returns:
    - The API key as a string.

    Raises:
    - ValueError if no key is found.
    """
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError(
            "Missing OpenAI API key. Please set it in your .env or environment variables.")
    return key
