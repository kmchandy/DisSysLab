# dsl/examples/ch02_keys/message_network.py
from dsl.kit import Network, FromListWithKey, AddSentiment, ToConsole


reviews = [
    "The movie was great. The music was superb!",
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]


def test_transform_simple_sentiment():

    network = Network(
        blocks={
            "source": FromListWithKey(items=reviews, key="review"),
            "add_sentiment": AddSentiment(input_key="review", add_key="sentiment"),
            "sink": ToConsole()
        },
        connections=[
            ("source", "out", "add_sentiment", "in"),
            ("add_sentiment", "out", "sink", "in")
        ]
    )
    network.compile_and_run()


if __name__ == "__main__":
    test_transform_simple_sentiment()
