"""
---
emits: the manager's decision on an escalated refund
in: amount
out: manager_decision (approve | refuse)
---
Approves everything. An English manager.md that decides from "item" and
"reason" would drop in with the same in: and out:.
"""


def step(item, settings):
    return {"manager_decision": "approve"}


class Manager:
    def __init__(self):
        self.settings = {}

    def __call__(self, item):
        return step(item, self.settings)
