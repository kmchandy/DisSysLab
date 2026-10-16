"""
---
emits: each item once; later items with the same key are dropped
kind: author
out: same as in
---
Arguments: by -- the field that identifies an item (default "url").
"""


def step(item, state, settings):
    key = item[settings["by"]]
    if key in state["seen"]:
        return [], state
    return [item], {"seen": state["seen"] + [key]}


class Deduplicator:
    def __init__(self, by="url"):
        self.settings = {"by": by}
        self.state = {"seen": []}

    def __call__(self, item):
        out, self.state = step(item, self.state, self.settings)
        return out

    def checkpoint(self):
        return self.state

    def restore(self, saved):
        self.state = saved
