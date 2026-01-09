# tests/transform_test.py

"""
Tests for the Transform implementation.

These tests demonstrate:
1. Basic transform functionality
2. Stateful transforms
3. Filter patterns (returning None)
4. Error handling
5. STOP signal propagation
"""

import traceback
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

    def broadcast_stop(self):
        for outport in self.outports:
            self.send(STOP, outport)


# Import Transform implementation


class Transform(MockAgent):
    """Transform Agent implementation"""

    def __init__(self, *, fn):
        if not callable(fn):
            raise TypeError(
                f"Transform fn must be callable. Got {type(fn).__name__}"
            )

        super().__init__(inports=["in"], outports=["out"])
        self._fn = fn

    def run(self):
        while True:
            msg = self.recv("in")

            if msg is STOP:
                self.broadcast_stop()
                return

            try:
                result = self._fn(msg)
            except Exception as e:
                print(f"[Transform] Error in fn: {e}")
                print(traceback.format_exc())
                self.broadcast_stop()
                return

            self.send(result, "out")


# ============================================================================
# Tests
# ============================================================================

def test_basic_transform():
    """Test basic stateless transform"""
    print("\n" + "="*70)
    print("TEST 1: Basic Transform (Double)")
    print("="*70)

    def double(msg):
        return {"value": msg["value"] * 2}

    transform = Transform(fn=double)

    # Setup queues
    input_queue = SimpleQueue()
    output_queue = SimpleQueue()
    transform.in_q["in"] = input_queue
    transform.out_q["out"] = output_queue

    # Send messages
    messages = [{"value": 1}, {"value": 2}, {"value": 3}]
    for msg in messages:
        input_queue.put(msg)
    input_queue.put(STOP)

    # Run transform
    transform.run()

    # Collect results
    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    expected = [{"value": 2}, {"value": 4}, {"value": 6}]
    print(f"Input:    {messages}")
    print(f"Output:   {results}")
    print(f"Expected: {expected}")
    assert results == expected, f"Expected {expected}, got {results}"
    print("✓ Test passed!")


def test_stateful_transform():
    """Test transform with state (counter)"""
    print("\n" + "="*70)
    print("TEST 2: Stateful Transform (Add Index)")
    print("="*70)

    class Counter:
        def __init__(self):
            self.count = 0

        def add_index(self, msg):
            self.count += 1
            return {**msg, "index": self.count}

    counter = Counter()
    transform = Transform(fn=counter.add_index)

    input_queue = SimpleQueue()
    output_queue = SimpleQueue()
    transform.in_q["in"] = input_queue
    transform.out_q["out"] = output_queue

    # Send messages
    messages = [{"value": "a"}, {"value": "b"}, {"value": "c"}]
    for msg in messages:
        input_queue.put(msg)
    input_queue.put(STOP)

    transform.run()

    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    expected = [
        {"value": "a", "index": 1},
        {"value": "b", "index": 2},
        {"value": "c", "index": 3}
    ]

    print(f"Results:")
    for r in results:
        print(f"  {r}")

    assert results == expected, f"Expected {expected}, got {results}"
    print("✓ Test passed!")


def test_filter_transform():
    """Test transform that filters messages (returns None)"""
    print("\n" + "="*70)
    print("TEST 3: Filter Transform (Positive Only)")
    print("="*70)

    class PositiveFilter:
        def filter(self, msg):
            if msg["value"] > 0:
                return msg
            return None  # Filter out non-positive

    filter_obj = PositiveFilter()
    transform = Transform(fn=filter_obj.filter)

    input_queue = SimpleQueue()
    output_queue = SimpleQueue()
    transform.in_q["in"] = input_queue
    transform.out_q["out"] = output_queue

    # Send mix of positive and negative
    messages = [
        {"value": 5},
        {"value": -3},
        {"value": 10},
        {"value": -1},
        {"value": 7}
    ]

    for msg in messages:
        input_queue.put(msg)
    input_queue.put(STOP)

    transform.run()

    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    expected = [{"value": 5}, {"value": 10}, {"value": 7}]

    print(f"Input (5 messages): {messages}")
    print(f"Output (3 messages): {results}")
    assert results == expected, f"Expected {expected}, got {results}"
    print("✓ Test passed!")


def test_transform_with_parameters():
    """Test transform using class with parameters"""
    print("\n" + "="*70)
    print("TEST 4: Transform with Parameters (Scaler)")
    print("="*70)

    class Scaler:
        def __init__(self, factor):
            self.factor = factor

        def scale(self, msg):
            return {"value": msg["value"] * self.factor}

    scaler = Scaler(factor=10)
    transform = Transform(fn=scaler.scale)

    input_queue = SimpleQueue()
    output_queue = SimpleQueue()
    transform.in_q["in"] = input_queue
    transform.out_q["out"] = output_queue

    messages = [{"value": 1}, {"value": 2}, {"value": 3}]
    for msg in messages:
        input_queue.put(msg)
    input_queue.put(STOP)

    transform.run()

    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    expected = [{"value": 10}, {"value": 20}, {"value": 30}]
    print(f"Factor: {scaler.factor}")
    print(f"Input:  {messages}")
    print(f"Output: {results}")
    assert results == expected
    print("✓ Test passed!")


def test_text_transform():
    """Test text processing transform"""
    print("\n" + "="*70)
    print("TEST 5: Text Transform (Clean)")
    print("="*70)

    import re

    class TextCleaner:
        def clean(self, msg):
            text = msg["text"]
            cleaned = re.sub(r'[^\w\s.,!?-]', '', text)
            cleaned = ' '.join(cleaned.split())
            return {**msg, "clean_text": cleaned}

    cleaner = TextCleaner()
    transform = Transform(fn=cleaner.clean)

    input_queue = SimpleQueue()
    output_queue = SimpleQueue()
    transform.in_q["in"] = input_queue
    transform.out_q["out"] = output_queue

    messages = [
        {"text": "Hello 😊 World!"},
        {"text": "Test   multiple    spaces"},
        {"text": "Remove 🎉 emojis 🚀"}
    ]

    for msg in messages:
        input_queue.put(msg)
    input_queue.put(STOP)

    transform.run()

    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    print("Results:")
    for r in results:
        print(f"  Original: {r['text']}")
        print(f"  Cleaned:  {r['clean_text']}")
        print()

    assert len(results) == 3
    assert "😊" not in results[0]["clean_text"]
    assert "🎉" not in results[2]["clean_text"]
    print("✓ Test passed!")


def test_error_handling():
    """Test that errors are handled gracefully"""
    print("\n" + "="*70)
    print("TEST 6: Error Handling")
    print("="*70)

    def error_fn(msg):
        if msg["value"] == 3:
            raise ValueError("Simulated error")
        return {"value": msg["value"] * 2}

    transform = Transform(fn=error_fn)

    input_queue = SimpleQueue()
    output_queue = SimpleQueue()
    transform.in_q["in"] = input_queue
    transform.out_q["out"] = output_queue

    # Send messages (error on 3rd)
    input_queue.put({"value": 1})
    input_queue.put({"value": 2})
    input_queue.put({"value": 3})  # This will error
    input_queue.put({"value": 4})  # Never reached
    input_queue.put(STOP)

    transform.run()

    # Should get 2 results then STOP
    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    print(f"Processed {len(results)} messages before error")
    assert len(results) == 2
    print("✓ Test passed! (Error handled gracefully)")


def test_invalid_fn():
    """Test that Transform validates fn is callable"""
    print("\n" + "="*70)
    print("TEST 7: Invalid Function")
    print("="*70)

    try:
        transform = Transform(fn="not a function")
        print("✗ Test failed! Should have raised TypeError")
        assert False
    except TypeError as e:
        print(f"✓ Correctly raised TypeError: {e}")


def test_moving_average():
    """Test stateful transform that computes moving average"""
    print("\n" + "="*70)
    print("TEST 8: Moving Average Transform")
    print("="*70)

    class MovingAverage:
        def __init__(self, window_size):
            self.window_size = window_size
            self.values = []

        def average(self, msg):
            self.values.append(msg["value"])
            if len(self.values) > self.window_size:
                self.values.pop(0)
            avg = sum(self.values) / len(self.values)
            return {**msg, "moving_avg": avg}

    avg = MovingAverage(window_size=3)
    transform = Transform(fn=avg.average)

    input_queue = SimpleQueue()
    output_queue = SimpleQueue()
    transform.in_q["in"] = input_queue
    transform.out_q["out"] = output_queue

    values = [10, 20, 30, 40, 50]
    for v in values:
        input_queue.put({"value": v})
    input_queue.put(STOP)

    transform.run()

    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    print("Results:")
    for r in results:
        print(
            f"  Value: {r['value']}, Moving Avg (window=3): {r['moving_avg']:.2f}")

    # Check moving averages
    assert abs(results[0]["moving_avg"] - 10.0) < 0.01  # [10]
    assert abs(results[1]["moving_avg"] - 15.0) < 0.01  # [10, 20]
    assert abs(results[2]["moving_avg"] - 20.0) < 0.01  # [10, 20, 30]
    assert abs(results[3]["moving_avg"] - 30.0) < 0.01  # [20, 30, 40]
    assert abs(results[4]["moving_avg"] - 40.0) < 0.01  # [30, 40, 50]
    print("✓ Test passed!")


# ============================================================================
# Run All Tests
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TRANSFORM IMPLEMENTATION TESTS")
    print("Testing the Transform agent")
    print("="*70)

    test_basic_transform()
    test_stateful_transform()
    test_filter_transform()
    test_transform_with_parameters()
    test_text_transform()
    test_error_handling()
    test_invalid_fn()
    test_moving_average()

    print("\n" + "="*70)
    print("ALL TESTS PASSED! ✓")
    print("="*70)
