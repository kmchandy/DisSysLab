"""
---
emits: whether the room is both too hot and too humid
in: temp, humidity
out: alert (yes | no)
---
Arguments: max_temp (default 80), max_humidity (default 60).
"""


def step(item, settings):
    hot = item["temp"] > settings["max_temp"]
    humid = item["humidity"] > settings["max_humidity"]
    return {"alert": "yes" if hot and humid else "no"}


class Checker:
    def __init__(self, max_temp=80, max_humidity=60):
        self.settings = {"max_temp": max_temp, "max_humidity": max_humidity}

    def __call__(self, item):
        return step(item, self.settings)
