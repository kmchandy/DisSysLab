# 🧩 Chapter 8 — Security Switching Agent (run-based, teacher-first layout)

from __future__ import annotations
from typing import List
import re

from dsl.core import Agent, Network
from dsl.block_lib.stream_generators import GenerateFromList
from dsl.block_lib.stream_recorders import RecordToList


# =========================
# 1) The Agent (core idea)
# =========================
class SecuritySwitchingAgent(Agent):
    """
    Two inports:  'messages', 'command'
    Two outports: 'normal', 'quarantine'

    Behavior:
      - When alarm is False: pass messages to 'normal'.
      - When alarm is True : send suspicious to 'quarantine', others to 'normal'.

    Commands to 'command':
      - "virus_detected" => alarm = True
      - "normal"         => alarm = False
    """

    def __init__(self, name: str = "SecuritySwitchingAgent") -> None:
        super().__init__(
            name,
            inports=["messages", "command"],
            outports=["normal", "quarantine"],
        )
        self.alarm: bool = False

    def run(self) -> None:
        while True:
            msg, inport = self.wait_for_any_port()

            if inport == "command":
                self.alarm = (msg == "virus_detected")

            elif inport == "messages":
                text = str(msg)
                if self.alarm:
                    if is_suspicious(text):           # defined later (Section 3)
                        self.send(text, outport="quarantine")
                    else:
                        self.send(text, outport="normal")
                else:
                    self.send(text, outport="normal")


# ==========================================
# 2) Blocks & Connections (core idea)
#    — try changing the delays!
# ==========================================
if __name__ == "__main__":
    normal, quarantine = [], []

    msgs = [
        "hello world",
        "DROP TABLE users;",
        "normal text with base64like QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
        "click here <script>alert('xss')</script>",
        "just emojis!!! $$$$",
        "More base64 UVwx$$**==why_nnot_GVuIHNlc2FtZQ",
    ]
    cmds = ["virus_detected", "normal"]

    net = Network(
        blocks={
            "generate_msg": GenerateFromList(items=msgs, delay=0.4),
            "generate_cmd": GenerateFromList(items=cmds, delay=0.8),
            "security_agent": SecuritySwitchingAgent(),
            "record_normal": RecordToList(normal),
            "record_quarantine": RecordToList(quarantine),
        },
        connections=[
            ("generate_msg", "out", "security_agent", "messages"),
            ("generate_cmd", "out", "security_agent", "command"),
            ("security_agent", "normal", "record_normal", "in"),
            ("security_agent", "quarantine", "record_quarantine", "in"),
        ],
    )

    net.compile_and_run()
    print("NORMAL:", normal)
    print("QUARANTINE:", quarantine)


# ==========================================
# 3) Playground (details for later)
#    Heuristics students can tweak
# ==========================================
_PATTERNS: List[str] = [
    r"\bdrop\s+table\b",
    r"<script\b",
    r"\beval\(",
    r"\bexec\(",
    r"rm\s+-rf",
    r"wget\s+http",
    r"powershell",
    r"cmd\.exe",
    r"/bin/sh",
    r"curl\s+http",
]
_DANGEROUS = [re.compile(pat, re.IGNORECASE) for pat in _PATTERNS]
_BASE64_LIKE = re.compile(r"^[A-Za-z0-9+/=]{24,}$")


def is_suspicious(text: str) -> bool:
    """
    Simple scoring:
      +2 if any dangerous pattern is present
      +1 if >25% symbols/punctuation
      +1 if any long base64-like token
    Suspicious if score > 0.
    """
    t = text or ""
    score = 0

    if any(rx.search(t) for rx in _DANGEROUS):
        score += 2

    if t:
        non_alnum = sum(1 for ch in t if not ch.isalnum() and not ch.isspace())
        if non_alnum / max(len(t), 1) > 0.25:
            score += 1

    for token in t.split():
        if len(token) >= 24 and _BASE64_LIKE.match(token):
            score += 1
            break

    return score > 0
