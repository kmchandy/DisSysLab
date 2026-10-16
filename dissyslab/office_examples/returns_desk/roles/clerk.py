"""
---
emits: approves small refunds; escalates the rest
in: amount
out: clerk_decision (approve | escalate)
---
Arguments: limit -- the largest refund the clerk may approve, in dollars
(default 50).
"""


def step(item, settings):
    if item["amount"] < settings["limit"]:
        return {"clerk_decision": "approve"}
    return {"clerk_decision": "escalate"}


class Clerk:
    def __init__(self, limit=50):
        self.settings = {"limit": limit}

    def __call__(self, item):
        return step(item, self.settings)
