"""
---
emits: a stand-in Sal for tests: books the last price named, whenever the customer says "book"
in: text, history
out: reply (text), book (yes | no), vehicle (tahoe | silverado | equinox | trax | malibu | none), price (number, >= 0), buyer
---
"""
import re


class Salesperson:
    def __call__(self, item):
        text = item["text"].lower()
        car = next((c for c in ("tahoe", "silverado", "equinox", "trax", "malibu") if c in text), "none")
        prices = [float(p.replace(",", "")) for p in re.findall(r"\$(\d[\d,]*)", item["text"])]
        if car == "none" or not prices or "book" not in text:
            return {"reply": "Happy to help!", "book": "no", "vehicle": "none", "price": 0, "buyer": "customer"}
        return {"reply": f"Deal at ${prices[-1]:,.0f}!", "book": "yes", "vehicle": car,
                "price": prices[-1], "buyer": "X"}
