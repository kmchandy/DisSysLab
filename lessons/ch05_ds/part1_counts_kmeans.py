# dsl/examples/ch05_ds/part1_counts_kmeans.py

import sklearn.feature_extraction.text as text      # vectorizers live here
# clustering algorithms live here
import sklearn.cluster as cluster
import matplotlib.pyplot as plt                     # plotting

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
# or TransformerFunction in your codebase
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_recorders import RecordToList

# --- Sample movie reviews ---
reviews = [
    "good fun with friends and a good ending",            # good=2, bad=0
    "bad movie, bad soundtrack, bad acting, but good date!",  # good=1, bad=3
    "really bad, bad acting and a poor script",           # good=0, bad=2
    "good soundtrack and good jokes but some bad scenes",  # good=2, bad=1
    "bad pacing but a good finale",                       # good=1, bad=1
    "all-around good experience, good vibes, not bad",    # good=2, bad=1
    "bad story, bad acting, bad music, bad cinematography.",    # good=0, bad=4
]

results = []

# --- Define transformers ---
# Simpler for beginners: fixed vocabulary (no fitting step needed for vectorizer)
vectorizer = text.CountVectorizer(vocabulary=["good", "bad"])

# Fit KMeans ONCE on the full corpus for stable clusters
X_all = vectorizer.transform(reviews).toarray()  # shape (N, 2)
kmeans = cluster.KMeans(n_clusters=2, random_state=42, n_init=10)
kmeans.fit(X_all)


def vectorize(single_review: str):
    """Return a 1x2 count vector for [good, bad]."""
    return vectorizer.transform([single_review]).toarray()  # shape (1,2)


def predict_cluster(v):
    """Predict cluster (0 or 1) for a 1x2 vector v."""
    return int(kmeans.predict(v)[0])


# --- Build network ---
net = Network(
    blocks={
        "generator": GenerateFromList(items=reviews, key="text"),
        "vectorizer": TransformerFunction(
            func=vectorize,
            input_key="text",
            output_key="vector"
        ),
        "cluster": TransformerFunction(
            func=predict_cluster,
            input_key="vector",
            output_key="cluster"
        ),
        "recorder": RecordToList(results),
    },
    connections=[
        ("generator", "out", "vectorizer", "in"),
        ("vectorizer", "out", "cluster", "in"),
        ("cluster", "out", "recorder", "in"),
    ]
)

net.compile_and_run()
print("Results:", results)

# --- Visualization (simple 2D scatter) ---
vectors = [r["vector"][0] for r in results]  # each is length-2
clusters = [r["cluster"] for r in results]

print("Vectors:", vectors)
print("Clusters:", clusters)
# Prepare data for plotting
xs = [v[0] for v in vectors]  # count('good')
ys = [v[1] for v in vectors]  # count('bad')

plt.scatter(xs, ys, c=clusters, s=80)
plt.xlabel("count('good')")
plt.ylabel("count('bad')")
plt.title("Clusters of Reviews (CountVectorizer + KMeans)")
plt.savefig("part1_plot.svg")
plt.show()
