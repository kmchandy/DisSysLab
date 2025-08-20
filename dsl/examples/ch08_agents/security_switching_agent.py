# dsl/examples/ch08_agents/security_switching_agent.py
import re
from dsl.core import Agent, Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_recorders import RecordToList

# --- tiny heuristics (readable, no deps) ---
PATTERNS = [
    r"\bdrop\s+table\b", r"<script\b", r"\beval\(", r"\bexec\(", r"rm\s+-rf",
    r"wget\s+http", r"curl\s+http", r"powershell", r"cmd\.exe", r"/bin/sh",
]
DANGEROUS = [re.compile(p, re.I) for p in PATTERNS]
BASE64_LIKE = re.compile(r"^[A-Za-z0-9+/=]{24,}$")


def detect_suspicious(text: str) -> bool:
    t = text or ""
    # Rule 1: explicit dangerous pattern
    if any(rx.search(t) for rx in DANGEROUS):
        return True
    # Rule 2: base64-ish long token
    for tok in t.split():
        if len(tok) >= 24 and BASE64_LIKE.match(tok):
            return True
    # Rule 3: lots of symbols (very rough)
    non_alnum = sum(1 for ch in t if not ch.isalnum() and not ch.isspace())
    return (non_alnum / max(len(t), 1)) > 0.25


def make_security_switching_agent(name="SecuritySwitchingAgent"):
    def run_fn(agent):
        agent.state = "safe"  # "safe" | "alert"
        # optional visibility for students:
        print(f"[{name}] mode = SAFE")

        while True:
            msg, port = agent.recv_from_any_port()

            if port == "command":
                agent.state = "alert" if msg == "virus_detected" else "safe"
                print(
                    f"[{name}] mode = {'ALERT' if agent.state == 'alert' else 'SAFE'}")
                continue

            # port == "messages"
            if agent.state == "safe":
                agent.send(msg, outport="clean")
            else:
                if detect_suspicious(str(msg)):
                    agent.send(msg, outport="quarantine")
                else:
                    agent.send(msg, outport="clean")

    return Agent(
        name=name,
        inports=["messages", "command"],
        outports=["clean", "quarantine"],
        run=run_fn,
    )


# --- demo network ---
if __name__ == "__main__":
    clean, quarantine = [], []

    msgs = [
        "hello world",                                   # safe
        "DROP TABLE users;",                             # pattern match
        "note: QWxhZGRpbjpvcGVuIHNlc2FtZQ== token",      # base64-like
        "click here <script>alert('xss')</script>",      # script
        "just emojis!!! $$$$",                           # symbol ratio
    ]
    cmds = ["virus_detected", "normal"]

    net = Network(
        blocks={
            "generate_msg": GenerateFromList(items=msgs, key=None, delay=0.1),
            "generate_cmd": GenerateFromList(items=cmds, key=None, delay=0.2),
            "security_agent": make_security_switching_agent(),
            "record_clean": RecordToList(clean),
            "record_quarantine": RecordToList(quarantine),
        },
        connections=[
            ("generate_msg", "out", "security_agent",
             "messages"),   # fixed block name
            ("generate_cmd", "out", "security_agent", "command"),
            ("security_agent", "clean", "record_clean", "in"),
            ("security_agent", "quarantine", "record_quarantine", "in"),
        ],
    )

    net.compile_and_run()
    print("CLEAN:", clean)
    print("QUARANTINE:", quarantine)
