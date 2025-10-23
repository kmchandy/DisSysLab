#modules.ch04_numeric.README_3_TFIDF.md

# 📚 4.3 Bag-of-Words (TF-IDF), KMeans & PCA

## Goal
Stream a small set of movie reviews through a graph of functions to cluster them, showing a snapshot after 5 and a final view after 10. The emphasis is on the nodes in the network and how they compose, not on the specific ML techniques.

## What you’ll build
A dsl graph that processes one review at a time:

```
from_reviews  →  tfidfify  →  predict_cluster  →  to_results
                          ↘
                           print_vec   (optional per-item log)
```

***TF-IDF*** converts text to numeric features (sparse counts reweighted by inverse document frequency).

***KMeans*** refits on vectors seen so far and predicts the current review’s cluster.

***PCA*** is used only after the run to reduce features to 2D for plotting snapshots.

## Message shape (per review)
Each node passes a small dict downstream:
```
{
  "text_of_review": str,
  "tfidf": np.ndarray  # shape (1, V) after tfidfify
  "cluster": int | None
}
```


- cluster=None means unassigned (too few points to fit KMeans yet).

## Nodes (callables)

### Source

```
from_reviews()
Yields one review at a time as {"text_of_review": ...}.
```

### Transform 1
```
tfidfify(msg)
```
Applies a TfidfVectorizer (fitted once on the full corpus upfront) and adds msg["tfidf"] (shape (1, V)).

### Transform 2
```
predict_cluster(msg)
```

- Maintains tfidf_so_far (all vectors up to now).
- Refits KMeans(k=2) on tfidf_so_far and predicts a label for the current msg["tfidf"].
- If fewer than k samples seen, sets msg["cluster"] = None.

### Sink: Log

print_vec(msg)
Prints a compact signature (e.g., number of non-zero TF-IDF features and current cluster). No plotting here.

### Sink saves results

to_results(msg)
Appends the processed message to a list for post-run snapshots.

## Snapshots: after network terminates execution
After g.run_network() finishes:

-Fit PCA(2D) once on all TF-IDF vectors (for visualization only).

=Save two plots:

- 1. part2_first5.svg — first 5 reviews only

- 2. part2_all10.svg — all 10 reviews


Rendering details:

- unassigned points (pre-KMeans) → gray “×”

- cluster 0 → ● circles

- cluster 1 → ■ squares

We plot after the run with a non-GUI backend to avoid problems with multithread plotting.

## Run the demo
```
python -m dsl.examples.ch05_ds.part2_tfidf_pca_kmeans
```

You’ll see a short log per review, and two files will be written:

- ```part2_first5.svg```

- ```part2_all10.svg```

## Takeaway

Use standard libraries (scikit-learn for TF-IDF, KMeans, PCA) as nodes.

## Tweakable parameters

- TfidfVectorizer: ngram_range, stop_words, min_df

- KMeans: n_clusters, random_state, n_init

- Reviews: replace with your own list; the network stays the same.


## 👉 Next
[Signal Processing Filters](./README_4_filter.md)