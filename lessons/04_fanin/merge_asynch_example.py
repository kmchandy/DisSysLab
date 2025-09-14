# lessons.04_fanin.merge_asynch_example

from dsl.kit import Network, FromListDelay, ToSet, MergeAsynch


def merge_asynch_example():
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
    merge_asynch_example()
