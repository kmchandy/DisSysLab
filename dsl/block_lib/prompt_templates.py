"""
Module: prompt_templates.py

This module provides reusable prompt functions for GPT-based blocks in DisSysLab.
Students can define and share new prompt templates here.
"""

import ast

def sentiment_prompt(msg: str) -> list[dict]:
    return [{
        "role": "user",
        "content": f"Classify the sentiment of the following text as Positive, Negative, or Neutral.\nText: \"{msg}\"\nSentiment:"
    }]

def summarize_prompt(msg: str, max_words: int = 50) -> list[dict]:
    return [
        {"role": "system", "content": "You are a helpful assistant that summarizes text."},
        {"role": "user", "content": f"Summarize the following in no more than {max_words} words:\n\n{msg}"}
    ]

def entity_extraction_prompt(msg: str) -> list[dict]:
    return [{
        "role": "user",
        "content": f"Extract named entities from the text as a Python list.\nText: \"{msg}\""
    }]

def headline_prompt(msg: str) -> list[dict]:
    return [{
        "role": "user",
        "content": f"Write a short, catchy headline for the following news story:\n\n{msg}"
    }]

def as_list(text: str):
    try:
        return ast.literal_eval(text) if text.strip().startswith("[") else []
    except Exception:
        return []
