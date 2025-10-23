# modules.ch05_ds.plot_after_PCA.py

import matplotlib.pyplot as plt
import numpy as np
from sklearn.decomposition import PCA


def _scatter_pca(subset_results, pca_model, title, out_path):
    """
    Project subset TF-IDF vectors into 2D using the provided PCA model (fit on all).
    Render unassigned as gray '×'; cluster 0 as circles; cluster 1 as squares.
    """
    # Stack TF-IDF for this subset
    X_sub = np.vstack([r["tfidf"] for r in subset_results])  # (n, V)
    Z = pca_model.transform(X_sub)                           # (n, 2)

    xs0, ys0 = [], []   # cluster 0
    xs1, ys1 = [], []   # cluster 1
    xsn, ysn = [], []   # None/unassigned

    for (r, (x2, y2)) in zip(subset_results, Z):
        c = r["cluster"]
        if c is None:
            xsn.append(x2)
            ysn.append(y2)
        elif c == 0:
            xs0.append(x2)
            ys0.append(y2)
        elif c == 1:
            xs1.append(x2)
            ys1.append(y2)
        else:
            xsn.append(x2)
            ysn.append(y2)

    plt.figure(figsize=(5.6, 4.6))
    if xsn:
        plt.scatter(xsn, ysn, marker='x', s=90, c='gray', label='unassigned')
    if xs0:
        plt.scatter(xs0, ys0, marker='o', s=90, label='cluster 0')
    if xs1:
        plt.scatter(xs1, ys1, marker='s', s=90, label='cluster 1')
    plt.title(title)
    plt.xlabel("PCA 1")
    plt.ylabel("PCA 2")
    plt.legend(loc='best', frameon=False)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def print_results_snapshots(results):
    # Fit PCA on the full TF-IDF matrix (all reviews)
    X_all = np.vstack([r["tfidf"] for r in results])   # (10, V)
    pca = PCA(n_components=2, random_state=42).fit(X_all)

    # First 5 snapshot
    first5 = results[:5]
    print("\n--- Part 2 Snapshot after 5 reviews ---")
    print("clusters(first 5):", [r["cluster"] for r in first5])
    _scatter_pca(first5, pca, "TF-IDF + PCA + KMeans (first 5)",
                 "part2_first5.svg")
    print("Saved: part2_first5.svg")

    # All 10 snapshot
    print("\n=== Part 2 Final summary ===")
    print("clusters(all):", [r["cluster"] for r in results])
    _scatter_pca(results, pca, "TF-IDF + PCA + KMeans (all 10)",
                 "part2_all10.svg")
    print("Saved: part2_all10.svg")
