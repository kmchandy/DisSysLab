# tests/test_routers_fanin.py
# Simple, self-contained tests for MergeSynch and MergeAsynch
# These tests monkeypatch `recv`, `wait_for_any_port`, and `send`
# so we don't need a full Network runner.

from __future__ import annotations

from dsl.kit import Network, FromListDelay, ToList, ToSet, MergeSynch, MergeAsynch

# ---------------------------
# MergeSynch tests
# ---------------------------


def test_merge_synch_basic_with_transformer():
    """
    Two inports: 'a' and 'b'.
    Each round, MergeSynch reads one message from each inport (in order),
    applies func(list_of_msgs), and emits the result.
    Stops when any inport yields '__STOP__'.
    """

    def f(pair):
        return pair[0] + pair[1]

    results = []
    network = Network(
        blocks={
            "source_a": FromListDelay(items=["HELLO", "GOOD", "HOW"], delay=0.1),
            "source_b": FromListDelay(items=[" world", " morning", " are you?"], delay=0.08),
            "merge_synch": MergeSynch(inports=["a", "b"], func=f),
            "sink": ToList(results)
        },
        connections=[
            ("source_a", "out", "merge_synch", "a"),
            ("source_b", "out", "merge_synch", "b"),
            ("merge_synch", "out", "sink", "in")
        ]
    )
    network.compile_and_run()
    assert results == ['HELLO world', 'GOOD morning', 'HOW are you?']
    print(f"Results: {results}")


# ---------------------------
# MergeAsynch tests
# ---------------------------
def test_merge_asynch_no_func():
    """

    """
    results = set()
    network = Network(
        blocks={
            "source_a": FromListDelay(items=["HELLO", "GOOD", "HOW"], delay=0.15),
            "source_b": FromListDelay(items=[" world", " morning", " are you?"], delay=0.09),
            "merge_asynch": MergeAsynch(inports=["a", "b"], func=None),
            "sink": ToSet(results)
        },
        connections=[
            ("source_a", "out", "merge_asynch", "a"),
            ("source_b", "out", "merge_asynch", "b"),
            ("merge_asynch", "out", "sink", "in")
        ]
    )
    network.compile_and_run()
    assert results == {'HELLO', 'GOOD', 'HOW',
                       ' world', ' morning', ' are you?'}


# ---------------------------
# MergeAsynch tests
# ---------------------------


def test_merge_asynch_with_func():
    """

    """
    def f(msg, port):
        if port == "a":
            return msg + " " + msg
        else:
            return msg + "!!!"

    results = set()
    network = Network(
        blocks={
            "source_a": FromListDelay(items=["HELLO", "GOOD", "HOW"], delay=0.15),
            "source_b": FromListDelay(items=[" world", " morning", " are you?"], delay=0.09),
            "merge_asynch": MergeAsynch(inports=["a", "b"], func=f),
            "sink": ToSet(results)
        },
        connections=[
            ("source_a", "out", "merge_asynch", "a"),
            ("source_b", "out", "merge_asynch", "b"),
            ("merge_asynch", "out", "sink", "in")
        ]
    )
    network.compile_and_run()
    assert results == {'HELLO HELLO', 'GOOD GOOD', 'HOW HOW',
                       ' world!!!', ' morning!!!', ' are you?!!!'}


if __name__ == "__main__":
    test_merge_synch_basic_with_transformer()
    test_merge_asynch_no_func()
    test_merge_asynch_with_func()
    print("All tests passed.")
