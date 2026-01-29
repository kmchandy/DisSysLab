"""Tests for all block types."""

import pytest
from queue import SimpleQueue
from threading import Thread
import time

from dsl.core import STOP
from dsl.blocks import Source, Transform, Sink, Broadcast, MergeAsynch, Split


class TestSource:
    """Test Source block."""

    def test_source_requires_name(self):
        """Source requires a name."""
        with pytest.raises(ValueError, match="requires a name"):
            Source(fn=lambda: None, name="")

    def test_source_requires_callable(self):
        """Source fn must be callable."""
        with pytest.raises(TypeError, match="must be callable"):
            Source(fn="not callable", name="src")

    def test_source_generates_messages(self):
        """Source generates messages from callable."""
        class ListSource:
            def __init__(self):
                self.data = [1, 2, 3]
                self.index = 0

            def run(self):
                if self.index >= len(self.data):
                    return None
                val = self.data[self.index]
                self.index += 1
                return val

        data = ListSource()
        source = Source(fn=data.run, name="src")
        source.out_q["out_"] = SimpleQueue()

        # Run in thread
        t = Thread(target=source.run)
        t.start()
        t.join(timeout=1)

        assert source.out_q["out_"].get() == 1
        assert source.out_q["out_"].get() == 2
        assert source.out_q["out_"].get() == 3
        assert source.out_q["out_"].get() is STOP

    def test_source_stops_on_none(self):
        """Source sends STOP when callable returns None."""
        call_count = [0]

        def gen():
            call_count[0] += 1
            if call_count[0] <= 2:
                return call_count[0]
            return None

        source = Source(fn=gen, name="src")
        source.out_q["out_"] = SimpleQueue()

        t = Thread(target=source.run)
        t.start()
        t.join(timeout=1)

        assert source.out_q["out_"].get() == 1
        assert source.out_q["out_"].get() == 2
        assert source.out_q["out_"].get() is STOP

    def test_source_has_default_outport(self):
        """Source has default_outport."""
        source = Source(fn=lambda: None, name="src")
        assert source.default_outport == "out_"


class TestTransform:
    """Test Transform block."""

    def test_transform_requires_name(self):
        """Transform requires a name."""
        with pytest.raises(ValueError, match="requires a name"):
            Transform(fn=lambda x: x, name="")

    def test_transform_requires_callable(self):
        """Transform fn must be callable."""
        with pytest.raises(TypeError, match="must be callable"):
            Transform(fn="not callable", name="trans")

    def test_transform_applies_function(self):
        """Transform applies function to messages."""
        transform = Transform(fn=lambda x: x * 2, name="double")
        transform.in_q["in_"] = SimpleQueue()
        transform.out_q["out_"] = SimpleQueue()

        transform.in_q["in_"].put(5)
        transform.in_q["in_"].put(10)
        transform.in_q["in_"].put(STOP)

        t = Thread(target=transform.run)
        t.start()
        t.join(timeout=1)

        assert transform.out_q["out_"].get() == 10
        assert transform.out_q["out_"].get() == 20
        assert transform.out_q["out_"].get() is STOP

    def test_transform_filters_none(self):
        """Transform filters None results."""
        def filter_positive(x):
            return x if x > 0 else None

        transform = Transform(fn=filter_positive, name="filter")
        transform.in_q["in_"] = SimpleQueue()
        transform.out_q["out_"] = SimpleQueue()

        transform.in_q["in_"].put(-5)
        transform.in_q["in_"].put(10)
        transform.in_q["in_"].put(-3)
        transform.in_q["in_"].put(STOP)

        t = Thread(target=transform.run)
        t.start()
        t.join(timeout=1)

        assert transform.out_q["out_"].get() == 10
        assert transform.out_q["out_"].get() is STOP

    def test_transform_with_params(self):
        """Transform passes params to function."""
        def scale(x, factor):
            return x * factor

        transform = Transform(fn=scale, params={"factor": 10}, name="scale")
        transform.in_q["in_"] = SimpleQueue()
        transform.out_q["out_"] = SimpleQueue()

        transform.in_q["in_"].put(5)
        transform.in_q["in_"].put(STOP)

        t = Thread(target=transform.run)
        t.start()
        t.join(timeout=1)

        assert transform.out_q["out_"].get() == 50

    def test_transform_has_default_ports(self):
        """Transform has default inport and outport."""
        transform = Transform(fn=lambda x: x, name="trans")
        assert transform.default_inport == "in_"
        assert transform.default_outport == "out_"


class TestSink:
    """Test Sink block."""

    def test_sink_requires_name(self):
        """Sink requires a name."""
        with pytest.raises(ValueError, match="requires a name"):
            Sink(fn=print, name="")

    def test_sink_requires_callable(self):
        """Sink fn must be callable."""
        with pytest.raises(TypeError, match="must be callable"):
            Sink(fn="not callable", name="sink")

    def test_sink_calls_function(self):
        """Sink calls function for each message."""
        results = []
        sink = Sink(fn=results.append, name="collector")
        sink.in_q["in_"] = SimpleQueue()

        sink.in_q["in_"].put(1)
        sink.in_q["in_"].put(2)
        sink.in_q["in_"].put(3)
        sink.in_q["in_"].put(STOP)

        t = Thread(target=sink.run)
        t.start()
        t.join(timeout=1)

        assert results == [1, 2, 3]

    def test_sink_with_params(self):
        """Sink passes params to function."""
        results = []

        def collect_with_prefix(msg, prefix):
            results.append(f"{prefix}{msg}")

        sink = Sink(fn=collect_with_prefix, params={
                    "prefix": ">> "}, name="sink")
        sink.in_q["in_"] = SimpleQueue()

        sink.in_q["in_"].put("hello")
        sink.in_q["in_"].put(STOP)

        t = Thread(target=sink.run)
        t.start()
        t.join(timeout=1)

        assert results == [">> hello"]

    def test_sink_has_default_inport(self):
        """Sink has default inport."""
        sink = Sink(fn=print, name="sink")
        assert sink.default_inport == "in_"


class TestBroadcast:
    """Test Broadcast block."""

    def test_broadcast_requires_name(self):
        """Broadcast requires a name."""
        with pytest.raises(ValueError, match="requires a name"):
            Broadcast(num_outputs=2, name="")

    def test_broadcast_requires_positive_outputs(self):
        """Broadcast requires at least 1 output."""
        with pytest.raises(ValueError, match="at least 1 output"):
            Broadcast(num_outputs=0, name="bc")

    def test_broadcast_copies_to_all(self):
        """Broadcast sends to all outputs."""
        broadcast = Broadcast(num_outputs=3, name="bc")
        broadcast.in_q["in_"] = SimpleQueue()
        broadcast.out_q["out_0"] = SimpleQueue()
        broadcast.out_q["out_1"] = SimpleQueue()
        broadcast.out_q["out_2"] = SimpleQueue()

        broadcast.in_q["in_"].put(42)
        broadcast.in_q["in_"].put(STOP)

        t = Thread(target=broadcast.run)
        t.start()
        t.join(timeout=1)

        # All outputs should receive the message
        assert broadcast.out_q["out_0"].get() == 42
        assert broadcast.out_q["out_1"].get() == 42
        assert broadcast.out_q["out_2"].get() == 42

        # All should receive STOP
        assert broadcast.out_q["out_0"].get() is STOP
        assert broadcast.out_q["out_1"].get() is STOP
        assert broadcast.out_q["out_2"].get() is STOP

    def test_broadcast_deep_copies(self):
        """Broadcast creates independent copies."""
        broadcast = Broadcast(num_outputs=2, name="bc")
        broadcast.in_q["in_"] = SimpleQueue()
        broadcast.out_q["out_0"] = SimpleQueue()
        broadcast.out_q["out_1"] = SimpleQueue()

        # Send mutable object
        original = {"value": 10}
        broadcast.in_q["in_"].put(original)
        broadcast.in_q["in_"].put(STOP)

        t = Thread(target=broadcast.run)
        t.start()
        t.join(timeout=1)

        copy_0 = broadcast.out_q["out_0"].get()
        copy_1 = broadcast.out_q["out_1"].get()

        # Should be equal but not the same object
        assert copy_0 == {"value": 10}
        assert copy_1 == {"value": 10}
        assert copy_0 is not original
        assert copy_1 is not original
        assert copy_0 is not copy_1

    def test_broadcast_has_default_inport(self):
        """Broadcast has default inport."""
        broadcast = Broadcast(num_outputs=2, name="bc")
        assert broadcast.default_inport == "in_"

    def test_broadcast_no_default_outport(self):
        """Broadcast has no default outport (multiple outputs)."""
        broadcast = Broadcast(num_outputs=2, name="bc")
        assert broadcast.default_outport is None


class TestMergeAsynch:
    """Test MergeAsynch block."""

    def test_merge_requires_name(self):
        """MergeAsynch requires a name."""
        with pytest.raises(ValueError, match="requires a name"):
            MergeAsynch(num_inputs=2, name="")

    def test_merge_requires_positive_inputs(self):
        """MergeAsynch requires at least 1 input."""
        with pytest.raises(ValueError, match="at least 1 input"):
            MergeAsynch(num_inputs=0, name="merge")

    def test_merge_combines_inputs(self):
        """MergeAsynch combines multiple inputs."""
        merge = MergeAsynch(num_inputs=2, name="merge")
        merge.in_q["in_0"] = SimpleQueue()
        merge.in_q["in_1"] = SimpleQueue()
        merge.out_q["out_"] = SimpleQueue()

        # Send messages from both inputs
        merge.in_q["in_0"].put(1)
        merge.in_q["in_0"].put(2)
        merge.in_q["in_0"].put(STOP)

        merge.in_q["in_1"].put(10)
        merge.in_q["in_1"].put(20)
        merge.in_q["in_1"].put(STOP)

        t = Thread(target=merge.run)
        t.start()
        t.join(timeout=1)

        # Collect all output messages (order may vary)
        results = []
        while True:
            msg = merge.out_q["out_"].get()
            if msg is STOP:
                break
            results.append(msg)

        assert set(results) == {1, 2, 10, 20}
        assert len(results) == 4

    def test_merge_waits_for_all_stops(self):
        """MergeAsynch waits for STOP from all inputs."""
        merge = MergeAsynch(num_inputs=2, name="merge")
        merge.in_q["in_0"] = SimpleQueue()
        merge.in_q["in_1"] = SimpleQueue()
        merge.out_q["out_"] = SimpleQueue()

        # Only one input sends STOP immediately
        merge.in_q["in_0"].put(STOP)

        t = Thread(target=merge.run)
        t.start()

        # Give it a moment
        time.sleep(0.1)

        # Should not have sent STOP yet (still waiting for in_1)
        assert merge.out_q["out_"].empty()

        # Now send STOP from second input
        merge.in_q["in_1"].put(STOP)

        t.join(timeout=1)

        # Now should have sent STOP
        assert merge.out_q["out_"].get() is STOP

    def test_merge_no_default_inport(self):
        """MergeAsynch has no default inport (multiple inputs)."""
        merge = MergeAsynch(num_inputs=2, name="merge")
        assert merge.default_inport is None

    def test_merge_has_default_outport(self):
        """MergeAsynch has default outport."""
        merge = MergeAsynch(num_inputs=2, name="merge")
        assert merge.default_outport == "out_"


class TestSplit:
    """Test Split block."""

    def test_split_requires_name(self):
        """Split requires a name."""
        with pytest.raises(ValueError, match="requires a name"):
            Split(fn=lambda x: [x, None], num_outputs=2, name="")

    def test_split_requires_callable(self):
        """Split fn must be callable."""
        with pytest.raises(TypeError, match="must be callable"):
            Split(fn="not callable", num_outputs=2, name="split")

    def test_split_requires_multiple_outputs(self):
        """Split requires at least 2 outputs."""
        with pytest.raises(ValueError, match="at least 2 outputs"):
            Split(fn=lambda x: [x], num_outputs=1, name="split")

    def test_split_routes_messages(self):
        """Split routes based on function."""
        def even_odd(x):
            if x % 2 == 0:
                return [x, None]
            else:
                return [None, x]

        split = Split(fn=even_odd, num_outputs=2, name="split")
        split.in_q["in_"] = SimpleQueue()
        split.out_q["out_0"] = SimpleQueue()
        split.out_q["out_1"] = SimpleQueue()

        split.in_q["in_"].put(2)
        split.in_q["in_"].put(3)
        split.in_q["in_"].put(4)
        split.in_q["in_"].put(STOP)

        t = Thread(target=split.run)
        t.start()
        t.join(timeout=1)

        # Even numbers to out_0
        assert split.out_q["out_0"].get() == 2
        assert split.out_q["out_0"].get() == 4
        assert split.out_q["out_0"].get() is STOP

        # Odd numbers to out_1
        assert split.out_q["out_1"].get() == 3
        assert split.out_q["out_1"].get() is STOP

    def test_split_multicast(self):
        """Split can send to multiple outputs."""
        def multicast(x):
            if x > 10:
                return [x, x]  # Send to both
            else:
                return [x, None]  # Send to first only

        split = Split(fn=multicast, num_outputs=2, name="split")
        split.in_q["in_"] = SimpleQueue()
        split.out_q["out_0"] = SimpleQueue()
        split.out_q["out_1"] = SimpleQueue()

        split.in_q["in_"].put(5)
        split.in_q["in_"].put(15)
        split.in_q["in_"].put(STOP)

        t = Thread(target=split.run)
        t.start()
        t.join(timeout=1)

        # out_0 gets both
        assert split.out_q["out_0"].get() == 5
        assert split.out_q["out_0"].get() == 15

        # out_1 only gets 15
        assert split.out_q["out_1"].get() == 15

    def test_split_validates_return_list(self):
        """Split validates function returns a list."""
        def bad_router(x):
            return x  # Should return list!

        split = Split(fn=bad_router, num_outputs=2, name="split")
        split.in_q["in_"] = SimpleQueue()
        split.out_q["out_0"] = SimpleQueue()
        split.out_q["out_1"] = SimpleQueue()

        split.in_q["in_"].put(5)
        split.in_q["in_"].put(STOP)

        t = Thread(target=split.run)
        t.start()
        t.join(timeout=1)

        # Should have broadcast STOP due to error
        assert split.out_q["out_0"].get() is STOP
        assert split.out_q["out_1"].get() is STOP

    def test_split_validates_list_length(self):
        """Split validates function returns correct length list."""
        def bad_router(x):
            return [x]  # Should return 2 items!

        split = Split(fn=bad_router, num_outputs=2, name="split")
        split.in_q["in_"] = SimpleQueue()
        split.out_q["out_0"] = SimpleQueue()
        split.out_q["out_1"] = SimpleQueue()

        split.in_q["in_"].put(5)
        split.in_q["in_"].put(STOP)

        t = Thread(target=split.run)
        t.start()
        t.join(timeout=1)

        # Should have broadcast STOP due to error
        assert split.out_q["out_0"].get() is STOP
        assert split.out_q["out_1"].get() is STOP

    def test_split_has_default_inport(self):
        """Split has default inport."""
        split = Split(fn=lambda x: [x, None], num_outputs=2, name="split")
        assert split.default_inport == "in_"

    def test_split_no_default_outport(self):
        """Split has no default outport (multiple outputs)."""
        split = Split(fn=lambda x: [x, None], num_outputs=2, name="split")
        assert split.default_outport is None
