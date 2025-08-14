"""
Chapter 2 — Input & Output Keys (Sentiment example)

Usage:
  export OPENAI_API_KEY=sk-...
  python examples/ch2_keys/chapter2_keys_sentiment.py
"""

from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import RecordToList
# the lean version (system_prompt only)
from dsl.block_lib.stream_transformers import PromptToBlock


def main():
    # Results will be a dict which includes sentiment scores for each input text and the text itself.
    results = []

    gpt = PromptToBlock(
        system_prompt="You are an expert at analyzing sentiment. Output a score 0..10 for positivity.",
        input_key="text",         # read from msg["text"]
        output_key="sentiment",   # write to msg["sentiment"]
        # model="gpt-4o-mini",    # optional override if your class exposes it
        # temperature=0.0,        # optional for determinism in class demos
    )

    net = Network(
        blocks={
            "gen": generate([
                {"text": "I love sunny days"},
                {"text": "I hate traffic jams"},
                {"text": "This pizza is amazing"},
            ]),
            "sentiment": gpt,
            "rec": RecordToList(results),
        },
        connections=[
            ("gen", "out", "sentiment", "in"),
            ("sentiment", "out", "rec", "in"),
        ],
    )

    net.compile_and_run()

    print("Final Results:")
    for item in results:
        # Expect each item like: {"text": "...", "sentiment": "..."}
        print(item)


if __name__ == "__main__":
    main()
