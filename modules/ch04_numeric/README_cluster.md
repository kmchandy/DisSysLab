#modules.ch04_numeric.README_cluster.md

# 📚 4.3 Simple Clustering
This module has examples in which agents execute programs in Python's numeric libraries. The examples show that building multiple-agent systems is straightforward. These examples do not describe the Python libraries.

This page and the next describe the same problem; the next page uses more sophisticated algorithms. The example has an agent that outputs a stream of movie reviews. The example uses a stored list of fake reviews. You can replace it by an agent that streams reviews from websites. 
The stream of reviews is analyzed by an agent which makes a vector from the text of each review when the agent receives the review.
A third agent receives streams of these vectors and classifies these vectors into categories. As more vector representations of reviews arrive, new reviews are evaluated and the classification of old reviews may change. 

In this example, reviews are re-clustered after the agent receives each new review. You can modify the code so that re-clustering takes place only after N reviews are received where N is a suitably large number.

These extremely simplistic examples illustrate how multiple agents concurrently input and output streams of messages.

***Network of agents structure***
```
from_reviews  →  vectorize  →  predict_cluster  →  to_results
                                               ↘
                                                print_vec
```


```python
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
#  Transform: Vectorize Text using CountVectorizer    |
#    from library                                     |         
# -----------------------------------------------------
vectorizer = text.CountVectorizer(vocabulary=["good", "bad"])


def vectorize(msg):
    vec = vectorizer.transform(
        [msg["text_of_review"]]).toarray()  # shape (1,2)
    msg["vector"] = vec
    return msg


# ------------------------------------------------------
# Transform: Cluster Vectors using KMeans from Library |
# ------------------------------------------------------
kmeans = cluster.KMeans(n_clusters=2)
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
# Open part1_all.svg to see clustering after all reviews.

```


## Run the demo
```
python -m modules.ch04_numeric.part1_counts_kmeans
```



## 👉 Next
[Clustering with TFIDF and PCA](./README_3_TFIDF.md)