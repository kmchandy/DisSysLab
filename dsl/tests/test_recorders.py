import os
import tempfile
import pytest
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import record


def test_record_to_memory():
    net = Network(
        blocks={
            "gen": generate(["A", "B", "C"]),
            "rec": record()
        },
        connections=[("gen", "out", "rec", "in")]
    )
    net.compile_and_run()
    assert net.blocks["rec"].saved == ["A", "B", "C"]


def test_record_to_file():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name

    net = Network(
        blocks={
            "gen": generate(["X", "Y"]),
            "rec": record(to=tmp_path)
        },
        connections=[("gen", "out", "rec", "in")]
    )
    net.compile_and_run()

    with open(tmp_path) as f:
        lines = [line.strip() for line in f]
    os.remove(tmp_path)
    assert lines == ["X", "Y"]


def test_record_to_file_and_forward():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name

    net = Network(
        blocks={
            "gen": generate(["M", "N"]),
            "rec": record(to="file+stream", filepath=tmp_path),
            "sink": record()
        },
        connections=[
            ("gen", "out", "rec", "in"),
            ("rec", "out", "sink", "in")
        ]
    )
    net.compile_and_run()

    with open(tmp_path) as f:
        lines = [line.strip() for line in f]
    os.remove(tmp_path)
    assert lines == ["M", "N"]
    assert net.blocks["sink"].saved == ["M", "N"]


def test_record_to_stdout(capfd):
    net = Network(
        blocks={
            "gen": generate(["hello"]),
            "rec": record(to="stdout")
        },
        connections=[("gen", "out", "rec", "in")]
    )
    net.compile_and_run()
    out, _ = capfd.readouterr()
    assert "📤 hello" in out


def test_record_invalid_to():
    with pytest.raises(ValueError, match="Invalid 'to' argument"):
        record(to=12345)


def test_record_missing_filepath():
    with pytest.raises(ValueError, match="Missing 'filepath='"):
        record(to="file+stream")
