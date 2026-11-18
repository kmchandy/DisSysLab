"""
---
emits: Sal's reply, with its sale checked and the binding line written by code
kind: author
in: session, turn, reply, sale, vehicle, price
out: session, turn, reply, sale (yes | no), vehicle, price
---
Arguments: inventory -- the file of list and floor prices
(default inventory.json, in the office's folder).
"""

import json

REFUSED = ("I'm sorry, I can't agree to that price for this car. "
           "Would you like to make another offer, or book a test drive?")


def why_refused(item, inventory):
    """Why this sale must not be agreed, or None if it may be."""
    if item["vehicle"] not in inventory:
        return "no such car on the lot"
    if float(item["price"]) < inventory[item["vehicle"]]["floor"]:
        return "below the floor"
    return None


def step(item, inventory):
    out = {k: item[k] for k in ("session", "turn", "reply", "sale", "vehicle", "price")}
    if item["sale"] != "yes":
        return [out]  # talk: nothing is agreed, so there is nothing to check
    if why_refused(item, inventory) is not None:
        return [{**out, "reply": REFUSED, "sale": "no", "vehicle": "none", "price": 0}]
    car = inventory.get(item["vehicle"], {}).get("name", item["vehicle"])
    out["reply"] = (f"{item['reply']}\n\nBINDING CONTRACT: {car}, "
                    f"${float(item['price']):,.0f}. Main Street Motors.")
    return [out]


class PriceGuard:
    def __init__(self, inventory="inventory.json"):
        with open(inventory, encoding="utf-8") as f:
            self.inventory = json.load(f)

    def __call__(self, item):
        return step(item, self.inventory)
