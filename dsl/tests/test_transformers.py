import pytest
from dsl.core import Network
from dsl.block_lib.stream_transformers import (
    StreamTransformer,
    WrapFunction,
    PromptToBlock,
    SentimentClassifierWithGPT,
    ExtractEntitiesWithGPT,
    SummarizeWithGPT,
    TransformMultipleStreams,
    transform
)
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import record


# ========== Helper Functions ==========

def reverse_text(text): return text[::-1]


def join_texts(msgs): return " + ".join(msgs)

# ========== Basic Transformers ==========


def test_stream_transformer_basic():
    net = Network(
        blocks={
            "gen": generate(["abc", "def"]),
            "xf": StreamTransformer(transform_fn=reverse_text),
            "rec": record(),
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert net.blocks["rec"].saved == ["cba", "fed"]


def test_wrap_function_upper():
    net = Network(
        blocks={
            "gen": generate(["one", "two"]),
            "xf": WrapFunction(str.upper),
            "rec": record(),
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert net.blocks["rec"].saved == ["ONE", "TWO"]


def test_transform_shortcut():
    net = Network(
        blocks={
            "gen": generate(["cat", "dog"]),
            "xf": transform(lambda x: f"Animal: {x}"),
            "rec": record(),
        },
        connections=[("gen", "out", "xf", "in"), ("xf", "out", "rec", "in")],
    )
    net.compile_and_run()
    assert net.blocks["rec"].saved == ["Animal: cat", "Animal: dog"]


# ========== Multi-Input Transformer ==========

def test_transform_multiple_streams():
    net = Network(
        blocks={
            "a": generate(["red", "blue"]),
            "b": generate(["apple", "berry"]),
            "c": TransformMultipleStreams(["x", "y"], transformer_fn=join_texts),
            "d": record(),
        },
        connections=[
            ("a", "out", "c", "x"),
            ("b", "out", "c", "y"),
            ("c", "out", "d", "in"),
        ],
    )
    net.compile_and_run()
    assert net.blocks["d"].saved == ["red + apple", "blue + berry"]


# ========== GPT-Based Transformers (mocked) ==========

@pytest.fixture
def mock_openai(monkeypatch):
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


def test_prompt_to_block_with_mock(monkeypatch):
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
            "rec": record(),
        },
        connections=[
            ("gen", "out", "gpt", "in"),
            ("gpt", "out", "rec", "in"),
        ],
    )
    net.compile_and_run()
    assert net.blocks["rec"].saved == ["42"]


def test_sentiment_classifier_with_mock(monkeypatch):
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
            "rec": record(),
        },
        connections=[
            ("gen", "out", "clf", "in"),
            ("clf", "out", "rec", "in"),
        ],
    )
    net.compile_and_run()
    assert net.blocks["rec"].saved == ["Positive"]


def test_extract_entities_with_mock(monkeypatch):
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
            "rec": record(),
        },
        connections=[
            ("gen", "out", "xf", "in"),
            ("xf", "out", "rec", "in"),
        ],
    )
    net.compile_and_run()
    assert net.blocks["rec"].saved == [["Barack Obama"]]


def test_summarize_with_mock(monkeypatch):
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
            "rec": record(),
        },
        connections=[
            ("gen", "out", "xf", "in"),
            ("xf", "out", "rec", "in"),
        ],
    )
    net.compile_and_run()
    assert net.blocks["rec"].saved == ["This is a summary."]
