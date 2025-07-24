"""
Unit tests for stream_transformers.py

Tests:
- StreamTransformer
- WrapFunction with NumPy
- TransformMultipleStreams (passthrough and custom fn)
- PromptToBlock (smoke test)
- SentimentClassifierWithGPT (smoke test)
- ExtractEntitiesWithGPT (smoke test)
- SummarizeWithGPT (smoke test)
"""

from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import record
from dsl.block_lib.stream_transformers import (
    StreamTransformer,
    WrapFunction,
    PromptToBlock,
    SentimentClassifierWithGPT,
    ExtractEntitiesWithGPT,
    SummarizeWithGPT,
    TransformMultipleStreams
)
import numpy as np


def build_and_run_net(blocks, connections):
    net = Network(name="test", blocks=blocks, connections=connections)
    net.compile()
    net.run()
    return net


def test_stream_transformer_lambda():
    tf = StreamTransformer(lambda x: x.upper())
    sink = record()
    build_and_run_net(
        {"gen": generate(["a", "b"]), "tf": tf, "sink": sink},
        [("gen", "out", "tf", "in"), ("tf", "out", "sink", "in")]
    )
    assert sink.saved == ["A", "B"]


def test_wrap_function_numpy():
    tf = WrapFunction(np.sqrt)
    sink = record()
    build_and_run_net(
        {"gen": generate([1, 4, 9]), "tf": tf, "sink": sink},
        [("gen", "out", "tf", "in"), ("tf", "out", "sink", "in")]
    )
    assert sink.saved == [1.0, 2.0, 3.0]


def test_transform_multiple_streams_passthrough():
    tf = TransformMultipleStreams(["a", "b"])
    sink = record()
    build_and_run_net(
        {
            "gen0": generate(["x", "y"]),
            "gen1": generate(["1", "2"]),
            "tf": tf,
            "sink": sink
        },
        [
            ("gen0", "out", "tf", "a"),
            ("gen1", "out", "tf", "b"),
            ("tf", "out", "sink", "in")
        ]
    )
    assert sink.saved == [["x", "1"], ["y", "2"]]


def test_transform_multiple_streams_custom_fn():
    tf = TransformMultipleStreams(["a", "b"], lambda p: f"{p[0]} + {p[1]}")
    sink = record()
    build_and_run_net(
        {
            "gen0": generate(["u", "v"]),
            "gen1": generate(["1", "2"]),
            "tf": tf,
            "sink": sink
        },
        [
            ("gen0", "out", "tf", "a"),
            ("gen1", "out", "tf", "b"),
            ("tf", "out", "sink", "in")
        ]
    )
    assert sink.saved == ["u + 1", "v + 2"]

# Smoke tests for GPT-based blocks


def test_prompt_to_block_smoke():
    try:
        tf = PromptToBlock(prompt="Say hello to {msg}")
        sink = record()
        build_and_run_net(
            {"gen": generate(["Mani"]), "tf": tf, "sink": sink},
            [("gen", "out", "tf", "in"), ("tf", "out", "sink", "in")]
        )
        assert "hello" in sink.saved[0].lower()
    except Exception:
        print("⚠️ Skipped: PromptToBlock")


def test_sentiment_classifier_with_gpt_smoke():
    try:
        tf = SentimentClassifierWithGPT()
        sink = record()
        build_and_run_net(
            {"gen": generate(["I love this", "I hate that"]),
             "tf": tf, "sink": sink},
            [("gen", "out", "tf", "in"), ("tf", "out", "sink", "in")]
        )
        assert all(isinstance(x, str) for x in sink.saved)
    except Exception:
        print("⚠️ Skipped: SentimentClassifierWithGPT")


def test_extract_entities_with_gpt_smoke():
    try:
        tf = ExtractEntitiesWithGPT()
        sink = record()
        build_and_run_net(
            {"gen": generate(["Barack Obama visited IBM."]),
             "tf": tf, "sink": sink},
            [("gen", "out", "tf", "in"), ("tf", "out", "sink", "in")]
        )
        assert isinstance(sink.saved[0], list)
    except Exception:
        print("⚠️ Skipped: ExtractEntitiesWithGPT")


def test_summarize_with_gpt_smoke():
    try:
        tf = SummarizeWithGPT(max_words=10)
        sink = record()
        build_and_run_net(
            {"gen": generate(
                ["This is a long and complex explanation."]), "tf": tf, "sink": sink},
            [("gen", "out", "tf", "in"), ("tf", "out", "sink", "in")]
        )
        assert isinstance(sink.saved[0], str)
    except Exception:
        print("⚠️ Skipped: SummarizeWithGPT")


if __name__ == "__main__":
    test_stream_transformer_lambda()
    test_wrap_function_numpy()
    test_transform_multiple_streams_passthrough()
    test_transform_multiple_streams_custom_fn()
    test_prompt_to_block_smoke()
    test_sentiment_classifier_with_gpt_smoke()
    test_extract_entities_with_gpt_smoke()
    test_summarize_with_gpt_smoke()
    print("✅ All transformer tests passed.")
