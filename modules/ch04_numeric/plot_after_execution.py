# modules.ch05_ds.plot_after_execution.py

import matplotlib.pyplot as plt
import random


def _scatter_by_cluster(subset_results, title, out_path):
    xs0, ys0 = [], []   # cluster 0
    xs1, ys1 = [], []   # cluster 1
    xsn, ysn = [], []   # None/unassigned

    for r in subset_results:
        g, b = r["vector"][0]
        g += (random.random() - 0.5) * 0.2  # jitter for visibility
        b += (random.random() - 0.5) * 0.2  # jitter to prevent overlap
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


def print_results_snapshots(results):
    _scatter_by_cluster(
        results, "KMeans on All Reviews ([good,bad])", "part1_all.svg")
    print("See diagram of clusters: part1_all.svg")
