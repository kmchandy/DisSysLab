# lessons.04_fanin.merge_synch_example

from dsl.kit import Network, FromListDelay, ToList, MergeSynch


def merge_synch_example():
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


if __name__ == "__main__":
    merge_synch_example()
