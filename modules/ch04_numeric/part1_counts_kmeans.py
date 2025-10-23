# dsl/examples/ch05_ds/part1_counts_kmeans.py

from .plot_after_execution import print_results_snapshots
from .good_bad_reviews import reviews  # list of 10 text reviews
import time
from dsl import network
import sklearn.cluster as cluster
import sklearn.feature_extraction.text as text
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless; avoid GUI/thread warnings

# -----------------------------------------------------
#                     Source                         |
# -----------------------------------------------------


def from_reviews():
    for review in reviews:
        yield {"text_of_review": review}
        time.sleep(0.25)  # simulate delay


# -----------------------------------------------------
#         Transform: Vectorize Text                  |
# -----------------------------------------------------
vectorizer = text.CountVectorizer(vocabulary=["good", "bad"])


def vectorize(msg):
    vec = vectorizer.transform(
        [msg["text_of_review"]]).toarray()  # shape (1,2)
    msg["vector"] = vec
    return msg


# -----------------------------------------------------
#        Transform: Cluster Vectors                  |
# -----------------------------------------------------
kmeans = cluster.KMeans(n_clusters=2, random_state=42, n_init=10)
vectors_so_far = []


def predict_cluster(msg):
    v = msg["vector"]              # shape (1,2)
    vectors_so_far.append(v)
    X = np.vstack(vectors_so_far)  # shape (t, 2)

    if X.shape[0] < kmeans.n_clusters:
        msg["cluster"] = None
        return msg

    kmeans.fit(X)
    msg["cluster"] = int(kmeans.predict(v)[0])
    return msg


# -----------------------------------------------------
#                       Sink                         |
# -----------------------------------------------------
results = []  # each: {"text_of_review", "vector", "cluster"}


def to_results(msg):
    results.append(msg)


# -----------------------------------------------------
#               Sink: Print Vector                   |
# -----------------------------------------------------


def print_vector(msg):
    g, b = msg["vector"][0]
    print(f"review → good={g:d}, bad={b:d}, cluster={msg.get('cluster')}")


# -----------------------------------------------------
#          Build and run the graph                   |
# -----------------------------------------------------
g = network([
    (from_reviews, vectorize),
    (vectorize, predict_cluster),
    (predict_cluster, to_results),
    (predict_cluster, print_vector),
])
g.run_network()

# --- Post-run snapshots (main thread; no GUI) ---
print_results_snapshots(results)
# Open part1_first5.svg to see clustering after first 5 reviews
# Open part1_all10.svg to see clustering after all reviews.

# To check results
for result in results:
    for key, value in result.items():
        print(f"{key}: {value}")
        print("---")
