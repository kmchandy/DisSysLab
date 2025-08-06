import pytest
from dsl.core import Network, SimpleAgent
from dsl.block_lib.stream_transformers import (
    StreamTransformer,
    WrapFunction,
    get_value_for_key,
    PromptToBlock,
    SentimentClassifierWithGPT,
    ExtractEntitiesWithGPT,
    SummarizeWithGPT,
    transform
)
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import record, RecordToList
from dsl.block_lib.fanin import MergeSynch, MergeAsynch


def reverse_text(text): return text[::-1]
def join_texts(msgs): return " + ".join(msgs)


def test_stream_transformer_basic():
    results = []

    net = Network(
        blocks={
            "gen": generate(["abc", "def"], key="data"),
            "xf": StreamTransformer(transform_fn=reverse_text, input_key="data", output_key="reverse_str"),
            "rec": RecordToList(results),
        },
        connections=[
            ("gen", "out", "xf", "in"),
            ("xf", "out", "rec", "in")
        ],
    )

    net.compile_and_run()
    assert results == [
        {'data': 'abc', 'reverse_str': 'cba'},
        {'data': 'def', 'reverse_str': 'fed'}
    ]


def test_stream_transformer_basic_short_record():
    results = []

    net = Network(
        blocks={
            "gen": generate(["abc", "def"], key="data"),
            "xf": StreamTransformer(transform_fn=reverse_text, input_key="data", output_key="reverse_str"),
            "rec": record(to="list", target=results)
        },
        connections=[
            ("gen", "out", "xf", "in"),
            ("xf", "out", "rec", "in")
        ],
    )

    net.compile_and_run()
    assert results == [
        {'data': 'abc', 'reverse_str': 'cba'},
        {'data': 'def', 'reverse_str': 'fed'}
    ]


def test_wrap_function_upper():
    results = []
    net = Network(
        blocks={
            "gen": generate(["one", "two"], key="data"),
            "xf": WrapFunction(func=str.upper, input_key="data"),
            "rec": RecordToList(results),
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert results == [
        {"data": "ONE"},
        {"data": "TWO"}
    ]


def test_transform_shortcut():
    results = []

    net = Network(
        blocks={
            "gen": generate(["cat", "dog"], key="data"),
            "xf": WrapFunction(get_value_for_key("data")),
            "rec": RecordToList(results),
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert results == ["cat", "dog"]


def test_transform_multiple_streams_synch():
    results = []
    net = Network(
        blocks={
            "a": generate(["red", "blue"]),
            "b": generate(["apple", "berry"]),
            "c": MergeSynch(["x", "y"]),
            "d": RecordToList(results),
        },
        connections=[
            ("a", "out", "c", "x"),
            ("b", "out", "c", "y"),
            ("c", "out", "d", "in"),
        ],
    )
    net.compile_and_run()
    assert results == [["red", "apple"], ["blue", "berry"]]


def test_transform_multiple_streams_asynch():
    results = []
    net = Network(
        blocks={
            "a": generate(["red", "blue"], delay=0.1),
            "b": generate(["apple", "berry"]),
            "c": MergeAsynch(["x", "y"]),
            "d": RecordToList(results),
        },
        connections=[
            ("a", "out", "c", "x"),
            ("b", "out", "c", "y"),
            ("c", "out", "d", "in"),
        ],
    )
    net.compile_and_run()

    from_a = {"red", "blue"}
    from_b = {"apple", "berry"}
    a_present = from_a.issubset(results)
    b_present = from_b.issubset(results)
    assert a_present and b_present, (
        f"Expected both full streams in output, but got: {saved}"
    )


def test_prompt_to_block_with_mock(monkeypatch):
    results = []

    class DummyClient:
        def __init__(self, *args, **kwargs): pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class Msg:
                        content = "42"
                    return type("Resp", (), {"choices": [type("C", (), {"message": Msg()})()]})()
    monkeypatch.setattr(
        "dsl.block_lib.stream_transformers.OpenAI", DummyClient)
    net = Network(
        blocks={
            "gen": generate(["What is 6 x 7?"]),
            "gpt": PromptToBlock("Answer this: {msg}"),
            "rec": RecordToList(results),
        },
        connections=[("gen", "out", "gpt", "in"), ("gpt", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert results == ["42"]


def test_sentiment_classifier_with_mock(monkeypatch):
    results = []

    class DummyClient:
        def __init__(self, *args, **kwargs): pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class Msg:
                        content = "Positive"
                    return type("Resp", (), {"choices": [type("C", (), {"message": Msg()})()]})()
    monkeypatch.setattr(
        "dsl.block_lib.stream_transformers.OpenAI", DummyClient)
    net = Network(
        blocks={
            "gen": generate(["I love pizza"]),
            "clf": SentimentClassifierWithGPT(),
            "rec": RecordToList(results),
        },
        connections=[("gen", "out", "clf", "in"), ("clf", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert results == ["Positive"]


def test_extract_entities_with_mock(monkeypatch):
    results = []

    class DummyClient:
        def __init__(self, *args, **kwargs): pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class Msg:
                        content = "['Barack Obama']"
                    return type("Resp", (), {"choices": [type("C", (), {"message": Msg()})()]})()
    monkeypatch.setattr(
        "dsl.block_lib.stream_transformers.OpenAI", DummyClient)
    net = Network(
        blocks={
            "gen": generate(["Barack Obama was the president"]),
            "xf": ExtractEntitiesWithGPT(),
            "rec": RecordToList(results)
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert results == [["Barack Obama"]]


def test_summarize_with_mock(monkeypatch):
    results = []

    class DummyClient:
        def __init__(self, *args, **kwargs): pass

        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    class Msg:
                        content = "This is a summary."
                    return type("Resp", (), {"choices": [type("C", (), {"message": Msg()})()]})()
    monkeypatch.setattr(
        "dsl.block_lib.stream_transformers.OpenAI", DummyClient)
    net = Network(
        blocks={
            "gen": generate(["This is a long paragraph..."]),
            "xf": SummarizeWithGPT(),
            "rec": RecordToList(results)
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert results == ["This is a summary."]
