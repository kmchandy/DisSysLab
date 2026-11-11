"""
---
emits: Sal's message, or a refusal if it books a sale below the floor
kind: author
in: session, turn, reply, book (yes | no), vehicle, price, buyer
out: session, turn, reply, book (yes | no), vehicle, price, buyer, guard (passed | refused)
---
The check in hooks/floor_guard.py, as a DisSysLab agent. office.md puts it
between Sal and the router that books sales, so every sale Sal proposes
passes through it. Arguments: inventory -- the file of list and floor
prices (default inventory.json, in the office's folder).
"""

import json

SAFE = ("I'm sorry, I can't go that low on this car. I'd be glad to find you "
        "the best price a sales manager can approve.")


def problem(item, inventory):
    """Why this sale must not be booked, or None. The same rule as the hook."""
    if item["vehicle"] not in inventory:
        return "there is no such vehicle on the lot"
    if not isinstance(item["price"], (int, float)):
        return "the price is not a number"
    if item["price"] < inventory[item["vehicle"]]["floor"]:
        return "the price is below what the dealership accepts for this car"
    return None


def step(item, inventory):
    sale = {k: item[k] for k in ("session", "turn", "reply", "book", "vehicle", "price", "buyer")}
    if item["book"] == "yes" and problem(item, inventory):
        return [{**sale, "book": "no", "reply": SAFE, "guard": "refused"}]
    return [{**sale, "guard": "passed"}]


class FloorGuard:
    def __init__(self, inventory="inventory.json"):
        with open(inventory, encoding="utf-8") as f:
            self.inventory = json.load(f)

    def __call__(self, item):
        return step(item, self.inventory)
