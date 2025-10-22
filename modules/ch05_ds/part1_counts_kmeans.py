# dsl/examples/ch05_ds/part1_counts_kmeans.py

import time
from dsl import network
import sklearn.cluster as cluster
import sklearn.feature_extraction.text as text
import matplotlib.pyplot as plt
import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless; avoid GUI/thread warnings

# --- Sample movie reviews ---
reviews = [
    "good fun with friends and a good ending",                 # good=2, bad=0
    "bad movie, bad soundtrack, bad acting, bad theater, good date!",   # good=1, bad=4
    "really bad, bad acting and a poor script",                # good=0, bad=2
    "good soundtrack and good jokes but some bad scenes",      # good=2, bad=1
    "bad pacing but a good finale",                            # good=1, bad=1
    "all-around good experience, good vibes, not bad",         # good=2, bad=1
    "bad story, bad acting, bad music, bad cinematography.",   # good=0, bad=4
    "good plot, good characters, good direction",              # good=3, bad=0
    "bad movie, bad acting, bad politics, good soundtrack, good scenery",  # good=1, bad=3
    "good cinematography, beautiful landscapes, good music, bad acting",  # good=2, bad=1
]

# --- Source ---


def from_reviews():
    for review in reviews:
        yield {"text_of_review": review}
        time.sleep(0.1)  # simulate delay


# --- Results store ---
results = []  # each: {"text_of_review", "vector", "cluster"}


def to_results(msg):
    results.append(msg)
    return msg


# --- Transformers ---
vectorizer = text.CountVectorizer(vocabulary=["good", "bad"])


def vectorize(msg):
    vec = vectorizer.transform(
        [msg["text_of_review"]]).toarray()  # shape (1,2)
    msg["vector"] = vec
    return msg


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

# --- (Optional) compact per-item logger without plotting ---


def print_vector(msg):
    g, b = msg["vector"][0]
    print(f"review → good={g:d}, bad={b:d}, cluster={msg.get('cluster')}")
    return msg


# --- Build and run the streaming graph ---
g = network([
    (from_reviews, vectorize),
    (vectorize, print_vector),      # optional
    (vectorize, predict_cluster),
    (predict_cluster, to_results),
])
g.run_network()

# --- Post-run snapshots (main thread; no GUI) ---


def _scatter_by_cluster(subset_results, title, out_path):
    xs0, ys0 = [], []   # cluster 0
    xs1, ys1 = [], []   # cluster 1
    xsn, ysn = [], []   # None/unassigned

    for r in subset_results:
        g, b = r["vector"][0]
        c = r["cluster"]
        if c is None:
            xsn.append(g)
            ysn.append(b)
        elif c == 0:
            xs0.append(g)
            ys0.append(b)
        elif c == 1:
            xs1.append(g)
            ys1.append(b)
        else:
            xsn.append(g)
            ysn.append(b)

    plt.figure(figsize=(5.2, 4.2))
    if xsn:
        plt.scatter(xsn, ysn, marker='x', s=90, c='gray', label='unassigned')
    if xs0:
        plt.scatter(xs0, ys0, marker='o', s=90, label='cluster 0')
    if xs1:
        plt.scatter(xs1, ys1, marker='s', s=90, label='cluster 1')
    plt.xlabel("count('good')")
    plt.ylabel("count('bad')")
    plt.title(title)
    plt.legend(loc='best', frameon=False)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


# Snapshot after first 5 reviews
first5 = results[:5]
print("\n--- Snapshot after 5 reviews ---")
print("clusters(first 5):", [r["cluster"] for r in first5])
_scatter_by_cluster(
    first5, "KMeans on First 5 Reviews ([good,bad])", "part1_first5.svg")
print("Saved: part1_first5.svg")

# Snapshot after all 10 reviews
print("\n=== Final summary ===")
print("clusters(all):", [r["cluster"] for r in results])
_scatter_by_cluster(
    results, "KMeans on All 10 Reviews ([good,bad])", "part1_all10.svg")
print("Saved: part1_all10.svg")
