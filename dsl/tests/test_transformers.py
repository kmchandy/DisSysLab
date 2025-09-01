import pytest
from dsl.core import Network
from dsl.block_lib.stream_transformers import (
    TransformerFunction,
    get_value_for_key,
    TransformerPrompt,
)
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_recorders import record, RecordToList
from dsl.block_lib.fanin import MergeSynch, MergeAsynch


def reverse_text(text): return text[::-1]
def join_texts(msgs): return " + ".join(msgs)


def test_stream_transformer_basic():
    results = []

    net = Network(
        blocks={
            "gen": GenerateFromList(items=["abc", "def"], key="data"),
            "xf": TransformerFunction(transform_fn=reverse_text, input_key="data", output_key="reverse_str"),
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


def test_stream_transformer_basic_no_keys():
    results = []

    net = Network(
        blocks={
            "gen": GenerateFromList(["abc", "def"]),
            "xf": TransformerFunction(transform_fn=reverse_text),
            "rec": RecordToList(results),
        },
        connections=[
            ("gen", "out", "xf", "in"),
            ("xf", "out", "rec", "in")
        ],
    )

    net.compile_and_run()
    assert results == ["cba", "fed"]


def test_stream_transformer_basic_short_record():
    results = []

    net = Network(
        blocks={
            "gen": GenerateFromList(items=["abc", "def"], key="data"),
            "xf": TransformerFunction(transform_fn=reverse_text, input_key="data", output_key="reverse_str"),
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


def test_transformer_function_upper():
    results = []
    net = Network(
        blocks={
            "gen": GenerateFromList(items=["one", "two"], key="data"),
            "xf": TransformerFunction(func=str.upper, input_key="data"),
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
            "gen": GenerateFromList(items=["cat", "dog"], key="data"),
            "xf": TransformerFunction(get_value_for_key("data")),
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
            "a": GenerateFromList(["red", "blue"]),
            "b": GenerateFromList(["apple", "berry"]),
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
            "a": GenerateFromList(["red", "blue"], delay=0.1),
            "b": GenerateFromList(["apple", "berry"]),
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
            "gen": GenerateFromList(["What is 6 x 7?"]),
            "gpt": TransformerPrompt("Answer this: {msg}"),
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
            "gen": GenerateFromList(["I love pizza"]),
            "clf": TransformerPrompt(
                "Classify the sentiment of this review as Positive, Negative, or Neutral: {msg}"
            ),
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
            "gen": GenerateFromList(["Barack Obama was the president"]),
            "xf": TransformerPrompt(
                "Extract the named entities from this text as a Python list: {msg}"
            ),
            "rec": RecordToList(results)
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert results == [["Biden"]]


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
            "gen": GenerateFromList([
                "There is no single best trail in the San Gabriel Mountains, as the ideal hike depends  on your experience level and desired scenery."
            ]),
            "xf": TransformerPrompt(
                "Summarize the following text: {msg}"
            ),
            "rec": RecordToList(results)
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )
    net.compile_and_run()
    print(f"results = {results}")
    assert results == ["This is a summary."]
