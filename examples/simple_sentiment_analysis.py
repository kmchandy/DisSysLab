# dsl.examples.simple_sentiment_analysis

from dsl import network
from dsl.ops.transforms.simple_sentiment import sentiment_score

# Define functions.


def stream_reviews():
    for x in reviews:
        yield {"review": x}


def add_sentiment(v):
    score = sentiment_score(v["review"])
    v["sentiment"] = score
    return v


results = []


def to_results(v):
    results.append(v)


reviews = [
    "The movie was great. The music was superb!",
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]

# Define the graph


g = network([(stream_reviews, add_sentiment), (add_sentiment, to_results)])

g.run_network()
if __name__ == "__main__":
    for result in results:
        print(result)
