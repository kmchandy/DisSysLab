# 🧩 Chapter 8 — Agents (Message Security Mode)

### 🎯 Goal

Build an **Agent** with multiple inports/outports that changes how it processes **messages** when a security mode flips (e.g., `normal` ↔ `virus_detected`). In "virus" mode, a checker runs on every message; in normal mode, messages pass through untouched.

---

## 📍 What We’ll Build

**Inports (2):**

* `messages` — stream of text payloads
* `command` — control messages (`"normal"`, `"virus_detected"`, optional `set_checker`)

**Outports (3):**

* `clean` — messages deemed safe (delivered)
* `quarantine` — messages flagged by checker
* `log` — status and diagnostics

**Visual**

```
 [ Msg Generator ] ─▶ (messages)         ┌──────────────────────────────┐
                                     │ SecuritySwitchingAgent │ ──▶ (clean)
 [ Cmd Generator ] ──▶ (command)  │                          │ ──▶ (quarantine)
                                     │                          │ ──▶ (log)
                                     └──────────────────────────────┘
```

---

## ⚙️ How It Works

* **State**: `{ mode: "normal" | "virus", checker: "lenient" | "strict" }` (default `normal + lenient`)
* **Normal mode**: messages go straight to `clean`.
* **Virus mode**: each message is scanned. If suspicious → `quarantine`; else → `clean`.
* **Commands**:

  * `"virus_detected"` → switch to virus mode
  * `"normal"` → switch back to normal
  * `{ "cmd": "set_checker", "value": "strict"|"lenient" }` → adjust sensitivity

**Checker** (zero-deps heuristic): looks for dangerous patterns (SQL/script/system), high symbol ratio, and base64-like blobs.

---

## Example Code

```python
# dsl/examples/ch08_agents/security_switching_agent.py
import re
from dsl.core import Agent, Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_recorders import RecordToList

# --- simple heuristics (no external libs) ---
PATTERNS = [
    r"\bdrop\s+table\b", r"<script\b", r"\beval\(", r"\bexec\(", r"rm\s+-rf",
    r"wget\s+http", r"powershell", r"cmd\.exe", r"/bin/sh", r"curl\s+http",
]
DANGEROUS = [re.compile(p, re.I) for p in PATTERNS]
BASE64_LIKE = re.compile(r"^[A-Za-z0-9+/=]{24,}$")

def suspicious_score(text: str):
    t = text or ""
    score = 0
    # rule 1: direct dangerous patterns
    if any(rx.search(t) for rx in DANGEROUS):
        score += 2
    # rule 2: symbol/garbage ratio
    if len(t) > 0:
        non_alnum = sum(1 for ch in t if not ch.isalnum() and not ch.isspace())
        if non_alnum / max(len(t),1) > 0.25:
            score += 1
    # rule 3: long base64-like segment
    for token in t.split():
        if len(token) >= 24 and BASE64_LIKE.match(token):
            score += 1
            break
    return score

THRESHOLDS = {"lenient": 2, "strict": 1}


def make_security_switching_agent(name="SecuritySwitchingAgent"):
    def init_fn(agent):
        agent.state = {"mode": "normal", "checker": "lenient"}
        agent.send({"event": "init", **agent.state}, outport="log")

    def handle_msg(agent, msg, inport=None):
        st = agent.state
        if inport == "command":
            if msg == "virus_detected":
                st["mode"] = "virus"
                agent.send({"event": "mode", "mode": "virus"}, outport="log")
            elif msg == "normal":
                st["mode"] = "normal"
                agent.send({"event": "mode", "mode": "normal"}, outport="log")
            elif isinstance(msg, dict) and msg.get("cmd") == "set_checker" and msg.get("value") in THRESHOLDS:
                st["checker"] = msg["value"]
                agent.send({"event": "checker", "checker": st["checker"]}, outport="log")
            else:
                agent.send({"event": "error", "message": f"bad command: {msg}"}, outport="log")
            return

        if inport == "messages":
            text = str(msg)
            if st["mode"] == "normal":
                agent.send({"text": text, "passed": True, "mode": "normal"}, outport="clean")
                agent.send({"event": "pass", "text": text}, outport="log")
                return
            # virus mode
            score = suspicious_score(text)
            thresh = THRESHOLDS[st["checker"]]
            if score >= thresh:
                agent.send({"text": text, "flag": "suspicious", "score": score}, outport="quarantine")
                agent.send({"event": "quarantine", "score": score}, outport="log")
            else:
                agent.send({"text": text, "passed": True, "mode": "virus"}, outport="clean")
                agent.send({"event": "pass", "score": score}, outport="log")
            return

        agent.send({"event": "error", "message": f"unknown inport: {inport}"}, outport="log")

    return Agent(
        name=name,
        inports=["messages", "command"],
        outports=["clean", "quarantine", "log"],
        init_fn=init_fn,
        handle_msg=handle_msg,
    )

# --- demo network ---
if __name__ == "__main__":
    clean, quarantine, logs = [], [], []

    msgs = [
        "hello world",  # normal safe
        "DROP TABLE users;",  # SQL injection-like
        "normal text with base64like QWxhZGRpbjpvcGVuIHNlc2FtZQ==",  # base64-like
        "click here <script>alert('xss')</script>",  # script
        "just emojis!!! $$$$",  # high symbol ratio
    ]
    cmds = ["virus_detected", {"cmd": "set_checker", "value": "strict"}, "normal"]

    net = Network(
        blocks={
            "gen_msg": GenerateFromList(items=msgs, key=None),
            "gen_cmd": GenerateFromList(items=cmds, key=None),
            "agent": make_security_switching_agent(),
            "rec_clean": RecordToList(clean),
            "rec_quar": RecordToList(quarantine),
            "rec_log": RecordToList(logs),
        },
        connections=[
            ("gen_msg", "out", "agent", "messages"),
            ("gen_cmd", "out", "agent", "command"),
            ("agent", "clean", "rec_clean", "in"),
            ("agent", "quarantine", "rec_quar", "in"),
            ("agent", "log", "rec_log", "in"),
        ],
    )

    net.compile_and_run()
    print("CLEAN:", clean)
    print("QUARANTINE:", quarantine)
    print("LOGS:", logs)
```

---

## Teaching Notes

* **Multiple inports/outports**: `messages` vs `command`, and `clean` vs `quarantine` vs `log`.
* **Asynchronous control**: flip modes on-the-fly; messages keep flowing.
* **Zero-dependency heuristics**: rules are readable; students can add their own (hash checks, keyword lists, length thresholds).
* **Extension ideas**: add a `release_quarantine` command; add per-sender rate limits; maintain stats and emit periodic summaries on a `stats` outport.
