"""
---
emits: books a sale, one line per sale
in: vehicle (tahoe | trax), price (number, >= 20000)
---
"""
import json


class Booking:
    def __call__(self, msg):
        with open("sales.jsonl", "a") as f:
            f.write(json.dumps(msg) + "\n")
