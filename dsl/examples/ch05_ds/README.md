# 🧩 Chapter 5 — Transformers for Data Science

### 🎯 Goal
Learn how to use **data science transformers** (like CountVectorizer, TF-IDF, KMeans, and PCA) in networks — just like GPT transformers.

---

## 📍 What We’ll Build

We’ll explore **two parts**:

1. **Part 1 — Simple Word Counts + KMeans**  
   Use a generator of short movie reviews → count words → cluster into groups.

2. **Part 2 — TF-IDF + PCA + KMeans**  
   Scale up with TF-IDF and dimensionality reduction for richer clusters and visualizations.

**Visual:**  
`[ Generator ] → [ Vectorizer ] → [ Clusterer ] → [ Plot Recorder ]`

---

## 💻 Part 1 — Simple Word Counts + KMeans

We’ll use `CountVectorizer` to turn reviews into counts of words like `"good"` and `"bad"`, and then cluster into 2 groups using KMeans.  

**Code:**  
```python
# dsl/examples/ch05_ds/part1_counts_kmeans.py

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import WrapFunction
from dsl.block_lib.stream_recorders import RecordToList

# Sample reviews
reviews = [
    "The movie was good and enjoyable",
    "Really bad acting and poor script",
    "Good fun with friends",
    "Terrible and bad experience",
    "An excellent and good film"
]

# Store vectorized outputs and clusters
results = []

# Define transformation blocks
vectorizer = CountVectorizer(vocabulary=["good", "bad"])
kmeans = KMeans(n_clusters=2, random_state=42)

def vectorize(texts):
    return vectorizer.transform(texts).toarray()

def cluster(vectors):
    return kmeans.fit_predict(vectors)

net = Network(
    blocks={
        "generator": GenerateFromList(items=reviews, key="text"),
        "vectorizer": WrapFunction(func=lambda x: vectorize([x]), input_key="text", output_key="vector"),
        "cluster": WrapFunction(func=lambda v: int(cluster(v)[0]), input_key="vector", output_key="cluster"),
        "recorder": RecordToList(results),
    },
    connections=[
        ("generator", "out", "vectorizer", "in"),
        ("vectorizer", "out", "cluster", "in"),
        ("cluster", "out", "recorder", "in"),
    ]
)

net.compile_and_run()
print(results)

# Plot counts
vectors = [r["vector"][0] for r in results]
clusters = [r["cluster"] for r in results]
xs = [v[0] for v in vectors]  # count of "good"
ys = [v[1] for v in vectors]  # count of "bad"

plt.scatter(xs, ys, c=clusters, cmap="coolwarm", s=80)
plt.xlabel("count('good')")
plt.ylabel("count('bad')")
plt.title("Clusters of Reviews (CountVectorizer + KMeans)")
plt.savefig("part1_plot.svg")
plt.show()
```

***What you’ll see:***
📊 A scatter plot where x = count('good'), y = count('bad'), colored by cluster.

## 💻 Part 2 — Real Bag-of-Words (TF-IDF + PCA + KMeans)

We scale up to TF-IDF (lots of words), cluster with KMeans, and then project to 2D with PCA so we can see it.

**Code:**
```
# dsl/examples/ch05_ds/part2_tfidf_pca_kmeans.py

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import WrapFunction
from dsl.block_lib.stream_recorders import RecordToList

# Reviews (same as Part 1)
reviews = [
    "The movie was good and enjoyable",
    "Really bad acting and poor script",
    "Good fun with friends",
    "Terrible and bad experience",
    "An excellent and good film"
]

results = []

# Define transformers
vectorizer = TfidfVectorizer()
kmeans = KMeans(n_clusters=2, random_state=42)
pca = PCA(n_components=2)

def vectorize(texts):
    return vectorizer.fit_transform(texts).toarray()

def cluster(vectors):
    return kmeans.fit_predict(vectors)

def reduce(vectors):
    return pca.fit_transform(vectors)

net = Network(
    blocks={
        "generator": GenerateFromList(items=reviews, key="text"),
        "vectorizer": WrapFunction(func=lambda _: vectorizer.fit_transform(reviews).toarray(), input_key="text", output_key="vectors"),
        "cluster": WrapFunction(func=lambda v: int(cluster([v])[0]), input_key="vectors", output_key="cluster"),
        "recorder": RecordToList(results),
    },
    connections=[
        ("generator", "out", "vectorizer", "in"),
        ("vectorizer", "out", "cluster", "in"),
        ("cluster", "out", "recorder", "in"),
    ]
)

net.compile_and_run()
print(results)

# Now do PCA on the full set
X = vectorizer.fit_transform(reviews).toarray()
X2d = pca.fit_transform(X)
clusters = kmeans.fit_predict(X)

plt.scatter(X2d[:, 0], X2d[:, 1], c=clusters, cmap="coolwarm", s=80)
plt.xlabel("PCA 1")
plt.ylabel("PCA 2")
plt.title("Clusters of Reviews (TF-IDF + PCA + KMeans)")
plt.savefig("part2_plot.svg")
plt.show()
```

***What you’ll see:***
📊 A scatter plot in 2D (PCA projection), with points colored by cluster.

## ✅ Key Takeaways
- Transformers can use any Python/ML function.

- Vectorizers (Count, TF-IDF) turn text into numeric vectors; KMeans groups messages into clusters; PCA lets us see high-dimensional vectors in 2D plots. More about this in related chapters

## ⏭️ Coming Up
✨ In the next chapter, you will learn how distributed applications can be used in collaboration. Specifically we will show blocks can push to and pull from GitHub.