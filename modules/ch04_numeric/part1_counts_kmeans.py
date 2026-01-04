# dsl/examples/ch05_ds/part1_counts_kmeans.py

from .plot_after_execution import print_results_snapshots
from .good_bad_reviews import reviews  # list of 10 text reviews
import time
from dsl import network
from dsl.natural_language_lib.count_words_vectorizer import CountWordsVectorizer
from dsl.math_lib.kmeans_cluster_vectors import KMeansClusterVectors
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
vectorizer = CountWordsVectorizer(
    vocabulary=["good", "bad"],
    input_field="text_of_review",
    output_field="vector"
)


# -----------------------------------------------------
#        Transform: Cluster Vectors                  |
# -----------------------------------------------------
# kmeans = cluster.KMeans(n_clusters=2)
# vectors_so_far = []


# def predict_cluster(msg):
#     v = msg["vector"]              # shape (1,2)
#     vectors_so_far.append(v)
#     X = np.vstack(vectors_so_far)  # shape (t, 2)

#     if X.shape[0] < kmeans.n_clusters:
#         msg["cluster"] = None
#         return msg

#     kmeans.fit(X)
#     msg["cluster"] = int(kmeans.predict(v)[0])
#     return msg
predict_cluster = KMeansClusterVectors(
    n_clusters=2,
    input_field="vector",
    output_field_inc="cluster_incremental",
    output_field_all="cluster_all",
    name="KMeansClusterVectors",
)

# -----------------------------------------------------
#                       Sink                         |
# -----------------------------------------------------
results_incremental = []  # each: {"text_of_review", "vector", "cluster"}
results_all = []  # each: {"text_of_review", "vector", "cluster"}


def to_results_incremental(msg):
    results_incremental.append(msg)


def to_results_all(msg):
    results_all.append(msg)


# -----------------------------------------------------
#               Sink: Print Vector                   |
# -----------------------------------------------------


def print_vector(msg):
    g, b = msg["vector"][0]
    print(
        f"review → good={g:d}, bad={b:d}, cluster_incremental={msg.get('cluster_incremental')}")
    print(f"    cluster_all={msg.get('cluster_all')}")


# -----------------------------------------------------
#          Build and run the graph                   |
# -----------------------------------------------------
g = network([
    (from_reviews, vectorizer.run),
    (vectorizer.run, predict_cluster.run),
    (predict_cluster.run, to_results_incremental),
    (predict_cluster.run, to_results_all),
    (predict_cluster.run, print_vector),
])
g.run_network()

# --- Post-run snapshots (main thread; no GUI) ---
print_results_snapshots(results_incremental,
                        diagram_title="part1_incremental.svg")
# Open part1_all.svg to see clustering after all reviews.
print(f"Labels {predict_cluster.labels}")
print_results_snapshots(predict_cluster.vectors_so_far,
                        diagram_title="part1_all.svg")
