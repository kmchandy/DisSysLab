# test_source.py

"""
Tests for the new Source implementation using .run() pattern.

These tests demonstrate:
1. Basic source functionality
2. Various data source types
3. Rate limiting with intervals
4. Error handling
5. Integration with the network infrastructure
"""

import traceback
import sys
import time
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


# Import Source implementation


class Source(MockAgent):
    """Source Agent using .run() pattern"""

    def __init__(self, *, data, interval=0):
        if not hasattr(data, 'run'):
            raise AttributeError(
                f"Source data object must have a .run() method. "
                f"Got {type(data).__name__} with no .run() method."
            )

        if not callable(data.run):
            raise AttributeError(
                f"Source data.run must be callable. "
                f"Got {type(data.run).__name__}"
            )

        super().__init__(inports=[], outports=["out"])
        self._data = data
        self._interval = interval

    def run(self):
        try:
            while True:
                msg = self._data.run()

                if msg is None:
                    self.send(STOP, "out")
                    return

                self.send(msg, "out")

                if self._interval > 0:
                    time.sleep(self._interval)

        except Exception as e:
            print(f"[Source] Error during data.run(): {e}")
            print(traceback.format_exc())
            self.send(STOP, "out")


# ============================================================================
# Example Data Sources
# ============================================================================

class ListSource:
    """Emit items from a list"""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def run(self):
        if self.index >= len(self.items):
            return None
        item = self.items[self.index]
        self.index += 1
        return item


class CounterSource:
    """Count up to max_count"""

    def __init__(self, max_count):
        self.count = 0
        self.max_count = max_count

    def run(self):
        if self.count >= self.max_count:
            return None
        self.count += 1
        return {"count": self.count}


class ErrorSource:
    """Source that raises an error after N calls"""

    def __init__(self, error_after=3):
        self.calls = 0
        self.error_after = error_after

    def run(self):
        self.calls += 1
        if self.calls > self.error_after:
            raise RuntimeError("Simulated error in source")
        return {"call": self.calls}


# ============================================================================
# Tests
# ============================================================================

def test_basic_list_source():
    """Test basic functionality with ListSource"""
    print("\n" + "="*70)
    print("TEST 1: Basic ListSource")
    print("="*70)

    items = [{"value": 1}, {"value": 2}, {"value": 3}]
    data = ListSource(items)
    source = Source(data=data)

    # Connect output queue
    output_queue = SimpleQueue()
    source.out_q["out"] = output_queue

    # Run the source
    source.run()

    # Collect results
    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    print(f"Input:  {items}")
    print(f"Output: {results}")
    assert results == items, f"Expected {items}, got {results}"
    print("✓ Test passed!")


def test_counter_source():
    """Test CounterSource with dict messages"""
    print("\n" + "="*70)
    print("TEST 2: CounterSource")
    print("="*70)

    data = CounterSource(max_count=5)
    source = Source(data=data)

    output_queue = SimpleQueue()
    source.out_q["out"] = output_queue

    source.run()

    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    expected = [{"count": i} for i in range(1, 6)]
    print(f"Expected: {expected}")
    print(f"Got:      {results}")
    assert results == expected, f"Expected {expected}, got {results}"
    print("✓ Test passed!")


def test_rate_limiting():
    """Test that interval parameter adds delays"""
    print("\n" + "="*70)
    print("TEST 3: Rate Limiting with interval")
    print("="*70)

    data = CounterSource(max_count=3)
    source = Source(data=data, interval=0.1)  # 100ms between messages

    output_queue = SimpleQueue()
    source.out_q["out"] = output_queue

    start_time = time.time()
    source.run()
    elapsed = time.time() - start_time

    # Should take at least 200ms (2 intervals for 3 messages)
    print(f"Elapsed time: {elapsed:.3f}s")
    print(f"Expected: >= 0.2s (3 messages with 0.1s interval)")
    assert elapsed >= 0.2, f"Expected >= 0.2s, got {elapsed:.3f}s"
    print("✓ Test passed!")


def test_empty_source():
    """Test source with no items"""
    print("\n" + "="*70)
    print("TEST 4: Empty Source")
    print("="*70)

    data = ListSource([])
    source = Source(data=data)

    output_queue = SimpleQueue()
    source.out_q["out"] = output_queue

    source.run()

    # Should only receive STOP
    msg = output_queue.get()
    print(f"Received: {msg}")
    assert msg is STOP, f"Expected STOP, got {msg}"
    print("✓ Test passed!")


def test_invalid_data_object():
    """Test that Source validates data object has .run() method"""
    print("\n" + "="*70)
    print("TEST 5: Invalid Data Object (no .run() method)")
    print("="*70)

    class InvalidSource:
        pass

    try:
        source = Source(data=InvalidSource())
        print("✗ Test failed! Should have raised AttributeError")
        assert False
    except AttributeError as e:
        print(f"✓ Correctly raised AttributeError: {e}")


def test_error_handling():
    """Test that errors in data.run() are handled gracefully"""
    print("\n" + "="*70)
    print("TEST 6: Error Handling")
    print("="*70)

    data = ErrorSource(error_after=2)
    source = Source(data=data)

    output_queue = SimpleQueue()
    source.out_q["out"] = output_queue

    # Run source (will error after 2 messages)
    source.run()

    # Should get 2 messages then STOP
    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    print(f"Received {len(results)} messages before error")
    assert len(results) == 2, f"Expected 2 messages, got {len(results)}"
    print("✓ Test passed!")


def test_stateful_source():
    """Test that source object maintains state across .run() calls"""
    print("\n" + "="*70)
    print("TEST 7: Stateful Source")
    print("="*70)

    class StatefulSource:
        def __init__(self):
            self.state = []

        def run(self):
            if len(self.state) >= 3:
                return None
            self.state.append(len(self.state))
            return {"state_snapshot": self.state.copy()}

    data = StatefulSource()
    source = Source(data=data)

    output_queue = SimpleQueue()
    source.out_q["out"] = output_queue

    source.run()

    results = []
    while True:
        msg = output_queue.get()
        if msg is STOP:
            break
        results.append(msg)

    expected = [
        {"state_snapshot": [0]},
        {"state_snapshot": [0, 1]},
        {"state_snapshot": [0, 1, 2]}
    ]

    print("Results:")
    for r in results:
        print(f"  {r}")

    assert results == expected, f"Expected {expected}, got {results}"
    print("✓ Test passed!")


# ============================================================================
# Run All Tests
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SOURCE IMPLEMENTATION TESTS")
    print("Testing the new .run() pattern for data sources")
    print("="*70)

    test_basic_list_source()
    test_counter_source()
    test_rate_limiting()
    test_empty_source()
    test_invalid_data_object()
    test_error_handling()
    test_stateful_source()

    print("\n" + "="*70)
    print("ALL TESTS PASSED! ✓")
    print("="*70)
