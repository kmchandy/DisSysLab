# dsl.examples.simple_sentiment_analysis

from dsl import Graph
from dsl.ops.transforms.simple_sentiment import sentiment_score

# -----------------------------------------------------------
# Define Python functions independent of dsl.
# -----------------------------------------------------------


def stream_reviews():
    for x in reviews:
        yield {"review": x}


def add_sentiment(v):
    score = sentiment_score(v["review"])
    v["sentiment"] = score
    return v


def to_results(v):
    results.append(v)


reviews = [
    "The movie was great. The music was superb!",
    "The concert was terrible. I hated the performance.",
    "The book was okay, not too bad but not great either.",
    "This is the best course on AI I've ever taken!",
]

# -----------------------------------------------------------
# Define the graph
# -----------------------------------------------------------
results = []

g = Graph(
    edges=[("src", "trn"), ("trn", "snk")],
    nodes=[("src", stream_reviews), ("trn", add_sentiment), ("snk", to_results)]
)
# -----------------------------------------------------------

g.compile_and_run()
if __name__ == "__main__":
    for result in results:
        print(result)
