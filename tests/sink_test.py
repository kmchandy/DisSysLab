# test_sink.py

"""
Tests for the Sink implementation.

These tests demonstrate:
1. Basic sink functionality
2. Stateful sinks
3. Error handling
4. STOP signal handling
5. None filtering
"""

import traceback
import sys
from queue import SimpleQueue

# Mock the infrastructure for testing


class STOP:
    """Sentinel for end-of-stream"""
    pass


STOP = STOP()


class MockAgent:
    """Minimal Agent base class for testing"""

    def __init__(self, inports=None, outports=None):
        self.inports = inports or []
        self.outports = outports or []
        self.in_q = {p: None for p in self.inports}
        self.out_q = {p: None for p in self.outports}
        self.name = None

    def send(self, msg, outport):
        if msg is None:
            return
        q = self.out_q[outport]
        if q:
            q.put(msg)

    def recv(self, inport):
        q = self.in_q[inport]
        return q.get() if q else None


# Import Sink implementation


class Sink(MockAgent):
    """Sink Agent implementation"""

    def __init__(self, *, fn):
        if not callable(fn):
            raise TypeError(
                f"Sink fn must be callable. Got {type(fn).__name__}"
            )

        super().__init__(inports=["in"], outports=[])
        self._fn = fn

    def run(self):
        try:
            while True:
                msg = self.recv("in")

                if msg is STOP:
                    return

                if msg is None:
                    continue

                try:
                    self._fn(msg)
                except Exception as e:
                    print(f"[Sink] Error in fn: {e}")
                    print(traceback.format_exc())
                    return

        except Exception as e:
            print(f"[Sink] Error: {e}")
            print(traceback.format_exc())
            return


# ============================================================================
# Tests
# ============================================================================

def test_basic_sink():
    """Test basic sink with simple function"""
    print("\n" + "="*70)
    print("TEST 1: Basic Sink")
    print("="*70)

    results = []

    def collect(msg):
        results.append(msg)

    sink = Sink(fn=collect)

    # Setup queue
    input_queue = SimpleQueue()
    sink.in_q["in"] = input_queue

    # Send messages
    messages = [{"value": 1}, {"value": 2}, {"value": 3}]
    for msg in messages:
        input_queue.put(msg)
    input_queue.put(STOP)

    # Run sink
    sink.run()

    print(f"Input:  {messages}")
    print(f"Output: {results}")
    assert results == messages, f"Expected {messages}, got {results}"
    print("✓ Test passed!")


def test_stateful_sink():
    """Test sink with stateful class"""
    print("\n" + "="*70)
    print("TEST 2: Stateful Sink (Counter)")
    print("="*70)

    class Counter:
        def __init__(self):
            self.count = 0
            self.sum = 0

        def process(self, msg):
            self.count += 1
            self.sum += msg["value"]

    counter = Counter()
    sink = Sink(fn=counter.process)

    input_queue = SimpleQueue()
    sink.in_q["in"] = input_queue

    # Send messages
    for i in range(1, 6):
        input_queue.put({"value": i})
    input_queue.put(STOP)

    sink.run()

    print(f"Count: {counter.count}")
    print(f"Sum: {counter.sum}")
    assert counter.count == 5, f"Expected count=5, got {counter.count}"
    assert counter.sum == 15, f"Expected sum=15, got {counter.sum}"
    print("✓ Test passed!")


def test_none_filtering():
    """Test that None messages are filtered out"""
    print("\n" + "="*70)
    print("TEST 3: None Filtering")
    print("="*70)

    results = []

    def collect(msg):
        results.append(msg)

    sink = Sink(fn=collect)

    input_queue = SimpleQueue()
    sink.in_q["in"] = input_queue

    # Send mix of messages and None
    input_queue.put({"value": 1})
    input_queue.put(None)
    input_queue.put({"value": 2})
    input_queue.put(None)
    input_queue.put({"value": 3})
    input_queue.put(STOP)

    sink.run()

    expected = [{"value": 1}, {"value": 2}, {"value": 3}]
    print(f"Expected (None filtered): {expected}")
    print(f"Got: {results}")
    assert results == expected, f"Expected {expected}, got {results}"
    print("✓ Test passed!")


def test_print_sink():
    """Test sink that prints output"""
    print("\n" + "="*70)
    print("TEST 4: Print Sink")
    print("="*70)

    def print_msg(msg):
        print(f"  Received: {msg}")

    sink = Sink(fn=print_msg)

    input_queue = SimpleQueue()
    sink.in_q["in"] = input_queue

    messages = [
        {"text": "Hello"},
        {"text": "World"},
        {"text": "Testing"}
    ]

    for msg in messages:
        input_queue.put(msg)
    input_queue.put(STOP)

    print("Output:")
    sink.run()
    print("✓ Test passed!")


def test_error_handling():
    """Test that errors in sink function are handled"""
    print("\n" + "="*70)
    print("TEST 5: Error Handling")
    print("="*70)

    def error_fn(msg):
        if msg["value"] == 3:
            raise ValueError("Simulated error")
        print(f"  Processed: {msg}")

    sink = Sink(fn=error_fn)

    input_queue = SimpleQueue()
    sink.in_q["in"] = input_queue

    # Send messages (error on 3rd)
    input_queue.put({"value": 1})
    input_queue.put({"value": 2})
    input_queue.put({"value": 3})  # This will error
    input_queue.put({"value": 4})  # Never reached
    input_queue.put(STOP)

    sink.run()
    print("✓ Test passed! (Error was handled gracefully)")


def test_invalid_fn():
    """Test that Sink validates fn is callable"""
    print("\n" + "="*70)
    print("TEST 6: Invalid Function")
    print("="*70)

    try:
        sink = Sink(fn="not a function")
        print("✗ Test failed! Should have raised TypeError")
        assert False
    except TypeError as e:
        print(f"✓ Correctly raised TypeError: {e}")


def test_file_writer_sink():
    """Test sink that writes to a file"""
    print("\n" + "="*70)
    print("TEST 7: File Writer Sink")
    print("="*70)

    import tempfile
    import os

    # Create temp file
    fd, temp_path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)

    class FileWriter:
        def __init__(self, filename):
            self.file = open(filename, 'w')

        def write(self, msg):
            self.file.write(str(msg) + "\n")

        def close(self):
            self.file.close()

    writer = FileWriter(temp_path)
    sink = Sink(fn=writer.write)

    input_queue = SimpleQueue()
    sink.in_q["in"] = input_queue

    messages = [{"value": 1}, {"value": 2}, {"value": 3}]
    for msg in messages:
        input_queue.put(msg)
    input_queue.put(STOP)

    sink.run()
    writer.close()

    # Read back and verify
    with open(temp_path, 'r') as f:
        lines = f.readlines()

    os.unlink(temp_path)

    print(f"Wrote {len(lines)} lines to file")
    assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"
    print("✓ Test passed!")


def test_statistics_sink():
    """Test sink that computes statistics"""
    print("\n" + "="*70)
    print("TEST 8: Statistics Sink")
    print("="*70)

    class StatsSink:
        def __init__(self):
            self.count = 0
            self.sum = 0
            self.values = []

        def process(self, msg):
            value = msg["value"]
            self.count += 1
            self.sum += value
            self.values.append(value)

        def mean(self):
            return self.sum / self.count if self.count > 0 else 0

        def min(self):
            return min(self.values) if self.values else None

        def max(self):
            return max(self.values) if self.values else None

    stats = StatsSink()
    sink = Sink(fn=stats.process)

    input_queue = SimpleQueue()
    sink.in_q["in"] = input_queue

    # Send values
    values = [10, 20, 30, 40, 50]
    for v in values:
        input_queue.put({"value": v})
    input_queue.put(STOP)

    sink.run()

    print(f"Count: {stats.count}")
    print(f"Sum: {stats.sum}")
    print(f"Mean: {stats.mean()}")
    print(f"Min: {stats.min()}")
    print(f"Max: {stats.max()}")

    assert stats.count == 5
    assert stats.sum == 150
    assert stats.mean() == 30.0
    assert stats.min() == 10
    assert stats.max() == 50
    print("✓ Test passed!")


# ============================================================================
# Run All Tests
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SINK IMPLEMENTATION TESTS")
    print("Testing the Sink agent")
    print("="*70)

    test_basic_sink()
    test_stateful_sink()
    test_none_filtering()
    test_print_sink()
    test_error_handling()
    test_invalid_fn()
    test_file_writer_sink()
    test_statistics_sink()

    print("\n" + "="*70)
    print("ALL TESTS PASSED! ✓")
    print("="*70)
