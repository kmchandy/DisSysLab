# lessons.02_msg_as_dict.example_with_time.py
from dsl.kit import Network, FromListWithKeyWithTime, AddSentiment, ToConsole


reviews = [
    "The movie was great. The music was superb!",
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]


def example_with_time():

    network = Network(
        blocks={
            "source": FromListWithKeyWithTime(items=reviews, key="review"),
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
    example_with_time()
