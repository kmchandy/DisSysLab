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
    print(f"Results: {results}")


# ---------------------------
# MergeAsynch tests
# ---------------------------
def test_merge_asynch():
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
    print(f"Results: {results}")


# # ---------------------------
# # MergeAsynch tests
# # ---------------------------
# def test_merge_asynch_v2():
#     """

#     """
#     def g(msg, port):
#         if port == "a":
#             return msg*2
#         else:
#             return msg + "!!"

#     results = []
#     network = Network(
#         blocks={
#             "source_a": Source(generator_fn=gen_list_with_delay(["x1", "x2", "__STOP__"], delay=0.15)),
#             "source_b": Source(generator_fn=gen_list_with_delay(["y1", "y2"], delay=0.09)),
#             "merge_asynch": MergeAsynch(inports=["a", "b"],
#                                         func=g),
#             "sink": Sink(record_fn=record_to_list(results))
#         },
#         connections=[
#             ("source_a", "out", "merge_asynch", "a"),
#             ("source_b", "out", "merge_asynch", "b"),
#             ("merge_asynch", "out", "sink", "in")
#         ]
#     )
#     network.compile_and_run()
#     assert results == ['x1x1', 'y1!!', 'y2!!', 'x2x2']


# ---------------------------
# Plain-Python runner
# ---------------------------


if __name__ == "__main__":
    test_merge_synch_basic_with_transformer()
    test_merge_asynch()
    # test_merge_asynch_v2()
    print("All tests passed.")
