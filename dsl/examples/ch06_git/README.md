# 🤝 Chapter 6 — Collaboration via GitHub (Pull inputs, Push results)

In this chapter we show how a distributed pipeline can **pull configs/data from GitHub** and **push results/artifacts back** to GitHub—so teams (or agents) can collaborate asynchronously.

---

## 🎯 Goals
- Pull **configs / prompts / datasets** from a GitHub repo at run time.
- Run a DisSysLab network using those inputs.
- Push **derived artifacts** (plots, JSON summaries, logs) back to GitHub.
- Do this with minimal glue code and clear error handling.

---

## 🧩 What We’ll Build

**Workflow A — Pull → Run → Local**
[ GitHub Config ] → [ Generator ] → [ Transformers ] → [ Recorder (local files) ]

css
Copy
Edit

**Workflow B — Pull → Run → Push**
[ GitHub Data ] → [ Network ] → [ Artifacts ] → [ GitHub (commit) ]

markdown
Copy
Edit

We’ll implement both using a small `github_io.py` helper that abstracts GitHub reads/writes.

---

## 📦 Prerequisites

1. **GitHub token** with `repo` scope  
   - Create a **fine-grained PAT** or classic PAT.
2. `.env` at the project root (or wherever your `get_credentials.py` reads from):
   ```env
   GITHUB_TOKEN=ghp_xxx_your_token
   GITHUB_REPO=yourusername/yourrepo
   GITHUB_BRANCH=main
Dependencies

bash
Copy
Edit
pip install PyGithub python-dotenv
(You can also use requests + raw URLs; we’ll use PyGithub for clarity.)

🗂️ Folder Layout
bash
Copy
Edit
dsl/
  examples/
    ch06_github/
      README.md                  # this file
      github_io.py               # minimal helper for read/write
      part1_pull_and_run.py      # Pull config/data from GH, run locally
      part2_push_artifacts.py    # Push results back to GH
      simple_github.py           # Runner that executes both parts
🔧 github_io.py (Helper)
python
Copy
Edit
# dsl/examples/ch06_github/github_io.py
import os
from typing import Optional, Tuple
from github import Github
from dataclasses import dataclass

@dataclass
class GHConfig:
    repo_full_name: str
    branch: str

def get_github() -> Tuple[Github, GHConfig]:
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    branch = os.getenv("GITHUB_BRANCH", "main")
    if not token:
        raise ValueError("GITHUB_TOKEN not set (check your .env)")
    if not repo:
        raise ValueError("GITHUB_REPO not set (e.g., user/repo)")
    return Github(token), GHConfig(repo_full_name=repo, branch=branch)

def read_text(path: str, encoding="utf-8") -> str:
    gh, cfg = get_github()
    repo = gh.get_repo(cfg.repo_full_name)
    file = repo.get_contents(path, ref=cfg.branch)
    return file.decoded_content.decode(encoding)

def upsert_text(path: str, content: str, message: str) -> None:
    gh, cfg = get_github()
    repo = gh.get_repo(cfg.repo_full_name)
    try:
        file = repo.get_contents(path, ref=cfg.branch)
        repo.update_file(path, message, content, file.sha, branch=cfg.branch)
    except Exception:
        repo.create_file(path, message, content, branch=cfg.branch)
💻 Part 1 — Pull Configs/Data, Then Run
Example pulls a vectorizer vocabulary and a small dataset from GitHub, runs a pipeline, and saves results locally.

python
Copy
Edit
# dsl/examples/ch06_github/part1_pull_and_run.py
import json
from dsl.core import Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_transformers import WrapFunction
from dsl.block_lib.stream_recorders import RecordToList
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.cluster import KMeans

from .github_io import read_text

# --- Pull inputs from GitHub ---
vocab = json.loads(read_text("data/ch06/vocab.json"))        # e.g., ["good","bad","excellent","terrible"]
reviews = json.loads(read_text("data/ch06/reviews.json"))    # list of strings

results = []

vec = CountVectorizer(vocabulary=vocab)
kmeans = KMeans(n_clusters=2, random_state=42)

def vectorize(text):
    return vec.transform([text]).toarray()[0].tolist()

def cluster(vec_row):
    # kmeans must fit on a batch; for demo fit on single-row to keep it simple
    # In real apps, fit on full corpus once, then predict per item.
    kmeans.fit([vec_row])
    return int(kmeans.labels_[0])

net = Network(
    blocks={
        "gen": GenerateFromList(items=reviews, key="text"),
        "vec": WrapFunction(func=vectorize, input_key="text", output_key="vector"),
        "clu": WrapFunction(func=cluster, input_key="vector", output_key="cluster"),
        "rec": RecordToList(results),
    },
    connections=[
        ("gen","out","vec","in"),
        ("vec","out","clu","in"),
        ("clu","out","rec","in"),
    ]
)

net.compile_and_run()
print("Results:", results)  # [{'cluster': 0, 'vector': [...]}, ...]

# Save locally for inspection
with open("part1_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("Saved part1_results.json")
Note: For proper ML practice, fit KMeans once on the full corpus and then predict per message. Here we keep it minimal to foreground the GitHub I/O flow.

💻 Part 2 — Push Artifacts Back to GitHub
This example writes a summary JSON and a small Markdown report to the repo.

python
Copy
Edit
# dsl/examples/ch06_github/part2_push_artifacts.py
import json
from collections import Counter
from .github_io import upsert_text

# Load the results produced by Part 1
with open("part1_results.json", "r") as f:
    results = json.load(f)

clusters = [r["cluster"] for r in results]
counts = Counter(clusters)
summary = {
    "total": len(results),
    "by_cluster": dict(counts)
}
summary_json = json.dumps(summary, indent=2)

report_md = f"""# Chapter 6 — Run Summary

- Total items: {summary['total']}
- Cluster counts: {summary['by_cluster']}
"""

# Commit paths (adjust to your repo layout)
summary_path = "reports/ch06/summary.json"
report_path  = "reports/ch06/README.md"

upsert_text(summary_path, summary_json, "ch06: add summary.json")
upsert_text(report_path, report_md, "ch06: add report README.md")

print("Pushed artifacts to GitHub:", summary_path, "and", report_path)
▶️ Runner
python
Copy
Edit
# dsl/examples/ch06_github/simple_github.py
import os
from dotenv import load_dotenv

def main():
    # Ensure .env is loaded so GITHUB_* vars are available
    load_dotenv()

    # Run Part 1
    from .part1_pull_and_run import results  # side-effect: executes pipeline and writes part1_results.json
    print("Part 1 complete. Example results:", results[:2])

    # Run Part 2
    from .part2_push_artifacts import summary  # side-effect: pushes artifacts; exposes summary

    print("Part 2 complete. Summary:", summary)

if __name__ == "__main__":
    main()
🏃 How to Run
From the project root:

bash
Copy
Edit
# 1) Ensure env
cp .env.example .env   # if you have one
# edit .env to include: GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH
# (and your OPENAI_API_KEY if later chapters use GPT)

# 2) Install deps if needed
pip install PyGithub python-dotenv scikit-learn

# 3) Run
cd dsl/examples/ch06_github
python simple_github.py
🧪 Troubleshooting
Auth errors: Double-check GITHUB_TOKEN and that it has repo scope for the target repository.

File not found: Ensure the paths you read (data/ch06/...) exist on the specified GITHUB_BRANCH.

Branch protection: If main is protected, push to a feature branch or open a PR with the artifacts.

Large files: Prefer pushing summaries (JSON/CSV/Markdown) and storing large blobs elsewhere (or use Git LFS).

🔐 Security Notes
Keep tokens in .env, not in code.

Use fine-grained PATs where possible.

Consider CI secrets to run pipelines in GitHub Actions for repeatability.

✅ Key Takeaways
GitHub can act as a shared memory for distributed workflows.

Pulling inputs at runtime + pushing outputs enables asynchronous collaboration.

With a tiny helper (github_io.py), DisSysLab networks can read/write repo files cleanly.

⏭️ Coming Up
In Chapter 7, we’ll combine GPT transformers and data science transformers in a single, collaborative pipeline that reads prompts/configs from GitHub and publishes both LLM outputs and analytics back to the repo.