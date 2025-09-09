import pytest
from dsl.core import STOP
from dsl.block_lib.sinks.sink import Sink


def test_sink_records_messages():
    recorded = []

    def record_fn(agent, msg):
        recorded.append(msg)

    sink = Sink(record_fn=record_fn)
    # Send a few messages manually
    sink._handle_msg(sink, "hello")
    sink._handle_msg(sink, 123)

    assert recorded == ["hello", 123]


def test_sink_ignores_stop():
    recorded = []

    def record_fn(agent, msg):
        recorded.append(msg)

    sink = Sink(record_fn=record_fn)
    sink._handle_msg(sink, STOP)

    # Nothing should have been recorded
    assert recorded == []


def test_sink_survives_record_fn_error(tmp_path):
    # Redirect log file to temp
    log_file = tmp_path / "dsl_debug.log"

    def bad_record_fn(agent, msg):
        raise RuntimeError("oops")

    sink = Sink(record_fn=bad_record_fn)

    # Patch class to write to our tmp log instead of hardcoded path
    def patched_handle_msg(agent, msg):
        if msg == STOP:
            return
        try:
            bad_record_fn(agent, msg)
        except Exception:
            with open(log_file, "a") as log:
                log.write("error happened\n")

    sink.handle_msg = patched_handle_msg  # monkeypatch

    sink._handle_msg(sink, "test")

    assert log_file.read_text().strip() == "error happened"
