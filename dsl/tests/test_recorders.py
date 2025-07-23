import tempfile
import os
from dsl.core import Network
from dsl.block_lib.stream_generators import generate
from dsl.block_lib.stream_recorders import record


def test_record_to_memory():
    gen = generate(["alpha", "beta"])
    sink = record(to="memory")
    net = Network(
        name="test_record_memory",
        blocks={"gen": gen, "sink": sink},
        connections=[("gen", "out", "sink", "in")]
    )
    net.compile()
    net.run()
    assert hasattr(sink, "saved")
    assert sink.saved == ["alpha", "beta"]


def test_record_to_file():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        gen = generate(["x", "y", "z"])
        sink = record(to=path)
        net = Network(
            name="test_record_file",
            blocks={"gen": gen, "sink": sink},
            connections=[("gen", "out", "sink", "in")]
        )
        net.compile()
        net.run()
        with open(path, "r") as f:
            lines = [line.strip() for line in f.readlines()]
        assert lines == ["x", "y", "z"]
    finally:
        os.remove(path)


def test_record_to_file_and_forward():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        gen = generate(["snap", "crackle"])
        tap = record(to="file+stream", filepath=path)
        sink = record(to="memory")
        net = Network(
            name="test_record_file_copy",
            blocks={"gen": gen, "tap": tap, "sink": sink},
            connections=[
                ("gen", "out", "tap", "in"),
                ("tap", "out", "sink", "in")
            ]
        )
        net.compile()
        net.run()
        assert hasattr(sink, "saved")
        assert sink.saved == ["snap", "crackle"]
        with open(path, "r") as f:
            contents = [line.strip() for line in f.readlines()]
        assert contents == ["'snap'", "'crackle'"]
    finally:
        os.remove(path)


def test_record_invalid_to_argument():
    # Use a non-string type to trigger the final ValueError
    try:
        record(to=42)  # Invalid type for 'to'
        assert False, "Expected ValueError for invalid 'to' argument"
    except ValueError as e:
        assert "Invalid 'to' argument" in str(e)


def test_record_file_stream_missing_filepath():
    try:
        record(to="file+stream")
        assert False, "Expected ValueError for missing 'filepath'"
    except ValueError as e:
        assert "Missing 'filepath='" in str(e)


def test_record_to_directory_should_fail():
    tmp_dir = tempfile.mkdtemp()
    try:
        record(to=tmp_dir)
        assert False, "Expected ValueError when using a directory as 'to' path"
    except ValueError as e:
        assert "cannot be a directory" in str(e)
    finally:
        os.rmdir(tmp_dir)


if __name__ == "__main__":
    test_record_to_memory()
    test_record_to_file()
    test_record_to_file_and_forward()
    test_record_invalid_to_argument()
    test_record_file_stream_missing_filepath()
    test_record_to_directory_should_fail()
    print("✅ All record(...) tests passed.")
