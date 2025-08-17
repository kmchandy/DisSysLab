# 🤝 Chapter 6 — Connectors (InputConnector & OutputConnector)

**Goal:** Shows you how blocks connect to external applications using two simple blocks:

- **InputConnector** — command‑driven *pull* from an external source → emits items on `out`.
- **OutputConnector** — command‑driven *push* to an external sink → performs a single write on `flush`.

**StreamGenerator** and  **StreamRecorder** generate and record **streams** of messages to lists, files, and other repositories. Connectors are used to call **external interfaces** using the APIs provided by the external applications.

---

## 🧭 Mental Model

```
[ Orchestrator ] --commands--> [ InputConnector ] --items--> [ Transformers ] --rows--> [ Orchestrator ] --flush cmd--> [ OutputConnector ]
```

- **Orchestrator** decides *when/what* to pull and when to flush (timer/manual).
- **InputConnector** does a one‑off pull per command and emits 0..N items.
- **OutputConnector** accepts a `{"cmd":"flush", "payload": [...], "meta": {...}}` command and performs one external write (e.g., one GitHub commit, one Markdown file write, one sheet update).

---

## 📦 Requirements

```bash
pip install PyGithub scikit-learn matplotlib
```

> PyGithub is used for a **single, real‑world demo** reading from a public repo (no token needed). Everything else uses local files so students can run it immediately.

---

## 🧱 Core Blocks (minimal, readable)

### `InputConnector` (base)

```python
# dsl/block_lib/connectors/input_connector.py
from typing import Dict, Any, Iterable
from dsl.core import SimpleAgent

class InputConnector(SimpleAgent):
    """Command‑driven pull from an external source.
    in:  command dicts like {"cmd":"pull", "args":{...}}
    out: item dicts  like {"data": ...}
    """
    def __init__(self, name="InputConnector"):
        super().__init__(name=name, inport="in", outports=["out", "status", "error"])

    def process(self, msg: Dict[str, Any], inport=None):
        cmd  = (msg or {}).get("cmd", "pull")
        args = (msg or {}).get("args", {}) or {}
        try:
            count = 0
            for item in self._pull(cmd, args):  # override in subclass
                self.send({"data": item}, outport="out")
                count += 1
            self.send({"event":"done","cmd":cmd,"count":count}, outport="status")
        except Exception as e:
            self.send({"event":"error","cmd":cmd,"message":repr(e)}, outport="error")

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError
```

### `OutputConnector` (base)

```python
# dsl/block_lib/connectors/output_connector.py
from typing import Dict, Any, List
from dsl.core import SimpleAgent

class OutputConnector(SimpleAgent):
    """Command‑driven push to an external sink.
    in: commands like {"cmd":"flush", "payload":[...], "meta":{...}}
    """
    def __init__(self, name="OutputConnector"):
        super().__init__(name=name, inport="in", outports=["status", "error"])

    def process(self, msg: Dict[str, Any], inport=None):
        cmd   = (msg or {}).get("cmd")
        meta  = (msg or {}).get("meta", {}) or {}
        try:
            if cmd == "flush":
                payload = msg.get("payload", [])
                self._flush(payload, meta)  # override in subclass
                self.send({"event":"flushed","count":len(payload)}, outport="status")
            elif cmd == "configure":
                self._configure(meta)
                self.send({"event":"configured"}, outport="status")
            else:
                self.send({"event":"error","message":f"unknown cmd {cmd}"}, outport="error")
        except Exception as e:
            self.send({"event":"error","cmd":cmd,"message":repr(e)}, outport="error")

    def _flush(self, payload: List[Dict[str, Any]], meta: Dict[str, Any]):
        raise NotImplementedError
    def _configure(self, meta: Dict[str, Any]):
        pass
```

### File‑based toy connectors (student‑owned)

```python
# dsl/block_lib/connectors/input_file.py
import json, pathlib
from typing import Dict, Any, Iterable
from .input_connector import InputConnector

class InputConnectorFile(InputConnector):
    """Reads items from a local JSON file on command.
    If the file holds a list, yields each element; if it's an object, yields that single object.
    """
    def __init__(self, path: str, name="InputConnectorFile"):
        super().__init__(name=name)
        self.path = pathlib.Path(path)

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        obj = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(obj, list):
            return obj
        return [obj]
```

```python
# dsl/block_lib/connectors/output_file.py
import json, pathlib
from typing import Dict, Any, List
from .output_connector import OutputConnector

class OutputConnectorFileJSON(OutputConnector):
    """Writes a single JSON file on flush (payload is a list of dicts)."""
    def __init__(self, path: str, name="OutputConnectorFileJSON"):
        super().__init__(name=name)
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _flush(self, payload: List[Dict[str, Any]], meta: Dict[str, Any]):
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

class OutputConnectorFileMarkdown(OutputConnector):
    """Writes a Markdown file on flush; payload is a list of rows (strings or dicts with 'row')."""
    def __init__(self, path: str, title: str = "Report", name="OutputConnectorFileMarkdown"):
        super().__init__(name=name)
        self.path = pathlib.Path(path)
        self.title = title
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _flush(self, payload: List[Dict[str, Any]], meta: Dict[str, Any]):
        lines = [f"# {meta.get('title', self.title)}", ""]
        for p in payload:
            if isinstance(p, str):
                lines.append(p)
            else:
                lines.append(p.get("row", str(p)))
        self.path.write_text("\n".join(lines), encoding="utf-8")
```

### Orchestrator (buffers and flushes)

```python
# dsl/block_lib/orchestrators/buffered_orchestrator.py
from typing import Dict, Any, List
from dsl.core import SimpleAgent

class BufferedOrchestrator(SimpleAgent):
    """Buffers rows arriving on data_in; on tick_in, sends one flush command with payload."""
    def __init__(self, meta_builder=None, name="BufferedOrchestrator"):
        super().__init__(name=name, inport=None, outports=["out"])
        self.inports = ["data_in", "tick_in"]
        self._buf: List[Dict[str, Any]] = []
        self._meta_builder = meta_builder or (lambda buf: {})

    def process(self, msg: Dict[str, Any], inport=None):
        if inport == "data_in":
            self._buf.append(msg)
        elif inport == "tick_in":
            meta = self._meta_builder(self._buf)
            self.send({"cmd":"flush", "payload": self._buf, "meta": meta}, outport="out")
            self._buf = []
```

---

## 🎬 Demo A — Toy connectors (file → compute → file)

**Goal:** Pull a JSON list of short issues, cluster them, format rows, flush once to a Markdown report.

**Data file:** `dsl/examples/ch06_connectors/data/issues.json`

```json
[
  {"title": "Crash on startup", "body": "App throws exception when launched"},
  {"title": "Feature: dark mode", "body": "Please add a dark theme"},
  {"title": "Docs: typo in README", "body": "Small spelling mistake"}
]
```

**Script:** `dsl/examples/ch06_connectors/file_demo.py`

```python
import sklearn.feature_extraction.text as text
import sklearn.cluster as cluster

from dsl.core import Network
from dsl.block_lib.connectors.input_file import InputConnectorFile
from dsl.block_lib.connectors.output_file import OutputConnectorFileMarkdown
from dsl.block_lib.orchestrators.buffered_orchestrator import BufferedOrchestrator
from dsl.block_lib.stream_transformers import TransformerFunction

SRC = "dsl/examples/ch06_connectors/data/issues.json"
OUT = "dsl/examples/ch06_connectors/reports/issue_summary.md"

# Fit once on full corpus
import json, pathlib
issues = json.loads(pathlib.Path(SRC).read_text())
texts = [f"{i['title']} {i['body']}" for i in issues]
vec = text.CountVectorizer(max_features=2000).fit(texts)
km  = cluster.KMeans(n_clusters=2, random_state=42, n_init=10).fit(vec.transform(texts).toarray())

def vectorize(msg):
    t = f"{msg['data']['title']} {msg['data']['body']}"
    return vec.transform([t]).toarray()

def predict(v):
    return int(km.predict(v)[0])

def to_row(msg):
    label = "bug" if any(k in (msg['data']['title']+msg['data']['body']).lower() for k in ["error","crash","exception"]) else "other"
    return {"row": f"- **[{label}]** {msg['data']['title']}"}

# Build network
orch = BufferedOrchestrator(meta_builder=lambda buf: {"title": "Issue Triage Summary"})

net = Network(
    blocks={
        "in": InputConnectorFile(SRC),
        "vec": TransformerFunction(func=vectorize, input_key=None, output_key="vec"),
        "clu": TransformerFunction(func=predict,   input_key="vec",  output_key="cluster"),
        "row": TransformerFunction(func=to_row,    input_key=None,    output_key="row"),
        "orch": orch,
        "out": OutputConnectorFileMarkdown(OUT, title="Issue Triage Summary"),
    },
    connections=[
        ("in","out","vec","in"),
        ("vec","out","clu","in"),
        ("clu","out","row","in"),
        ("row","out","orch","data_in"),
        ("orch","out","out","in"),
    ],
)

# Kick: send a single pull command and then a single flush command
net.compile()
net.blocks["in"].process({"cmd":"pull"})
net.blocks["orch"].process({"tick": True}, inport="tick_in")
print("Wrote:", OUT)
```

---

## 🌐 Demo B — Real‑world read (PyGitHub, public repo)

**Goal:** small, authentic connector with **no auth** (public repo). Pull README text from a GitHub repo and write a local Markdown summary.

**Connector:** `dsl/block_lib/connectors/input_github_readme.py`

```python
from github import Github
from typing import Dict, Any, Iterable
from .input_connector import InputConnector

class InputConnectorGitHubReadme(InputConnector):
    """Pulls README from a public GitHub repo on command.
    args: {"repo": "owner/name", "branch": "main"}
    emits one item: {"text": "...README content..."}
    """
    def __init__(self, name="InputConnectorGitHubReadme"):
        super().__init__(name=name)
        self.gh = Github()  # no token → public only

    def _pull(self, cmd: str, args: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        repo_full = args.get("repo")
        if not repo_full:
            raise ValueError("Missing 'repo' (e.g., 'pallets/flask')")
        repo = self.gh.get_repo(repo_full)
        readme = repo.get_readme()
        text = readme.decoded_content.decode("utf-8", errors="replace")
        return [{"text": text, "repo": repo_full}]
```

**Script:** `dsl/examples/ch06_connectors/github_readme_demo.py`

```python
from dsl.core import Network
from dsl.block_lib.connectors.input_github_readme import InputConnectorGitHubReadme
from dsl.block_lib.connectors.output_file import OutputConnectorFileMarkdown
from dsl.block_lib.orchestrators.buffered_orchestrator import BufferedOrchestrator
from dsl.block_lib.stream_transformers import TransformerFunction

OUT = "dsl/examples/ch06_connectors/reports/readme_report.md"

# Tiny transformers: count lines and words
def summarize(msg):
    text = msg["data"]["text"]
    lines = text.splitlines()
    words = text.split()
    return {"row": f"- Repo README has {len(lines)} lines and {len(words)} words."}

orch = BufferedOrchestrator(meta_builder=lambda buf: {"title": "README Summary"})

net = Network(
    blocks={
        "in": InputConnectorGitHubReadme(),
        "sum": TransformerFunction(func=summarize, input_key=None, output_key="row"),
        "orch": orch,
        "out": OutputConnectorFileMarkdown(OUT, title="README Summary"),
    },
    connections=[
        ("in","out","sum","in"),
        ("sum","out","orch","data_in"),
        ("orch","out","out","in"),
    ],
)

net.compile()
# Pull from a public repo (no token). Try 'pallets/flask' or 'numpy/numpy'.
net.blocks["in"].process({"cmd":"pull", "args": {"repo": "pallets/flask"}})
# Single flush
net.blocks["orch"].process({"tick": True}, inport="tick_in")
print("Wrote:", OUT)
```

> To use **private** repos later, pass a token to `Github(token)` via environment variable and expose a small `configure` command.

---

## 🧠 Take Away

- **Why connectors?** They make *external world I/O* explicit and replaceable without changing the network shape.
- **When to use StreamRecorder?** For per‑item appends (logging, row insert). Connectors are for *commanded, transactional writes* like a one‑shot Markdown report or commit.
- **Real world path:** Today’s GitHub demo reads public content; a graded assignment could invite students to add a token and write a report back to their fork.
- **Future (MCP):** An MCP client can implement the same `InputConnector`/`OutputConnector` contracts. Your networks stay the same; only the connector internals change.

---



