# modules/ch04_numeric/part2_tfidf_pca_kmeans.py

import time
from .good_bad_reviews import reviews  # list of 10 text reviews
from .plot_after_PCA import print_results_snapshots
from dsl import network
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless backend for safe, post-run plotting


# ----------------------------------------------------------------------
# Source
# ----------------------------------------------------------------------


def from_reviews():
    """Yield one review at a time."""
    for review in reviews:
        yield {"text_of_review": review}
        time.sleep(0.25)  # simulate delay


# ----------------------------------------------------------------------
# Transformer 1: TF-IDF
# We fit the vectorizer ONCE on the full corpus so the feature space is fixed.
# Then we stream-transform each incoming review.
# ----------------------------------------------------------------------
# A light, reasonable config; adjust as desired.
vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    # unigrams + bigrams for slightly richer features
    ngram_range=(1, 2),
    min_df=1,
)

# Fit once on the full corpus
vectorizer.fit(reviews)


def tfidfify(msg):
    """Attach a 1xV TF-IDF vector for the incoming review."""
    X = vectorizer.transform([msg["text_of_review"]]).toarray()  # shape (1, V)
    msg["tfidf"] = X
    return msg


# ----------------------------------------------------------------------
# Transformer 2: KMeans (streaming predict; refit on all seen so far)
# ----------------------------------------------------------------------
kmeans = KMeans(n_clusters=2)
tfidf_so_far = []  # list of 1xV arrays


def predict_cluster(msg):
    """Refit KMeans on TF-IDF vectors seen so far, predict cluster for current item."""
    v = msg["tfidf"]              # shape (1, V)
    tfidf_so_far.append(v)
    X = np.vstack(tfidf_so_far)   # shape (t, V)

    if X.shape[0] < kmeans.n_clusters:
        msg["cluster"] = None
        return msg

    kmeans.fit(X)
    msg["cluster"] = int(kmeans.predict(v)[0])
    return msg


# ----------------------------------------------------------------------
#                         Sink: Store results
# ----------------------------------------------------------------------
# each: {"text_of_review", "tfidf": (1, V) array, "cluster": int|None}
results = []


def to_results(msg):
    results.append(msg)
    return msg


# ----------------------------------------------------------------------
#                       Sink per-item logger
# ----------------------------------------------------------------------


def print_vec(msg):
    # Show nnz, the number of nonzero features, and current cluster
    nnz = int(np.count_nonzero(msg["tfidf"]))
    print(f"review → nnz={nnz}, cluster={msg.get('cluster')}")


# ----------------------------------------------------------------------
# Build and run the streaming graph
# ----------------------------------------------------------------------
print("nnz = number of nonzero TF-IDF features per review")
g = network([
    (from_reviews, tfidfify),     # optional console log per item
    (tfidfify, predict_cluster),
    (predict_cluster, to_results),
    (predict_cluster, print_vec),
])
g.run_network()

# ----------------------------------------------------------------------
# Post-run visualization with PCA(2D)
# - Fit PCA on the full TF-IDF matrix (all reviews)
# - Plot a snapshot of the first 5 and then all 10
# ----------------------------------------------------------------------

print_results_snapshots(results)
