# 🧩 Chapter 5 — Homework: TF‑IDF + PCA + KMeans

## 🎯 Learning Objectives

- Build an application. 
- Use **TF‑IDF** instead of simple counts to represent text numerically.
- Apply **PCA** to reduce dimensionality for visualization and clustering.
- Compare results against the **CountVectorizer + KMeans** pipeline from Part 1.

---

## 📋 Assignment (Short)

**HW 5.1 — Replace Count with TF‑IDF**\
Use `TfidfVectorizer` (scikit‑learn) to transform the same list of short movie reviews you used in Part 1. Use blocks with `TransformerFunction`.

**HW 5.2 — Add PCA (2 components)**\
Fit `PCA(n_components=2)` on the **full corpus** (all reviews) and transform each review to 2D.

**HW 5.3 — Cluster & Visualize**\
Run `KMeans(n_clusters=2, random_state=42)` on the **2D PCA points** and make a 2D scatter plot colored by cluster labels. Save the figure (e.g., `hw5_plot.svg`).

**HW 5.4 — Reflection (3–5 sentences)**\
Briefly compare TF‑IDF + PCA + KMeans vs. CountVectorizer + KMeans from Part 1:

- Do the clusters look different?
- Which representation seems more informative on these reviews, and why?

> **Important:** For TF‑IDF and PCA you must **fit on the full dataset once** (outside the per‑message transform), then use those fitted models inside your `TransformerFunction` blocks. This mirrors best practices and avoids refitting for every message.

---

## ✅ What to Submit

- **Code file**: `dsl/examples/ch05_ds/hw_tfidf_pca_kmeans.py`
- **Plot**: `hw5_plot.svg` (or `.png`)
- **Short reflection**: `hw5_reflection.md` (3–5 sentences)

---

## 🧰 Hints

- Install requirements in your venv:
  ```bash
  pip install scikit-learn matplotlib
  ```
- Idiomatic imports for this homework:
  ```python
  from sklearn.feature_extraction.text import TfidfVectorizer
  from sklearn.decomposition import PCA
  from sklearn.cluster import KMeans
  import matplotlib.pyplot as plt
  ```
- Keep using your **Part 1 review list** (with varied counts of "good"/"bad" etc.).
- Use `TransformerFunction` throughout, consistent with Chapter 5.

---

## 🧪 Reference Solution (Python Script)

> Save as: `dsl/examples/ch05_ds/hw_tfidf_pca_kmeans_solution.py`

```python
"""
Chapter 5 Homework Solution — TF-IDF + PCA + KMeans
Path: dsl/examples/ch05_ds/hw_tfidf_pca_kmeans_solution.py

This solution:
- Fits TF-IDF and PCA on the full corpus ONCE (good practice)
- Uses TransformerFunction blocks for per-item transform steps
- Clusters in 2D PCA space and plots the result
Requirements: scikit-learn, matplotlib
"""

from typing import List

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_recorders import RecordToList

# --- Sample movie reviews (corrected counts and variety) ---
reviews: List[str] = [
    "good fun with friends and a good ending",              # many 'good'
    "bad movie, bad soundtrack, bad acting, but good date!",# mix
    "really bad, bad acting and a poor script",             # more 'bad'
    "good soundtrack and good jokes but some bad scenes",   # mixed
    "bad pacing but a good finale",                         # balanced
    "all-around good experience, good vibes, not bad",      # mixed
    "bad story, bad acting, bad music, bad cinematography.",# heavy 'bad'
]

# --- Fit models ONCE on the full corpus ---
# TF-IDF is fitted on all reviews so that IDF weights reflect the corpus.
vectorizer = TfidfVectorizer()
X_all = vectorizer.fit_transform(reviews).toarray()   # shape (N, D)

# Reduce to 2D with PCA for visualization and clustering
pca = PCA(n_components=2, random_state=42)
X2d_all = pca.fit_transform(X_all)                    # shape (N, 2)

# Cluster in 2D to align with the visualization space
kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
kmeans.fit(X2d_all)

# Storage for per-item outputs
results = []

# --- Per-item transform functions (use fitted models) ---
def tfidf_single(text: str):
    """Transform one review using the fitted TF-IDF; returns shape (1, D)."""
    return vectorizer.transform([text]).toarray()

def pca_single(vec):
    """Project a single TF-IDF row vector to 2D using fitted PCA; shape (1, 2)."""
    return pca.transform(vec)

def cluster_single(vec2d):
    """Predict KMeans label (0 or 1) for a single 1x2 vector."""
    return int(kmeans.predict(vec2d)[0])

# --- Build DisSysLab network ---
net = Network(
    blocks={
        "gen": GenerateFromList(items=reviews, key="text"),
        "tfidf": TransformerFunction(
            func=tfidf_single, input_key="text", output_key="tfidf"
        ),
        "pca2d": TransformerFunction(
            func=pca_single, input_key="tfidf", output_key="pca2d"
        ),
        "cluster": TransformerFunction(
            func=cluster_single, input_key="pca2d", output_key="cluster"
        ),
        "rec": RecordToList(results),
    },
    connections=[
        ("gen", "out", "tfidf", "in"),
        ("tfidf", "out", "pca2d", "in"),
        ("pca2d", "out", "cluster", "in"),
        ("cluster", "out", "rec", "in"),
    ],
)

net.compile_and_run()

# Inspect a couple of results
print("Example result:", results[0])

# --- Build arrays for plotting from recorded results ---
# Each result row contains keys: tfidf (1xD), pca2d (1x2), cluster (int)
X2d_points = [r["pca2d"][0] for r in results]  # list of [x, y]
labels = [r["cluster"] for r in results]

xs = [p[0] for p in X2d_points]
ys = [p[1] for p in X2d_points]

plt.scatter(xs, ys, c=labels, s=80)
plt.xlabel("PCA 1")
plt.ylabel("PCA 2")
plt.title("TF-IDF → PCA (2D) → KMeans Clusters")
plt.savefig("hw5_plot.svg")
plt.show()  # Close the window to end the program
```

---

## ⚠️ Plotting Tip

`plt.show()` opens a window and **pauses** the program until you close it. If running in a terminal without a UI, prefer saving and closing:

```python
plt.savefig("hw5_plot.svg")
plt.close()
```

