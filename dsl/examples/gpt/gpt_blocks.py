# examples/gpt/sentiment_classifier.py

from dsl.stream_transformers.prompt_to_block import PromptToBlock


class SentimentClassifier(PromptToBlock):
    """
Name: SentimentClassifier

Summary:
A GPT-powered block that classifies the sentiment of input text as positive, negative, or neutral.

Parameters:
- name: Optional name for the block.
- description: Optional description.
- model: Optional OpenAI model (default inherited from PromptToBlock).
- temperature: Optional temperature for generation (default inherited from PromptToBlock).

Behavior:
- Sends input text to the LLM using a sentiment classification prompt.
- Returns a single word: "positive", "negative", or "neutral".

Use Cases:
- Analyzing product reviews.
- Classifying social media posts.
- Plug-and-play with other blocks for user feedback analysis.

Example:
>>> net = Network(
>>>     blocks={
>>>         'text': GenerateFromList(items=["I love it!", "It was bad."], name="input"),
>>>         'sentiment': SentimentClassifier(),
>>>         'collect': StreamToList(),
>>>     },
>>>     connections=[
>>>         ('text', 'out', 'sentiment', 'in'),
>>>         ('sentiment', 'out', 'collect', 'in')
>>>     ]
>>> )
>>> net.run()
>>> print(net.blocks['collect'].saved)

Tags: gpt, sentiment, classifier, llm, transformer
    """

    def __init__(self, name=None, description=None, model=None, temperature=None):
        prompt = (
            "You are a sentiment analysis model. "
            "Return 'positive', 'negative', or 'neutral' for the sentiment of the input text.\n"
            "Text: {input}"
        )
        super().__init__(
            prompt_template=prompt,
            name=name or "SentimentClassifier",
            description=description or "Classify input text into positive, negative, or neutral sentiment.",
            model=model,
            temperature=temperature,
        )

# examples/gpt/extract_entities.py


class ExtractEntities(PromptToBlock):
    """
Name: ExtractEntities

Summary:
A GPT-powered block that extracts named entities from input text.

Parameters:
- name: Optional name for the block.
- description: Optional description.
- model: Optional OpenAI model (default inherited from PromptToBlock).
- temperature: Optional temperature (default inherited from PromptToBlock).

Behavior:
- Extracts names of people, organizations, and locations from text.
- Returns them as a JSON object.

Use Cases:
- NLP pipelines.
- Document analysis and information retrieval.
- Real-time text monitoring.

Example:
>>> net = Network(
>>>     blocks={
>>>         'text': GenerateFromList(items=["Barack Obama visited Microsoft in Seattle."], name="input"),
>>>         'entities': ExtractEntities(),
>>>         'collect': StreamToList(),
>>>     },
>>>     connections=[
>>>         ('text', 'out', 'entities', 'in'),
>>>         ('entities', 'out', 'collect', 'in')
>>>     ]
>>> )
>>> net.run()
>>> print(net.blocks['collect'].saved)

Tags: gpt, extraction, entities, llm, transformer
    """

    def __init__(self, name=None, description=None, model=None, temperature=None):
        prompt = (
            "Extract named entities from the following text. Return a JSON object with 'people', 'organizations', and 'locations'.\n"
            "Text: {input}"
        )
        super().__init__(
            prompt_template=prompt,
            name=name or "ExtractEntities",
            description=description or "Extract named entities from text using GPT.",
            model=model,
            temperature=temperature,
        )

# examples/gpt/summarize_text.py


class SummarizeText(PromptToBlock):
    """
Name: SummarizeText

Summary:
A GPT-powered block that generates a concise summary of the input text.

Parameters:
- name: Optional name for the block.
- description: Optional description.
- model: Optional OpenAI model (default inherited from PromptToBlock).
- temperature: Optional temperature (default inherited from PromptToBlock).

Behavior:
- Converts long input into a short summary.
- Output is a 1–2 sentence summary.

Use Cases:
- Text compression and summarization.
- Knowledge distillation.
- Educational summarization tools.

Example:
>>> net = Network(
>>>     blocks={
>>>         'text': GenerateFromList(items=["Distributed systems are composed of ..."], name="input"),
>>>         'summary': SummarizeText(),
>>>         'collect': StreamToList(),
>>>     },
>>>     connections=[
>>>         ('text', 'out', 'summary', 'in'),
>>>         ('summary', 'out', 'collect', 'in')
>>>     ]
>>> )
>>> net.run()
>>> print(net.blocks['collect'].saved)

Tags: gpt, summary, transformer, llm
    """

    def __init__(self, name=None, description=None, model=None, temperature=None):
        prompt = (
            "Summarize the following passage into 1–2 concise sentences.\n"
            "Text: {input}"
        )
        super().__init__(
            prompt_template=prompt,
            name=name or "SummarizeText",
            description=description or "Generate a short summary of the input text.",
            model=model,
            temperature=temperature,
        )
