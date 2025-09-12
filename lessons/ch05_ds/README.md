# 🧩 Chapter 5 — Transformers for Data Science

### 🎯 Goal
Learn how to build **data science blocks** (like CountVectorizer, TF-IDF, KMeans, and PCA) in exactly the same way that you build GPT blocks or other types of blocks.

---

### 📦 Requirements

Before running these examples, make sure your Python virtual environment has the right packages installed:

```bash
# Activate your venv first
source venv/bin/activate   # Mac/Linux
.\venv\Scripts\activate    # Windows PowerShell

# Then install dependencies
pip install scikit-learn matplotlib
```

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

import sklearn.feature_extraction.text as text      # text vectorizers live here
import sklearn.cluster as cluster                   # clustering algorithms live here
import matplotlib.pyplot as plt                     # plotting library

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import WrapFunction
from dsl.block_lib.stream_recorders import RecordToList

# --- Sample movie reviews ---
reviews = [
    "The movie was good and enjoyable",
    "Really bad acting and poor script",
    "Good fun with friends",
    "Terrible and bad experience",
    "An excellent and good film"
]

# Store outputs (each element will be a dict with vector + cluster)
results = []

# --- Define transformers ---
# Count how many times words "good" and "bad" appear
vectorizer = text.CountVectorizer(vocabulary=["good", "bad"])

# Group reviews into 2 clusters
kmeans = cluster.KMeans(n_clusters=2, random_state=42)

def vectorize(single_review: str):
    """Turn one review into a count vector [count_good, count_bad]."""
    return vectorizer.transform([single_review]).toarray()

def cluster_one(vector):
    """Cluster one vector into group 0 or 1."""
    return kmeans.fit_predict(vector)

# --- Build network ---
net = Network(
    blocks={
        "generator": GenerateFromList(items=reviews, key="text"),
        "vectorizer": WrapFunction(
            func=lambda x: vectorize(x),
            input_key="text",
            output_key="vector"
        ),
        "cluster": WrapFunction(
            func=lambda v: int(cluster_one(v)[0]),
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

# --- Visualization ---
# Each result dict has {"vector": [good_count, bad_count], "cluster": c}
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

⚠️ **Tip for running plots**  
When `plt.show()` runs, a plot window will open.  
The Python program pauses until you **close the window**.  
- On most systems, click the ❌ close button.  
- If you’re running in some terminals, you may need to press **Ctrl-C** to break out.  


## ✅ Key Takeaways
- The two core ideas -- (1) blocks execute functions that process messages and (2) connections specify the flow of messages between blocks -- can be used for data science applications in exactly the same way as they are used for GPT and other applications.

- Vectorizers (Count, TF-IDF) turn text into numeric vectors; KMeans groups messages into clusters; PCA lets us see high-dimensional vectors in 2D plots. More about this in related chapters

## ⏭️ Coming Up
✨ What if you wanted a distributed application that connected to external objects such as your calendar, email, shopping apps, or GitHub? The next chapter describe blocks that connect to external applications.

👉 **Next up: [Chapter 6 — Connectors](../ch06_git/README.md)**