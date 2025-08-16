# 🤝 Chapter 6 — Collaboration via GitHub (Part 1 + Homework)

**Goal:** Show how a DisSysLab pipeline can **pull** small inputs from GitHub, run locally, and (as homework) **push** artifacts back. Keep the lecture minimal on tooling; emphasize the *collaboration concept*.

---

## 📦 Requirements

```bash
pip install python-dotenv requests
# (Homework adds: PyGithub OR use git CLI)
```

Create a `.env` in your project root (where your `get_credentials.py` loads from):

```env
# For reading raw files (public or private)
GITHUB_REPO=your-user/your-repo
GITHUB_BRANCH=main
GITHUB_TOKEN=ghp_xxx_optional_if_private
```

> If the repo is **public**, `GITHUB_TOKEN` is optional. If **private**, set a token with `repo` scope.

---

## 🗂 Folder Layout

```
dsl/
  examples/
    ch06_github/
      README.md                      # this file
      github_io_min.py               # tiny helper for GET (pull)
      part1_pull_and_run.py          # in-class demo: pull → run → save local
      hw_push_artifacts.py           # (starter) homework: push JSON/MD
      data/
        ch06_reviews.json            # small text dataset (JSON list of strings)
        ch06_vocab.json              # optional config (JSON list of words)
```

---

## 🔧 Minimal Helper — `github_io_min.py`

*Focus on the concept: one small function that reads text content from GitHub.*

```python
# dsl/examples/ch06_github/github_io_min.py
import os
import base64
import json
from typing import Optional
import requests

RAW_BASE = "https://raw.githubusercontent.com"

def gh_read_text(path: str) -> str:
    """Read a text file from GitHub at (repo, branch, path) using optional token.
    Works for public repos without a token; supports private via token.
    """
    repo = os.getenv("GITHUB_REPO")
    branch = os.getenv("GITHUB_BRANCH", "main")
    token = os.getenv("GITHUB_TOKEN")  # optional for private repos
    if not repo:
        raise ValueError("GITHUB_REPO not set (e.g., your-user/your-repo)")

    url = f"{RAW_BASE}/{repo}/{branch}/{path}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"GET {url} failed: {r.status_code} — {r.text[:200]}")
    return r.text

def gh_read_json(path: str):
    return json.loads(gh_read_text(path))
```

---

## 🎬 Part 1 (In-Class): Pull → Run → Save Local

This example pulls a tiny review dataset from GitHub, runs a simple DisSysLab pipeline (vectorize → cluster), and saves a local JSON result. It uses the Chapter 5 Part 1 style for continuity.

```python
# dsl/examples/ch06_github/part1_pull_and_run.py
import json
import sklearn.feature_extraction.text as text
import sklearn.cluster as cluster

from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import TransformerFunction
from dsl.block_lib.stream_recorders import RecordToList

from .github_io_min import gh_read_json

# --- Pull inputs from GitHub (data managed by your repo) ---
# Expect: data/ch06_reviews.json is a JSON list of short review strings
reviews = gh_read_json("dsl/examples/ch06_github/data/ch06_reviews.json")
# Optional: pull a fixed vocabulary so students can reason about features
try:
    vocab = gh_read_json("dsl/examples/ch06_github/data/ch06_vocab.json")
except Exception:
    vocab = ["good", "bad"]

# --- Build simple CountVectorizer + KMeans (fit once) ---
vec = text.CountVectorizer(vocabulary=vocab)
X_all = vec.fit_transform(reviews).toarray()  # fit on full corpus
km = cluster.KMeans(n_clusters=2, random_state=42, n_init=10)
km.fit(X_all)

results = []

def vectorize_one(review: str):
    return vec.transform([review]).toarray()  # shape (1, D)

def predict_one(x):
    return int(km.predict(x)[0])

net = Network(
    blocks={
        "gen": GenerateFromList(items=reviews, key="text"),
        "vec": TransformerFunction(func=vectorize_one, input_key="text", output_key="vector"),
        "clu": TransformerFunction(func=predict_one, input_key="vector", output_key="cluster"),
        "rec": RecordToList(results),
    },
    connections=[
        ("gen", "out", "vec", "in"),
        ("vec", "out", "clu", "in"),
        ("clu", "out", "rec", "in"),
    ],
)

net.compile_and_run()

# Save local artifact for later use (e.g., by homework script)
with open("part1_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("Saved part1_results.json with", len(results), "rows")
```

> **Teaching note:** This keeps GitHub usage to a single idea — *pull inputs at runtime*. No auth complexity if the repo is public. If private, add `GITHUB_TOKEN` in `.env`.

---

## 🧭 Homework (Extension): Push Artifacts Back to GitHub

**Task:** After running `part1_pull_and_run.py`, write a script that:

1. Computes a **summary JSON** (e.g., cluster counts), and
2. Creates a short **Markdown report**, and
3. **Pushes** both files into your repo under `reports/ch06/`.

Choose one of two push methods:

### Option A — PyGithub (clean Python API)

```bash
pip install PyGithub
```

Starter (`dsl/examples/ch06_github/hw_push_artifacts.py`):

```python
import os, json
from collections import Counter
from github import Github

# Load local results produced by Part 1
with open("part1_results.json", "r") as f:
    results = json.load(f)

# Build summary
clusters = [r["cluster"] for r in results]
summary = {"total": len(results), "by_cluster": dict(Counter(clusters))}
summary_json = json.dumps(summary, indent=2)
report_md = f"""# Chapter 6 — Run Summary\n\n- Total items: {summary['total']}\n- Cluster counts: {summary['by_cluster']}\n"""

# Push via GitHub API
repo_full = os.getenv("GITHUB_REPO")
branch = os.getenv("GITHUB_BRANCH", "main")
token = os.getenv("GITHUB_TOKEN")
if not token:
    raise ValueError("GITHUB_TOKEN required for pushing to private or protected repos")

gh = Github(token)
repo = gh.get_repo(repo_full)

paths = {
    "reports/ch06/summary.json": summary_json,
    "reports/ch06/README.md": report_md,
}

for path, content in paths.items():
    try:
        file = repo.get_contents(path, ref=branch)
        repo.update_file(path, f"ch06: update {os.path.basename(path)}", content, file.sha, branch=branch)
        print("Updated", path)
    except Exception:
        repo.create_file(path, f"ch06: add {os.path.basename(path)}", content, branch=branch)
        print("Created", path)
```

### Option B — Git CLI (good for learning Git)

You can also write the files locally and then run standard Git commands:

```bash
# From repo root
echo '{"hello": "world"}' > reports/ch06/summary.json
printf "# Chapter 6 — Run Summary\n\nHello!" > reports/ch06/README.md

git add reports/ch06/
git commit -m "ch06: add summary + report"
git push origin main
```

> **Tip:** If `main` is protected, push to a feature branch and open a PR.

---

## ✅ What to Submit (Homework)

- `reports/ch06/summary.json`  (cluster counts)
- `reports/ch06/README.md`     (short write-up)
- Your script (`hw_push_artifacts.py`) or the git commands you used

---

## 🔍 Grading Guide (Suggested)

- **Correctness (40%)** — Artifacts exist and are pushed to the repo; summary reflects the data.
- **Code Quality (30%)** — Clear, commented, robust error handling (token, paths, branch).
- **Reproducibility (20%)** — Uses `.env` config; avoids hard-coded tokens.
- **Reflection (10%)** — 2–3 sentences on why GitHub-as-shared-storage is useful for distributed pipelines.

---

## 🧪 Troubleshooting

- **GET 404**: Verify `GITHUB_REPO`, `GITHUB_BRANCH`, and `path` match your repo. Try opening the constructed raw URL in a browser.
- **Private repo**: Set `GITHUB_TOKEN` in `.env` and restart your shell so env vars are loaded.
- **Push errors**: Branch protections may require a PR. Use a feature branch or the Git CLI path.
- **Large artifacts**: Keep homework small (JSON/MD). For larger files consider Git LFS or external storage.

---

## 🧠 Teaching Notes

- Part 1 focuses on the **single mental model**: *pipelines can read their inputs from a shared repo.*
- Homework extends the model to **writing results**, reinforcing the collaboration loop.
- Keep examples tiny so students can reason about them end-to-end.

