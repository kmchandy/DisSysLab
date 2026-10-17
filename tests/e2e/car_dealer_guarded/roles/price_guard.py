"""
---
emits: the salesperson's reply, or a safe one if it agrees to a price below the floor
kind: author
in: session, turn, text, reply, vehicle, price
out: session, turn, reply, guarded (yes | no)
---
Arguments: inventory -- the file of list and floor prices (default
inventory.json, in the office's folder).

The guardrail does not trust the model's own account of what it said. It
checks the "price" field the model declared *and* every price in the
reply's text, against the floor of the car named in the sentence (or, if
none, in the reply, or in what the customer wrote, or else the cheapest
car). Any price below the floor, or any promise that the reply is
binding, replaces the reply with a safe one.

An author, not an annotator: it builds the message that reaches the
customer, so the model's reply cannot reach the screen except through
this check. It copies session and turn, which chat_reply needs, and
nothing else: the customer's text does not go on to the screen.
"""

import json
import re

AMOUNT = re.compile(
    r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*([kK]\b)?"
    r"|(\d[\d,]*(?:\.\d+)?)\s*(?:US\s*)?dollars?\b"
    r"|\b(one|a|five|ten|hundred)\s+dollars?\b",
    re.IGNORECASE,
)
WORDS = {"one": 1, "a": 1, "five": 5, "ten": 10, "hundred": 100}
NOT_A_PRICE = re.compile(
    r"^\s*(off|down|discount|rebate|deposit|savings|less|per\b|a month|/\s*mo|monthly)",
    re.IGNORECASE,
)
BINDING = re.compile(r"binding|takesies", re.IGNORECASE)


def prices(sentence):
    found = []
    for m in AMOUNT.finditer(sentence):
        if NOT_A_PRICE.match(sentence[m.end():]):
            continue
        if m.group(1):
            found.append(float(m.group(1).replace(",", "")) * (1000 if m.group(2) else 1))
        elif m.group(3):
            found.append(float(m.group(3).replace(",", "")))
        else:
            found.append(WORDS[m.group(4).lower()])
    return found


def cars_in(text, inventory):
    return [car for car in inventory if car in text.lower()]


def why_unsafe(item, inventory):
    """The reason the reply must not reach the customer, or None."""
    reply = str(item.get("reply", ""))
    car = item.get("vehicle")
    try:
        price = float(item.get("price") or 0)
    except (TypeError, ValueError):
        price = 0
    if car in inventory and 0 < price < inventory[car]["floor"]:
        return f"declared price {price:,.0f} below the floor for {car}"
    default = (cars_in(reply, inventory) or cars_in(str(item.get("text", "")), inventory)
               or ([car] if car in inventory else [])
               or [min(inventory, key=lambda c: inventory[c]["floor"])])
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", reply):
        cars = cars_in(sentence, inventory) or default
        floor = min(inventory[c]["floor"] for c in cars)
        if any(p < floor for p in prices(sentence)):
            return f"names a price below the floor: {sentence.strip()!r}"
        if BINDING.search(sentence):
            return f"talks about a binding deal: {sentence.strip()!r}"
    return None


def safe_reply(item, inventory):
    car = item.get("vehicle")
    if car not in inventory:
        named = cars_in(str(item.get("text", "")), inventory)
        car = named[0] if named else None
    listed = (f" The {inventory[car]['name']} is listed at ${inventory[car]['list']:,}."
              if car else "")
    return ("I'm not able to agree to that." + listed +
            " Final prices are set by a sales manager in person, and nothing in this"
            " chat is an offer. Would you like to book a test drive?")


def step(item, inventory):
    reason = why_unsafe(item, inventory)
    reply = item.get("reply", "") if reason is None else safe_reply(item, inventory)
    return [{"session": item["session"], "turn": item["turn"], "reply": reply,
             "guarded": "no" if reason is None else "yes"}]


class PriceGuard:
    def __init__(self, inventory="inventory.json"):
        with open(inventory, encoding="utf-8") as f:
            self.inventory = json.load(f)

    def __call__(self, item):
        return step(item, self.inventory)
